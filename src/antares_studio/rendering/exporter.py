"""Pipeline d'export vidéo (master prompt §7.2).

Plan → frames QImage → FFmpeg → ffprobe → remplacement atomique. Sans dépendance à l'interface :
la progression passe par des callbacks et l'annulation par ``threading.Event``.
Nécessite une ``QGuiApplication`` existante (polices) ; peut s'exécuter dans un thread secondaire.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from antares_studio.audio.subtitles import format_srt
from antares_studio.domain.model import Project
from antares_studio.domain.validation import ProjectValidationError, validate_project
from antares_studio.persistence.schema import project_to_dict
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.plan import AudioClipPlan, RenderPlan, RenderProfile, build_render_plan
from antares_studio.rendering.qt_painter import AssetResolver, ImageCache
from antares_studio.rendering.transitions import FrameRenderer
from antares_studio.resources.licenses import credits_lines

ProgressCallback = Callable[[int, int], None]


class RenderCancelledError(RuntimeError):
    pass


class RenderError(RuntimeError):
    def __init__(self, message: str, details: str = ""):
        super().__init__(message)
        self.details = details


@dataclass(frozen=True)
class RenderResult:
    output_path: Path
    manifest_path: Path
    probe: ff.ProbeResult
    elapsed_seconds: float
    plan: RenderPlan


# Atténuation de la musique sous la voix : compresseur déclenché par la narration (≈ -15 dB pendant
# la parole, retour en 0,35 s). Seuils choisis pour une voix normalisée autour de -20 dBFS.
DUCKING_FILTER = "sidechaincompress=threshold=0.02:ratio=12:attack=15:release=350:makeup=1"
# Volume normalisé (EBU R128) : −14 LUFS intégrés, comme YouTube et Spotify ; crêtes vraies ≤ −1,5 dBTP.
# loudnorm suréchantillonne en interne : retour explicite à 48 kHz.
LOUDNESS_FILTER = "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"


def _build_ffmpeg_command(ffmpeg: Path, plan: RenderPlan, tmp_output: Path) -> list[str]:
    profile = plan.profile
    rate = plan.output_fps
    cmd = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    first_audio = 0
    if profile.has_video:
        cmd += [
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{plan.width}x{plan.height}",
            "-r",
            f"{rate.numerator}/{rate.denominator}",
            "-i",
            "pipe:0",
        ]
        first_audio = 1
    video_map = ["-map", "0:v:0"] if profile.has_video else []
    filters: list[str] = []
    labels: list[str] = []
    roles: list[str] = []
    for i, clip in enumerate(plan.audio):
        cmd += ["-i", clip.path]
        idx = i + first_audio
        chain = [f"[{idx}:a]"]
        parts: list[str] = []
        if clip.in_seconds > 0 or clip.out_seconds is not None:
            trim = f"atrim=start={clip.in_seconds:.6f}"
            if clip.out_seconds is not None:
                trim += f":end={clip.out_seconds:.6f}"
            parts += [trim, "asetpts=PTS-STARTPTS"]
        if clip.fade_in_seconds > 0:
            parts.append(f"afade=t=in:st=0:d={clip.fade_in_seconds:.6f}")
        if clip.fade_out_seconds > 0 and clip.out_seconds is not None:
            length = clip.out_seconds - clip.in_seconds
            parts.append(
                f"afade=t=out:st={max(0.0, length - clip.fade_out_seconds):.6f}:d={clip.fade_out_seconds:.6f}"
            )
        if clip.gain != 1.0:
            parts.append(f"volume={clip.gain:.6f}")
        delay_ms = int(round(clip.offset_frames * plan.fps_den / plan.fps_num * 1000))
        if delay_ms > 0:
            parts.append(f"adelay={delay_ms}|{delay_ms}")
        parts.append("aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo")
        filters.append("".join(chain) + ",".join(parts) + f"[a{idx}]")
        labels.append(f"[a{idx}]")
        roles.append(clip.role)
    if labels:
        voices = [lab for lab, r in zip(labels, roles, strict=True) if r == "voice"]
        music = [lab for lab, r in zip(labels, roles, strict=True) if r == "music"]
        if plan.ducking and voices and music:
            others = [lab for lab, r in zip(labels, roles, strict=True) if r not in ("voice", "music")]
            filters.append("".join(voices) + f"amix=inputs={len(voices)}:normalize=0:duration=longest[voix]")
            filters.append("[voix]asplit=2[voixsortie][voixcmd];[voixcmd]apad[voixcmdp]")
            filters.append("".join(music) + f"amix=inputs={len(music)}:normalize=0:duration=longest[musique]")
            filters.append(f"[musique][voixcmdp]{DUCKING_FILTER}[musiquebasse]")
            labels = ["[voixsortie]", "[musiquebasse]", *others]
        # la vidéo est maître : l'audio est complété par du silence (apad) puis coupé à la durée (-t)
        level = f"{LOUDNESS_FILTER}," if plan.loudness else ""
        mix = (
            "".join(labels)
            + f"amix=inputs={len(labels)}:normalize=0:duration=longest[mix];[mix]{level}apad[aout]"
        )
        filters.append(mix)
        cmd += ["-filter_complex", ";".join(filters), *video_map, "-map", "[aout]"]
        cmd += profile.ffmpeg_audio_args()
    elif plan.silent_audio:
        # piste silencieuse : toutes les scènes d'un export complet ont la même structure de flux
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        cmd += [*video_map, "-map", f"{first_audio}:a:0", *profile.ffmpeg_audio_args()]
    if profile.has_video:
        cmd += profile.ffmpeg_video_args(plan.transparent)
    cmd += ["-t", f"{plan.duration_seconds:.6f}", "-f", profile.container, str(tmp_output)]
    return cmd


def audio_plans_for_scene(
    project: Project, scene_id: str, assets: AssetResolver | None
) -> tuple[AudioClipPlan, ...]:
    """Convertit les clips audio de la scène en entrées de plan (fichiers résolus, clips muets ignorés)."""
    scene = project.scene(scene_id)
    plans: list[AudioClipPlan] = []
    for clip in scene.audio:
        if clip.muted or clip.gain <= 0.0:
            continue
        path = assets(clip.asset_id) if assets else None
        if path is None:
            raise RenderError(f"Fichier audio introuvable pour le clip « {clip.name or clip.id} ».")
        plans.append(
            AudioClipPlan(
                path=str(path),
                offset_frames=clip.offset_frames,
                gain=clip.gain,
                in_seconds=clip.in_seconds,
                out_seconds=clip.out_seconds,
                fade_in_seconds=clip.fade_in_seconds,
                fade_out_seconds=clip.fade_out_seconds,
                role=clip.role,
            )
        )
    return tuple(plans)


def _frame_bytes(renderer: FrameRenderer, plan: RenderPlan, frame: int) -> bytes:
    """Image ``frame`` de la scène au format du plan (bandes noires si ``content_rect``)."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QImage, QPainter

    if plan.content_rect is None:
        img = renderer.render(plan.scene_id, frame, plan.width, plan.height)
    else:
        x, y, w, h = plan.content_rect
        inner = renderer.render(plan.scene_id, frame, w, h)
        img = QImage(plan.width, plan.height, QImage.Format.Format_RGBA8888)
        img.fill(QColor(0, 0, 0))
        p = QPainter(img)
        p.drawImage(QRectF(x, y, w, h), inner)
        p.end()
    if img.format() != QImage.Format.Format_RGBA8888:
        img = img.convertToFormat(QImage.Format.Format_RGBA8888)  # FFmpeg attend un alpha non prémultiplié
    data = bytes(img.constBits())
    if len(data) != plan.width * plan.height * 4:
        raise RenderError("taille d'image inattendue (stride non contigu)")
    return data


def export_video(
    project: Project,
    plan: RenderPlan,
    progress: ProgressCallback | None = None,
    cancel: threading.Event | None = None,
    assets: AssetResolver | None = None,
    ffmpeg_path: str | None = None,
    write_manifest: bool = True,
) -> RenderResult:
    """Exécute le plan de rendu et retourne le résultat vérifié par ffprobe."""
    issues = validate_project(project)
    if issues:
        raise ProjectValidationError(issues)
    ffmpeg = ff.require_ffmpeg(ffmpeg_path)
    ffprobe = ff.find_ffprobe(ffmpeg=ffmpeg)
    if ffprobe is None:
        raise ff.FFmpegNotFoundError(
            "ffprobe est introuvable à côté de FFmpeg ; l'export ne peut pas être vérifié."
        )
    _check_encoders(ffmpeg, plan.profile)
    output = Path(plan.output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    _check_free_space(output.parent, plan)
    for clip in plan.audio:
        if not Path(clip.path).is_file():
            raise RenderError(f"Fichier audio introuvable : {clip.path}")
    if plan.profile.is_sequence:
        return _export_sequence(
            project, plan, output, progress, cancel, assets, ffmpeg, ffprobe, write_manifest
        )

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{output.stem}-", suffix=f".{plan.profile.container}.part", dir=output.parent
    )
    os.close(fd)
    tmp_output = Path(tmp_name)
    cancel = cancel or threading.Event()
    encoder = ff.FrameEncoder(_build_ffmpeg_command(ffmpeg, plan, tmp_output))
    t0 = time.perf_counter()
    renderer = FrameRenderer(project, assets, ImageCache(), transparent=plan.transparent)
    try:
        encoder.start()
        total = plan.total_frames if plan.profile.has_video else 0
        for i in range(total):
            if cancel.is_set():
                raise RenderCancelledError("export annulé")
            encoder.write(_frame_bytes(renderer, plan, plan.start_frame + i * plan.frame_step))
            if progress:
                progress(i + 1, total)
        if cancel.is_set():
            raise RenderCancelledError("export annulé")
        rc = encoder.finish()
        if rc != 0:
            raise RenderError(f"FFmpeg a échoué (code {rc}).", encoder.stderr_text())
        if progress and not total:
            progress(1, 1)
        result = ff.probe(ffprobe, tmp_output, require_video=plan.profile.has_video)
        _verify(result, plan)
        os.replace(tmp_output, output)
    except RenderCancelledError:
        encoder.abort()
        _cleanup(tmp_output)
        raise
    except BaseException as exc:
        encoder.abort()
        _cleanup(tmp_output)
        if isinstance(exc, RenderError | ff.FFmpegError | ProjectValidationError):
            raise
        raise RenderError(f"Erreur pendant l'export : {exc}", encoder.stderr_text()) from exc
    elapsed = time.perf_counter() - t0
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    _write_companions(project, plan, output)
    if write_manifest:
        _write_manifest(
            manifest_path, project, plan, result, elapsed, ffmpeg, ffprobe, credits_lines(project)
        )
    return RenderResult(output, manifest_path, result, elapsed, plan)


def _write_companions(project: Project, plan: RenderPlan, output: Path) -> None:
    """Sous-titres SRT (sauf bande-son seule) et crédits, à côté du fichier exporté."""
    scene = project.scene(plan.scene_id)
    if scene.subtitles and plan.profile.has_video:
        # fichier SRT compagnon (les sous-titres sont aussi incrustés dans l'image)
        srt_path = output.with_suffix(".srt")
        shifted = [s for s in scene.subtitles if s.end_frame > plan.start_frame]
        from antares_studio.domain.model import Subtitle

        rel = [
            Subtitle(s.id, max(0, s.start_frame - plan.start_frame), s.end_frame - plan.start_frame, s.text)
            for s in shifted
        ]
        srt_path.write_text(format_srt(rel, project.canvas.fps), encoding="utf-8")
    credits = credits_lines(project)
    # crédits et attributions à côté de la vidéo (master prompt §9.1) ; même base que la scène « Crédits »
    output.with_suffix(".credits.txt").write_text("\n".join(credits) + "\n", encoding="utf-8")


SEQUENCE_PATTERN = "image_{:05d}.png"
SEQUENCE_AUDIO = "bande-son.wav"


def _export_sequence(
    project: Project,
    plan: RenderPlan,
    output: Path,
    progress: ProgressCallback | None,
    cancel: threading.Event | None,
    assets: AssetResolver | None,
    ffmpeg: Path,
    ffprobe: Path,
    write_manifest: bool,
) -> RenderResult:
    """Séquence PNG : un dossier ``image_00000.png…`` (transparence possible) et, si la scène a du son,
    la bande-son en WAV à côté des images. Le dossier est écrit à part puis mis en place d'un coup."""
    from PySide6.QtGui import QImage

    if output.exists() and (
        not output.is_dir() or any(p.suffix not in (".png", ".wav") for p in output.iterdir())
    ):
        # jamais d'écrasement d'un dossier qui contient autre chose qu'une séquence exportée
        raise RenderError(
            f"{output} existe déjà et n'est pas une séquence d'images : choisissez un autre nom."
        )
    cancel = cancel or threading.Event()
    tmp = Path(tempfile.mkdtemp(prefix=f".{output.name}-", suffix=".part", dir=output.parent))
    t0 = time.perf_counter()
    renderer = FrameRenderer(project, assets, ImageCache(), transparent=plan.transparent)
    total = plan.total_frames
    try:
        for i in range(total):
            if cancel.is_set():
                raise RenderCancelledError("export annulé")
            img = renderer.render(
                plan.scene_id, plan.start_frame + i * plan.frame_step, plan.width, plan.height
            )
            img = img.convertToFormat(
                QImage.Format.Format_RGBA8888 if plan.transparent else QImage.Format.Format_RGB888
            )
            if not img.save(str(tmp / SEQUENCE_PATTERN.format(i))):  # format déduit de l'extension .png
                raise RenderError(f"Impossible d'écrire l'image {i} dans {tmp}.")
            if progress:
                progress(i + 1, total)
        written = sorted(tmp.glob("image_*.png"))
        check = QImage(str(written[-1])) if written else QImage()
        if len(written) != total or (check.width(), check.height()) != (plan.width, plan.height):
            raise RenderError(f"Séquence incomplète : {len(written)} images au lieu de {total}.")
        if plan.audio:
            sound = dataclasses.replace(
                plan, profile_id="audio_wav", output_path=str(tmp / SEQUENCE_AUDIO), silent_audio=False
            )
            cmd = _build_ffmpeg_command(ffmpeg, sound, tmp / SEQUENCE_AUDIO)
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=3600, check=False, creationflags=ff._NO_WINDOW
            )
            if proc.returncode != 0:
                raise RenderError(f"FFmpeg a échoué sur la bande-son (code {proc.returncode}).", proc.stderr)
        old = None
        if output.exists():
            old = output.with_name(f".{output.name}-ancien")
            shutil.rmtree(old, ignore_errors=True)
            os.replace(output, old)
        os.replace(tmp, output)
        if old is not None:
            shutil.rmtree(old, ignore_errors=True)
    except BaseException as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        if isinstance(exc, RenderError | RenderCancelledError | ff.FFmpegError):
            raise
        raise RenderError(f"Erreur pendant l'export : {exc}") from exc
    elapsed = time.perf_counter() - t0
    result = ff.ProbeResult(
        width=plan.width,
        height=plan.height,
        fps=plan.output_fps,
        nb_frames=total,
        duration=plan.duration_seconds,
        video_codec="png",
        has_audio=bool(plan.audio),
    )
    manifest_path = output.with_name(output.name + ".manifest.json")
    _write_companions(project, plan, output.with_name(output.name + ".png"))
    if write_manifest:
        _write_manifest(
            manifest_path, project, plan, result, elapsed, ffmpeg, ffprobe, credits_lines(project)
        )
    return RenderResult(output, manifest_path, result, elapsed, plan)


@dataclass(frozen=True)
class ProjectRenderResult:
    output_path: Path
    manifest_path: Path
    probe: ff.ProbeResult
    elapsed_seconds: float
    plans: tuple[RenderPlan, ...]


def export_project(
    project: Project,
    profile_id: str,
    output_path: str,
    progress: ProgressCallback | None = None,
    cancel: threading.Event | None = None,
    assets: AssetResolver | None = None,
    ffmpeg_path: str | None = None,
    scene_ids: list[str] | None = None,
    transparent: bool = False,
) -> ProjectRenderResult:
    """Exporte les scènes à la suite (vidéo complète) : rendu par scène puis enchaînement sans ré-encodage.

    Chaque scène est rendue avec le même profil et une piste audio (silence si besoin) ; FFmpeg concatène
    les fichiers (démultiplexeur ``concat``, ``-c copy``), le résultat est vérifié (somme des images),
    les sous-titres sont fusionnés avec décalage et les crédits écrits à côté.
    """
    from antares_studio.domain.model import Subtitle

    ids = scene_ids or [s.id for s in project.scenes]
    if not ids:
        raise RenderError("le projet ne contient aucune scène")
    from antares_studio.rendering.plan import PROFILES

    if PROFILES[profile_id].is_sequence:
        raise RenderError(
            "La séquence PNG s'exporte scène par scène (un dossier d'images par scène) : décochez "
            "« Toutes les scènes à la suite »."
        )
    ffmpeg = ff.require_ffmpeg(ffmpeg_path)
    ffprobe = ff.find_ffprobe(ffmpeg=ffmpeg)
    if ffprobe is None:
        raise ff.FFmpegNotFoundError(
            "ffprobe est introuvable à côté de FFmpeg ; l'export ne peut pas être vérifié."
        )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cancel = cancel or threading.Event()
    t0 = time.perf_counter()
    plans: list[RenderPlan] = []
    for sid in ids:
        audio = audio_plans_for_scene(project, sid, assets)
        plans.append(
            build_render_plan(
                project, sid, profile_id, "", audio=audio, silent_audio=not audio, transparent=transparent
            )
        )
    total = sum(p.total_frames for p in plans)
    done = 0
    merged: list[Subtitle] = []
    offset = 0
    with tempfile.TemporaryDirectory(prefix=".antares-export-", dir=output.parent) as tmpdir:
        tmp = Path(tmpdir)
        parts: list[Path] = []
        for i, plan in enumerate(plans):
            part = tmp / f"scene-{i:03d}.{plan.profile.container}"
            plan_i = dataclasses.replace(plan, output_path=str(part))
            base = done

            def cb(k: int, _n: int, base: int = base) -> None:
                if progress:
                    progress(base + k, total)

            export_video(
                project,
                plan_i,
                progress=cb,
                cancel=cancel,
                assets=assets,
                ffmpeg_path=ffmpeg_path,
                write_manifest=False,
            )
            parts.append(part)
            done += plan.total_frames
            scene = project.scene(plan.scene_id)
            for s in scene.subtitles:
                if s.end_frame > plan.start_frame:
                    merged.append(
                        Subtitle(
                            s.id,
                            offset + max(0, s.start_frame - plan.start_frame),
                            offset + min(plan.total_frames, s.end_frame - plan.start_frame),
                            s.text,
                        )
                    )
            offset += plan.total_frames
        if cancel.is_set():
            raise RenderCancelledError("export annulé")
        listing = tmp / "concat.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{output.stem}-", suffix=f".{plans[0].profile.container}.part", dir=output.parent
        )
        os.close(fd)
        tmp_output = Path(tmp_name)
        cmd = [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            *_concat_args(plans[0].profile),
            "-f",
            plans[0].profile.container,
            str(tmp_output),
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600, check=False, creationflags=ff._NO_WINDOW
        )
        if proc.returncode != 0:
            _cleanup(tmp_output)
            raise RenderError(
                f"FFmpeg a échoué lors de l'enchaînement (code {proc.returncode}).", proc.stderr
            )
        has_video = plans[0].profile.has_video
        result = ff.probe(ffprobe, tmp_output, require_video=has_video)
        problems = []
        if has_video and result.nb_frames != total:
            problems.append(f"{result.nb_frames} images au lieu de {total}")
        if (result.width, result.height) != (plans[0].width, plans[0].height):
            problems.append("résolution inattendue")
        expected = sum(p.duration_seconds for p in plans)
        if not has_video and abs(result.duration - expected) > 0.1 * len(plans):
            problems.append(f"durée {result.duration:.2f} s au lieu de {expected:.2f} s")
        if plans[0].profile.has_audio and not result.has_audio:
            problems.append("piste audio absente")
        if problems:
            _cleanup(tmp_output)
            raise RenderError("La vidéo complète ne correspond pas au plan : " + " ; ".join(problems))
        os.replace(tmp_output, output)
    elapsed = time.perf_counter() - t0
    if merged:
        output.with_suffix(".srt").write_text(format_srt(merged, project.canvas.fps), encoding="utf-8")
    credits = credits_lines(project)
    output.with_suffix(".credits.txt").write_text("\n".join(credits) + "\n", encoding="utf-8")
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest: dict[str, Any] = {
        "software": "ANTARES Studio",
        "software_version": plans[0].software_version,
        "created_at": plans[0].created_at,
        "profile_id": profile_id,
        "scenes": [
            {
                "scene_id": p.scene_id,
                "scene_name": p.scene_name,
                "frames": p.total_frames,
                "audio_clips": len(p.audio),
            }
            for p in plans
        ],
        "tools": {"ffmpeg": ff.tool_version(ffmpeg), "ffprobe": ff.tool_version(ffprobe)},
        "result": {
            "width": result.width,
            "height": result.height,
            "fps": str(result.fps),
            "nb_frames": result.nb_frames,
            "duration": result.duration,
            "video_codec": result.video_codec,
            "has_audio": result.has_audio,
            "elapsed_seconds": round(elapsed, 3),
        },
        "warnings": [w for p in plans for w in p.warnings],
        "credits": credits,
        "scientific_metadata": project.scientific_metadata,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return ProjectRenderResult(output, manifest_path, result, elapsed, tuple(plans))


def _concat_args(profile: RenderProfile) -> list[str]:
    """Enchaînement des scènes : copie des flux, sauf GIF (palette commune recalculée sur l'ensemble)."""
    if profile.container == "gif":
        return profile.ffmpeg_video_args()
    args = ["-c", "copy"]
    if profile.container == "mp4":
        args += ["-movflags", "+faststart"]
    return args


def _check_encoders(ffmpeg: Path, profile: RenderProfile) -> None:
    video = [profile.video_codec] if profile.has_video and not profile.is_sequence else []  # PNG : par Qt
    needed = video + ([profile.audio_codec] if profile.has_audio else [])
    for codec in needed:
        if not ff.has_encoder(ffmpeg, codec):
            raise RenderError(
                f"L'encodeur « {codec} » est absent de votre FFmpeg. "
                "Installez un FFmpeg complet (libx264, libvpx-vp9, libopus, libmp3lame, prores_ks) ou "
                "choisissez un autre profil."
            )


def _verify(result: ff.ProbeResult, plan: RenderPlan) -> None:
    problems = []
    if not plan.profile.has_video:
        # bande-son seule : durée de la scène, à une trame audio près (MP3 : ~26 ms de remplissage)
        if not result.has_audio:
            problems.append("piste audio absente")
        elif abs(result.duration - plan.duration_seconds) > 0.1:
            problems.append(f"durée {result.duration:.2f} s au lieu de {plan.duration_seconds:.2f} s")
        if problems:
            raise RenderError("Le fichier exporté ne correspond pas au plan : " + " ; ".join(problems))
        return
    if (result.width, result.height) != (plan.width, plan.height):
        problems.append(f"résolution {result.width}x{result.height} au lieu de {plan.width}x{plan.height}")
    if result.nb_frames != plan.total_frames:
        problems.append(f"{result.nb_frames} images au lieu de {plan.total_frames}")
    rate = plan.output_fps
    # GIF : délais en centièmes de seconde, la cadence relue est arrondie (vérifiée sur la durée)
    if plan.profile.container != "gif" and result.fps != rate:
        problems.append(f"cadence {result.fps} au lieu de {rate}")
    if (plan.audio or plan.silent_audio) and not result.has_audio:
        problems.append("piste audio absente")
    if problems:
        raise RenderError("Le fichier exporté ne correspond pas au plan : " + " ; ".join(problems))


def _check_free_space(folder: Path, plan: RenderPlan) -> None:
    try:
        usage = shutil.disk_usage(folder)
    except OSError:
        return
    # estimation prudente, ×4 de marge, minimum 50 Mo : 2 Mo/s à 1080p crf 18, ProRes ~30 Mo/s,
    # PNG ~3 Mo par image ; proportionnelle au nombre de pixels
    profile = plan.profile
    pixels = max(1.0, plan.width * plan.height / (1920 * 1080))
    if profile.is_sequence:
        rate = 3.0 * float(plan.output_fps) * pixels
    elif profile.video_codec == "prores_ks":
        rate = 30.0 * pixels
    elif not profile.has_video:
        rate = 0.2
    else:
        rate = 2.0 * pixels
    needed = max(50 * 1024 * 1024, int(plan.duration_seconds * rate * 1024 * 1024 * 4))
    if usage.free < needed:
        raise RenderError(
            f"Espace disque insuffisant dans {folder} : {usage.free // (1024 * 1024)} Mo libres, "
            f"au moins {needed // (1024 * 1024)} Mo recommandés."
        )


def _cleanup(tmp: Path, attempts: int = 20) -> None:
    """Supprime le fichier temporaire ; sous Windows, FFmpeg peut libérer le descripteur avec retard."""
    for i in range(attempts):
        try:
            if tmp.exists():
                tmp.unlink()
            return
        except OSError:
            if i == attempts - 1:
                return
            time.sleep(0.1)


def _write_manifest(
    path: Path,
    project: Project,
    plan: RenderPlan,
    result: ff.ProbeResult,
    elapsed: float,
    ffmpeg: Path,
    ffprobe: Path,
    credits: list[str] | None = None,
) -> None:
    scene = project.scene(plan.scene_id)
    scene_json = json.dumps(project_to_dict(project)["scenes"][project.scenes.index(scene)], sort_keys=True)
    manifest: dict[str, Any] = {
        "software": "ANTARES Studio",
        "software_version": plan.software_version,
        "created_at": plan.created_at,
        "plan": plan.to_dict(),
        "tools": {"ffmpeg": ff.tool_version(ffmpeg), "ffprobe": ff.tool_version(ffprobe)},
        "sources": {"scene_sha256": hashlib.sha256(scene_json.encode("utf-8")).hexdigest()},
        "result": {
            "width": result.width,
            "height": result.height,
            "fps": str(result.fps),
            "nb_frames": result.nb_frames,
            "duration": result.duration,
            "video_codec": result.video_codec,
            "has_audio": result.has_audio,
            "elapsed_seconds": round(elapsed, 3),
        },
        "warnings": list(plan.warnings),
        "credits": list(credits or []),
        "scientific_metadata": project.scientific_metadata,
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

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
from antares_studio.rendering.plan import AudioClipPlan, RenderPlan, build_render_plan
from antares_studio.rendering.qt_painter import AssetResolver, ImageCache, render_state_to_image
from antares_studio.resources.licenses import credits_lines
from antares_studio.timeline.evaluator import evaluate

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


def _build_ffmpeg_command(ffmpeg: Path, plan: RenderPlan, tmp_output: Path) -> list[str]:
    profile = plan.profile
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s",
        f"{plan.width}x{plan.height}",
        "-r",
        f"{plan.fps_num}/{plan.fps_den}",
        "-i",
        "pipe:0",
    ]
    filters: list[str] = []
    labels: list[str] = []
    for i, clip in enumerate(plan.audio):
        cmd += ["-i", clip.path]
        idx = i + 1
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
    if labels:
        # la vidéo est maître : l'audio est complété par du silence (apad) puis coupé à la durée (-t)
        mix = "".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest[mix];[mix]apad[aout]"
        filters.append(mix)
        cmd += ["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[aout]"]
        cmd += ["-c:a", profile.audio_codec, "-b:a", profile.audio_bitrate]
    elif plan.silent_audio:
        # piste silencieuse : toutes les scènes d'un export complet ont la même structure de flux
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", profile.audio_codec, "-b:a", profile.audio_bitrate]
    cmd += profile.ffmpeg_video_args()
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
            )
        )
    return tuple(plans)


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
    if not ff.has_encoder(ffmpeg, plan.profile.video_codec):
        raise RenderError(
            f"L'encodeur « {plan.profile.video_codec} » est absent de votre FFmpeg. "
            "Installez un FFmpeg incluant libx264 ou choisissez un autre profil."
        )
    output = Path(plan.output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    _check_free_space(output.parent, plan)
    for clip in plan.audio:
        if not Path(clip.path).is_file():
            raise RenderError(f"Fichier audio introuvable : {clip.path}")

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{output.stem}-", suffix=f".{plan.profile.container}.part", dir=output.parent
    )
    os.close(fd)
    tmp_output = Path(tmp_name)
    cancel = cancel or threading.Event()
    encoder = ff.FrameEncoder(_build_ffmpeg_command(ffmpeg, plan, tmp_output))
    t0 = time.perf_counter()
    cache = ImageCache()
    scene = project.scene(plan.scene_id)
    try:
        encoder.start()
        total = plan.total_frames
        frame_bytes = plan.width * plan.height * 4
        for i in range(total):
            if cancel.is_set():
                raise RenderCancelledError("export annulé")
            state = evaluate(project, scene.id, plan.start_frame + i)
            img = render_state_to_image(
                state,
                project.canvas,
                plan.width,
                plan.height,
                assets,
                cache,
                subtitle_style=project.subtitle_style,
            )
            data = bytes(img.constBits())
            if len(data) != frame_bytes:
                raise RenderError("taille d'image inattendue (stride non contigu)")
            encoder.write(data)
            if progress:
                progress(i + 1, total)
        rc = encoder.finish()
        if rc != 0:
            raise RenderError(f"FFmpeg a échoué (code {rc}).", encoder.stderr_text())
        result = ff.probe(ffprobe, tmp_output)
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
    if scene.subtitles:
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
    if write_manifest:
        _write_manifest(manifest_path, project, plan, result, elapsed, ffmpeg, ffprobe, credits)
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
        plans.append(build_render_plan(project, sid, profile_id, "", audio=audio, silent_audio=not audio))
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
            "-c",
            "copy",
            "-movflags",
            "+faststart",
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
        result = ff.probe(ffprobe, tmp_output)
        problems = []
        if result.nb_frames != total:
            problems.append(f"{result.nb_frames} images au lieu de {total}")
        if (result.width, result.height) != (plans[0].width, plans[0].height):
            problems.append("résolution inattendue")
        if not result.has_audio:
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


def _verify(result: ff.ProbeResult, plan: RenderPlan) -> None:
    problems = []
    if (result.width, result.height) != (plan.width, plan.height):
        problems.append(f"résolution {result.width}x{result.height} au lieu de {plan.width}x{plan.height}")
    if result.nb_frames != plan.total_frames:
        problems.append(f"{result.nb_frames} images au lieu de {plan.total_frames}")
    if result.fps.numerator * plan.fps_den != plan.fps_num * result.fps.denominator:
        problems.append(f"cadence {result.fps} au lieu de {plan.fps_num}/{plan.fps_den}")
    if (plan.audio or plan.silent_audio) and not result.has_audio:
        problems.append("piste audio absente")
    if problems:
        raise RenderError("Le fichier exporté ne correspond pas au plan : " + " ; ".join(problems))


def _check_free_space(folder: Path, plan: RenderPlan) -> None:
    try:
        usage = shutil.disk_usage(folder)
    except OSError:
        return
    # estimation prudente : 2 Mo/s à 1080p crf 18, ×4 de marge, minimum 50 Mo
    needed = max(50 * 1024 * 1024, int(plan.duration_seconds * 2 * 1024 * 1024 * 4))
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

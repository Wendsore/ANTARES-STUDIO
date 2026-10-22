"""Plan de rendu immuable (master prompt §7.2 étape 2) et profils d'export."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from fractions import Fraction
from typing import Any

from antares_studio import __version__
from antares_studio.domain.model import Canvas, Project
from antares_studio.resources.licenses import provenance_warnings


@dataclass(frozen=True)
class RenderProfile:
    """Profil d'export. ``fixed_frame`` : cadre imposé par une plateforme (bandes noires si le format du
    projet diffère) ; sinon le petit côté du profil s'applique au format du projet (``output_size``)."""

    id: str
    label: str
    width: int
    height: int
    video_codec: str = "libx264"
    crf: int = 18
    preset: str = "medium"
    pixel_format: str = "yuv420p"
    audio_codec: str = "aac"
    audio_bitrate: str = "160k"
    container: str = "mp4"
    fixed_frame: bool = False
    max_fps: float | None = None  # GIF : images sautées pour rester sous cette cadence
    extension: str = ""  # extension du fichier (par défaut : celle du conteneur)
    group: str = "Usage"
    alpha: bool = False  # transparence possible (ProRes 4444, séquence PNG)
    prores_profile: str = ""  # ProRes : « 3 » (422 HQ) ou « 4 » (4444)

    @property
    def has_audio(self) -> bool:
        return self.container not in ("gif", "png")

    @property
    def has_video(self) -> bool:
        return self.container not in AUDIO_CONTAINERS

    @property
    def is_sequence(self) -> bool:
        """Séquence d'images : un dossier de PNG numérotés au lieu d'un fichier vidéo."""
        return self.container == "png"

    @property
    def suffix(self) -> str:
        if self.is_sequence:
            return ""  # un dossier
        return "." + (self.extension or self.container)

    def ffmpeg_audio_args(self) -> list[str]:
        args = ["-c:a", self.audio_codec]
        if not self.audio_codec.startswith("pcm_"):
            args += ["-b:a", self.audio_bitrate]
        return args

    def ffmpeg_video_args(self, transparent: bool = False) -> list[str]:
        if self.video_codec == "prores_ks":
            args = ["-c:v", "prores_ks", "-profile:v", self.prores_profile, "-vendor", "apl0"]
            if self.alpha and transparent:
                return [*args, "-pix_fmt", "yuva444p10le", "-alpha_bits", "16"]
            return [*args, "-pix_fmt", self.pixel_format]
        if self.container == "gif":
            # palette optimisée pour chaque fichier : couleurs fidèles sans tramage grossier
            return [
                "-filter_complex",
                "[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse",
                "-loop",
                "0",
            ]
        if self.video_codec == "libvpx-vp9":
            return [
                "-c:v",
                "libvpx-vp9",
                "-b:v",
                "0",
                "-crf",
                str(self.crf),
                "-row-mt",
                "1",
                "-deadline",
                "good",
                "-cpu-used",
                "4",
                "-pix_fmt",
                self.pixel_format,
            ]
        args = [
            "-c:v",
            self.video_codec,
            "-preset",
            self.preset,
            "-crf",
            str(self.crf),
            "-pix_fmt",
            self.pixel_format,
        ]
        if self.container == "mp4":
            args += ["-movflags", "+faststart"]
        return args


AUDIO_CONTAINERS = ("wav", "mp3")

PROFILES: dict[str, RenderProfile] = {
    p.id: p
    for p in (
        RenderProfile("draft_720p", "Brouillon 720p (rapide)", 1280, 720, crf=28, preset="veryfast"),
        RenderProfile("final_1080p", "Final 1080p (qualité)", 1920, 1080, crf=18, preset="medium"),
        RenderProfile("final_1440p", "Final 1440p (QHD)", 2560, 1440, crf=18, preset="medium"),
        RenderProfile(
            "final_2160p", "Final 4K UHD 2160p (long à rendre)", 3840, 2160, crf=18, preset="medium"
        ),
        RenderProfile("mobile_720p", "Mobile 720p (fichier léger)", 1280, 720, crf=26, preset="slow"),
        RenderProfile("preview_360p", "Aperçu rapide 360p", 640, 360, crf=30, preset="ultrafast"),
        RenderProfile(
            "youtube_1080p", "YouTube, Vimeo (16:9)", 1920, 1080, crf=18, fixed_frame=True, group="Plateforme"
        ),
        RenderProfile(
            "vertical_1080x1920",
            "Shorts, Reels, TikTok (9:16)",
            1080,
            1920,
            crf=20,
            fixed_frame=True,
            group="Plateforme",
        ),
        RenderProfile("square_1080", "Carré (1:1)", 1080, 1080, crf=20, fixed_frame=True, group="Plateforme"),
        RenderProfile(
            "slides_4_3", "Présentation (4:3)", 1440, 1080, crf=18, fixed_frame=True, group="Plateforme"
        ),
        RenderProfile(
            "webm_1080p",
            "WebM VP9 + Opus (pages web, libre)",
            1920,
            1080,
            video_codec="libvpx-vp9",
            crf=32,
            audio_codec="libopus",
            audio_bitrate="128k",
            container="webm",
            group="Format",
        ),
        RenderProfile(
            "gif_480",
            "GIF animé 480p (sans son)",
            854,
            480,
            video_codec="gif",
            container="gif",
            max_fps=15.0,
            group="Format",
        ),
        RenderProfile(
            "prores_hq",
            "ProRes 422 HQ (montage, fichier lourd)",
            1920,
            1080,
            video_codec="prores_ks",
            prores_profile="3",
            pixel_format="yuv422p10le",
            audio_codec="pcm_s16le",
            container="mov",
            group="Montage",
        ),
        RenderProfile(
            "prores_4444",
            "ProRes 4444 avec transparence (incrustation)",
            1920,
            1080,
            video_codec="prores_ks",
            prores_profile="4",
            pixel_format="yuv444p10le",
            audio_codec="pcm_s16le",
            container="mov",
            alpha=True,
            group="Montage",
        ),
        RenderProfile(
            "png_sequence",
            "Séquence d'images PNG (dossier, sans son)",
            1920,
            1080,
            video_codec="png",
            container="png",
            alpha=True,
            group="Montage",
        ),
        RenderProfile(
            "audio_wav",
            "Bande-son seule WAV (sans perte)",
            0,
            0,
            video_codec="",
            audio_codec="pcm_s16le",
            container="wav",
            group="Audio",
        ),
        RenderProfile(
            "audio_mp3",
            "Bande-son seule MP3 (192 kb/s)",
            0,
            0,
            video_codec="",
            audio_codec="libmp3lame",
            audio_bitrate="192k",
            container="mp3",
            group="Audio",
        ),
    )
}


@dataclass(frozen=True)
class AudioClipPlan:
    path: str  # chemin absolu résolu
    offset_frames: int
    gain: float = 1.0
    in_seconds: float = 0.0
    out_seconds: float | None = None
    fade_in_seconds: float = 0.0
    fade_out_seconds: float = 0.0
    role: str = "voice"


@dataclass(frozen=True)
class RenderPlan:
    project_id: str
    scene_id: str
    scene_name: str
    profile_id: str
    width: int
    height: int
    fps_num: int
    fps_den: int
    start_frame: int
    end_frame: int  # exclusif
    output_path: str
    audio: tuple[AudioClipPlan, ...] = ()
    subtitles_path: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    software_version: str = __version__
    tool_versions: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    silent_audio: bool = False  # piste stéréo silencieuse si aucun clip (enchaînement de scènes homogène)
    content_rect: tuple[int, int, int, int] | None = None  # image utile dans le cadre (bandes noires)
    frame_step: int = 1  # 1 image sur N (GIF : cadence réduite)
    ducking: bool = True  # musique atténuée pendant la voix (si les deux sont présents)
    loudness: bool = True  # volume normalisé (EBU R128, −14 LUFS, crêtes ≤ −1,5 dBTP)
    transparent: bool = False  # fond de scène non peint (profils à canal alpha uniquement)

    @property
    def source_frames(self) -> int:
        """Images de la scène couvertes par le plan."""
        return max(0, self.end_frame - self.start_frame)

    @property
    def total_frames(self) -> int:
        """Images écrites dans le fichier (une sur ``frame_step``)."""
        return -(-self.source_frames // self.frame_step)

    @property
    def output_fps(self) -> Fraction:
        return Fraction(self.fps_num, self.fps_den * self.frame_step)

    @property
    def profile(self) -> RenderProfile:
        return PROFILES[self.profile_id]

    @property
    def duration_seconds(self) -> float:
        return float(self.total_frames / self.output_fps)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_frames"] = self.total_frames
        d["duration_seconds"] = self.duration_seconds
        return d


def output_size(profile: RenderProfile, canvas: Canvas) -> tuple[int, int]:
    """Dimensions de sortie : le petit côté du profil (720 ou 1080) appliqué au format du projet.

    Un projet 16:9 garde exactement les dimensions du profil ; un projet vertical 9:16 ou carré n'est
    plus étiré dans un cadre 16:9. Dimensions paires (exigence de H.264 en 4:2:0). Un profil de
    plateforme (``fixed_frame``) impose son cadre : voir ``content_rect``.
    """
    if profile.fixed_frame or not profile.has_video:
        return profile.width, profile.height
    short = min(profile.width, profile.height)
    cw, ch = canvas.width, canvas.height
    if cw >= ch:
        width, height = round(short * cw / ch), short
    else:
        width, height = short, round(short * ch / cw)
    return width + width % 2, height + height % 2


def content_rect(profile: RenderProfile, canvas: Canvas) -> tuple[int, int, int, int] | None:
    """Zone (x, y, largeur, hauteur) de l'image du projet dans un cadre imposé ; None si elle le remplit.

    L'image est réduite sans déformation et centrée ; le reste du cadre est noir.
    """
    if not profile.fixed_frame:
        return None
    fw, fh = profile.width, profile.height
    k = min(fw / canvas.width, fh / canvas.height)
    w, h = round(canvas.width * k), round(canvas.height * k)
    if abs(w - fw) <= 1 and abs(h - fh) <= 1:
        return None
    return (fw - w) // 2, (fh - h) // 2, w, h


def _ratio_label(w: int, h: int) -> str:
    from math import gcd

    g = gcd(w, h) or 1
    return f"{w // g}:{h // g}"


def build_render_plan(
    project: Project,
    scene_id: str,
    profile_id: str,
    output_path: str,
    start_frame: int = 0,
    end_frame: int | None = None,
    audio: tuple[AudioClipPlan, ...] = (),
    subtitles_path: str | None = None,
    tool_versions: dict[str, str] | None = None,
    silent_audio: bool = False,
    transparent: bool = False,
) -> RenderPlan:
    scene = project.scene(scene_id)
    profile = PROFILES[profile_id]
    end = scene.duration_frames if end_frame is None else min(end_frame, scene.duration_frames)
    start = max(0, start_frame)
    warnings: list[str] = []
    if end <= start:
        raise ValueError("la plage de rendu est vide (0 image)")
    if end - start > 10_000_000:
        raise ValueError("plage de rendu trop longue")
    width, height = output_size(profile, project.canvas)
    rect = content_rect(profile, project.canvas)
    if rect is not None:
        project_ratio = _ratio_label(project.canvas.width, project.canvas.height)
        warnings.append(
            f"Le projet est au format {project_ratio} et le profil « {profile.label} » attend "
            f"{_ratio_label(width, height)} : bandes noires ajoutées. Pour remplir le cadre, créez le "
            "projet à ce format."
        )
    step = 1
    if profile.max_fps is not None:
        fps = float(project.canvas.fps)
        while fps / step > profile.max_fps:
            step += 1
    if transparent and not profile.alpha:
        raise ValueError(f"le profil « {profile.label} » ne gère pas la transparence")
    if not profile.has_video:
        silent_audio = True  # bande-son seule : du silence plutôt qu'un fichier vide
    warnings.extend(provenance_warnings(project, scene_id))
    warnings.extend(subtitle_warnings(project, scene_id))
    return RenderPlan(
        project_id=project.project_id,
        scene_id=scene_id,
        scene_name=scene.name,
        profile_id=profile_id,
        width=width,
        height=height,
        fps_num=project.canvas.fps_num,
        fps_den=project.canvas.fps_den,
        start_frame=start,
        end_frame=end,
        output_path=output_path,
        subtitles_path=subtitles_path,
        tool_versions=dict(tool_versions or {}),
        warnings=tuple(warnings),
        silent_audio=silent_audio and profile.has_audio,
        content_rect=rect,
        frame_step=step,
        audio=audio if profile.has_audio else (),
        ducking=bool(project.settings.get("ducking", True)),
        loudness=bool(project.settings.get("loudnorm", True)),
        transparent=transparent,
    )


def subtitle_warnings(project: Project, scene_id: str) -> list[str]:
    """Sous-titres à revoir (lisibilité) et style peu contrasté, résumés pour le dialogue d'export."""
    from antares_studio.audio.subtitles import check_subtitle_style, check_subtitles

    scene = project.scene(scene_id)
    out: list[str] = []
    issues = check_subtitles(scene.subtitles, scene.duration_frames, project.canvas.fps)
    if issues:
        numbers = sorted({i.index + 1 for i in issues})
        shown = ", ".join(str(n) for n in numbers[:6]) + ("…" if len(numbers) > 6 else "")
        out.append(
            f"Scène « {scene.name} » : {len(numbers)} sous-titre(s) à revoir (n° {shown}) — "
            "voir Narration > Sous-titres."
        )
    if scene.subtitles:
        out.extend(check_subtitle_style(project.subtitle_style))
    return out

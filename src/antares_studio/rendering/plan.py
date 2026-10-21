"""Plan de rendu immuable (master prompt §7.2 étape 2) et profils d'export."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from antares_studio import __version__
from antares_studio.domain.model import Project
from antares_studio.resources.licenses import provenance_warnings


@dataclass(frozen=True)
class RenderProfile:
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

    def ffmpeg_video_args(self) -> list[str]:
        return [
            "-c:v",
            self.video_codec,
            "-preset",
            self.preset,
            "-crf",
            str(self.crf),
            "-pix_fmt",
            self.pixel_format,
            "-movflags",
            "+faststart",
        ]


PROFILES: dict[str, RenderProfile] = {
    p.id: p
    for p in (
        RenderProfile("draft_720p", "Brouillon 720p (rapide)", 1280, 720, crf=28, preset="veryfast"),
        RenderProfile("final_1080p", "Final 1080p (qualité)", 1920, 1080, crf=18, preset="medium"),
        RenderProfile("mobile_720p", "Mobile 720p (fichier léger)", 1280, 720, crf=26, preset="slow"),
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

    @property
    def total_frames(self) -> int:
        return max(0, self.end_frame - self.start_frame)

    @property
    def profile(self) -> RenderProfile:
        return PROFILES[self.profile_id]

    @property
    def duration_seconds(self) -> float:
        return self.total_frames * self.fps_den / self.fps_num

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_frames"] = self.total_frames
        d["duration_seconds"] = self.duration_seconds
        return d


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
    if profile.width / profile.height != project.canvas.width / project.canvas.height:
        warnings.append("Le ratio du profil d'export diffère de celui du projet : l'image sera étirée.")
    warnings.extend(provenance_warnings(project, scene_id))
    return RenderPlan(
        project_id=project.project_id,
        scene_id=scene_id,
        scene_name=scene.name,
        profile_id=profile_id,
        width=profile.width,
        height=profile.height,
        fps_num=project.canvas.fps_num,
        fps_den=project.canvas.fps_den,
        start_frame=start,
        end_frame=end,
        output_path=output_path,
        audio=audio,
        subtitles_path=subtitles_path,
        tool_versions=dict(tool_versions or {}),
        warnings=tuple(warnings),
        silent_audio=silent_audio,
    )

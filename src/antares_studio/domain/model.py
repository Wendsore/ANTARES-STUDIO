"""Modèle de projet pur (sans Qt) : projet, canevas, scènes, nœuds, pistes et keyframes.

Voir ADR-0002. Les valeurs sont des types JSON simples ; aucune logique d'interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from antares_studio.domain.ids import new_id

SCHEMA_VERSION = 1

Value = float | int | bool | str | list[float]

EASINGS: tuple[str, ...] = ("step", "linear", "ease_in", "ease_out", "ease_in_out")

# Style de sous-titres lisible sur téléphone : bande inférieure, fond semi-opaque, contour.
DEFAULT_SUBTITLE_STYLE: dict[str, Any] = {
    "font_family": "DejaVu Sans",
    "font_size_ratio": 0.045,  # fraction de la hauteur du canevas
    "color": "#FFFFFF",
    "background": "#000000A0",
    "outline": "#000000",
    "outline_width": 2.0,
    "bottom_margin_ratio": 0.08,
    "max_width_ratio": 0.86,
    "bold": False,
}


@dataclass
class Canvas:
    width: int = 1920
    height: int = 1080
    fps_num: int = 30
    fps_den: int = 1

    @property
    def fps(self) -> Fraction:
        return Fraction(self.fps_num, self.fps_den)

    def frame_to_seconds(self, frame: int) -> float:
        return float(Fraction(frame) / self.fps)

    def seconds_to_frame(self, seconds: float) -> int:
        return int(round(seconds * float(self.fps)))


@dataclass
class Keyframe:
    frame: int
    value: Value
    easing: str = "linear"


@dataclass
class Track:
    target_id: str
    property: str
    keyframes: list[Keyframe] = field(default_factory=list)

    def sorted_keyframes(self) -> list[Keyframe]:
        """Keyframes triées par frame ; en cas de doublon, la dernière déclarée gagne (ADR-0002 §5)."""
        by_frame: dict[int, Keyframe] = {}
        for kf in self.keyframes:
            by_frame[kf.frame] = kf
        return [by_frame[f] for f in sorted(by_frame)]

    def set_keyframe(self, frame: int, value: Value, easing: str = "linear") -> Keyframe:
        for kf in self.keyframes:
            if kf.frame == frame:
                kf.value = value
                kf.easing = easing
                return kf
        kf = Keyframe(frame=frame, value=value, easing=easing)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda k: k.frame)
        return kf

    def remove_keyframe(self, frame: int) -> bool:
        before = len(self.keyframes)
        self.keyframes = [kf for kf in self.keyframes if kf.frame != frame]
        return len(self.keyframes) != before


@dataclass
class Node:
    """Objet de scène. ``params`` dépend de ``kind`` (voir ``domain.kinds``)."""

    id: str
    kind: str
    name: str
    parent_id: str | None = None
    position: list[float] = field(default_factory=lambda: [0.0, 0.0])
    rotation_deg: float = 0.0
    scale: list[float] = field(default_factory=lambda: [1.0, 1.0])
    opacity: float = 1.0
    visible: bool = True
    locked: bool = False
    z_index: int = 0
    style: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, kind: str, name: str, **kwargs: Any) -> Node:
        return cls(id=new_id("node"), kind=kind, name=name, **kwargs)


@dataclass
class AudioClip:
    """Référence non destructive à une ressource audio (narration, musique) placée sur la timeline."""

    id: str
    asset_id: str
    name: str = ""
    offset_frames: int = 0
    gain: float = 1.0
    in_seconds: float = 0.0
    out_seconds: float | None = None  # None = jusqu'à la fin du fichier
    fade_in_seconds: float = 0.0
    fade_out_seconds: float = 0.0
    muted: bool = False
    duration_seconds: float = 0.0  # durée du fichier source, mesurée à l'import (informative)

    @classmethod
    def create(cls, asset_id: str, name: str = "", **kwargs: Any) -> AudioClip:
        return cls(id=new_id("audio"), asset_id=asset_id, name=name, **kwargs)


@dataclass
class Subtitle:
    id: str
    start_frame: int
    end_frame: int  # exclusif
    text: str

    @classmethod
    def create(cls, start_frame: int, end_frame: int, text: str) -> Subtitle:
        return cls(id=new_id("sub"), start_frame=start_frame, end_frame=end_frame, text=text)


@dataclass
class Scene:
    id: str
    name: str
    duration_frames: int = 300
    background: str = "#0B1020"
    nodes: list[Node] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=list)
    audio: list[AudioClip] = field(default_factory=list)
    subtitles: list[Subtitle] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, duration_frames: int = 300, **kwargs: Any) -> Scene:
        return cls(id=new_id("scene"), name=name, duration_frames=duration_frames, **kwargs)

    def node(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)

    def find_node(self, node_id: str) -> Node | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def children_of(self, parent_id: str | None) -> list[Node]:
        return [n for n in self.nodes if n.parent_id == parent_id]

    def track_for(self, target_id: str, prop: str) -> Track | None:
        return next((t for t in self.tracks if t.target_id == target_id and t.property == prop), None)

    def ensure_track(self, target_id: str, prop: str) -> Track:
        t = self.track_for(target_id, prop)
        if t is None:
            t = Track(target_id=target_id, property=prop)
            self.tracks.append(t)
        return t

    def tracks_for(self, target_id: str) -> list[Track]:
        return [t for t in self.tracks if t.target_id == target_id]

    def subtitle_at(self, frame: int) -> Subtitle | None:
        """Sous-titre actif à ``frame`` (le premier dans l'ordre de début en cas de chevauchement)."""
        active = [s for s in self.subtitles if s.start_frame <= frame < s.end_frame]
        if not active:
            return None
        return min(active, key=lambda s: (s.start_frame, s.id))

    def audio_clip(self, clip_id: str) -> AudioClip | None:
        return next((c for c in self.audio if c.id == clip_id), None)


@dataclass
class AssetLicense:
    author: str = ""
    source_url: str = ""
    license: str = ""
    attribution_required: bool = False
    redistribution_allowed: bool = False
    verified_on: str = ""


@dataclass
class Asset:
    id: str
    path: str  # chemin relatif à la racine du projet, séparateur '/'
    kind: str  # image | audio | svg | other
    sha256: str = ""
    license: AssetLicense = field(default_factory=AssetLicense)


@dataclass
class Project:
    project_id: str
    title: str
    schema_version: int = SCHEMA_VERSION
    locale: str = "fr-FR"
    canvas: Canvas = field(default_factory=Canvas)
    scenes: list[Scene] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    scientific_metadata: dict[str, Any] = field(
        default_factory=lambda: {"representation": "schematic", "to_scale": False, "sources": []}
    )
    settings: dict[str, Any] = field(default_factory=dict)

    @property
    def subtitle_style(self) -> dict[str, Any]:
        """Style des sous-titres (fusion des défauts et de ``settings['subtitle_style']``)."""
        style = dict(DEFAULT_SUBTITLE_STYLE)
        custom = self.settings.get("subtitle_style")
        if isinstance(custom, dict):
            style.update({k: v for k, v in custom.items() if k in DEFAULT_SUBTITLE_STYLE})
        return style

    @classmethod
    def create(cls, title: str, canvas: Canvas | None = None) -> Project:
        return cls(project_id=new_id("project"), title=title, canvas=canvas or Canvas())

    def scene(self, scene_id: str) -> Scene:
        for s in self.scenes:
            if s.id == scene_id:
                return s
        raise KeyError(scene_id)

    def find_scene(self, scene_id: str) -> Scene | None:
        return next((s for s in self.scenes if s.id == scene_id), None)

    def asset(self, asset_id: str) -> Asset | None:
        return next((a for a in self.assets if a.id == asset_id), None)

"""Presets d'animation du MVP : générateurs de keyframes paramétrables (master prompt §6.2).

Chaque preset retourne des ``Track`` prêtes à être posées sur un nœud. Les presets sont non destructifs :
ils ne lisent que les valeurs de base du nœud et ne modifient pas le projet eux-mêmes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from antares_studio.domain.model import Node, Track


@dataclass(frozen=True)
class PresetParam:
    name: str
    label: str
    type: str  # float | int | bool | choice
    default: Any
    min: float | None = None
    max: float | None = None
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class PresetSpec:
    id: str
    label: str
    description: str
    params: tuple[PresetParam, ...] = field(default_factory=tuple)

    def defaults(self) -> dict[str, Any]:
        return {p.name: p.default for p in self.params}


_COMMON = (
    PresetParam("start_frame", "Début (image)", "int", 0, min=0),
    PresetParam("duration_frames", "Durée (images)", "int", 60, min=1),
)
_EASING = PresetParam(
    "easing",
    "Interpolation",
    "choice",
    "ease_in_out",
    choices=("linear", "ease_in", "ease_out", "ease_in_out"),
)

PRESETS: dict[str, PresetSpec] = {
    s.id: s
    for s in (
        PresetSpec(
            "appear",
            "Apparition",
            "Fondu entrant de l'opacité de 0 vers la valeur actuelle.",
            _COMMON + (_EASING,),
        ),
        PresetSpec("disappear", "Disparition", "Fondu sortant de l'opacité vers 0.", _COMMON + (_EASING,)),
        PresetSpec(
            "translate",
            "Translation",
            "Déplacement de la position actuelle d'un vecteur (dx, dy).",
            _COMMON
            + (
                PresetParam("dx", "Déplacement X (px)", "float", 300.0),
                PresetParam("dy", "Déplacement Y (px)", "float", 0.0),
                _EASING,
            ),
        ),
        PresetSpec(
            "rotate",
            "Rotation",
            "Rotation autour du centre de l'objet. 360° = un tour complet, sans saut si bouclé.",
            _COMMON
            + (
                PresetParam("turns", "Nombre de tours", "float", 1.0),
                PresetParam("clockwise", "Sens horaire (à l'écran)", "bool", True),
                PresetParam(
                    "easing",
                    "Interpolation",
                    "choice",
                    "linear",
                    choices=("linear", "ease_in", "ease_out", "ease_in_out"),
                ),
            ),
        ),
        PresetSpec(
            "pulse",
            "Pulsation",
            "Variation d'échelle aller-retour répétée.",
            _COMMON
            + (
                PresetParam("amplitude", "Amplitude (0.2 = ±20 %)", "float", 0.2, min=0),
                PresetParam("repeats", "Répétitions", "int", 3, min=1),
            ),
        ),
        PresetSpec(
            "orbit",
            "Orbite schématique",
            "Mouvement circulaire uniforme autour d'un centre ; l'angle de départ fixe la phase initiale.",
            _COMMON
            + (
                PresetParam("center_x", "Centre X (px)", "float", 0.0),
                PresetParam("center_y", "Centre Y (px)", "float", 0.0),
                PresetParam("radius", "Rayon (px)", "float", 300.0, min=0),
                PresetParam("turns", "Nombre de tours", "float", 1.0),
                PresetParam("clockwise", "Sens horaire (à l'écran)", "bool", False),
                PresetParam("samples_per_turn", "Échantillons par tour", "int", 36, min=4, max=720),
                PresetParam("start_angle_deg", "Angle de départ (°)", "float", 0.0),
            ),
        ),
    )
}


def apply_preset(preset_id: str, node: Node, params: dict[str, Any] | None = None) -> list[Track]:
    """Construit les pistes d'un preset pour ``node`` ; ``ValueError`` si preset ou paramètre invalide."""
    spec = PRESETS.get(preset_id)
    if spec is None:
        raise ValueError(f"preset inconnu : {preset_id!r}")
    p = spec.defaults()
    p.update(params or {})
    start = int(p["start_frame"])
    dur = int(p["duration_frames"])
    if start < 0 or dur < 1:
        raise ValueError("début >= 0 et durée >= 1 requis")
    end = start + dur
    easing = str(p.get("easing", "linear"))
    tracks: list[Track] = []

    if preset_id == "appear":
        t = Track(node.id, "opacity")
        t.set_keyframe(start, 0.0, easing)
        t.set_keyframe(end, float(node.opacity), easing)
        tracks.append(t)
    elif preset_id == "disappear":
        t = Track(node.id, "opacity")
        t.set_keyframe(start, float(node.opacity), easing)
        t.set_keyframe(end, 0.0, easing)
        tracks.append(t)
    elif preset_id == "translate":
        tx = Track(node.id, "position.x")
        tx.set_keyframe(start, node.position[0], easing)
        tx.set_keyframe(end, node.position[0] + float(p["dx"]), easing)
        ty = Track(node.id, "position.y")
        ty.set_keyframe(start, node.position[1], easing)
        ty.set_keyframe(end, node.position[1] + float(p["dy"]), easing)
        tracks += [tx, ty]
    elif preset_id == "rotate":
        sign = 1.0 if bool(p["clockwise"]) else -1.0  # y vers le bas : +deg = horaire à l'écran
        t = Track(node.id, "rotation_deg")
        t.set_keyframe(start, node.rotation_deg, easing)
        t.set_keyframe(end, node.rotation_deg + sign * 360.0 * float(p["turns"]), easing)
        tracks.append(t)
    elif preset_id == "pulse":
        amp = float(p["amplitude"])
        reps = int(p["repeats"])
        sx, sy = node.scale
        tx, ty = Track(node.id, "scale.x"), Track(node.id, "scale.y")
        seg = dur / (2 * reps)
        for i in range(2 * reps + 1):
            f = start + int(round(i * seg))
            k = 1.0 + amp if i % 2 == 1 else 1.0
            tx.set_keyframe(f, sx * k, "ease_in_out")
            ty.set_keyframe(f, sy * k, "ease_in_out")
        tracks += [tx, ty]
    elif preset_id == "orbit":
        cx, cy, r = float(p["center_x"]), float(p["center_y"]), float(p["radius"])
        turns, n_per_turn = float(p["turns"]), int(p["samples_per_turn"])
        sign = 1.0 if bool(p["clockwise"]) else -1.0
        a0 = math.radians(float(p["start_angle_deg"]))
        # jamais plus d'échantillons que d'images : chaque clé tombe sur une frame distincte
        n = max(2, min(dur, int(round(n_per_turn * abs(turns)))))
        tx, ty = Track(node.id, "position.x"), Track(node.id, "position.y")
        for i in range(n + 1):
            u = i / n
            f = start + int(round(u * dur))
            a = a0 + sign * 2 * math.pi * turns * u
            tx.set_keyframe(f, cx + r * math.cos(a), "linear")
            ty.set_keyframe(f, cy + r * math.sin(a), "linear")
        tracks += [tx, ty]
    return tracks

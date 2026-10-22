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
        PresetSpec(
            "trace",
            "Tracer la courbe",
            "Dessine progressivement la courbe d'un graphique (progression 0 → 1).",
            _COMMON + (_EASING,),
        ),
        PresetSpec(
            "morph",
            "Transformer la formule",
            "Passe d'une équation à la formule cible (paramètre « Transformer en ») : les symboles communs "
            "glissent vers leur nouvelle place, les autres apparaissent en fondu.",
            _COMMON + (_EASING,),
        ),
        PresetSpec(
            "kepler",
            "Orbite de Kepler (modélisation)",
            "Ellipse képlérienne autour d'un corps placé au foyer (lois de Kepler, deux corps) ; "
            "solution analytique ou intégration numérique (Verlet) avec contrôle de l'énergie.",
            _COMMON
            + (
                PresetParam("focus_x", "Foyer X (px)", "float", 0.0),
                PresetParam("focus_y", "Foyer Y (px)", "float", 0.0),
                PresetParam("semi_major_px", "Demi-grand axe (px)", "float", 300.0, min=1),
                PresetParam("eccentricity", "Excentricité (0 ≤ e < 1)", "float", 0.5, min=0.0, max=0.99),
                PresetParam("periods", "Nombre de révolutions", "float", 1.0, min=0.01),
                PresetParam("clockwise", "Sens horaire (à l'écran)", "bool", False),
                PresetParam("periapsis_angle_deg", "Direction du périapse (°)", "float", 0.0),
                PresetParam("samples_per_period", "Échantillons par révolution", "int", 72, min=8, max=720),
                PresetParam("method", "Méthode", "choice", "analytique", choices=("analytique", "verlet")),
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
    elif preset_id == "trace":
        t = Track(node.id, "params.progress")
        t.set_keyframe(start, 0.0, easing)
        t.set_keyframe(end, 1.0, easing)
        tracks.append(t)
    elif preset_id == "morph":
        t = Track(node.id, "params.morph")
        t.set_keyframe(start, 0.0, easing)
        t.set_keyframe(end, 1.0, easing)
        tracks.append(t)
    elif preset_id == "kepler":
        tracks += _kepler_tracks(node, p, start, dur)
    return tracks


def _kepler_tracks(node: Node, p: dict[str, Any], start: int, dur: int) -> list[Track]:
    """Positions en pixels depuis ``science.kepler`` : le temps de la vidéo est proportionnel au temps
    physique (une révolution = ``dur / periods`` images) ; le foyer est fixe à l'écran."""
    from antares_studio.science.kepler import OrbitElements, position_at, simulate_elements

    a_px = float(p["semi_major_px"])
    elements = OrbitElements(a_px, float(p["eccentricity"]), mu=1.0)  # unités d'écran : μ arbitraire
    periods = float(p["periods"])
    n = max(2, min(dur, int(round(int(p["samples_per_period"]) * periods))))
    fx, fy = float(p["focus_x"]), float(p["focus_y"])
    theta = math.radians(float(p["periapsis_angle_deg"]))
    sign = 1.0 if bool(p["clockwise"]) else -1.0
    total_t = periods * elements.period
    if str(p["method"]) == "verlet":
        sim = simulate_elements(elements, steps=max(n * 50, 1000), periods=periods)
        samples = [sim.positions[int(round(i / n * (len(sim.positions) - 1)))] for i in range(n + 1)]
    else:
        samples = [position_at(elements, i / n * total_t) for i in range(n + 1)]
    tx, ty = Track(node.id, "position.x"), Track(node.id, "position.y")
    for i, (x, y) in enumerate(samples):
        f = start + int(round(i / n * dur))
        # repère écran : y vers le bas ; « sens horaire » inverse le sens de parcours
        rx = x * math.cos(theta) - sign * y * math.sin(theta)
        ry = x * math.sin(theta) + sign * y * math.cos(theta)
        tx.set_keyframe(f, fx + rx, "linear")
        ty.set_keyframe(f, fy + ry, "linear")
    return [tx, ty]

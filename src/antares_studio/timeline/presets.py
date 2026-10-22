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
            "Dessine progressivement la courbe d'un graphique ou les lignes d'une grille "
            "(progression 0 → 1).",
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
            "write",
            "Écrire",
            "Le texte ou l'équation s'écrit sous vos yeux, lettre après lettre. La façon d'écrire (tracé "
            "3Blue1Brown, craie, machine à écrire, fondu) se choisit dans l'Inspecteur.",
            _COMMON[:1]
            + (
                PresetParam("duration_frames", "Durée (images)", "int", 75, min=1),
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
            "erase",
            "Effacer l'écriture",
            "L'écriture se défait en sens inverse, de la dernière lettre à la première.",
            _COMMON[:1] + (PresetParam("duration_frames", "Durée (images)", "int", 30, min=1), _EASING),
        ),
        PresetSpec(
            "spin3d",
            "Rotation 3D",
            "Le solide ou le modèle 3D tourne sur lui-même (axe vertical) en s'inclinant éventuellement.",
            _COMMON
            + (
                PresetParam("turns", "Nombre de tours", "float", 1.0),
                PresetParam("tilt_deg", "Inclinaison ajoutée (°)", "float", 0.0, min=-180, max=180),
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
            "linear_map",
            "Transformation linéaire",
            "La grille se transforme sous l'effet d'une matrice [[a, b], [c, d]] : les colonnes sont les "
            "images des vecteurs î et ĵ (« Essence of linear algebra », 3Blue1Brown).",
            _COMMON
            + (
                PresetParam("a", "a (î en x)", "float", 1.0, min=-20, max=20),
                PresetParam("b", "b (ĵ en x)", "float", 1.0, min=-20, max=20),
                PresetParam("c", "c (î en y)", "float", 0.0, min=-20, max=20),
                PresetParam("d", "d (ĵ en y)", "float", 1.0, min=-20, max=20),
                _EASING,
            ),
        ),
        PresetSpec(
            "warp",
            "Courber l'espace",
            "La grille se creuse, ondule ou tourbillonne jusqu'à l'intensité voulue. Choisissez d'abord la "
            "déformation (puits de gravité, onde, tourbillon) dans l'Inspecteur.",
            _COMMON + (PresetParam("amount", "Intensité finale", "float", 1.0, min=-3, max=3), _EASING),
        ),
        PresetSpec(
            "wave_travel",
            "Onde qui se propage",
            "Les rides de la déformation « Onde » s'éloignent du centre (ondes gravitationnelles, ronds "
            "dans l'eau).",
            _COMMON + (PresetParam("cycles", "Nombre de rides émises", "float", 3.0, min=0.1),),
        ),
        PresetSpec(
            "shake",
            "Secousse",
            "Tremblement bref autour de la position actuelle (impact, explosion, séisme), qui s'amortit "
            "et revient exactement à sa place.",
            _COMMON[:1]
            + (
                PresetParam("duration_frames", "Durée (images)", "int", 18, min=2),
                PresetParam("amplitude", "Amplitude (px)", "float", 14.0, min=0),
                PresetParam("jolts", "Nombre d'à-coups", "int", 10, min=2, max=200),
            ),
        ),
        PresetSpec(
            "flash",
            "Éclat lumineux",
            "La lueur de l'objet s'allume puis s'éteint : explosion, supernova, idée qui jaillit.",
            _COMMON[:1]
            + (
                PresetParam("duration_frames", "Durée (images)", "int", 24, min=2),
                PresetParam("radius", "Rayon de la lueur (px)", "float", 60.0, min=1),
                PresetParam("strength", "Intensité maximale", "float", 2.5, min=0.1, max=4),
            ),
        ),
        PresetSpec(
            "blink",
            "Clignotement",
            "L'objet s'allume et s'éteint plusieurs fois : signal, alerte, balise.",
            _COMMON
            + (
                PresetParam("repeats", "Clignotements", "int", 3, min=1),
                PresetParam("dim", "Opacité éteinte (0 → 1)", "float", 0.15, min=0, max=1),
            ),
        ),
        PresetSpec(
            "focus",
            "Mise au point",
            "L'objet passe du flou au net (ou l'inverse) : attirer le regard, changer de plan.",
            _COMMON
            + (
                PresetParam("blur", "Flou de départ (px)", "float", 16.0, min=0, max=200),
                PresetParam("reverse", "Du net au flou", "bool", False),
                _EASING,
            ),
        ),
        PresetSpec(
            "glow_pulse",
            "Pulsation lumineuse",
            "La lueur respire régulièrement : étoile variable, pulsar, élément à surveiller.",
            _COMMON
            + (
                PresetParam("radius", "Rayon de la lueur (px)", "float", 30.0, min=1),
                PresetParam("low", "Intensité basse", "float", 0.3, min=0, max=4),
                PresetParam("high", "Intensité haute", "float", 1.8, min=0, max=4),
                PresetParam("repeats", "Pulsations", "int", 3, min=1),
            ),
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
    elif preset_id in ("write", "erase"):
        a, b = (0.0, 1.0) if preset_id == "write" else (1.0, 0.0)
        t = Track(node.id, "params.write")
        t.set_keyframe(start, a, easing)
        t.set_keyframe(end, b, easing)
        tracks.append(t)
    elif preset_id == "spin3d":
        yaw0 = float(node.params.get("yaw_deg", 0.0))
        pitch0 = float(node.params.get("pitch_deg", 0.0))
        yaw = Track(node.id, "params.yaw_deg")
        yaw.set_keyframe(start, yaw0, easing)
        yaw.set_keyframe(end, yaw0 + 360.0 * float(p["turns"]), easing)
        tracks.append(yaw)
        if float(p["tilt_deg"]) != 0.0:
            pitch = Track(node.id, "params.pitch_deg")
            pitch.set_keyframe(start, pitch0, easing)
            pitch.set_keyframe(end, pitch0 + float(p["tilt_deg"]), easing)
            tracks.append(pitch)
    elif preset_id == "linear_map":
        for name, default in (("a", 1.0), ("b", 0.0), ("c", 0.0), ("d", 1.0)):
            t = Track(node.id, f"params.m_{name}")
            t.set_keyframe(start, float(node.params.get(f"m_{name}", default)), easing)
            t.set_keyframe(end, float(p[name]), easing)
            tracks.append(t)
    elif preset_id == "warp":
        t = Track(node.id, "params.warp_amount")
        t.set_keyframe(start, float(node.params.get("warp_amount", 0.0)), easing)
        t.set_keyframe(end, float(p["amount"]), easing)
        tracks.append(t)
    elif preset_id == "wave_travel":
        phase0 = float(node.params.get("warp_phase", 0.0))
        t = Track(node.id, "params.warp_phase")
        t.set_keyframe(start, phase0, "linear")
        t.set_keyframe(end, phase0 + float(p["cycles"]), "linear")
        tracks.append(t)
    elif preset_id == "kepler":
        tracks += _kepler_tracks(node, p, start, dur)
    elif preset_id == "shake":
        tracks += _shake_tracks(node, p, start, dur)
    elif preset_id == "flash":
        radius, peak = float(p["radius"]), float(p["strength"])
        glow, strength = Track(node.id, "style.fx_glow"), Track(node.id, "style.fx_glow_strength")
        glow.set_keyframe(start, radius, "linear")
        glow.set_keyframe(end, radius, "linear")
        rise = start + max(1, dur // 4)
        strength.set_keyframe(start, 0.0, "ease_out")
        strength.set_keyframe(rise, peak, "ease_in_out")
        strength.set_keyframe(end, 0.0, "linear")
        tracks += [glow, strength]
    elif preset_id == "blink":
        reps, dim = int(p["repeats"]), float(p["dim"])
        t = Track(node.id, "opacity")
        seg = dur / (2 * reps)
        for i in range(2 * reps + 1):
            # paliers nets : éteint sur les demi-périodes impaires, rallumé à la fin
            t.set_keyframe(start + int(round(i * seg)), node.opacity * (dim if i % 2 == 1 else 1.0), "step")
        tracks.append(t)
    elif preset_id == "focus":
        blur = float(p["blur"])
        a, b = (0.0, blur) if bool(p["reverse"]) else (blur, 0.0)
        t = Track(node.id, "style.fx_blur")
        t.set_keyframe(start, a, easing)
        t.set_keyframe(end, b, easing)
        tracks.append(t)
    elif preset_id == "glow_pulse":
        reps, low, high = int(p["repeats"]), float(p["low"]), float(p["high"])
        glow, strength = Track(node.id, "style.fx_glow"), Track(node.id, "style.fx_glow_strength")
        glow.set_keyframe(start, float(p["radius"]), "linear")
        glow.set_keyframe(end, float(p["radius"]), "linear")
        seg = dur / (2 * reps)
        for i in range(2 * reps + 1):
            strength.set_keyframe(start + int(round(i * seg)), high if i % 2 == 1 else low, "ease_in_out")
        tracks += [glow, strength]
    return tracks


def _shake_tracks(node: Node, p: dict[str, Any], start: int, dur: int) -> list[Track]:
    """Écarts pseudo-aléatoires reproductibles (graine : identifiant de l'objet), amortis linéairement ;
    la dernière clé ramène l'objet à sa position exacte."""
    import random

    rng = random.Random(f"shake:{node.id}")
    amp = float(p["amplitude"])
    n = max(2, min(dur, int(p["jolts"])))  # jamais plus d'à-coups que d'images
    x0, y0 = node.position
    tx, ty = Track(node.id, "position.x"), Track(node.id, "position.y")
    for i in range(n + 1):
        f = start + int(round(i * dur / n))
        k = amp * (1.0 - i / n)
        dx = 0.0 if i in (0, n) else rng.uniform(-k, k)
        dy = 0.0 if i in (0, n) else rng.uniform(-k, k)
        tx.set_keyframe(f, x0 + dx, "linear")
        ty.set_keyframe(f, y0 + dy, "linear")
    return [tx, ty]


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

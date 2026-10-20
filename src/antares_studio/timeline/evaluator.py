"""Évaluateur pur : ``evaluate(project, scene_id, frame) -> SceneState`` (ADR-0002 §6).

Aucune dépendance Qt ni au temps réel. Même entrée → même sortie.
Convention d'angles : les angles sont interpolés tels quels (0 → 360 = un tour complet).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from antares_studio.domain.colors import is_color, mix_color
from antares_studio.domain.kinds import spec_for
from antares_studio.domain.model import Node, Project, Scene, Track, Value
from antares_studio.domain.properties import get_property
from antares_studio.timeline.easing import apply_easing

# Matrice affine 2D (a, b, c, d, tx, ty) : x' = a*x + c*y + tx ; y' = b*x + d*y + ty
Affine = tuple[float, float, float, float, float, float]
IDENTITY: Affine = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def compose(m: Affine, n: Affine) -> Affine:
    """Retourne m ∘ n (appliquer n puis m)."""
    a1, b1, c1, d1, tx1, ty1 = m
    a2, b2, c2, d2, tx2, ty2 = n
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * tx2 + c1 * ty2 + tx1,
        b1 * tx2 + d1 * ty2 + ty1,
    )


def local_transform(position: list[float], rotation_deg: float, scale: list[float]) -> Affine:
    r = math.radians(rotation_deg)
    cos_r, sin_r = math.cos(r), math.sin(r)
    sx, sy = scale
    return (cos_r * sx, sin_r * sx, -sin_r * sy, cos_r * sy, position[0], position[1])


def apply_affine(m: Affine, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, tx, ty = m
    return (a * x + c * y + tx, b * x + d * y + ty)


@dataclass(frozen=True)
class NodeState:
    id: str
    kind: str
    name: str
    parent_id: str | None
    position: tuple[float, float]
    rotation_deg: float
    scale: tuple[float, float]
    opacity: float  # opacité locale
    world_opacity: float  # opacité effective (produit des parents)
    visible: bool  # visibilité effective
    locked: bool
    z_index: int
    style: dict[str, Any]
    params: dict[str, Any]
    world: Affine  # transformation locale -> monde (pixels du canevas)


@dataclass(frozen=True)
class SceneState:
    scene_id: str
    frame: int
    background: str
    nodes: tuple[NodeState, ...]  # ordre de dessin (z_index croissant, puis ordre de déclaration)
    subtitle: str | None = None  # texte du sous-titre actif, incrusté par le même painter que les objets

    def node(self, node_id: str) -> NodeState:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)


def interpolate_value(v0: Value, v1: Value, u: float) -> Value:
    """Interpole selon le type : nombres, couleurs, listes de nombres ; sinon ``step``."""
    if isinstance(v0, bool) or isinstance(v1, bool):
        return v0 if u < 1.0 else v1
    if isinstance(v0, int | float) and isinstance(v1, int | float):
        return v0 + (v1 - v0) * u
    if isinstance(v0, str) and isinstance(v1, str):
        if is_color(v0) and is_color(v1):
            return mix_color(v0, v1, u)
        return v0 if u < 1.0 else v1
    if isinstance(v0, list) and isinstance(v1, list) and len(v0) == len(v1):
        return [a + (b - a) * u for a, b in zip(v0, v1, strict=True)]
    return v0 if u < 1.0 else v1


def sample_track(track: Track, frame: int) -> Value | None:
    """Valeur de la piste à ``frame`` ; None si la piste n'a aucune keyframe."""
    kfs = track.sorted_keyframes()
    if not kfs:
        return None
    if frame <= kfs[0].frame:
        return kfs[0].value
    if frame >= kfs[-1].frame:
        return kfs[-1].value
    lo, hi = 0, len(kfs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if kfs[mid].frame <= frame:
            lo = mid
        else:
            hi = mid
    k0, k1 = kfs[lo], kfs[hi]
    if k1.frame == k0.frame:
        return k1.value
    u = (frame - k0.frame) / (k1.frame - k0.frame)
    # l'interpolation est portée par la keyframe de départ du segment
    return interpolate_value(k0.value, k1.value, apply_easing(k0.easing, u))


def resolve_node(node: Node, tracks: list[Track], frame: int) -> dict[str, Any]:
    """Propriétés résolues (valeurs de base surchargées par les pistes) sous forme de chemins pointés."""
    spec = spec_for(node.kind)
    values: dict[str, Any] = {
        "position.x": node.position[0],
        "position.y": node.position[1],
        "rotation_deg": node.rotation_deg,
        "scale.x": node.scale[0],
        "scale.y": node.scale[1],
        "opacity": node.opacity,
        "visible": node.visible,
    }
    for p in spec.params:
        values[f"params.{p.name}"] = node.params.get(p.name, p.default)
    for p in spec.style:
        values[f"style.{p.name}"] = node.style.get(p.name, p.default)
    for key in node.params:
        values.setdefault(f"params.{key}", node.params[key])
    for key in node.style:
        values.setdefault(f"style.{key}", node.style[key])
    for track in tracks:
        v = sample_track(track, frame)
        if v is not None:
            values[track.property] = v
    return values


def evaluate_scene(scene: Scene, frame: int) -> SceneState:
    frame = max(0, min(int(frame), max(0, scene.duration_frames - 1)))
    tracks_by_target: dict[str, list[Track]] = {}
    for t in scene.tracks:
        tracks_by_target.setdefault(t.target_id, []).append(t)
    nodes_by_id = {n.id: n for n in scene.nodes}
    resolved: dict[str, dict[str, Any]] = {
        n.id: resolve_node(n, tracks_by_target.get(n.id, []), frame) for n in scene.nodes
    }
    world: dict[str, Affine] = {}
    world_opacity: dict[str, float] = {}
    world_visible: dict[str, bool] = {}

    def compute(node_id: str, stack: tuple[str, ...] = ()) -> None:
        if node_id in world:
            return
        if node_id in stack:
            raise ValueError(f"cycle de parenté détecté : {' -> '.join(stack + (node_id,))}")
        node = nodes_by_id[node_id]
        r = resolved[node_id]
        local = local_transform(
            [r["position.x"], r["position.y"]], r["rotation_deg"], [r["scale.x"], r["scale.y"]]
        )
        parent = node.parent_id if node.parent_id in nodes_by_id else None
        if parent is None:
            world[node_id] = local
            world_opacity[node_id] = float(r["opacity"])
            world_visible[node_id] = bool(r["visible"])
        else:
            compute(parent, stack + (node_id,))
            world[node_id] = compose(world[parent], local)
            world_opacity[node_id] = world_opacity[parent] * float(r["opacity"])
            world_visible[node_id] = world_visible[parent] and bool(r["visible"])

    for n in scene.nodes:
        compute(n.id)

    states: list[NodeState] = []
    for n in scene.nodes:
        r = resolved[n.id]
        states.append(
            NodeState(
                id=n.id,
                kind=n.kind,
                name=n.name,
                parent_id=n.parent_id,
                position=(float(r["position.x"]), float(r["position.y"])),
                rotation_deg=float(r["rotation_deg"]),
                scale=(float(r["scale.x"]), float(r["scale.y"])),
                opacity=float(r["opacity"]),
                world_opacity=world_opacity[n.id],
                visible=world_visible[n.id],
                locked=n.locked,
                z_index=n.z_index,
                style={k[6:]: v for k, v in r.items() if k.startswith("style.")},
                params={k[7:]: v for k, v in r.items() if k.startswith("params.")},
                world=world[n.id],
            )
        )
    order_index = {n.id: i for i, n in enumerate(scene.nodes)}
    states.sort(key=lambda s: (s.z_index, order_index[s.id]))
    sub = scene.subtitle_at(frame)
    return SceneState(
        scene_id=scene.id,
        frame=frame,
        background=scene.background,
        nodes=tuple(states),
        subtitle=sub.text if sub is not None else None,
    )


def evaluate(project: Project, scene_id: str, frame: int) -> SceneState:
    return evaluate_scene(project.scene(scene_id), frame)


def evaluate_at_seconds(project: Project, scene_id: str, seconds: float) -> SceneState:
    return evaluate(project, scene_id, project.canvas.seconds_to_frame(seconds))


def base_value(node: Node, path: str) -> Any:
    """Valeur non animée d'une propriété (avec défaut de catalogue pour params/style)."""
    try:
        return get_property(node, path)
    except KeyError:
        spec = spec_for(node.kind)
        group, _, name = path.partition(".")
        for p in spec.params if group == "params" else spec.style if group == "style" else ():
            if p.name == name:
                return p.default
        raise

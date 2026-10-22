"""Presse-papiers d'objets : copie autonome (objets, descendants, pistes, ressources) et collage sûr.

Le contenu collé vient d'une source non fiable (autre instance, autre projet) : il est relu par les mêmes
validateurs stricts que le fichier de projet, et chaque objet reçoit un nouvel identifiant.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any

from antares_studio.domain.ids import new_id
from antares_studio.domain.kinds import KINDS
from antares_studio.domain.model import Asset, Node, Project, Scene, Track

MIME_TYPE = "application/x-antares-studio-objects+json"
FORMAT = "antares-studio-objects"
FORMAT_VERSION = 1
MAX_NODES = 2000


class ClipboardError(ValueError):
    pass


def asset_params(node: Node) -> list[str]:
    """Noms des paramètres du nœud qui référencent une ressource du projet."""
    spec = KINDS.get(node.kind)
    return [p.name for p in spec.params if p.type == "asset"] if spec else []


def _with_descendants(scene: Scene, ids: list[str]) -> list[Node]:
    wanted = set(ids)
    changed = True
    while changed:
        changed = False
        for n in scene.nodes:
            if n.parent_id in wanted and n.id not in wanted:
                wanted.add(n.id)
                changed = True
    return [n for n in scene.nodes if n.id in wanted]  # ordre de la scène (ordre de dessin)


def copy_nodes(
    project: Project, scene: Scene, ids: list[str], root_path: str | None = None
) -> dict[str, Any]:
    """Sérialise la sélection et ses descendants ; ``root_path`` : dossier d'origine des fichiers.

    Un objet copié sans son groupe parent devient indépendant : sa position est convertie dans le repère
    de la scène (valeurs de base, hors animation) pour qu'il colle au même endroit à l'écran.
    """
    nodes = [copy.deepcopy(n) for n in _with_descendants(scene, ids)]
    node_ids = {n.id for n in nodes}
    tracks = [copy.deepcopy(t) for t in scene.tracks if t.target_id in node_ids]
    for n in nodes:
        if n.parent_id is not None and n.parent_id not in node_ids:
            old = list(n.position)
            n.position, n.rotation_deg, n.scale = _scene_space(scene, n)
            n.parent_id = None
            # trajectoire animée décalée de la même translation (exact si le groupe n'est ni tourné ni étiré)
            for t in tracks:
                if t.target_id == n.id and t.property in ("position.x", "position.y"):
                    axis = 0 if t.property == "position.x" else 1
                    for kf in t.keyframes:
                        if isinstance(kf.value, int | float) and not isinstance(kf.value, bool):
                            kf.value = float(kf.value) + n.position[axis] - old[axis]
    asset_ids = {str(n.params.get(name, "")) for n in nodes for name in asset_params(n)} - {""}
    assets = [asdict(a) for a in project.assets if a.id in asset_ids]
    return {
        "format": FORMAT,
        "version": FORMAT_VERSION,
        "project_id": project.project_id,
        "root_path": root_path or "",
        "fps": [project.canvas.fps_num, project.canvas.fps_den],
        "nodes": [asdict(n) for n in nodes],
        "tracks": [asdict(t) for t in tracks],
        "assets": assets,
    }


def _scene_space(scene: Scene, node: Node) -> tuple[list[float], float, list[float]]:
    """Position, rotation et échelle de ``node`` dans le repère de la scène (composition des parents)."""
    from antares_studio.timeline.evaluator import apply_affine, compose, local_transform

    m = local_transform(node.position, node.rotation_deg, node.scale)
    rotation, sx, sy = node.rotation_deg, node.scale[0], node.scale[1]
    parent = scene.find_node(node.parent_id) if node.parent_id else None
    seen: set[str] = set()
    while parent is not None and parent.id not in seen:
        seen.add(parent.id)
        m = compose(local_transform(parent.position, parent.rotation_deg, parent.scale), m)
        rotation += parent.rotation_deg
        sx, sy = sx * parent.scale[0], sy * parent.scale[1]
        parent = scene.find_node(parent.parent_id) if parent.parent_id else None
    x, y = apply_affine(m, 0.0, 0.0)
    return [x, y], rotation, [sx, sy]


@dataclass
class PastePayload:
    nodes: list[Node]
    tracks: list[Track]
    assets: list[Asset]  # ressources référencées, telles que décrites par le projet d'origine
    same_project: bool
    root_path: str
    warnings: list[str] = field(default_factory=list)


def read_payload(data: Any, project: Project, offset: tuple[float, float] = (20.0, 20.0)) -> PastePayload:
    """Valide ``data`` et retourne des copies prêtes à insérer (nouveaux identifiants, parents remappés)."""
    from antares_studio.persistence.schema import (
        ProjectFormatError,
        _asset_from,
        _expect_dict,
        _expect_list,
        _node_from,
        _track_from,
    )

    try:
        d = _expect_dict(data, "$")
        if d.get("format") != FORMAT or d.get("version") != FORMAT_VERSION:
            raise ClipboardError("le presse-papiers ne contient pas d'objets ANTARES Studio")
        raw_nodes = _expect_list(d.get("nodes", []), "$.nodes")
        if not raw_nodes:
            raise ClipboardError("aucun objet à coller")
        if len(raw_nodes) > MAX_NODES:
            raise ClipboardError(f"trop d'objets à coller (maximum {MAX_NODES})")
        nodes = [_node_from(n, f"$.nodes[{i}]") for i, n in enumerate(raw_nodes)]
        tracks = [
            _track_from(t, f"$.tracks[{i}]")
            for i, t in enumerate(_expect_list(d.get("tracks", []), "$.tracks"))
        ]
        assets = [
            _asset_from(a, f"$.assets[{i}]")
            for i, a in enumerate(_expect_list(d.get("assets", []), "$.assets"))
        ]
    except ProjectFormatError as exc:
        raise ClipboardError(f"contenu invalide ({exc})") from exc
    warnings: list[str] = []
    unknown = sorted({n.kind for n in nodes if n.kind not in KINDS})
    if unknown:
        raise ClipboardError(f"types d'objets inconnus : {', '.join(unknown)}")
    mapping = {n.id: new_id("node") for n in nodes}
    out_nodes: list[Node] = []
    for n in nodes:
        clone = copy.deepcopy(n)
        clone.id = mapping[n.id]
        clone.parent_id = mapping.get(n.parent_id) if n.parent_id else None
        if clone.parent_id is None:  # racines collées : décalées pour rester visibles à côté de l'original
            clone.position = [clone.position[0] + offset[0], clone.position[1] + offset[1]]
        out_nodes.append(clone)
    out_tracks: list[Track] = []
    for t in tracks:
        if t.target_id not in mapping:
            continue
        clone_t = copy.deepcopy(t)
        clone_t.target_id = mapping[t.target_id]
        if t.property in ("position.x", "position.y") and next(
            (n.parent_id is None for n in nodes if n.id == t.target_id), False
        ):
            delta = offset[0] if t.property == "position.x" else offset[1]
            for kf in clone_t.keyframes:
                if isinstance(kf.value, int | float) and not isinstance(kf.value, bool):
                    kf.value = float(kf.value) + delta
        out_tracks.append(clone_t)
    fps = d.get("fps")
    if isinstance(fps, list) and fps != [project.canvas.fps_num, project.canvas.fps_den]:
        warnings.append("cadence différente : les animations collées gardent leurs numéros d'image")
    return PastePayload(
        nodes=out_nodes,
        tracks=out_tracks,
        assets=assets,
        same_project=d.get("project_id") == project.project_id,
        root_path=str(d.get("root_path", "")),
        warnings=warnings,
    )


def remap_assets(payload: PastePayload, mapping: dict[str, str]) -> None:
    """Remplace les références de ressources (``mapping`` : ancien id -> nouvel id, "" = retirée)."""
    for n in payload.nodes:
        for name in asset_params(n):
            old = str(n.params.get(name, ""))
            if old in mapping:
                n.params[name] = mapping[old]

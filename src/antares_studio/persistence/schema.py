"""Sérialisation JSON stricte du modèle (ADR-0002 §7). Aucune exécution de code."""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

from antares_studio.domain.model import (
    SCHEMA_VERSION,
    Asset,
    AssetLicense,
    Canvas,
    Keyframe,
    Node,
    Project,
    Scene,
    Track,
)


class ProjectFormatError(ValueError):
    """Fichier de projet illisible ou invalide ; ``path`` désigne l'emplacement JSON fautif."""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


def project_to_dict(project: Project) -> dict[str, Any]:
    d = asdict(project)
    d["schema_version"] = project.schema_version
    return d


def project_from_dict(data: Any) -> Project:
    """Construit un ``Project`` depuis un dictionnaire JSON en validant chaque champ."""
    obj = _expect_dict(data, "$")
    version = _expect_int(obj.get("schema_version"), "$.schema_version")
    if version != SCHEMA_VERSION:
        raise ProjectFormatError(
            "$.schema_version", f"version {version} non prise en charge (attendu {SCHEMA_VERSION})"
        )
    project = Project(
        project_id=_expect_str(obj.get("project_id"), "$.project_id"),
        title=_expect_str(obj.get("title", ""), "$.title"),
        schema_version=version,
        locale=_expect_str(obj.get("locale", "fr-FR"), "$.locale"),
        canvas=_canvas_from(obj.get("canvas", {}), "$.canvas"),
        scenes=[
            _scene_from(s, f"$.scenes[{i}]")
            for i, s in enumerate(_expect_list(obj.get("scenes", []), "$.scenes"))
        ],
        assets=[
            _asset_from(a, f"$.assets[{i}]")
            for i, a in enumerate(_expect_list(obj.get("assets", []), "$.assets"))
        ],
        scientific_metadata=_expect_dict(obj.get("scientific_metadata", {}), "$.scientific_metadata"),
        settings=_expect_dict(obj.get("settings", {}), "$.settings"),
    )
    return project


def _canvas_from(data: Any, path: str) -> Canvas:
    d = _expect_dict(data, path)
    return Canvas(
        width=_expect_int(d.get("width", 1920), f"{path}.width"),
        height=_expect_int(d.get("height", 1080), f"{path}.height"),
        fps_num=_expect_int(d.get("fps_num", 30), f"{path}.fps_num"),
        fps_den=_expect_int(d.get("fps_den", 1), f"{path}.fps_den"),
    )


def _scene_from(data: Any, path: str) -> Scene:
    d = _expect_dict(data, path)
    return Scene(
        id=_expect_str(d.get("id"), f"{path}.id"),
        name=_expect_str(d.get("name", ""), f"{path}.name"),
        duration_frames=_expect_int(d.get("duration_frames", 300), f"{path}.duration_frames"),
        background=_expect_str(d.get("background", "#0B1020"), f"{path}.background"),
        nodes=[
            _node_from(n, f"{path}.nodes[{i}]")
            for i, n in enumerate(_expect_list(d.get("nodes", []), f"{path}.nodes"))
        ],
        tracks=[
            _track_from(t, f"{path}.tracks[{i}]")
            for i, t in enumerate(_expect_list(d.get("tracks", []), f"{path}.tracks"))
        ],
    )


def _node_from(data: Any, path: str) -> Node:
    d = _expect_dict(data, path)
    parent = d.get("parent_id")
    if parent is not None and not isinstance(parent, str):
        raise ProjectFormatError(f"{path}.parent_id", "identifiant ou null attendu")
    return Node(
        id=_expect_str(d.get("id"), f"{path}.id"),
        kind=_expect_str(d.get("kind"), f"{path}.kind"),
        name=_expect_str(d.get("name", ""), f"{path}.name"),
        parent_id=parent,
        position=_expect_vec2(d.get("position", [0.0, 0.0]), f"{path}.position"),
        rotation_deg=_expect_number(d.get("rotation_deg", 0.0), f"{path}.rotation_deg"),
        scale=_expect_vec2(d.get("scale", [1.0, 1.0]), f"{path}.scale"),
        opacity=_expect_number(d.get("opacity", 1.0), f"{path}.opacity"),
        visible=_expect_bool(d.get("visible", True), f"{path}.visible"),
        locked=_expect_bool(d.get("locked", False), f"{path}.locked"),
        z_index=_expect_int(d.get("z_index", 0), f"{path}.z_index"),
        style=_expect_json_dict(d.get("style", {}), f"{path}.style"),
        params=_expect_json_dict(d.get("params", {}), f"{path}.params"),
    )


def _track_from(data: Any, path: str) -> Track:
    d = _expect_dict(data, path)
    kfs = []
    for i, k in enumerate(_expect_list(d.get("keyframes", []), f"{path}.keyframes")):
        kd = _expect_dict(k, f"{path}.keyframes[{i}]")
        if "value" not in kd:
            raise ProjectFormatError(f"{path}.keyframes[{i}].value", "valeur manquante")
        kfs.append(
            Keyframe(
                frame=_expect_int(kd.get("frame"), f"{path}.keyframes[{i}].frame"),
                value=_expect_json_value(kd["value"], f"{path}.keyframes[{i}].value"),
                easing=_expect_str(kd.get("easing", "linear"), f"{path}.keyframes[{i}].easing"),
            )
        )
    return Track(
        target_id=_expect_str(d.get("target_id"), f"{path}.target_id"),
        property=_expect_str(d.get("property"), f"{path}.property"),
        keyframes=kfs,
    )


def _asset_from(data: Any, path: str) -> Asset:
    d = _expect_dict(data, path)
    lic = _expect_dict(d.get("license", {}), f"{path}.license")
    return Asset(
        id=_expect_str(d.get("id"), f"{path}.id"),
        path=_expect_str(d.get("path"), f"{path}.path"),
        kind=_expect_str(d.get("kind", "other"), f"{path}.kind"),
        sha256=_expect_str(d.get("sha256", ""), f"{path}.sha256"),
        license=AssetLicense(
            author=_expect_str(lic.get("author", ""), f"{path}.license.author"),
            source_url=_expect_str(lic.get("source_url", ""), f"{path}.license.source_url"),
            license=_expect_str(lic.get("license", ""), f"{path}.license.license"),
            attribution_required=_expect_bool(
                lic.get("attribution_required", False), f"{path}.license.attribution_required"
            ),
            redistribution_allowed=_expect_bool(
                lic.get("redistribution_allowed", False), f"{path}.license.redistribution_allowed"
            ),
            verified_on=_expect_str(lic.get("verified_on", ""), f"{path}.license.verified_on"),
        ),
    )


# --- vérifications de type -------------------------------------------------


def _expect_dict(v: Any, path: str) -> dict[str, Any]:
    if not isinstance(v, dict):
        raise ProjectFormatError(path, "objet attendu")
    return v


def _expect_list(v: Any, path: str) -> list[Any]:
    if not isinstance(v, list):
        raise ProjectFormatError(path, "liste attendue")
    return v


def _expect_str(v: Any, path: str) -> str:
    if not isinstance(v, str):
        raise ProjectFormatError(path, "texte attendu")
    return v


def _expect_bool(v: Any, path: str) -> bool:
    if not isinstance(v, bool):
        raise ProjectFormatError(path, "booléen attendu")
    return v


def _expect_int(v: Any, path: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise ProjectFormatError(path, "entier attendu")
    return v


def _expect_number(v: Any, path: str) -> float:
    if isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v):
        raise ProjectFormatError(path, "nombre fini attendu")
    return float(v)


def _expect_vec2(v: Any, path: str) -> list[float]:
    if not isinstance(v, list) or len(v) != 2:
        raise ProjectFormatError(path, "couple [x, y] attendu")
    return [_expect_number(v[0], f"{path}[0]"), _expect_number(v[1], f"{path}[1]")]


def _expect_json_value(v: Any, path: str, depth: int = 0) -> Any:
    if depth > 8:
        raise ProjectFormatError(path, "imbrication trop profonde")
    if v is None or isinstance(v, bool | str):
        return v
    if isinstance(v, int | float):
        if not math.isfinite(v):
            raise ProjectFormatError(path, "nombre fini attendu")
        return v
    if isinstance(v, list):
        return [_expect_json_value(x, f"{path}[{i}]", depth + 1) for i, x in enumerate(v)]
    if isinstance(v, dict):
        return {_expect_str(k, path): _expect_json_value(x, f"{path}.{k}", depth + 1) for k, x in v.items()}
    raise ProjectFormatError(path, f"type non autorisé : {type(v).__name__}")


def _expect_json_dict(v: Any, path: str) -> dict[str, Any]:
    d = _expect_dict(v, path)
    return {k: _expect_json_value(x, f"{path}.{k}") for k, x in d.items()}

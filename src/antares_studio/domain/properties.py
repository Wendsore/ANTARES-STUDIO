"""Accès aux propriétés d'un nœud par chemin pointé (``position.x``, ``style.fill``, ``params.radius``)."""

from __future__ import annotations

from typing import Any

from antares_studio.domain.effects import EFFECTS_BY_NAME, supports_effects
from antares_studio.domain.kinds import BASE_ANIMATABLE, check_param_value, spec_for
from antares_studio.domain.model import Node

_BASE_SCALAR = ("rotation_deg", "opacity", "visible", "locked", "z_index", "name", "parent_id")


def get_property(node: Node, path: str) -> Any:
    group, _, name = path.partition(".")
    if group == "position" and name in ("x", "y"):
        return node.position[0 if name == "x" else 1]
    if group == "scale" and name in ("x", "y"):
        return node.scale[0 if name == "x" else 1]
    if group == "params":
        return node.params[name]
    if group == "style":
        if name not in node.style and name in EFFECTS_BY_NAME and supports_effects(node.kind):
            return EFFECTS_BY_NAME[name].default  # effet jamais réglé : sa valeur neutre
        return node.style[name]
    if path in _BASE_SCALAR:
        return getattr(node, path)
    raise KeyError(path)


def set_property(node: Node, path: str, value: Any) -> None:
    """Affecte ``value`` à ``path`` après validation de type ; lève ``ValueError`` sinon."""
    err = check_property_value(node, path, value)
    if err:
        raise ValueError(err)
    group, _, name = path.partition(".")
    if group == "position":
        node.position[0 if name == "x" else 1] = float(value)
    elif group == "scale":
        node.scale[0 if name == "x" else 1] = float(value)
    elif group == "params":
        node.params[name] = value
    elif group == "style":
        node.style[name] = value
    elif path == "rotation_deg":
        node.rotation_deg = float(value)
    elif path == "opacity":
        node.opacity = float(value)
    elif path in ("visible", "locked"):
        setattr(node, path, bool(value))
    elif path == "z_index":
        node.z_index = int(value)
    elif path == "name":
        node.name = str(value)
    elif path == "parent_id":
        node.parent_id = value
    else:
        raise KeyError(path)


def check_property_value(node: Node, path: str, value: Any) -> str | None:
    group, _, name = path.partition(".")
    if group in ("position", "scale") and name in ("x", "y"):
        return None if _finite(value) else f"{path} : nombre attendu"
    if path == "rotation_deg":
        return None if _finite(value) else "rotation_deg : nombre attendu"
    if path == "opacity":
        if not _finite(value) or not 0.0 <= value <= 1.0:
            return "opacity : nombre entre 0 et 1 attendu"
        return None
    if path in ("visible", "locked"):
        return None if isinstance(value, bool) else f"{path} : booléen attendu"
    if path == "z_index":
        return None if isinstance(value, int) and not isinstance(value, bool) else "z_index : entier attendu"
    if path == "name":
        return None if isinstance(value, str) else "name : texte attendu"
    if path == "parent_id":
        return None if value is None or isinstance(value, str) else "parent_id : identifiant attendu"
    spec = spec_for(node.kind)
    specs = spec.params if group == "params" else spec.style if group == "style" else ()
    for p in specs:
        if p.name == name:
            return check_param_value(p, value)
    if group == "style" and name in EFFECTS_BY_NAME and supports_effects(node.kind):
        return check_param_value(EFFECTS_BY_NAME[name], value)
    return f"propriété inconnue pour {node.kind} : {path}"


def is_animatable(node: Node, path: str) -> bool:
    if path in BASE_ANIMATABLE:
        return True
    group, _, name = path.partition(".")
    spec = spec_for(node.kind)
    specs = spec.params if group == "params" else spec.style if group == "style" else ()
    if group == "style" and name in EFFECTS_BY_NAME and supports_effects(node.kind):
        return EFFECTS_BY_NAME[name].animatable
    return any(p.name == name and p.animatable for p in specs)


def _finite(v: Any) -> bool:
    return (
        isinstance(v, int | float)
        and not isinstance(v, bool)
        and v == v
        and v not in (float("inf"), float("-inf"))
    )

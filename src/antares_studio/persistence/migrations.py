"""Migrations de schéma ``N -> N+1`` sur dictionnaires JSON, sans perte."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from antares_studio.domain.model import SCHEMA_VERSION

Migration = Callable[[dict[str, Any]], dict[str, Any]]

# version source -> fonction produisant la version suivante
MIGRATIONS: dict[int, Migration] = {}


def migrate_dict(data: Any) -> Any:
    """Applique les migrations successives jusqu'à ``SCHEMA_VERSION``. Ne modifie pas l'entrée."""
    if not isinstance(data, dict):
        return data
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool):
        return data
    if version > SCHEMA_VERSION:
        return data  # rejeté ensuite par project_from_dict avec un message explicite
    current = dict(data)
    while version < SCHEMA_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            return current
        current = step(current)
        version = current.get("schema_version", version + 1)
    return current


def needs_migration(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and isinstance(data.get("schema_version"), int)
        and data["schema_version"] < SCHEMA_VERSION
    )

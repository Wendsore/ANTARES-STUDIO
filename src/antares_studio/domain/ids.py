"""Identifiants stables des objets de projet."""

from __future__ import annotations

import re
import uuid

_ID_RE = re.compile(r"^[a-z][a-z0-9]*-[0-9a-f]{12}$")


def new_id(prefix: str) -> str:
    """Retourne un identifiant stable ``prefix-xxxxxxxxxxxx`` (12 hex aléatoires)."""
    if not re.fullmatch(r"[a-z][a-z0-9]*", prefix):
        raise ValueError(f"préfixe d'identifiant invalide : {prefix!r}")
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def is_valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(_ID_RE.match(value))

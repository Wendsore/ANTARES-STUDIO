"""Résolution sûre des chemins de ressources sous la racine du projet (protection contre la traversée)."""

from __future__ import annotations

from pathlib import Path, PurePosixPath


class UnsafePathError(ValueError):
    pass


def normalize_relative(rel: str) -> str:
    """Normalise un chemin relatif en forme POSIX ; refuse absolu, ``..``, lecteur Windows et octet nul."""
    if not rel or "\x00" in rel:
        raise UnsafePathError("chemin vide ou invalide")
    candidate = rel.replace("\\", "/")
    if candidate.startswith("/") or (len(candidate) > 1 and candidate[1] == ":"):
        raise UnsafePathError(f"chemin absolu interdit : {rel!r}")
    parts = [p for p in PurePosixPath(candidate).parts if p not in ("", ".")]
    if any(p == ".." for p in parts) or not parts:
        raise UnsafePathError(f"traversée de répertoire interdite : {rel!r}")
    return "/".join(parts)


def resolve_under(root: Path, rel: str) -> Path:
    """Retourne ``root/rel`` en vérifiant que le chemin résolu reste sous ``root`` (symlinks compris)."""
    norm = normalize_relative(rel)
    root_resolved = root.resolve()
    target = root_resolved / norm
    resolved = target.resolve() if target.exists() else target.parent.resolve() / target.name
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        raise UnsafePathError(f"le chemin sort de la racine du projet : {rel!r}") from None
    return resolved

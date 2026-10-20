"""Import de ressources dans le dossier projet (copie, hachage SHA-256, fiche de licence à compléter)."""

from __future__ import annotations

import hashlib
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from antares_studio.app.document import ProjectDocument
from antares_studio.domain.ids import new_id
from antares_studio.domain.model import Asset, AssetLicense

MAX_ASSET_BYTES = 256 * 1024 * 1024
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".svg"}
AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}


def _safe_name(name: str) -> str:
    base = re.sub(r"[^\w.\- ]+", "_", name, flags=re.UNICODE).strip() or "ressource"
    return base[:120]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def import_asset(document: ProjectDocument, source: Path, kind: str = "image") -> Asset:
    """Copie ``source`` dans ``assets/`` ou ``audio/`` du projet et enregistre la ressource."""
    if document.paths is None:
        raise ValueError("le projet doit être enregistré avant d'importer une ressource")
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"fichier introuvable : {source}")
    ext = source.suffix.lower()
    if kind == "image" and ext not in IMAGE_EXT:
        raise ValueError(f"format d'image non pris en charge : {ext or '(sans extension)'}")
    if kind == "audio" and ext not in AUDIO_EXT:
        raise ValueError(f"format audio non pris en charge : {ext or '(sans extension)'}")
    size = source.stat().st_size
    if size > MAX_ASSET_BYTES:
        raise ValueError(
            f"fichier trop volumineux ({size // 2**20} Mo, maximum {MAX_ASSET_BYTES // 2**20} Mo)"
        )
    folder = document.paths.audio if kind == "audio" else document.paths.assets
    folder.mkdir(parents=True, exist_ok=True)
    digest = sha256_of(source)
    for existing in document.project.assets:
        if existing.sha256 == digest and (document.paths.root / existing.path).is_file():
            return existing
    target = folder / _safe_name(source.name)
    i = 1
    while target.exists():
        target = folder / f"{target.stem.rsplit('-', 1)[0] if i > 1 else target.stem}-{i}{target.suffix}"
        i += 1
    shutil.copy2(source, target)
    rel = target.relative_to(document.paths.root).as_posix()
    asset = Asset(
        id=new_id("asset"),
        path=rel,
        kind=kind,
        sha256=digest,
        license=AssetLicense(verified_on=datetime.now(UTC).date().isoformat()),
    )
    document.project.assets.append(asset)
    document.version += 1
    document.changed.emit()
    return asset

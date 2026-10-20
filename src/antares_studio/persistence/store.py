"""Dossier projet ``Nom.antares/`` : chargement, sauvegarde atomique, autosave, récupération.

Voir ADR-0002 §1 et §8.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from antares_studio.domain.model import Project
from antares_studio.domain.validation import ProjectValidationError, validate_project
from antares_studio.persistence.migrations import migrate_dict
from antares_studio.persistence.schema import ProjectFormatError, project_from_dict, project_to_dict

PROJECT_SUFFIX = ".antares"
PROJECT_FILE = "project.json"
SUBDIRS = ("assets", "audio", "licenses", "autosaves", "cache", "renders")
MAX_PROJECT_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def project_file(self) -> Path:
        return self.root / PROJECT_FILE

    @property
    def assets(self) -> Path:
        return self.root / "assets"

    @property
    def audio(self) -> Path:
        return self.root / "audio"

    @property
    def autosaves(self) -> Path:
        return self.root / "autosaves"

    @property
    def renders(self) -> Path:
        return self.root / "renders"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def licenses(self) -> Path:
        return self.root / "licenses"


def resolve_project_root(path: Path) -> Path:
    """Accepte le dossier ``X.antares`` ou le fichier ``X.antares/project.json``."""
    p = Path(path)
    if p.name == PROJECT_FILE:
        return p.parent
    return p


class ProjectStore:
    """Opérations disque sur un dossier projet. Pas de dépendance Qt."""

    def create(self, root: Path, project: Project) -> ProjectPaths:
        root = Path(root)
        if root.suffix != PROJECT_SUFFIX:
            root = root.with_name(root.name + PROJECT_SUFFIX)
        if root.exists() and any(root.iterdir()):
            raise FileExistsError(f"le dossier existe déjà et n'est pas vide : {root}")
        root.mkdir(parents=True, exist_ok=True)
        paths = ProjectPaths(root)
        for sub in SUBDIRS:
            (root / sub).mkdir(exist_ok=True)
        self.save_atomic(project, paths.project_file)
        return paths

    def load(self, path: Path) -> Project:
        root = resolve_project_root(Path(path))
        file = root / PROJECT_FILE
        if not file.is_file():
            raise FileNotFoundError(f"fichier de projet introuvable : {file}")
        if file.stat().st_size > MAX_PROJECT_BYTES:
            raise ProjectFormatError("$", "fichier de projet trop volumineux")
        try:
            raw = file.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ProjectFormatError("$", f"encodage UTF-8 invalide ({exc.reason})") from exc
        return self.parse(raw)

    def parse(self, raw: str) -> Project:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProjectFormatError(
                "$", f"JSON invalide ligne {exc.lineno}, colonne {exc.colno} : {exc.msg}"
            ) from exc
        data = migrate_dict(data)
        project = project_from_dict(data)
        issues = validate_project(project)
        if issues:
            raise ProjectValidationError(issues)
        return project

    def save_atomic(self, project: Project, path: Path) -> Path:
        """Écrit ``project.json`` via fichier temporaire + remplacement atomique ; valide avant d'écrire."""
        issues = validate_project(project)
        if issues:
            raise ProjectValidationError(issues)
        root = resolve_project_root(Path(path))
        root.mkdir(parents=True, exist_ok=True)
        target = root / PROJECT_FILE
        payload = json.dumps(project_to_dict(project), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        fd, tmp_name = tempfile.mkstemp(prefix=".project-", suffix=".json.tmp", dir=root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, target)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise
        return target

    def autosave(self, project: Project, root: Path, keep: int = 10) -> Path:
        """Enregistre une copie datée dans ``autosaves/`` sans toucher au fichier principal."""
        paths = ProjectPaths(resolve_project_root(Path(root)))
        paths.autosaves.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        target = paths.autosaves / f"autosave-{stamp}.json"
        payload = json.dumps(project_to_dict(project), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)
        for old in self.list_autosaves(paths.root)[keep:]:
            with contextlib.suppress(OSError):
                old.unlink()
        return target

    def list_autosaves(self, root: Path) -> list[Path]:
        paths = ProjectPaths(resolve_project_root(Path(root)))
        if not paths.autosaves.is_dir():
            return []
        return sorted(paths.autosaves.glob("autosave-*.json"), reverse=True)

    def backup_project_file(self, root: Path, label: str = "backup") -> Path | None:
        """Copie ``project.json`` dans ``autosaves/`` (avant migration ou récupération)."""
        paths = ProjectPaths(resolve_project_root(Path(root)))
        if not paths.project_file.is_file():
            return None
        paths.autosaves.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        target = paths.autosaves / f"{label}-{stamp}.json"
        shutil.copy2(paths.project_file, target)
        return target

    def latest_valid_autosave(self, root: Path) -> tuple[Path, Project] | None:
        for candidate in self.list_autosaves(root):
            try:
                return candidate, self.parse(candidate.read_text(encoding="utf-8"))
            except (ProjectFormatError, ProjectValidationError, OSError, UnicodeDecodeError):
                continue
        return None

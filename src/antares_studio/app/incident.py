"""Rapport d'incident local : un fichier .zip que l'utilisateur joint lui-même à sa demande d'aide.

Rien n'est envoyé : le rapport est écrit sur le disque, son contenu est lisible (texte brut) et listé
dans ``LISEZMOI.txt``. Il contient le diagnostic, un résumé du projet ouvert (structure, jamais les
médias ni les textes) et les dernières erreurs inattendues ; le dossier personnel est remplacé par « ~ ».
"""

from __future__ import annotations

import contextlib
import os
import sys
import traceback
import zipfile
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import TracebackType

from antares_studio.domain.model import Project
from antares_studio.domain.validation import validate_project

CRASH_LOG = "erreurs.log"
MAX_LOG_BYTES = 200_000
README = """Rapport d'incident ANTARES Studio
================================

Ce fichier a été créé sur votre ordinateur à votre demande ; il n'a été envoyé nulle part.
Joignez-le à votre message si vous demandez de l'aide.

Contenu (texte lisible, vous pouvez l'ouvrir et le vérifier avant de l'envoyer) :
- diagnostic.txt : versions (ANTARES Studio, Python, Qt), système, FFmpeg et ses encodeurs, Blender ;
- projet.txt : structure du projet ouvert (scènes, nombre d'objets par type, ressources, problèmes
  de validation). Les textes, images, sons et données du projet ne sont PAS inclus ;
- erreurs.log : dernières erreurs inattendues de l'application (traces techniques), s'il y en a.

Le chemin de votre dossier personnel est remplacé par « ~ ».
"""


def log_dir() -> Path:
    """Dossier des journaux : celui des préférences isolées (tests) ou le dossier de données utilisateur."""
    folder = os.environ.get("ANTARES_SETTINGS_DIR", "").strip()
    if folder:
        return Path(folder)
    from PySide6.QtCore import QStandardPaths

    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))


def anonymize(text: str) -> str:
    home = str(Path.home())
    return text.replace(home, "~") if home and home != "/" else text


def record_exception(
    exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None, folder: Path | None = None
) -> Path:
    """Ajoute la trace au journal (borné aux derniers ~200 ko)."""
    path = (folder or log_dir()) / CRASH_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = f"--- {datetime.now().isoformat(timespec='seconds')} ---\n" + "".join(
        traceback.format_exception(exc_type, exc, tb)
    )
    old = path.read_bytes() if path.is_file() else b""
    # borne en octets, fins de ligne « \n » sur tous les systèmes (Windows écrirait « \r\n » en mode texte) ;
    # un caractère UTF-8 coupé au début est écarté
    tail = (old + entry.encode("utf-8"))[-MAX_LOG_BYTES:]
    path.write_bytes(tail.decode("utf-8", errors="ignore").encode("utf-8"))
    return path


def install_exception_logger(folder: Path | None = None) -> Callable[..., None]:
    """Journalise toute exception non rattrapée puis laisse le comportement d'origine s'appliquer."""
    previous = sys.excepthook

    def hook(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
        with contextlib.suppress(OSError):  # un disque plein ne doit pas masquer l'erreur d'origine
            record_exception(exc_type, exc, tb, folder)
        previous(exc_type, exc, tb)

    sys.excepthook = hook
    return previous


def project_summary(project: Project | None, root: Path | None) -> str:
    if project is None:
        return "Aucun projet ouvert.\n"
    lines = [
        f"Projet : {len(project.title)} caractères de titre (titre non inclus)",
        f"Format : {project.canvas.width}×{project.canvas.height}, {project.canvas.fps_num}/"
        f"{project.canvas.fps_den} i/s",
        f"Dossier : {anonymize(str(root)) if root else '(non enregistré)'}",
        f"Scènes : {len(project.scenes)}",
    ]
    for i, scene in enumerate(project.scenes, start=1):
        kinds = Counter(n.kind for n in scene.nodes)
        detail = ", ".join(f"{k} × {v}" for k, v in sorted(kinds.items())) or "vide"
        lines.append(
            f"  {i}. {scene.duration_frames} images ; objets : {detail} ; "
            f"pistes animées : {len(scene.tracks)} ; audio : {len(scene.audio)} ; "
            f"sous-titres : {len(scene.subtitles)} ; transition : {scene.transition.kind}"
        )
    lines.append(f"Ressources : {len(project.assets)}")
    for asset in project.assets:
        state = "?"
        if root is not None:
            state = "présente" if (root / asset.path).is_file() else "MANQUANTE"
        ext = Path(asset.path).suffix.lower() or "(sans extension)"
        lines.append(
            f"  - {asset.kind} {ext} : {state} ; licence : {asset.license.license or 'non renseignée'}"
        )
    issues = validate_project(project)
    lines.append(f"Validation : {len(issues)} problème(s)")
    lines += [f"  - {issue.path} : {issue.message}" for issue in issues[:50]]
    return "\n".join(lines) + "\n"


def write_incident_report(
    target: Path,
    diagnostics: str,
    project: Project | None,
    root: Path | None,
    folder: Path | None = None,
) -> list[str]:
    """Écrit le .zip et retourne la liste des fichiers inclus."""
    log = (folder or log_dir()) / CRASH_LOG
    files = {
        "LISEZMOI.txt": README,
        "diagnostic.txt": anonymize(diagnostics) + "\n",
        "projet.txt": project_summary(project, root),
    }
    if log.is_file():
        files["erreurs.log"] = anonymize(log.read_text(encoding="utf-8", errors="replace"))
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    os.replace(tmp, target)
    return list(files)

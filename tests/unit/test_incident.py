"""Rapport d'incident local : contenu lisible, sans textes ni médias du projet, dossier personnel masqué."""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

from antares_studio.app.incident import (
    CRASH_LOG,
    MAX_LOG_BYTES,
    install_exception_logger,
    record_exception,
    write_incident_report,
)
from antares_studio.domain.model import Asset, Subtitle
from tests.unit.helpers import earth_moon_project


def test_report_lists_structure_but_never_project_content(tmp_path: Path) -> None:
    project, scene, *_ = earth_moon_project(duration_frames=90)
    project.title = "Titre confidentiel"
    scene.subtitles.append(Subtitle.create(0, 30, "Phrase privée du sous-titre"))
    project.assets.append(Asset(id="asset-000000000001", path="assets/photo-secrete.png", kind="image"))
    root = Path.home() / "Projets" / "Démo.antares"
    target = tmp_path / "rapport.zip"
    files = write_incident_report(
        target, f"Système : test\nDossier : {Path.home()}/x", project, root, tmp_path
    )
    assert files == ["LISEZMOI.txt", "diagnostic.txt", "projet.txt"]  # pas de journal d'erreurs
    with zipfile.ZipFile(target) as zf:
        content = {n: zf.read(n).decode("utf-8") for n in zf.namelist()}
    everything = "".join(content.values())
    for secret in ("Titre confidentiel", "Phrase privée", "photo-secrete", str(Path.home())):
        assert secret not in everything
    assert "circle × 2" in content["projet.txt"] and "MANQUANTE" in content["projet.txt"]
    assert f"~{os.sep}Projets" in content["projet.txt"] and "~/x" in content["diagnostic.txt"]
    assert "n'a été envoyé nulle part" in content["LISEZMOI.txt"]
    assert not list(tmp_path.glob("*.part"))


def test_uncaught_errors_are_logged_bounded_and_included(tmp_path: Path) -> None:
    calls: list[str] = []
    previous = sys.excepthook
    sys.excepthook = lambda *a: calls.append("origine")  # type: ignore[assignment]
    try:
        install_exception_logger(tmp_path)
        try:
            raise RuntimeError("panne simulée pour le test")
        except RuntimeError as exc:
            sys.excepthook(type(exc), exc, exc.__traceback__)
    finally:
        sys.excepthook = previous
    assert calls == ["origine"]  # le comportement d'origine reste appliqué
    log = (tmp_path / CRASH_LOG).read_text(encoding="utf-8")
    assert "RuntimeError: panne simulée pour le test" in log
    for _ in range(400):
        try:
            raise ValueError("é" * 1000)  # 2 octets par caractère : la borne est en octets, pas en caractères
        except ValueError as exc:
            record_exception(type(exc), exc, exc.__traceback__, tmp_path)
    raw = (tmp_path / CRASH_LOG).read_bytes()
    assert len(raw) <= MAX_LOG_BYTES and b"\r\n" not in raw
    raw.decode("utf-8")  # aucun caractère coupé
    files = write_incident_report(tmp_path / "r.zip", "diag", None, None, tmp_path)
    assert "erreurs.log" in files
    with zipfile.ZipFile(tmp_path / "r.zip") as zf:
        assert "Aucun projet ouvert" in zf.read("projet.txt").decode()

"""Rapport d'incident depuis l'interface, captures de recette (``--capture``), Inspecteur sans débordement."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QScrollArea

from antares_studio.app.main_window import MainWindow

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1500, 900)
    w.show()
    qtbot.waitExposed(w)
    return w


def test_incident_report_from_the_help_menu(window, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    window.add_template_scene("moon_phases")
    target = window.create_incident_report(str(tmp_path / "rapport"))
    assert target == tmp_path / "rapport.zip"
    with zipfile.ZipFile(target) as zf:
        names = zf.namelist()
        diag = zf.read("diagnostic.txt").decode("utf-8")
    assert {"LISEZMOI.txt", "diagnostic.txt", "projet.txt"} <= set(names)
    assert "ANTARES Studio" in diag and "Qt" in diag
    assert "rapport.zip" in window.statusBar().currentMessage()
    help_menu = next(a.menu() for a in window.menuBar().actions() if a.text().replace("&", "") == "Aide")
    assert window.act_incident in help_menu.actions()


def test_scene_inspector_never_scrolls_horizontally(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    window.add_template_scene("moon_phases")
    window.document.set_selection([])
    qtbot.wait(50)
    area = window.inspector.findChild(QScrollArea)
    assert area is not None and area.horizontalScrollBar().maximum() == 0


def test_capture_writes_every_screen_and_keeps_settings_isolated(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    import os

    from antares_studio.app.cli import run_cli

    before = os.environ.get("ANTARES_SETTINGS_DIR")
    assert run_cli(["--capture", str(tmp_path / "captures")]) == 0
    assert os.environ.get("ANTARES_SETTINGS_DIR") == before  # préférences des tests intactes
    images = sorted((tmp_path / "captures").glob("*.png"))
    assert len(images) == 9 and images[0].name == "01-editeur-sombre.png"
    assert all(p.stat().st_size > 5000 for p in images)
    info = (tmp_path / "captures" / "captures.txt").read_text(encoding="utf-8")
    assert "Écran :" in info and "rapport de pixels" in info

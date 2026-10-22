"""Captures des écrans principaux pour la recette visuelle (option ``--capture DOSSIER``).

Destinées à la liste de contrôle Windows 11 (``docs/recette-windows-11.md``) : la personne qui teste
lance la commande sur sa machine, compare chaque image aux points de la liste et joint le dossier.
Les préférences sont isolées dans un dossier temporaire : rien n'est lu ni modifié chez l'utilisateur.
Le projet montré est le modèle intégré « Phases de la Lune », sans ressource externe.
"""

from __future__ import annotations

import os
import platform
import tempfile
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QApplication, QWidget

from antares_studio import __version__


def _settle(app: QApplication, n: int = 8) -> None:
    for _ in range(n):
        app.processEvents()


def capture_screens(folder: Path) -> list[Path]:
    """Écrit les captures et ``captures.txt`` (système, écran, échelle) ; retourne les images écrites."""
    previous = os.environ.get("ANTARES_SETTINGS_DIR")
    os.environ["ANTARES_SETTINGS_DIR"] = tempfile.mkdtemp(prefix="antares-capture-")
    try:
        return _capture(folder)
    finally:
        if previous is None:
            os.environ.pop("ANTARES_SETTINGS_DIR", None)
        else:
            os.environ["ANTARES_SETTINGS_DIR"] = previous


def _capture(folder: Path) -> list[Path]:
    from antares_studio.app.main import create_app

    app = create_app([])
    from antares_studio.app.curve_editor import CurveEditorDialog
    from antares_studio.app.document import ProjectDocument
    from antares_studio.app.export_dialog import ExportDialog
    from antares_studio.app.main_window import MainWindow
    from antares_studio.app.units_dialog import UnitsDialog
    from antares_studio.app.welcome import WelcomeDialog
    from antares_studio.domain.model import Canvas
    from antares_studio.resources.templates import create_project

    folder.mkdir(parents=True, exist_ok=True)
    window = MainWindow()
    window.resize(1500, 900)
    window.show()
    window._set_document(ProjectDocument(create_project("Phases de la Lune", Canvas(), "moon_phases", 20)))
    window.document.set_frame(120)
    _settle(app)
    window.canvas.fit_to_view()
    _settle(app)
    written: list[Path] = []

    def shot(name: str, widget: QWidget) -> None:
        _settle(app)
        path = folder / f"{len(written) + 1:02d}-{name}.png"
        widget.grab().save(str(path))
        written.append(path)

    def dialog(name: str, factory: Callable[[], QWidget]) -> None:
        dlg = factory()
        dlg.show()
        shot(name, dlg)
        dlg.close()

    shot("editeur-sombre", window)
    window.set_theme("clair")
    shot("editeur-clair", window)
    window.set_theme("sombre")
    window.set_font_scale(150)
    shot("editeur-texte-150", window)
    window.set_font_scale(100)
    window.narration_dock.raise_()
    shot("narration", window)
    window.timeline_dock.raise_()
    dialog("accueil", lambda: WelcomeDialog([], {"interface"}, True, True, window))
    dialog(
        "export", lambda: ExportDialog(window.document, window.settings, window, queue=window.export_queue)
    )
    dialog("constantes-unites", lambda: UnitsDialog(window))
    dialog("courbe-interpolation", lambda: CurveEditorDialog([0.25, 0.1, 0.25, 1.0], window))
    center = window.show_help("export-video")
    center.resize(1100, 760)
    shot("centre-aide", center)
    center.close()
    screen = app.primaryScreen()
    info = [
        f"ANTARES Studio {__version__}",
        f"Système : {platform.system()} {platform.release()} ({platform.version()})",
        f"Qt : {qVersion()} — plateforme : {app.platformName()}",
        f"Écran : {screen.size().width()}×{screen.size().height()} px logiques, "
        f"rapport de pixels {screen.devicePixelRatio():g}, {screen.logicalDotsPerInch():.0f} ppp",
        "Images : " + ", ".join(p.name for p in written),
    ]
    (folder / "captures.txt").write_text("\n".join(info) + "\n", encoding="utf-8")
    window.document.undo.mark_clean()
    window.close()
    return written

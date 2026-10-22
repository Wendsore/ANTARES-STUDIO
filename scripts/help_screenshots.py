"""Génère les illustrations de l'aide intégrée et les captures de documentation depuis l'interface réelle.

Usage : ``QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/help_screenshots.py [--docs DOSSIER]``.

- ``src/antares_studio/resources/help/images/interface.png`` : fenêtre annotée (zones numérotées 1 à 7,
  numéros identiques à la rubrique « L'espace de travail ») ;
- ``src/antares_studio/resources/help/images/timeline.png`` : la Timeline du modèle Phases de la Lune ;
- avec ``--docs`` : captures de l'accueil, du centre d'aide, d'un tutoriel en cours et des deux thèmes.

Les préférences Qt sont isolées dans un dossier temporaire : les réglages de l'utilisateur ne sont ni lus
ni modifiés. Le projet montré est le modèle intégré « Phases de la Lune », sans ressource externe.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRect, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HELP_IMAGES = ROOT / "src" / "antares_studio" / "resources" / "help" / "images"


def _settle(app: QApplication, n: int = 6) -> None:
    for _ in range(n):
        app.processEvents()


def _rect_in(window: QWidget, widget: QWidget) -> QRect:
    return QRect(widget.mapTo(window, widget.rect().topLeft()), widget.size())


def annotate(img: QImage, marks: list[tuple[int, QRect]]) -> QImage:
    """Pastilles numérotées (or ANTARES) au coin supérieur droit de chaque zone, cadre fin autour."""
    out = img.copy()
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(17)
    p.setFont(font)
    for number, rect in marks:
        p.setPen(QPen(QColor("#F2A93B"), 2, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(rect).adjusted(3, 3, -3, -3), 8, 8)
        # en haut à droite : le titre des panneaux (en haut à gauche) reste lisible
        r = min(15.0, rect.height() / 2 - 1)  # zones basses (barre d'état) : pastille réduite
        center = QPointF(rect.right() - 26, rect.top() + min(22.0, rect.height() / 2))
        p.setPen(QPen(QColor("#1A1200"), 2))
        p.setBrush(QColor("#F2A93B"))
        p.drawEllipse(center, r, r)
        badge = QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r)
        p.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(number))
    p.end()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--docs", type=Path, default=None, help="dossier des captures de documentation")
    args = parser.parse_args(argv)

    os.environ["ANTARES_SETTINGS_DIR"] = tempfile.mkdtemp(prefix="antares-shots-")
    sys.path.insert(0, str(ROOT / "src"))
    from antares_studio.app.document import ProjectDocument
    from antares_studio.app.main import create_app
    from antares_studio.app.main_window import MainWindow
    from antares_studio.domain.model import Canvas
    from antares_studio.resources.templates import create_project

    app = create_app([])
    window = MainWindow()
    window.settings.set_show_tips(False)  # aucune bulle d'astuce sur les illustrations
    window.resize(1500, 900)
    window.show()
    window._set_document(ProjectDocument(create_project("Phases de la Lune", Canvas(), "moon_phases", 20)))
    window.document.set_frame(120)
    moon = next(n for n in window.document.scene.nodes if n.name == "Lune")  # type: ignore[union-attr]
    window.document.set_selection([moon.id])
    _settle(app)
    window.canvas.fit_to_view()
    _settle(app)

    HELP_IMAGES.mkdir(parents=True, exist_ok=True)
    shot = window.grab().toImage()
    toolbar_rect = QRect(0, 0, window.width(), window.toolbar.geometry().bottom())
    marks = [
        (1, toolbar_rect),
        (2, _rect_in(window, window.library_dock)),
        (3, _rect_in(window, window.layers_dock)),
        (4, _rect_in(window, window.canvas)),
        (5, _rect_in(window, window.inspector_dock)),
        (6, _rect_in(window, window.timeline_dock)),
        (7, QRect(0, window.statusBar().geometry().top(), window.width(), window.statusBar().height())),
    ]
    annotate(shot, marks).scaledToWidth(1100, Qt.TransformationMode.SmoothTransformation).save(
        str(HELP_IMAGES / "interface.png")
    )
    window.timeline_dock.grab().toImage().scaledToWidth(
        1000, Qt.TransformationMode.SmoothTransformation
    ).save(str(HELP_IMAGES / "timeline.png"))
    print("aide :", HELP_IMAGES / "interface.png", HELP_IMAGES / "timeline.png")

    if args.docs is not None:
        docs = args.docs
        docs.mkdir(parents=True, exist_ok=True)
        stamp = "2026-10-22"
        window.grab().save(str(docs / f"editeur-theme-sombre-{stamp}.png"))
        window.set_theme("clair")
        _settle(app)
        window.grab().save(str(docs / f"editeur-theme-clair-{stamp}.png"))
        window.set_theme("sombre")
        _settle(app)
        from antares_studio.app.welcome import WelcomeDialog

        welcome = WelcomeDialog(window.settings.recent_projects(), {"interface"}, True, True, window)
        welcome.show()
        _settle(app)
        welcome.grab().save(str(docs / f"accueil-{stamp}.png"))
        welcome.close()
        center = window.show_help("animations")
        center.resize(1100, 760)
        _settle(app)
        center.grab().save(str(docs / f"centre-aide-{stamp}.png"))
        center.close()
        window.start_tutorial("premiere-scene")
        _settle(app)
        window.add_node_of_kind("circle")
        window.tutorial.refresh()
        _settle(app)
        window.grab().save(str(docs / f"tutoriel-{stamp}.png"))
        print("documentation :", docs)
    window.document.undo.mark_clean()  # pas de question à la fermeture
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

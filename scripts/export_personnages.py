"""Archive les personnages du catalogue (fiches × proportions) en SVG et PNG.

    python scripts/export_personnages.py assets/personnages/archives

Les dessins sont produits par ``rendering.chibi.chibi_svg`` : ce sont des créations du projet,
sans ressource tierce.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from antares_studio.domain.characters import PERSONALITIES, PROPORTIONS
from antares_studio.rendering.chibi import chibi_svg


def main(out: Path) -> None:
    _app = QGuiApplication.instance() or QGuiApplication([])
    for proportions, _label in PROPORTIONS:
        folder = out / proportions
        folder.mkdir(parents=True, exist_ok=True)
        for fiche in PERSONALITIES:
            svg = chibi_svg({**fiche.params, "proportions": proportions}, fiche.style)
            (folder / f"{fiche.id}.svg").write_text(svg, encoding="utf-8")
            img = QImage(800, 1120, QImage.Format.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, 800, 1120))
            painter.end()
            img.save(str(folder / f"{fiche.id}.png"))
            print(folder / fiche.id)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

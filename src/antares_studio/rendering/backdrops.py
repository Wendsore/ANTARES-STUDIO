"""Décors de fond procéduraux (tableau noir, papier quadrillé, plan, ciel étoilé…).

Dessinés par le logiciel à la taille de sortie, sans image à fournir ni licence à vérifier, et mis en
cache : une scène de 10 000 images ne recalcule son décor qu'une fois. Le hasard (traces de craie,
étoiles) est tiré d'une graine fixe : deux exports sont identiques.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen

from antares_studio.domain.model import BACKDROPS

MAX_SIDE = 3840


def paint_backdrop(painter: QPainter, kind: str, width: int, height: int) -> None:
    """Peint le décor ``kind`` sur tout le rectangle ``width × height`` (rien si ``kind`` est vide)."""
    if not kind or kind not in BACKDROPS or width < 1 or height < 1:
        return
    # éditeur très zoomé : décor calculé en 4K au plus puis agrandi (mémoire bornée)
    shrink = min(1.0, MAX_SIDE / max(width, height))
    gw, gh = max(1, round(width * shrink)), max(1, round(height * shrink))
    painter.drawImage(QRectF(0, 0, width, height), backdrop_image(kind, gw, gh))


@lru_cache(maxsize=6)
def backdrop_image(kind: str, width: int, height: int) -> QImage:
    img = QImage(width, height, QImage.Format.Format_RGBA8888_Premultiplied)
    u = height / 1080.0  # unité : les décors gardent leurs proportions à toutes les définitions
    if kind in ("chalkboard_black", "chalkboard_green"):
        _chalkboard(img, "#1D2120" if kind == "chalkboard_black" else "#23392E", u)
        return img
    painter = QPainter(img)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if kind == "grid_paper":
            img.fill(QColor("#FBFBF6"))
            _lines(painter, width, height, 36 * u, QColor(110, 160, 210, 70), 1.0 * u, both=True)
            _lines(painter, width, height, 180 * u, QColor(90, 140, 200, 120), 1.6 * u, both=True)
        elif kind == "lined_paper":
            img.fill(QColor("#FCFAF2"))
            _lines(
                painter, width, height, 54 * u, QColor(90, 140, 210, 110), 1.4 * u, both=False, start=140 * u
            )
            painter.setPen(QPen(QColor(220, 70, 80, 150), 2.0 * u))
            painter.drawLine(QPointF(170 * u, 0), QPointF(170 * u, height))
        elif kind == "blueprint":
            img.fill(QColor("#1B4F8C"))
            _lines(painter, width, height, 40 * u, QColor(255, 255, 255, 28), 1.0 * u, both=True)
            _lines(painter, width, height, 200 * u, QColor(255, 255, 255, 60), 1.6 * u, both=True)
        elif kind == "starfield":
            img.fill(QColor("#04060D"))
            _stars(painter, width, height, u)
    finally:
        painter.end()
    return img


def _lines(
    painter: QPainter,
    width: int,
    height: int,
    step: float,
    color: QColor,
    pen_width: float,
    both: bool,
    start: float = 0.0,
) -> None:
    painter.setPen(QPen(color, max(0.6, pen_width)))
    y = start or step
    while y < height:
        painter.drawLine(QPointF(0, y), QPointF(width, y))
        y += step
    if both:
        x = step
        while x < width:
            painter.drawLine(QPointF(x, 0), QPointF(x, height))
            x += step


def _stars(painter: QPainter, width: int, height: int, u: float) -> None:
    rng = np.random.default_rng(42)
    count = int(width * height / (1920 * 1080) * 900)
    xs = rng.random(count) * width
    ys = rng.random(count) * height
    mags = rng.random(count) ** 3  # beaucoup d'étoiles faibles, peu de brillantes
    tints = rng.integers(0, 10, count)
    painter.setPen(Qt.PenStyle.NoPen)
    for x, y, m, t in zip(xs, ys, mags, tints, strict=True):
        r = (0.5 + 2.2 * m) * u
        color = QColor("#FFFFFF") if t < 7 else QColor("#BFD7FF") if t < 9 else QColor("#FFD9A8")
        color.setAlphaF(0.25 + 0.75 * float(m))
        painter.setBrush(color)
        painter.drawEllipse(QPointF(float(x), float(y)), r, r)


def _chalkboard(img: QImage, base: str, u: float) -> None:
    """Ardoise : teinte de base, voile de craie effacée (bruit basse fréquence, traînées horizontales
    de chiffon), grain fin et bords plus sombres."""
    w, h = img.width(), img.height()
    rng = np.random.default_rng(7)
    c = QColor(base)
    rgb = np.array([c.redF(), c.greenF(), c.blueF()], dtype=np.float32)
    # voile : bruit grossier agrandi en douceur, étiré horizontalement (coups de chiffon)
    gw, gh = max(2, int(w / (u * 90))), max(2, int(h / (u * 30)))
    coarse = rng.random((gh, gw)).astype(np.float32)
    small = QImage(
        np.ascontiguousarray((coarse * 255).astype(np.uint8)).data,
        gw,
        gh,
        gw,
        QImage.Format.Format_Grayscale8,
    ).copy()
    big = small.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    big = big.convertToFormat(QImage.Format.Format_Grayscale8)
    buf = np.frombuffer(big.constBits(), dtype=np.uint8, count=big.bytesPerLine() * h)
    haze = buf.reshape(h, big.bytesPerLine())[:, :w].astype(np.float32) / 255.0
    haze = np.clip((haze - 0.45) * 1.6, 0.0, 1.0) ** 1.5
    grain = rng.random((h, w), dtype=np.float32)
    xx = (np.arange(w, dtype=np.float32) - w / 2) / (w / 2)
    yy = (np.arange(h, dtype=np.float32) - h / 2) / (h / 2)
    edge = np.sqrt(xx[None, :] ** 2 * 0.6 + yy[:, None] ** 2 * 0.6)
    shade = 1.0 - 0.28 * np.clip(edge - 0.45, 0.0, 1.0)
    chalk = 0.07 * haze + 0.025 * grain  # poussière blanche
    out = (rgb[None, None, :] * (shade * (0.94 + 0.08 * grain))[..., None]) + chalk[..., None]
    out = np.clip(out, 0.0, 1.0)
    rgba = np.concatenate([out, np.ones((h, w, 1), dtype=np.float32)], axis=-1)
    data = np.ascontiguousarray((rgba * 255 + 0.5).astype(np.uint8))
    tmp = QImage(data.data, w, h, w * 4, QImage.Format.Format_RGBA8888_Premultiplied)
    painter = QPainter(img)
    try:
        painter.drawImage(0, 0, tmp)
    finally:
        painter.end()

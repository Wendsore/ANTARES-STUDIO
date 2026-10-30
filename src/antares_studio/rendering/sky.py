"""Ciel étoilé réel : 5 044 étoiles (Hipparcos, magnitude ≤ 6) et 88 constellations (ADR-0009).

Projection stéréographique centrée sur (ascension droite, déclinaison) avec un champ ``fov_deg`` sur la
largeur ; l'est est à gauche, comme sur une carte du ciel tenue au-dessus de la tête. Taille des étoiles
selon la magnitude, couleur selon l'indice B−V (température de Ballesteros → corps noir).
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from antares_studio.resources.astro import constellations, star_name_fr, stars
from antares_studio.science.light import blackbody_rgb, bv_to_temperature

Array = Any


@lru_cache(maxsize=1)
def star_table() -> tuple[Array, Array, Array, Array, tuple[str, ...]]:
    """(ra rad, dec rad, magnitude, couleurs RGB 0..1, noms français ou '')."""
    rows, names = stars()
    ra = np.radians(np.array([r[1] for r in rows], dtype=np.float64))
    dec = np.radians(np.array([r[2] for r in rows], dtype=np.float64))
    mag = np.array([r[3] for r in rows], dtype=np.float64)
    cols = []
    for r in rows:
        bv = r[4] if r[4] is not None else 0.6
        rgb = blackbody_rgb(round(bv_to_temperature(max(-0.4, min(2.0, float(bv)))), -1))
        # les étoiles paraissent peu saturées à l'œil : mélange avec le blanc
        cols.append([0.45 * c + 0.55 for c in rgb])
    label = tuple(star_name_fr(names.get(str(r[0]), "")) for r in rows)
    return ra, dec, mag, np.array(cols), label


def stereographic(ra: Array, dec: Array, ra0: float, dec0: float) -> tuple[Array, Array, Array]:
    """→ (x, y vers le haut, cos c) en unités de la projection ; est à gauche."""
    dra = ra - ra0
    cos_c = math.sin(dec0) * np.sin(dec) + math.cos(dec0) * np.cos(dec) * np.cos(dra)
    k = 2.0 / np.maximum(1.0 + cos_c, 1e-6)
    x = -k * np.cos(dec) * np.sin(dra)
    y = k * (math.cos(dec0) * np.sin(dec) - math.sin(dec0) * np.cos(dec) * np.cos(dra))
    return x, y, cos_c


def _view(params: dict[str, Any]) -> tuple[float, float, float, float, float, float]:
    w = max(10.0, float(params.get("width", 1600.0)))
    h = max(10.0, float(params.get("height", 900.0)))
    fov = max(1.0, min(220.0, float(params.get("fov_deg", 90.0))))
    scale = (w / 2) / (2 * math.tan(math.radians(fov) / 4))
    return (
        w,
        h,
        scale,
        math.radians(float(params.get("center_ra_deg", 85.0))),
        math.radians(float(params.get("center_dec_deg", 0.0))),
        math.radians(float(params.get("field_rotation_deg", 0.0))),
    )


def _to_screen(x: Array, y: Array, scale: float, rot: float) -> tuple[Array, Array]:
    c, s = math.cos(rot), math.sin(rot)
    return (x * c - y * s) * scale, -(x * s + y * c) * scale


def paint_sky(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    w, h, scale, ra0, dec0, rot = _view(params)
    painter.save()
    painter.setClipRect(QRectF(-w / 2, -h / 2, w, h))
    bg = qcolor(style.get("fill", "#00000000"))
    if bg.alpha() > 0:
        painter.fillRect(QRectF(-w / 2, -h / 2, w, h), bg)
    mag_limit = float(params.get("mag_limit", 5.5))
    star_scale = float(params.get("star_scale", 1.0))
    highlight = str(params.get("highlight", ""))

    if bool(params.get("show_lines", True)):
        base = qcolor(style.get("line_color", "#7FB3FF66"))
        hl = qcolor(style.get("highlight_color", "#FFD27A"))
        lw = float(style.get("line_width", 1.6))
        for con in constellations():
            on = con["id"] == highlight
            if highlight and not on and not bool(params.get("show_all_lines", True)):
                continue
            pen = QPen(hl if on else base, lw * (1.8 if on else 1.0))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            for line in con["lines"]:
                arr = np.radians(np.asarray(line, dtype=np.float64))
                x, y, cc = stereographic(arr[:, 0], arr[:, 1], ra0, dec0)
                sx, sy = _to_screen(x, y, scale, rot)
                for i in range(len(sx) - 1):
                    if cc[i] > -0.3 and cc[i + 1] > -0.3:
                        painter.drawLine(QPointF(sx[i], sy[i]), QPointF(sx[i + 1], sy[i + 1]))

    ra, dec, mag, cols, names = star_table()
    x, y, cc = stereographic(ra, dec, ra0, dec0)
    sx, sy = _to_screen(x, y, scale, rot)
    keep = (mag <= mag_limit) & (cc > -0.3) & (np.abs(sx) <= w / 2 + 10) & (np.abs(sy) <= h / 2 + 10)
    idx = np.nonzero(keep)[0]
    idx = idx[np.argsort(-mag[idx])]  # faibles d'abord, brillantes par-dessus
    painter.setPen(Qt.PenStyle.NoPen)
    twinkle = float(params.get("twinkle", 0.0))
    t = float(params.get("time_s", 0.0))
    for i in idx:
        r = star_scale * 0.9 * max(0.35, (mag_limit + 1.2 - mag[i]) ** 1.15) * 0.55
        if twinkle > 0:
            r *= 1.0 + twinkle * 0.25 * math.sin(7.3 * t + i * 1.618)
        c = QColor.fromRgbF(*(float(v) for v in cols[i]))
        if mag[i] < 1.5:  # halo des étoiles les plus brillantes
            halo = QColor(c)
            halo.setAlphaF(0.18)
            painter.setBrush(halo)
            painter.drawEllipse(QPointF(sx[i], sy[i]), r * 2.6, r * 2.6)
        painter.setBrush(c)
        painter.drawEllipse(QPointF(sx[i], sy[i]), r, r)

    font = QFont(str(params.get("font_family", "DejaVu Sans")))
    if bool(params.get("show_star_names", True)):
        name_mag = float(params.get("name_mag_limit", 1.6))
        font.setPixelSize(max(6, int(float(params.get("label_size", 22.0)))))
        painter.setFont(font)
        painter.setPen(QPen(qcolor(style.get("label_color", "#E8EEF9CC"))))
        for i in idx:
            if mag[i] <= name_mag and names[i]:
                painter.drawText(QPointF(sx[i] + 10, sy[i] - 8), names[i])
    if bool(params.get("show_constellation_names", True)):
        font.setPixelSize(max(6, int(float(params.get("label_size", 22.0)) * 1.05)))
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 112)
        painter.setFont(font)
        for con in constellations():
            if highlight and con["id"] != highlight and not bool(params.get("show_all_lines", True)):
                continue
            lra, ldec = (math.radians(float(v)) for v in con["label"])
            x1, y1, c1 = stereographic(np.array([lra]), np.array([ldec]), ra0, dec0)
            if c1[0] < 0:
                continue
            px, py = _to_screen(x1, y1, scale, rot)
            on = con["id"] == highlight
            painter.setPen(
                QPen(
                    qcolor(
                        style.get("highlight_color", "#FFD27A")
                        if on
                        else style.get("constellation_label_color", "#9FC7EE99")
                    )
                )
            )
            painter.drawText(
                QRectF(float(px[0]) - 160, float(py[0]) - 16, 320, 32),
                int(Qt.AlignmentFlag.AlignCenter),
                con["fr"].upper(),
            )
    painter.restore()


def sky_bounds(params: dict[str, Any]) -> QRectF:
    w = max(10.0, float(params.get("width", 1600.0)))
    h = max(10.0, float(params.get("height", 900.0)))
    return QRectF(-w / 2, -h / 2, w, h)


def constellation_center(con_id: str) -> tuple[float, float] | None:
    """Point d'étiquette (ascension droite °, déclinaison °) de la constellation, pour la centrer."""
    for con in constellations():
        if con["id"] == con_id:
            return float(con["label"][0]), float(con["label"][1])
    return None

"""Grille de coordonnées animable : transformation linéaire (matrice 2 × 2, comme dans « Essence of
linear algebra » de 3Blue1Brown) puis déformation non linéaire (puits de gravité, onde, tourbillon),
vue de dessus ou en perspective (nappe d'espace-temps creusée par une masse).

La géométrie est calculée en NumPy (``grid_geometry``, testable sans affichage) ; ``paint_grid`` la
dessine avec QPainter. Unités : un carreau = ``step`` pixels ; la matrice agit sur les coordonnées
mathématiques (y vers le haut), si bien que [[1, 1], [0, 1]] penche la grille vers la droite.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from antares_studio.rendering.writing import unit_progress

Points = np.ndarray[Any, np.dtype[np.float64]]

MAX_LINES = 400  # garde-fou : un pas minuscule sur un grand cadre ne gèle pas le rendu
SAMPLES_PER_STEP = 8  # points par carreau : lignes courbes lisses après déformation


@dataclass
class GridGeometry:
    lines: list[Points] = field(default_factory=list)  # lignes de la grille, (N, 2) px écran
    order: list[float] = field(default_factory=list)  # distance au centre (ordre du tracé progressif)
    axes: list[Points] = field(default_factory=list)
    ghost: list[Points] = field(default_factory=list)  # grille d'origine (filigrane)
    basis: list[tuple[Points, str]] = field(default_factory=list)  # (polyligne, "i" | "j")
    frame: tuple[float, float] = (0.0, 0.0)  # largeur, hauteur du cadre


def _f(params: dict[str, Any], name: str, default: float) -> float:
    try:
        v = float(params.get(name, default))
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def matrix(params: dict[str, Any]) -> Points:
    return np.array(
        [[_f(params, "m_a", 1.0), _f(params, "m_b", 0.0)], [_f(params, "m_c", 0.0), _f(params, "m_d", 1.0)]]
    )


def is_deformed(params: dict[str, Any]) -> bool:
    warped = str(params.get("warp", "none")) != "none" and abs(_f(params, "warp_amount", 0.0)) > 1e-9
    return warped or not np.allclose(matrix(params), np.eye(2))


def transform(params: dict[str, Any], pts: Points) -> tuple[Points, Points]:
    """Points de la grille (unités mathématiques, y vers le haut) -> (position dans le plan en px, y écran
    vers le bas ; hauteur z en px pour la vue en perspective)."""
    step = max(1.0, _f(params, "step", 100.0))
    q = pts @ matrix(params).T * step
    q[:, 1] *= -1.0  # y écran vers le bas
    z = np.zeros(len(q))
    warp = str(params.get("warp", "none"))
    amount = _f(params, "warp_amount", 0.0)
    radius = max(1.0, _f(params, "warp_radius", 250.0))
    persp = bool(params.get("perspective", False))
    if warp == "none" or amount == 0.0:
        return q, z
    r2 = np.sum(q * q, axis=1)
    r = np.sqrt(r2)
    if warp == "gravity":
        if persp:  # creux en 1/r adouci, comme le potentiel d'une masse
            z = -amount * radius * 1.6 * radius / np.sqrt(r2 + radius * radius)
        else:  # vue de dessus : l'espace est tiré vers la masse
            q = q * (1.0 - amount * radius * radius / (r2 + radius * radius))[:, None]
    elif warp == "wave":
        phase = 2.0 * math.pi * _f(params, "warp_phase", 0.0)
        ripple = np.sin(2.0 * math.pi * r / radius - phase) * np.exp(-r / (radius * 6.0))
        if persp:
            z = amount * radius * 0.25 * ripple
        else:
            safe = np.where(r > 1e-9, r, 1.0)
            q = q + (q / safe[:, None]) * (amount * step * 0.3 * ripple)[:, None]
    elif warp == "swirl":
        theta = amount * math.pi * np.exp(-r2 / (radius * radius))
        c, s = np.cos(theta), np.sin(theta)
        q = np.stack([q[:, 0] * c - q[:, 1] * s, q[:, 0] * s + q[:, 1] * c], axis=1)
    return q, z


def project(params: dict[str, Any], q: Points, z: Points) -> Points:
    """Plan -> écran. Vue de dessus : identité ; perspective : nappe inclinée de ``tilt_deg`` vue par une
    caméra placée devant (le haut de l'écran est le fond)."""
    if not bool(params.get("perspective", False)):
        return q
    t = math.radians(max(0.0, min(85.0, _f(params, "tilt_deg", 60.0))))
    focal = 1.6 * max(_f(params, "width", 1600.0), _f(params, "height", 900.0))
    y = q[:, 1] * math.cos(t) - z * math.sin(t)
    depth = -q[:, 1] * math.sin(t) - z * math.cos(t)
    s = focal / np.maximum(focal * 0.15, focal + depth)
    return np.stack([q[:, 0] * s, y * s], axis=1)


def grid_geometry(params: dict[str, Any]) -> GridGeometry:
    w = max(1.0, _f(params, "width", 1600.0))
    h = max(1.0, _f(params, "height", 900.0))
    step = max(1.0, _f(params, "step", 100.0))
    persp = bool(params.get("perspective", False))
    geo = GridGeometry(frame=(w, h))
    # étendue en unités : les lignes dont l'image peut traverser le cadre, c'est-à-dire l'antécédent des
    # coins du cadre par la matrice (une rotation d'un quart de tour échange largeur et hauteur)
    hx, hy = w / 2 / step, h / 2 / step
    nx, ny = math.ceil(hx), math.ceil(hy)
    if not persp:
        corners = np.array([[hx, hy], [hx, -hy], [-hx, hy], [-hx, -hy]])
        try:
            pre = corners @ np.linalg.inv(matrix(params)).T
            limit = 6.0 * max(hx, hy)  # matrice presque dégénérée : étendue bornée
            nx = math.ceil(min(limit, float(np.max(np.abs(pre[:, 0])))) + 1)
            ny = math.ceil(min(limit, float(np.max(np.abs(pre[:, 1])))) + 1)
        except np.linalg.LinAlgError:
            nx, ny = math.ceil(4 * max(hx, hy)), math.ceil(4 * max(hx, hy))
    else:
        ny = math.ceil(h / step)  # nappe plus profonde que haute : on la voit de biais
    while (2 * nx + 1) + (2 * ny + 1) > MAX_LINES:
        nx, ny = max(1, nx // 2), max(1, ny // 2)
    xs_span, ys_span = float(nx), float(ny)
    samples_x = max(2, int(2 * nx * SAMPLES_PER_STEP) + 1)
    samples_y = max(2, int(2 * ny * SAMPLES_PER_STEP) + 1)
    tx = np.linspace(-xs_span, xs_span, min(samples_x, 1200))
    ty = np.linspace(-ys_span, ys_span, min(samples_y, 1200))

    def line(pts: Points) -> Points:
        q, z = transform(params, pts)
        return project(params, q, z)

    for i in range(-nx, nx + 1):  # verticales x = i
        pts = np.stack([np.full_like(ty, float(i)), ty], axis=1)
        target = geo.axes if i == 0 else geo.lines
        target.append(line(pts))
        if i != 0:
            geo.order.append(abs(i) * step)
    for j in range(-ny, ny + 1):  # horizontales y = j
        pts = np.stack([tx, np.full_like(tx, float(j))], axis=1)
        target = geo.axes if j == 0 else geo.lines
        target.append(line(pts))
        if j != 0:
            geo.order.append(abs(j) * step + 0.5)
    if bool(params.get("show_ghost", True)) and not persp and is_deformed(params):
        gx, gy = math.ceil(w / 2 / step), math.ceil(h / 2 / step)
        for i in range(-gx, gx + 1):
            geo.ghost.append(np.array([[i * step, -gy * step], [i * step, gy * step]], dtype=float))
        for j in range(-gy, gy + 1):
            geo.ghost.append(np.array([[-gx * step, j * step], [gx * step, j * step]], dtype=float))
    if bool(params.get("show_basis", False)):
        for name, vec in (("i", (1.0, 0.0)), ("j", (0.0, 1.0))):
            u = np.linspace(0.0, 1.0, 24)[:, None] * np.array(vec)[None, :]
            geo.basis.append((line(u), name))
    return geo


def _polyline(pts: Points, fraction: float = 1.0) -> QPolygonF:
    n = len(pts)
    if fraction < 1.0:
        n = max(2, int(math.ceil(n * fraction)))
    return QPolygonF([QPointF(float(x), float(y)) for x, y in pts[:n]])


def grid_rect(params: dict[str, Any]) -> QRectF:
    w, h = _f(params, "width", 1600.0), _f(params, "height", 900.0)
    return QRectF(-w / 2, -h / 2, w, h)


def paint_grid(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    geo = grid_geometry(params)
    progress = max(0.0, min(1.0, _f(params, "progress", 1.0)))
    if progress <= 0.0:
        return
    width = max(0.0, float(style.get("stroke_width", 2.0) or 0.0))
    painter.save()
    if not bool(params.get("perspective", False)):
        painter.setClipRect(grid_rect(params), Qt.ClipOperation.IntersectClip)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if geo.ghost:
        painter.setPen(QPen(qcolor(style.get("ghost_color", "#FFFFFF30")), max(1.0, width * 0.6)))
        for pts in geo.ghost:
            painter.drawPolyline(_polyline(pts, progress))
    # tracé progressif : les lignes proches du centre d'abord, chacune de bout en bout
    ranked = sorted(range(len(geo.lines)), key=lambda k: geo.order[k])
    pen = QPen(qcolor(style.get("stroke", "#4FC3F7")), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    if width > 0:
        for rank, k in enumerate(ranked):
            u = unit_progress(progress, rank, len(ranked), max(1.0, len(ranked) * 0.6))
            if u > 0:
                painter.drawPolyline(_polyline(geo.lines[k], u))
    if bool(params.get("show_axes", True)):
        painter.setPen(QPen(qcolor(style.get("axis_color", "#FFFFFF")), max(1.0, width * 1.5)))
        for pts in geo.axes:
            painter.drawPolyline(_polyline(pts, min(1.0, progress * 2.0)))
    painter.restore()
    for pts, name in geo.basis:  # flèches î, ĵ (hors découpage : la pointe peut dépasser du cadre)
        _arrow(painter, pts, qcolor(style.get(f"{name}_color", "#83C167")), max(3.0, width * 2.5), progress)


def _arrow(painter: QPainter, pts: Points, color: QColor, width: float, progress: float) -> None:
    if progress <= 0 or len(pts) < 2:
        return
    end = pts[max(1, int(round((len(pts) - 1) * progress)))]
    before = pts[max(0, int(round((len(pts) - 1) * progress)) - 1)]
    head = width * 4.0
    dx, dy = float(end[0] - before[0]), float(end[1] - before[1])
    norm = math.hypot(dx, dy) or 1.0
    ux, uy = dx / norm, dy / norm
    path = QPainterPath(QPointF(float(pts[0][0]), float(pts[0][1])))
    for x, y in pts[1 : max(2, int(round((len(pts) - 1) * progress)))]:
        path.lineTo(float(x), float(y))
    path.lineTo(float(end[0]) - ux * head * 0.8, float(end[1]) - uy * head * 0.8)
    painter.save()
    painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
    tip = QPointF(float(end[0]), float(end[1]))  # la pointe finit exactement au bout du vecteur
    left = QPointF(tip.x() - ux * head - uy * head * 0.45, tip.y() - uy * head + ux * head * 0.45)
    right = QPointF(tip.x() - ux * head + uy * head * 0.45, tip.y() - uy * head - ux * head * 0.45)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPolygon(QPolygonF([tip, left, right]))
    painter.restore()

"""Optique : rayons lumineux, éléments d'optique, écran de détection de photons (ADR-0009).

- **Rayon** : ligne brisée (chemin passant par des miroirs, lames…) dessinée en faisceau, en onde
  (sinusoïde le long du chemin), en paquets d'onde, en photons (points), en pointillés ou avec flèches ;
  ``progress`` trace le chemin, ``phase`` fait défiler l'onde, ``photon_pos`` fait voyager les photons.
  La couleur peut venir d'une longueur d'onde réelle (``wavelength_nm``, couleur de Bruton).
- **Élément d'optique** : laser, lampe, miroir, lame séparatrice, lentilles, fentes, écran, détecteur,
  prisme, polariseur ; ``active`` allume le laser ou fait clignoter le détecteur.
- **Écran de détection** : impacts de photons tirés un à un selon la loi d'intensité réelle — deux fentes
  I(x) ∝ cos²(π·N·x)·sinc²(x/a), une fente sinc²(x/a), chemin connu (sans interférence) : somme des deux
  figures d'une fente. Montrer les impacts s'accumuler (``count``) fait voir la dualité onde-corpuscule :
  chaque photon arrive en un point, la figure d'interférence n'apparaît qu'avec le nombre.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)

from antares_studio.science.light import wavelength_rgb

Array = Any


def ray_color(params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> QColor:
    nm = float(params.get("wavelength_nm", 0.0) or 0.0)
    if nm > 0:
        r, g, b = wavelength_rgb(nm)
        if r + g + b > 0:
            return QColor.fromRgbF(r, g, b)
    return QColor(qcolor(style.get("stroke", "#FF5A4E")))


def _polyline(params: dict[str, Any]) -> list[tuple[float, float]]:
    pts = params.get("points") or [[0.0, 0.0], [600.0, 0.0]]
    return [(float(p[0]), float(p[1])) for p in pts]


def path_length(pts: list[tuple[float, float]]) -> float:
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def point_at(pts: list[tuple[float, float]], s: float) -> tuple[float, float, float, float]:
    """Point à l'abscisse curviligne ``s`` et direction unitaire (x, y, dx, dy)."""
    s = max(0.0, s)
    for i in range(len(pts) - 1):
        seg = math.dist(pts[i], pts[i + 1])
        if seg <= 1e-9:
            continue
        if s <= seg or i == len(pts) - 2:
            u = min(1.0, s / seg)
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, (x1 - x0) / seg, (y1 - y0) / seg
        s -= seg
    x, y = pts[-1]
    return x, y, 1.0, 0.0


def _truncated(pts: list[tuple[float, float]], length: float) -> list[tuple[float, float]]:
    out = [pts[0]]
    left = length
    for i in range(len(pts) - 1):
        seg = math.dist(pts[i], pts[i + 1])
        if left >= seg:
            out.append(pts[i + 1])
            left -= seg
            continue
        if seg > 0 and left > 0:
            u = left / seg
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            out.append((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u))
        break
    return out


def paint_ray(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    pts = _polyline(params)
    if len(pts) < 2:
        return
    total = path_length(pts)
    progress = max(0.0, min(1.0, float(params.get("progress", 1.0))))
    shown = total * progress
    mode = str(params.get("mode", "beam"))
    color = ray_color(params, style, qcolor)
    width = max(0.5, float(style.get("stroke_width", 4.0)))
    part = _truncated(pts, shown)
    painter.save()
    if mode == "beam":
        glow = QColor(color)
        glow.setAlphaF(0.22)
        pen = QPen(
            glow, width * 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin
        )
        painter.setPen(pen)
        painter.drawPolyline(QPolygonF([QPointF(x, y) for x, y in part]))
        core = QColor(color).lighter(135)
        painter.setPen(
            QPen(core, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        )
        painter.drawPolyline(QPolygonF([QPointF(x, y) for x, y in part]))
    elif mode in ("dashed", "arrows"):
        pen = QPen(color, width, Qt.PenStyle.DashLine if mode == "dashed" else Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPolyline(QPolygonF([QPointF(x, y) for x, y in part]))
        if mode == "arrows":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for i in range(len(part) - 1):
                (x0, y0), (x1, y1) = part[i], part[i + 1]
                seg = math.dist(part[i], part[i + 1])
                if seg < width * 6:
                    continue
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                dx, dy = (x1 - x0) / seg, (y1 - y0) / seg
                a = width * 3.2
                painter.drawPolygon(
                    QPolygonF(
                        [
                            QPointF(mx + dx * a, my + dy * a),
                            QPointF(mx - dx * a - dy * a * 0.8, my - dy * a + dx * a * 0.8),
                            QPointF(mx - dx * a + dy * a * 0.8, my - dy * a - dx * a * 0.8),
                        ]
                    )
                )
    elif mode == "wave":
        _paint_wave_along(painter, pts, 0.0, shown, params, color, width, envelope=None)
    elif mode in ("packets", "photons"):
        faint = QColor(color)
        faint.setAlphaF(0.18 * float(params.get("path_opacity", 1.0)))
        painter.setPen(QPen(faint, max(1.0, width * 0.5), Qt.PenStyle.DashLine))
        painter.drawPolyline(QPolygonF([QPointF(x, y) for x, y in part]))
        count = max(1, int(params.get("photon_count", 1)))
        pos = float(params.get("photon_pos", 0.0))
        spacing = 1.0 / count
        for i in range(count):
            u = pos - i * spacing
            if u < 0 or u > 1:
                continue
            s = u * total
            if s > shown + 1e-6:
                continue
            if mode == "photons":
                x, y, _dx, _dy = point_at(pts, s)
                r = max(3.0, float(params.get("photon_size", 10.0)))
                grad = QRadialGradient(QPointF(x, y), r * 2.6)
                c0, c1 = QColor(color).lighter(160), QColor(color)
                c1.setAlphaF(0.0)
                grad.setColorAt(0.0, QColor("#FFFFFF"))
                grad.setColorAt(0.25, c0)
                grad.setColorAt(1.0, c1)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(grad))
                painter.drawEllipse(QPointF(x, y), r * 2.6, r * 2.6)
            else:
                half = max(10.0, float(params.get("packet_length", 120.0))) / 2
                _paint_wave_along(
                    painter,
                    pts,
                    max(0.0, s - half),
                    min(shown, s + half),
                    params,
                    color,
                    width,
                    envelope=(s, half),
                )
    painter.restore()


def _paint_wave_along(
    painter: QPainter,
    pts: list[tuple[float, float]],
    s0: float,
    s1: float,
    params: dict[str, Any],
    color: QColor,
    width: float,
    envelope: tuple[float, float] | None,
) -> None:
    if s1 <= s0:
        return
    lam = max(4.0, float(params.get("wave_length_px", 40.0)))
    amp = float(params.get("amplitude", 14.0))
    phase = float(params.get("phase", 0.0))
    n = max(8, int((s1 - s0) / 2.5))
    poly = []
    for i in range(n + 1):
        s = s0 + (s1 - s0) * i / n
        x, y, dx, dy = point_at(pts, s)
        a = amp
        if envelope is not None:
            c, half = envelope
            a *= math.exp(-(((s - c) / (half * 0.55)) ** 2))
        off = a * math.sin(2 * math.pi * (s / lam - phase))
        poly.append(QPointF(x - dy * off, y + dx * off))
    pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPolyline(QPolygonF(poly))


def ray_bounds(params: dict[str, Any]) -> QRectF:
    pts = _polyline(params)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = abs(float(params.get("amplitude", 14.0))) + 30
    return QRectF(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)


# --- éléments d'optique ----------------------------------------------------------------------------


def paint_optic(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    el = str(params.get("element", "mirror"))
    s = max(4.0, float(params.get("size", 120.0)))
    active = max(0.0, min(1.0, float(params.get("active", 0.0))))
    fill = qcolor(style.get("fill", "#9FC7EE"))
    stroke = qcolor(style.get("stroke", "#E8EEF9"))
    lw = max(1.0, float(style.get("stroke_width", 3.0)))
    painter.save()
    pen = QPen(stroke, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    if el == "laser":
        body = QRectF(-s / 2, -s * 0.18, s, s * 0.36)
        grad = QLinearGradient(0, body.top(), 0, body.bottom())
        grad.setColorAt(0, QColor("#6B7A90"))
        grad.setColorAt(0.5, QColor("#AAB6C8"))
        grad.setColorAt(1, QColor("#4A566A"))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(body, s * 0.05, s * 0.05)
        painter.setBrush(QColor("#222831"))
        painter.drawRect(QRectF(s / 2 - s * 0.06, -s * 0.08, s * 0.08, s * 0.16))
        beam = qcolor(style.get("beam_color", "#FF3B30"))
        painter.setPen(Qt.PenStyle.NoPen)
        led = QColor(beam) if active > 0 else QColor("#3A3F47")
        painter.setBrush(led)
        painter.drawEllipse(QPointF(-s * 0.32, 0), s * 0.04, s * 0.04)
        if active > 0:
            _glow(painter, QPointF(s / 2 + s * 0.02, 0), s * 0.18 * active, beam)
    elif el == "lamp":
        painter.setBrush(QColor("#FFE9A8") if active > 0 else QColor("#7A7466"))
        painter.drawEllipse(QPointF(0, 0), s * 0.3, s * 0.3)
        if active > 0:
            _glow(painter, QPointF(0, 0), s * 0.7 * active, QColor("#FFE08A"))
    elif el in ("mirror", "beam_splitter", "polarizer"):
        t = s * 0.07
        rect = QRectF(-t / 2, -s / 2, t, s)
        if el == "mirror":
            painter.setBrush(fill)
            painter.drawRect(rect)
            hatch = QPen(stroke, max(1.0, lw * 0.6))
            painter.setPen(hatch)
            for i in range(9):
                y = -s / 2 + s * (i + 0.5) / 9
                painter.drawLine(QPointF(t / 2, y), QPointF(t / 2 + s * 0.08, y - s * 0.08))
        elif el == "beam_splitter":
            c = QColor(fill)
            c.setAlphaF(0.45)
            painter.setBrush(c)
            painter.drawRect(rect)
            painter.setPen(QPen(stroke, max(1.0, lw * 0.6), Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(0, -s / 2), QPointF(0, s / 2))
        else:
            c = QColor(fill)
            c.setAlphaF(0.35)
            painter.setBrush(c)
            painter.drawRect(QRectF(-t, -s / 2, 2 * t, s))
            painter.setPen(QPen(stroke, max(1.0, lw * 0.5)))
            for i in range(7):
                y = -s / 2 + s * (i + 0.5) / 7
                painter.drawLine(QPointF(-t, y), QPointF(t, y))
    elif el in ("lens_convex", "lens_concave"):
        path = QPainterPath()
        h2, bulge = s / 2, s * 0.16
        if el == "lens_convex":
            path.moveTo(0, -h2)
            path.quadTo(bulge * 2, 0, 0, h2)
            path.quadTo(-bulge * 2, 0, 0, -h2)
        else:
            path.moveTo(-bulge, -h2)
            path.lineTo(bulge, -h2)
            path.quadTo(0, 0, bulge, h2)
            path.lineTo(-bulge, h2)
            path.quadTo(0, 0, -bulge, -h2)
        c = QColor(fill)
        c.setAlphaF(0.4)
        painter.setBrush(c)
        painter.drawPath(path)
    elif el in ("double_slit", "single_slit", "screen"):
        t = s * 0.06
        painter.setBrush(fill if el != "screen" else QColor("#E8EEF2"))
        if el == "screen":
            painter.drawRect(QRectF(-t / 2, -s / 2, t, s))
        else:
            gap = s * float(params.get("slit_width", 0.05))
            sep = s * float(params.get("slit_separation", 0.22)) if el == "double_slit" else 0.0
            cuts = [(-sep / 2 - gap / 2, -sep / 2 + gap / 2), (sep / 2 - gap / 2, sep / 2 + gap / 2)]
            if el == "single_slit":
                cuts = [(-gap / 2, gap / 2)]
            y = -s / 2
            for a, b in cuts:
                painter.drawRect(QRectF(-t / 2, y, t, a - y))
                y = b
            painter.drawRect(QRectF(-t / 2, y, t, s / 2 - y))
    elif el == "detector":
        body = QRectF(-s * 0.3, -s * 0.3, s * 0.6, s * 0.6)
        painter.setBrush(QColor("#2B3442"))
        painter.drawRoundedRect(body, s * 0.08, s * 0.08)
        click = qcolor(style.get("beam_color", "#FFD27A"))
        painter.setBrush(click if active > 0 else QColor("#5A6575"))
        painter.drawEllipse(QPointF(-s * 0.3, 0), s * 0.1, s * 0.16)
        if active > 0:
            _glow(painter, QPointF(-s * 0.3, 0), s * 0.5 * active, click)
    elif el == "prism":
        tri = QPolygonF([QPointF(0, -s / 2), QPointF(s * 0.45, s * 0.35), QPointF(-s * 0.45, s * 0.35)])
        c = QColor(fill)
        c.setAlphaF(0.35)
        painter.setBrush(c)
        painter.drawPolygon(tri)
    painter.restore()


def _glow(painter: QPainter, center: QPointF, radius: float, color: QColor) -> None:
    if radius <= 0:
        return
    grad = QRadialGradient(center, radius)
    c0, c1 = QColor(color), QColor(color)
    c0.setAlphaF(0.85)
    c1.setAlphaF(0.0)
    grad.setColorAt(0.0, QColor("#FFFFFF"))
    grad.setColorAt(0.2, c0)
    grad.setColorAt(1.0, c1)
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(grad))
    painter.drawEllipse(center, radius, radius)
    painter.restore()


def optic_bounds(params: dict[str, Any]) -> QRectF:
    s = max(4.0, float(params.get("size", 120.0)))
    return QRectF(-s * 0.75, -s * 0.75, s * 1.5, s * 1.5)


# --- écran de détection -----------------------------------------------------------------------------


def intensity(pattern: str, x: Array, fringes: float, envelope: float) -> Array:
    """Loi d'intensité sur l'écran, x ∈ [−1, 1] (bords de l'écran)."""
    env = max(1e-3, envelope)
    single = np.sinc(x / env) ** 2
    if pattern == "two_slits":
        return np.cos(math.pi * fringes * x) ** 2 * single
    if pattern == "one_slit":
        return single
    if pattern == "which_path":
        shift = 0.5 / max(1e-3, fringes)  # demi-interfrange : la séparation des fentes
        return 0.5 * (np.sinc((x - shift) / env) ** 2 + np.sinc((x + shift) / env) ** 2)
    return np.ones_like(x)


@lru_cache(maxsize=16)
def impact_points(pattern: str, fringes: float, envelope: float, seed: int, n: int) -> Array:
    """``n`` impacts (x ∈ [−1, 1], y ∈ [−1, 1]) tirés par rejet selon ``intensity`` — reproductibles."""
    rng = np.random.default_rng(seed)
    out = np.empty((0, 2))
    while len(out) < n:
        x = rng.uniform(-1, 1, n * 3)
        keep = rng.uniform(0, 1, x.size) < intensity(pattern, x, fringes, envelope)
        y = rng.uniform(-1, 1, x.size)
        out = np.vstack([out, np.stack([x[keep], y[keep]], axis=1)])
    return out[:n]


def paint_impacts(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    w = max(10.0, float(params.get("width", 220.0)))
    h = max(10.0, float(params.get("height", 700.0)))
    vertical = bool(params.get("vertical", True))  # écran vertical : la figure s'étale en hauteur
    pattern = str(params.get("pattern", "two_slits"))
    fringes = max(0.1, float(params.get("fringes", 6.0)))
    envelope = max(0.02, float(params.get("envelope", 0.55)))
    max_count = max(1, min(50_000, int(params.get("max_count", 8000))))
    count = max(0, min(max_count, int(round(float(params.get("count", 2000))))))
    seed = int(params.get("seed", 1))
    bg = qcolor(style.get("fill", "#0A0E16"))
    dot = qcolor(style.get("dot_color", "#7CFFB2"))
    size = max(0.5, float(params.get("dot_size", 2.2)))
    painter.save()
    painter.setPen(QPen(qcolor(style.get("stroke", "#5A6575")), 2.0))
    painter.setBrush(bg)
    painter.drawRect(QRectF(-w / 2, -h / 2, w, h))
    pts = impact_points(pattern, round(fringes, 3), round(envelope, 3), seed, max_count)[:count]
    if count:
        xy = pts[:, ::-1] if vertical else pts
        sx = xy[:, 0] * (w / 2 - size)
        sy = xy[:, 1] * (h / 2 - size)
        # un point rond par impact (drawPoints : rapide même pour des dizaines de milliers)
        painter.setPen(QPen(dot, 2 * size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPoints(QPolygonF([QPointF(float(a), float(b)) for a, b in zip(sx, sy, strict=True)]))
        if bool(params.get("highlight_last", True)):
            painter.setPen(QPen(QColor("#FFFFFF"), 5 * size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawPoints(
                QPolygonF([QPointF(float(a), float(b)) for a, b in zip(sx[-1:], sy[-1:], strict=True)])
            )
    if bool(params.get("show_curve", False)):
        xs = np.linspace(-1, 1, 400)
        ys = intensity(pattern, xs, fringes, envelope)
        ys = ys / max(1e-9, float(ys.max()))
        pen = QPen(qcolor(style.get("curve_color", "#FFD27A")), 3.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        amp = float(params.get("curve_size", 160.0))
        if vertical:
            poly = [
                QPointF(w / 2 + 12 + float(v) * amp, float(x) * h / 2) for x, v in zip(xs, ys, strict=True)
            ]
        else:
            poly = [
                QPointF(float(x) * w / 2, -h / 2 - 12 - float(v) * amp) for x, v in zip(xs, ys, strict=True)
            ]
        painter.drawPolyline(QPolygonF(poly))
    painter.restore()


def impacts_bounds(params: dict[str, Any]) -> QRectF:
    w = max(10.0, float(params.get("width", 220.0)))
    h = max(10.0, float(params.get("height", 700.0)))
    rect = QRectF(-w / 2, -h / 2, w, h)
    if bool(params.get("show_curve", False)):
        amp = float(params.get("curve_size", 160.0)) + 16
        rect = (
            rect.adjusted(0, 0, amp, 0)
            if bool(params.get("vertical", True))
            else rect.adjusted(0, -amp, 0, 0)
        )
    return rect

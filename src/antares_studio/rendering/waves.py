"""Ondes : fronts circulaires (effet Doppler, cône de Mach), champ d'interférences, corde (ADR-0009).

Toutes les ondes sont pilotées par le temps ``time_s`` (animez-le avec le preset « Faire avancer le
temps ») ; les vitesses sont en pixels par seconde de ce temps, les fréquences en hertz.

- **Fronts** : la source part de l'origine de l'objet à ``source_speed`` dans la direction
  ``direction_deg`` ; le front émis à l'instant τₖ = k/f a pour rayon c·(t − τₖ) et pour centre la
  position de la source à τₖ. En avant de la source les fronts se resserrent (fréquence perçue
  f·c/(c − v)), en arrière ils s'espacent ; si v > c, ils s'enveloppent en un cône de demi-angle
  arcsin(c/v).
- **Champ** : somme de sources cohérentes A·cos(k·r − ω·t)/√r (deux sources = trous de Young),
  affichée en valeur instantanée ou en intensité moyenne (franges fixes).
- **Corde** : onde progressive y = A·sin(kx − ωt) ou stationnaire y = 2A·sin(kx)·cos(ωt).
"""

from __future__ import annotations

import math
from collections import OrderedDict
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF

from antares_studio.rendering.celestial import _qimage

Array = Any


def front_circles(params: dict[str, Any]) -> list[tuple[float, float, float, float]]:
    """Fronts visibles : (cx, cy, rayon, âge relatif 0..1), du plus ancien au plus récent."""
    t = max(0.0, float(params.get("time_s", 0.0)))
    c = max(1e-6, float(params.get("wave_speed", 200.0)))
    f = max(1e-6, float(params.get("frequency", 2.0)))
    v = float(params.get("source_speed", 0.0))
    a = math.radians(float(params.get("direction_deg", 0.0)))
    max_r = max(1.0, float(params.get("max_radius", 900.0)))
    follow = bool(params.get("follow_source", False))
    sx, sy = v * math.cos(a) * t, -v * math.sin(a) * t
    out = []
    k_max = int(math.floor(t * f + 1e-9))
    k_min = max(0, int(math.floor((t - max_r / c) * f)))
    for k in range(k_min, min(k_max, k_min + 2000) + 1):
        tau = k / f
        r = c * (t - tau)
        if r <= 0 or r > max_r:
            continue
        cx, cy = v * math.cos(a) * tau, -v * math.sin(a) * tau
        if follow:
            cx, cy = cx - sx, cy - sy
        out.append((cx, cy, r, r / max_r))
    return out


def source_position(params: dict[str, Any]) -> tuple[float, float]:
    if bool(params.get("follow_source", False)):
        return 0.0, 0.0
    t = max(0.0, float(params.get("time_s", 0.0)))
    v = float(params.get("source_speed", 0.0))
    a = math.radians(float(params.get("direction_deg", 0.0)))
    return v * math.cos(a) * t, -v * math.sin(a) * t


_FIELD_CACHE: OrderedDict[tuple[Any, ...], QImage] = OrderedDict()


def field_sources(params: dict[str, Any]) -> list[tuple[float, float]]:
    n = int(params.get("sources", 2))
    d = float(params.get("separation", 120.0))
    if n <= 1:
        return [(0.0, 0.0)]
    return [(0.0, (i - (n - 1) / 2) * d) for i in range(n)]


def field_image(
    params: dict[str, Any], px_w: int, px_h: int, colors: tuple[QColor, QColor, QColor]
) -> QImage:
    w = max(10.0, float(params.get("width", 1200.0)))
    h = max(10.0, float(params.get("height", 700.0)))
    lam = max(2.0, float(params.get("wavelength", 60.0)))
    c = max(1e-6, float(params.get("wave_speed", 200.0)))
    t = float(params.get("time_s", 0.0))
    display = str(params.get("display", "instant"))
    half = bool(params.get("half_plane", False))
    origin_x = float(params.get("source_x", -w / 2 + 60.0 if half else 0.0))
    key = (
        round(w),
        round(h),
        round(lam, 2),
        round(c, 2),
        round(t, 3) if display == "instant" else 0,
        display,
        half,
        round(origin_x, 1),
        tuple(field_sources(params)),
        px_w,
        px_h,
        tuple(q.rgba() for q in colors),
    )
    img = _FIELD_CACHE.get(key)
    if img is not None:
        return img
    xs = (np.arange(px_w) + 0.5) / px_w * w - w / 2
    ys = (np.arange(px_h) + 0.5) / px_h * h - h / 2
    x, y = np.meshgrid(xs, ys)
    k = 2 * math.pi / lam
    re = np.zeros_like(x)
    im = np.zeros_like(x)
    for sx, sy in field_sources(params):
        r = np.hypot(x - (origin_x + sx), y - sy)
        amp = 1.0 / np.sqrt(np.maximum(r, lam * 0.5) / lam)
        re += amp * np.cos(k * r)
        im += amp * np.sin(k * r)
    if display == "intensity":
        val = re**2 + im**2
        val = np.clip(val / max(1e-9, float(np.percentile(val, 99))), 0, 1)
        lo, hi = colors[1], colors[0]
        rgb = np.stack(
            [
                lo.redF() + (hi.redF() - lo.redF()) * val,
                lo.greenF() + (hi.greenF() - lo.greenF()) * val,
                lo.blueF() + (hi.blueF() - lo.blueF()) * val,
            ],
            axis=-1,
        )
    else:
        wt = k * c * t
        val = re * math.cos(wt) + im * math.sin(wt)  # Re(Σ e^{i(kr − ωt)})
        val = np.clip(val / max(1e-9, float(np.percentile(np.abs(val), 98))), -1, 1)
        pos, mid, neg = colors
        p = np.clip(val, 0, 1)[..., None]
        n = np.clip(-val, 0, 1)[..., None]
        m = np.array([mid.redF(), mid.greenF(), mid.blueF()])
        rgb = m * (1 - p - n) + np.array([pos.redF(), pos.greenF(), pos.blueF()]) * p
        rgb = rgb + np.array([neg.redF(), neg.greenF(), neg.blueF()]) * n
    alpha = np.ones(x.shape)
    if half:
        alpha = np.clip((x - origin_x) / 6.0, 0, 1)
    img = _qimage(np.concatenate([rgb, alpha[..., None]], axis=-1))
    _FIELD_CACHE[key] = img
    if len(_FIELD_CACHE) > 24:
        _FIELD_CACHE.popitem(last=False)
    return img


def paint_waves(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    mode = str(params.get("mode", "fronts"))
    if mode == "field":
        w = max(10.0, float(params.get("width", 1200.0)))
        h = max(10.0, float(params.get("height", 700.0)))
        t = painter.worldTransform()
        dev = max(1e-3, math.hypot(t.m11(), t.m12()))
        res = max(0.15, min(1.0, float(params.get("resolution", 0.5))))
        pw, ph = max(8, int(w * dev * res)), max(8, int(h * dev * res))
        colors = (
            qcolor(style.get("crest_color", "#FFFFFF")),
            qcolor(style.get("fill", "#0B1020")),
            qcolor(style.get("trough_color", "#2677B8")),
        )
        painter.drawImage(QRectF(-w / 2, -h / 2, w, h), field_image(params, pw, ph, colors))
        if bool(params.get("show_source", True)):
            half = bool(params.get("half_plane", False))
            ox = float(params.get("source_x", -w / 2 + 60.0 if half else 0.0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qcolor(style.get("source_color", "#FFD27A")))
            for sx, sy in field_sources(params):
                painter.drawEllipse(QPointF(ox + sx, sy), 7.0, 7.0)
        return
    if mode == "string":
        _paint_string(painter, params, style, qcolor)
        return
    color = qcolor(style.get("stroke", "#9FC7EE"))
    width = max(0.5, float(style.get("stroke_width", 3.0)))
    fade = bool(params.get("fade", True))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for cx, cy, r, age in front_circles(params):
        c = QColor(color)
        if fade:
            c.setAlphaF(c.alphaF() * max(0.0, 1.0 - age) ** 0.7)
        painter.setPen(QPen(c, width))
        painter.drawEllipse(QPointF(cx, cy), r, r)
    if bool(params.get("show_source", True)):
        sx, sy = source_position(params)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor(style.get("source_color", "#FFD27A")))
        s = max(4.0, float(params.get("source_size", 14.0)))
        painter.drawEllipse(QPointF(sx, sy), s, s)


def string_points(params: dict[str, Any], samples: int = 400) -> list[tuple[float, float]]:
    w = max(10.0, float(params.get("width", 1200.0)))
    lam = max(2.0, float(params.get("wavelength", 200.0)))
    amp = float(params.get("amplitude", 60.0))
    c = float(params.get("wave_speed", 200.0))
    t = float(params.get("time_s", 0.0))
    k = 2 * math.pi / lam
    om = k * c
    standing = bool(params.get("standing", False))
    pts = []
    for i in range(samples + 1):
        x = -w / 2 + w * i / samples
        u = x + w / 2
        y = 2 * amp * math.sin(k * u) * math.cos(om * t) if standing else amp * math.sin(k * u - om * t)
        pts.append((x, -y))
    return pts


def _paint_string(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    pts = string_points(params)
    pen = QPen(qcolor(style.get("stroke", "#9FC7EE")), max(0.5, float(style.get("stroke_width", 4.0))))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPolyline(QPolygonF([QPointF(x, y) for x, y in pts]))
    beads = int(params.get("beads", 0))
    if beads > 0:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor(style.get("source_color", "#FFD27A")))
        step = max(1, len(pts) // beads)
        for x, y in pts[::step]:
            painter.drawEllipse(QPointF(x, y), 6.0, 6.0)


def waves_bounds(params: dict[str, Any]) -> QRectF:
    mode = str(params.get("mode", "fronts"))
    if mode in ("field", "string"):
        w = max(10.0, float(params.get("width", 1200.0)))
        h = (
            max(10.0, float(params.get("height", 700.0)))
            if mode == "field"
            else 2.5
            * abs(float(params.get("amplitude", 60.0)))
            * (2 if bool(params.get("standing", False)) else 1)
            + 20
        )
        return QRectF(-w / 2, -h / 2, w, h)
    r = max(1.0, float(params.get("max_radius", 900.0)))
    sx, sy = source_position(params)
    rect = QRectF(-r, -r, 2 * r, 2 * r)
    return rect.united(QRectF(sx - r, sy - r, 2 * r, 2 * r))

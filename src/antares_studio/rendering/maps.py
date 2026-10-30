"""Cartes du monde (Natural Earth) : planisphère vectoriel ou image satellite (ADR-0009).

Projections : équirectangulaire (plate carrée), Equal Earth (Šavrič, Patterson et Jenny, 2018 — à aires
égales) et Mercator (bornée à ±82°). Les contours sont projetés une fois puis mis en cache ; l'image
satellite est reprojetée pixel par pixel par la projection inverse.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from functools import lru_cache
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPolygonF

from antares_studio.rendering.celestial import _qimage, _sample, load_texture
from antares_studio.resources.astro import CONTINENT_LABELS, CONTINENTS_FR, countries, texture_path

Array = Any

CONTINENT_COLORS: dict[str, str] = {
    "Africa": "#E7B35A",
    "Asia": "#E07A5F",
    "Europe": "#6BA4D8",
    "North America": "#83C167",
    "South America": "#B39DDB",
    "Oceania": "#4DB6AC",
    "Antarctica": "#E8EEF2",
    "Seven seas (open ocean)": "#C9B99A",
}

_A1, _A2, _A3, _A4 = 1.340264, -0.081106, 0.000893, 0.003796
_SQ3 = math.sqrt(3.0)
MERCATOR_LAT = 82.0


def _ee_y(theta: Array) -> Array:
    return theta * (_A1 + _A2 * theta**2 + theta**6 * (_A3 + _A4 * theta**2))


def project(projection: str, lon_deg: Array, lat_deg: Array) -> tuple[Array, Array]:
    """(lon, lat) en degrés → coordonnées normalisées : x ∈ [−1, 1], y vers le haut, même échelle."""
    lam = np.radians(np.asarray(lon_deg, dtype=np.float64))
    phi = np.radians(np.asarray(lat_deg, dtype=np.float64))
    if projection == "equirectangular":
        return lam / math.pi, phi / math.pi
    if projection == "mercator":
        phi = np.clip(phi, -math.radians(MERCATOR_LAT), math.radians(MERCATOR_LAT))
        return lam / math.pi, np.log(np.tan(math.pi / 4 + phi / 2)) / math.pi
    theta = np.arcsin(_SQ3 / 2 * np.sin(phi))
    x = (
        2
        * _SQ3
        * lam
        * np.cos(theta)
        / (3 * (9 * _A4 * theta**8 + 7 * _A3 * theta**6 + 3 * _A2 * theta**2 + _A1))
    )
    xmax = 2 * _SQ3 * math.pi / (3 * _A1)
    return x / xmax, _ee_y(theta) / xmax


def unproject(projection: str, x: Array, y: Array) -> tuple[Array, Array, Array]:
    """Inverse de ``project`` : (lon°, lat°, masque des points valides)."""
    if projection == "equirectangular":
        lon, lat = x * 180.0, y * 180.0
        return lon, lat, (np.abs(lat) <= 90) & (np.abs(lon) <= 180)
    if projection == "mercator":
        lat = np.degrees(2 * np.arctan(np.exp(y * math.pi)) - math.pi / 2)
        return x * 180.0, lat, (np.abs(lat) <= MERCATOR_LAT) & (np.abs(x) <= 1)
    xmax = 2 * _SQ3 * math.pi / (3 * _A1)
    yy = y * xmax
    theta = np.clip(yy / _A1, -1.3, 1.3)
    for _ in range(6):  # Newton sur y(θ)
        f = _ee_y(theta) - yy
        df = _A1 + 3 * _A2 * theta**2 + theta**6 * (7 * _A3 + 9 * _A4 * theta**2)
        theta = theta - f / df
    ok = np.abs(theta) <= math.pi / 3 + 1e-9
    theta = np.clip(theta, -math.pi / 3, math.pi / 3)
    lam = (
        3
        * (x * xmax)
        * (9 * _A4 * theta**8 + 7 * _A3 * theta**6 + 3 * _A2 * theta**2 + _A1)
        / (2 * _SQ3 * np.cos(theta))
    )
    phi = np.arcsin(np.clip(2 * np.sin(theta) / _SQ3, -1, 1))
    return np.degrees(lam), np.degrees(phi), ok & (np.abs(lam) <= math.pi + 1e-9)


def aspect(projection: str) -> float:
    """Largeur / hauteur de la carte complète."""
    _x, top = project(projection, 0.0, 90.0 if projection != "mercator" else MERCATOR_LAT)
    return float(1.0 / top)


def map_size(params: dict[str, Any]) -> tuple[float, float]:
    w = max(10.0, float(params.get("width", 1600.0)))
    return w, w / aspect(str(params.get("projection", "equal_earth")))


@lru_cache(maxsize=8)
def _country_paths(detail: str, projection: str) -> tuple[tuple[str, str, QPainterPath], ...]:
    """Contours projetés en coordonnées normalisées (x ∈ [−1, 1], y vers le bas)."""
    out = []
    for f in countries(detail):
        polys = f["coords"] if f["type"] == "MultiPolygon" else [f["coords"]]
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        for poly in polys:
            for ring in poly:
                arr = np.asarray(ring, dtype=np.float64)
                x, y = project(projection, arr[:, 0], arr[:, 1])
                path.addPolygon(QPolygonF([QPointF(float(a), float(-b)) for a, b in zip(x, y, strict=True)]))
                path.closeSubpath()
        out.append((str(f["continent"]), str(f["name"]), path))
    return tuple(out)


def _outline_path(projection: str, samples: int = 181) -> QPainterPath:
    lats = np.linspace(-90, 90, samples)
    if projection == "mercator":
        lats = np.linspace(-MERCATOR_LAT, MERCATOR_LAT, samples)
    xr, yr = project(projection, np.full_like(lats, 180.0), lats)
    xl, yl = project(projection, np.full_like(lats, -180.0), lats[::-1])
    pts = [QPointF(float(a), float(-b)) for a, b in zip(np.r_[xr, xl], np.r_[yr, yl], strict=True)]
    path = QPainterPath()
    path.addPolygon(QPolygonF(pts))
    path.closeSubpath()
    return path


_SAT_CACHE: OrderedDict[tuple[Any, ...], QImage] = OrderedDict()


def _satellite_image(projection: str, night: bool, w: int, h: int) -> QImage:
    key = (projection, night, w, h)
    img = _SAT_CACHE.get(key)
    if img is not None:
        return img
    half_h = h / w
    xs = (np.arange(w) + 0.5) / w * 2 - 1
    ys = half_h - (np.arange(h) + 0.5) / h * 2 * half_h
    x, y = np.meshgrid(xs, ys)
    lon, lat, ok = unproject(projection, x, y)
    tex = load_texture(str(texture_path("earth_nightmap.jpg" if night else "earth_daymap.jpg")))
    rgb = _sample(tex, lon / 360.0 + 0.5, 0.5 - lat / 180.0)[..., :3]
    if night:
        rgb = np.clip(rgb * 1.6, 0, 1)
    rgba = np.concatenate([rgb, ok[..., None].astype(np.float32)], axis=-1)
    img = _qimage(rgba)
    _SAT_CACHE[key] = img
    if len(_SAT_CACHE) > 6:
        _SAT_CACHE.popitem(last=False)
    return img


def _graticule(painter: QPainter, projection: str, scale: float, color: QColor, width: float) -> None:
    pen = QPen(color, width)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    top = 90 if projection != "mercator" else MERCATOR_LAT
    for lon in range(-180, 181, 30):
        lats = np.linspace(-top, top, 61)
        x, y = project(projection, np.full_like(lats, float(lon)), lats)
        painter.drawPolyline(
            QPolygonF([QPointF(float(a) * scale, float(-b) * scale) for a, b in zip(x, y, strict=True)])
        )
    for lat in range(-60, 61, 30):
        if abs(lat) > top:
            continue
        lons = np.linspace(-180, 180, 121)
        x, y = project(projection, lons, np.full_like(lons, float(lat)))
        painter.drawPolyline(
            QPolygonF([QPointF(float(a) * scale, float(-b) * scale) for a, b in zip(x, y, strict=True)])
        )


def paint_map(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    projection = str(params.get("projection", "equal_earth"))
    mode = str(params.get("map_style", "continents"))
    w, h = map_size(params)
    scale = w / 2  # coordonnées normalisées → px
    progress = max(0.0, min(1.0, float(params.get("progress", 1.0))))
    highlight = str(params.get("highlight", ""))
    outline = _outline_path(projection)
    painter.save()
    if progress < 1.0:  # balayage d'ouest en est
        painter.setClipRect(QRectF(-w / 2 - 2, -h / 2 - 2, w * progress + 4, h + 4))
    painter.scale(scale, scale)
    lw = 1.0 / scale  # 1 px à l'échelle de la carte
    ocean = qcolor(style.get("ocean_color", "#0E2A47"))
    if mode in ("satellite", "night"):
        t = painter.worldTransform()
        dev = max(1e-3, math.hypot(t.m11(), t.m12()))
        pw = int(min(3200, max(16, round(2 * dev))))
        ph = int(round(pw * h / w))
        img = _satellite_image(projection, mode == "night", pw, ph)
        painter.drawImage(QRectF(-1, -h / w, 2, 2 * h / w), img)
    else:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ocean)
        painter.drawPath(outline)
    if bool(params.get("graticule", True)):
        _graticule(painter, projection, 1.0, qcolor(style.get("graticule_color", "#FFFFFF26")), lw)
        painter.scale(1, 1)
    detail = str(params.get("detail", "50m"))
    land = qcolor(style.get("land_color", "#D9CBA3"))
    border = qcolor(style.get("border_color", "#33415588"))
    hl = qcolor(style.get("highlight_color", "#FFD27A"))
    for continent, _name, path in _country_paths(detail, projection):
        if mode in ("satellite", "night"):
            if continent == highlight:
                c = QColor(hl)
                c.setAlphaF(0.45)
                painter.setPen(QPen(hl, 2 * lw))
                painter.setBrush(c)
                painter.drawPath(path)
            continue
        if mode == "outline":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(hl if continent == highlight else land, 1.4 * lw))
        else:
            base = (
                QColor(CONTINENT_COLORS.get(continent, "#C9B99A")) if mode == "continents" else QColor(land)
            )
            if highlight:
                base = QColor(hl) if continent == highlight else base.darker(170)
            painter.setBrush(base)
            painter.setPen(QPen(border, (0.8 if mode == "political" else 0.4) * lw))
        painter.drawPath(path)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(qcolor(style.get("frame_color", "#FFFFFF66")), 1.2 * lw))
    painter.drawPath(outline)
    painter.restore()
    if bool(params.get("labels", False)):
        painter.save()
        font = QFont(str(params.get("font_family", "DejaVu Sans")))
        font.setPixelSize(max(6, int(w * 0.017)))
        font.setBold(True)
        painter.setFont(font)
        for key, (lon, lat) in CONTINENT_LABELS.items():
            x, y = project(projection, lon, lat)
            px, py = float(x) * scale, -float(y) * scale
            if progress < 1.0 and px > -w / 2 + w * progress:
                continue
            label = CONTINENTS_FR[key]
            rect = QRectF(px - w * 0.12, py - w * 0.02, w * 0.24, w * 0.04)
            painter.setPen(QPen(QColor(0, 0, 0, 150)))
            painter.drawText(rect.translated(1.5, 1.5), int(Qt.AlignmentFlag.AlignCenter), label)
            painter.setPen(QPen(qcolor(style.get("label_color", "#FFFFFF"))))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), label)
        painter.restore()


def map_bounds(params: dict[str, Any]) -> QRectF:
    w, h = map_size(params)
    return QRectF(-w / 2, -h / 2, w, h)

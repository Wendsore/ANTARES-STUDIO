"""Dessin d'un ``SceneState`` avec ``QPainter`` — unique code de rastérisation (ADR-0001).

Utilisé à l'identique par l'éditeur (prévisualisation) et par l'exporteur (QImage hors écran).
Les coordonnées des nœuds sont en pixels du canevas de projet ; ``scale`` adapte à la sortie.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QTransform,
)

from antares_studio.domain.colors import is_color, parse_color
from antares_studio.domain.model import Canvas
from antares_studio.timeline.evaluator import NodeState, SceneState

AssetResolver = Callable[[str], Path | None]


def qcolor(value: Any, fallback: str = "#FFFFFF") -> QColor:
    if not is_color(value):
        value = fallback
    r, g, b, a = parse_color(str(value))
    c = QColor()
    c.setRgbF(r, g, b, a)
    return c


class ImageCache:
    """Cache mémoire borné des images de ressources (régénérable, non autoritatif)."""

    def __init__(self, limit: int = 64):
        self._items: dict[str, QImage] = {}
        self._limit = limit

    def get(self, path: Path) -> QImage | None:
        key = str(path)
        img = self._items.get(key)
        if img is None:
            if not path.is_file():
                return None
            img = QImage(str(path))
            if img.isNull():
                return None
            if len(self._items) >= self._limit:
                self._items.pop(next(iter(self._items)))
            self._items[key] = img
        return img

    def clear(self) -> None:
        self._items.clear()


def paint_scene_state(
    painter: QPainter,
    state: SceneState,
    canvas: Canvas,
    target_width: int,
    target_height: int,
    assets: AssetResolver | None = None,
    image_cache: ImageCache | None = None,
    paint_background: bool = True,
) -> None:
    """Dessine ``state`` dans un rectangle ``target_width × target_height`` (mise à l'échelle uniforme)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    if paint_background:
        painter.fillRect(QRectF(0, 0, target_width, target_height), qcolor(state.background, "#000000"))
    sx = target_width / canvas.width
    sy = target_height / canvas.height
    base = QTransform.fromScale(sx, sy)
    cache = image_cache or _DEFAULT_CACHE
    for node in state.nodes:
        if not node.visible or node.world_opacity <= 0.0:
            continue
        painter.save()
        a, b, c, d, tx, ty = node.world
        painter.setWorldTransform(QTransform(a, b, c, d, tx, ty) * base, False)
        painter.setOpacity(node.world_opacity)
        paint_node(painter, node, assets, cache)
        painter.restore()
    painter.restore()


def paint_node(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    drawer = _DRAWERS.get(node.kind)
    if drawer is not None:
        drawer(painter, node, assets, cache)


def _shape_pen_brush(painter: QPainter, style: dict[str, Any], default_fill: str = "#2677B8") -> None:
    fill = style.get("fill")
    stroke = style.get("stroke")
    width = float(style.get("stroke_width", 0.0) or 0.0)
    if fill is None:
        painter.setBrush(Qt.BrushStyle.NoBrush)
    else:
        painter.setBrush(QBrush(qcolor(fill, default_fill)))
    if width > 0 and stroke is not None:
        pen = QPen(qcolor(stroke), width)
        if style.get("dash"):
            pen.setStyle(Qt.PenStyle.DashLine)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
    else:
        painter.setPen(Qt.PenStyle.NoPen)


def _line_pen(painter: QPainter, style: dict[str, Any]) -> float:
    width = float(style.get("stroke_width", 4.0) or 0.0)
    pen = QPen(qcolor(style.get("stroke", "#F2A93B")), width)
    if style.get("dash"):
        pen.setStyle(Qt.PenStyle.DashLine)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    return width


def _draw_circle(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    r = float(node.params.get("radius", 80.0))
    _shape_pen_brush(painter, node.style)
    painter.drawEllipse(QPointF(0, 0), r, r)


def _draw_ellipse(
    painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache
) -> None:
    rx = float(node.params.get("rx", 120.0))
    ry = float(node.params.get("ry", 70.0))
    _shape_pen_brush(painter, node.style)
    painter.drawEllipse(QPointF(0, 0), rx, ry)


def _draw_rect(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    w = float(node.params.get("width", 200.0))
    h = float(node.params.get("height", 120.0))
    cr = float(node.params.get("corner_radius", 0.0))
    _shape_pen_brush(painter, node.style)
    rect = QRectF(-w / 2, -h / 2, w, h)
    if cr > 0:
        painter.drawRoundedRect(rect, cr, cr)
    else:
        painter.drawRect(rect)


def _draw_polygon(
    painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache
) -> None:
    pts = node.params.get("points") or []
    if len(pts) < 2:
        return
    _shape_pen_brush(painter, node.style)
    poly = QPolygonF([QPointF(float(p[0]), float(p[1])) for p in pts])
    if node.params.get("closed", True):
        painter.drawPolygon(poly)
    else:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(poly)


def _draw_star(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    n = max(3, int(node.params.get("points_count", 5)))
    ro = float(node.params.get("outer_radius", 60.0))
    ri = float(node.params.get("inner_radius", 25.0))
    _shape_pen_brush(painter, node.style, "#FFD966")
    pts = []
    for i in range(2 * n):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / n
        pts.append(QPointF(r * math.cos(a), r * math.sin(a)))
    painter.drawPolygon(QPolygonF(pts))


def _draw_line(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    end = node.params.get("end") or [200.0, 0.0]
    _line_pen(painter, node.style)
    painter.drawLine(QPointF(0, 0), QPointF(float(end[0]), float(end[1])))


def _draw_arrow(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    end = node.params.get("end") or [200.0, 0.0]
    ex, ey = float(end[0]), float(end[1])
    head = float(node.params.get("head_size", 18.0))
    width = _line_pen(painter, node.style)
    length = math.hypot(ex, ey)
    if length <= 1e-9:
        return
    ux, uy = ex / length, ey / length
    shaft_end = QPointF(ex - ux * head * 0.8, ey - uy * head * 0.8) if length > head else QPointF(0, 0)
    painter.drawLine(QPointF(0, 0), shaft_end)
    ang = math.atan2(uy, ux)
    tip = QPointF(ex, ey)
    left = QPointF(ex - head * math.cos(ang - 0.45), ey - head * math.sin(ang - 0.45))
    right = QPointF(ex - head * math.cos(ang + 0.45), ey - head * math.sin(ang + 0.45))
    painter.setBrush(QBrush(qcolor(node.style.get("stroke", "#F2A93B"))))
    painter.setPen(QPen(qcolor(node.style.get("stroke", "#F2A93B")), max(1.0, width * 0.5)))
    painter.drawPolygon(QPolygonF([tip, left, right]))


def _draw_orbit_path(
    painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache
) -> None:
    r = float(node.params.get("radius", 300.0))
    style = dict(node.style)
    style.setdefault("stroke", "#FFFFFF40")
    style.setdefault("stroke_width", 2.0)
    _line_pen(painter, style)
    painter.drawEllipse(QPointF(0, 0), r, r)


def text_font(params: dict[str, Any]) -> QFont:
    font = QFont(str(params.get("font_family", "DejaVu Sans")))
    font.setPointSizeF(max(1.0, float(params.get("font_size", 48.0))))
    font.setBold(bool(params.get("bold", False)))
    font.setItalic(bool(params.get("italic", False)))
    return font


def text_layout_rect(params: dict[str, Any]) -> tuple[QRectF, int]:
    """Rectangle local (centré) et drapeaux d'alignement du texte ; partagé avec l'éditeur."""
    font = text_font(params)
    fm = QFontMetricsF(font)
    text = str(params.get("text", ""))
    max_w = float(params.get("max_width", 0.0) or 0.0)
    align = str(params.get("align", "center"))
    flags = Qt.TextFlag.TextWordWrap if max_w > 0 else 0
    h_align = {"left": Qt.AlignmentFlag.AlignLeft, "right": Qt.AlignmentFlag.AlignRight}.get(
        align, Qt.AlignmentFlag.AlignHCenter
    )
    width = max_w if max_w > 0 else 1e6
    bound = fm.boundingRect(
        QRectF(0, 0, width, 1e6), int(flags) | int(h_align) | int(Qt.AlignmentFlag.AlignTop), text
    )
    w = max_w if max_w > 0 else bound.width()
    h = bound.height()
    return QRectF(-w / 2, -h / 2, w, h), int(flags) | int(h_align) | int(Qt.AlignmentFlag.AlignVCenter)


def _draw_text(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    text = str(node.params.get("text", ""))
    if not text:
        return
    font = text_font(node.params)
    rect, flags = text_layout_rect(node.params)
    stroke_w = float(node.style.get("stroke_width", 0.0) or 0.0)
    if stroke_w > 0:
        path = QPainterPath()
        fm = QFontMetricsF(font)
        y = rect.top() + fm.ascent()
        for line in text.split("\n"):
            lw = fm.horizontalAdvance(line)
            if flags & int(Qt.AlignmentFlag.AlignLeft):
                x = rect.left()
            elif flags & int(Qt.AlignmentFlag.AlignRight):
                x = rect.right() - lw
            else:
                x = rect.center().x() - lw / 2
            path.addText(QPointF(x, y), font, line)
            y += fm.lineSpacing()
        painter.setPen(
            QPen(
                qcolor(node.style.get("stroke", "#000000")),
                stroke_w,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
    painter.setFont(font)
    painter.setPen(QPen(qcolor(node.style.get("fill", "#FFFFFF"))))
    painter.drawText(rect, flags, text)


def _draw_image(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    w = float(node.params.get("width", 300.0))
    h = float(node.params.get("height", 0.0) or 0.0)
    img: QImage | None = None
    asset_id = str(node.params.get("asset_id", ""))
    if assets is not None and asset_id:
        path = assets(asset_id)
        if path is not None:
            img = cache.get(path)
    if img is None or img.width() == 0:
        # ressource absente : cadre hachuré explicite, jamais de crash (MOD-07)
        if h <= 0:
            h = w * 0.75
        painter.setPen(QPen(QColor("#FF5555"), 3, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(QColor(255, 85, 85, 40)))
        painter.drawRect(QRectF(-w / 2, -h / 2, w, h))
        return
    if h <= 0:
        h = w * img.height() / img.width()
    target = QRectF(-w / 2, -h / 2, w, h)
    painter.drawImage(target, img)
    tint = node.style.get("tint")
    if is_color(tint):
        color = qcolor(tint)
        if color.alpha() > 0:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            painter.fillRect(target, color)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)


def _draw_group(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    return None


_DRAWERS: dict[str, Callable[[QPainter, NodeState, AssetResolver | None, ImageCache], None]] = {
    "circle": _draw_circle,
    "ellipse": _draw_ellipse,
    "rect": _draw_rect,
    "polygon": _draw_polygon,
    "star": _draw_star,
    "line": _draw_line,
    "arrow": _draw_arrow,
    "orbit_path": _draw_orbit_path,
    "text": _draw_text,
    "image": _draw_image,
    "group": _draw_group,
}

_DEFAULT_CACHE = ImageCache()


def local_bounds(node: NodeState) -> QRectF:
    """Boîte englobante locale (avant transformation) utilisée pour la sélection et les poignées."""
    k, p = node.kind, node.params
    if k == "circle":
        r = float(p.get("radius", 80.0))
        return QRectF(-r, -r, 2 * r, 2 * r)
    if k == "orbit_path":
        r = float(p.get("radius", 300.0))
        return QRectF(-r, -r, 2 * r, 2 * r)
    if k == "ellipse":
        rx, ry = float(p.get("rx", 120.0)), float(p.get("ry", 70.0))
        return QRectF(-rx, -ry, 2 * rx, 2 * ry)
    if k == "rect":
        w, h = float(p.get("width", 200.0)), float(p.get("height", 120.0))
        return QRectF(-w / 2, -h / 2, w, h)
    if k in ("polygon",):
        pts = p.get("points") or [[0, 0]]
        xs = [float(q[0]) for q in pts]
        ys = [float(q[1]) for q in pts]
        return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    if k == "star":
        r = float(p.get("outer_radius", 60.0))
        return QRectF(-r, -r, 2 * r, 2 * r)
    if k in ("line", "arrow"):
        end = p.get("end") or [200.0, 0.0]
        x0, x1 = min(0.0, float(end[0])), max(0.0, float(end[0]))
        y0, y1 = min(0.0, float(end[1])), max(0.0, float(end[1]))
        pad = 6.0
        return QRectF(x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad)
    if k == "text":
        rect, _ = text_layout_rect(p)
        return rect
    if k == "image":
        w = float(p.get("width", 300.0))
        h = float(p.get("height", 0.0) or 0.0) or w * 0.75
        return QRectF(-w / 2, -h / 2, w, h)
    return QRectF(-20, -20, 40, 40)


def render_state_to_image(
    state: SceneState,
    canvas: Canvas,
    width: int,
    height: int,
    assets: AssetResolver | None = None,
    image_cache: ImageCache | None = None,
) -> QImage:
    """Rastérise un état dans une ``QImage`` RGBA8888 (utilisé par l'export et les tests visuels)."""
    img = QImage(width, height, QImage.Format.Format_RGBA8888)
    img.fill(0)
    painter = QPainter(img)
    try:
        paint_scene_state(painter, state, canvas, width, height, assets, image_cache)
    finally:
        painter.end()
    return img

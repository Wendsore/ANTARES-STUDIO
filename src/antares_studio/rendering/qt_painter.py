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
from antares_studio.domain.model import DEFAULT_SUBTITLE_STYLE, Canvas
from antares_studio.rendering.formula_layout import formula_rect, paint_formula
from antares_studio.science.data import DataError, DataTable, load_csv, nice_ticks
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

    def __init__(self, limit: int = 600):
        self._items: dict[str, QImage] = {}
        self._tables: dict[str, DataTable | None] = {}
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

    def get_table(self, path: Path) -> DataTable | None:
        """Table CSV (données de graphique) mise en cache ; ``None`` si absente ou illisible."""
        key = str(path)
        if key in self._tables:
            return self._tables[key]
        table: DataTable | None
        try:
            table = load_csv(path) if path.is_file() else None
        except (DataError, OSError):
            table = None
        if len(self._tables) >= self._limit:
            self._tables.pop(next(iter(self._tables)))
        self._tables[key] = table
        return table

    def clear(self) -> None:
        self._items.clear()
        self._tables.clear()


def paint_scene_state(
    painter: QPainter,
    state: SceneState,
    canvas: Canvas,
    target_width: int,
    target_height: int,
    assets: AssetResolver | None = None,
    image_cache: ImageCache | None = None,
    paint_background: bool = True,
    subtitle_style: dict[str, Any] | None = None,
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
        # combine=True : la transformation s'ajoute à celle du painter (décalage/zoom de l'éditeur)
        painter.setWorldTransform(QTransform(a, b, c, d, tx, ty) * base, True)
        painter.setOpacity(node.world_opacity)
        paint_node(painter, node, assets, cache)
        painter.restore()
    if state.subtitle:
        paint_subtitle(
            painter, state.subtitle, target_width, target_height, subtitle_style or DEFAULT_SUBTITLE_STYLE
        )
    painter.restore()


def paint_subtitle(painter: QPainter, text: str, width: int, height: int, style: dict[str, Any]) -> QRectF:
    """Incruste un sous-titre dans la bande inférieure (zone sûre), fond et contour lisibles sur mobile."""
    painter.save()
    painter.setOpacity(1.0)
    font = QFont(str(style.get("font_family", "DejaVu Sans")))
    # taille relative à la plus petite dimension : lisible en 16:9 comme en 9:16 (téléphone)
    font.setPixelSize(max(8, int(round(min(width, height) * float(style.get("font_size_ratio", 0.045))))))
    font.setBold(bool(style.get("bold", False)))
    painter.setFont(font)
    fm = QFontMetricsF(font)
    max_w = width * float(style.get("max_width_ratio", 0.86))
    flags = (
        int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignHCenter) | int(Qt.AlignmentFlag.AlignTop)
    )
    bound = fm.boundingRect(QRectF(0, 0, max_w, height), flags, text)
    pad = fm.height() * 0.3
    bottom = height - height * float(style.get("bottom_margin_ratio", 0.08))
    rect = QRectF(
        (width - bound.width()) / 2 - pad,
        bottom - bound.height() - pad,
        bound.width() + 2 * pad,
        bound.height() + 2 * pad,
    )
    bg = qcolor(style.get("background", "#000000A0"))
    if bg.alpha() > 0:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(rect, pad * 0.5, pad * 0.5)
    text_rect = rect.adjusted(pad, pad, -pad, -pad)
    outline_w = float(style.get("outline_width", 0.0) or 0.0)
    if outline_w > 0:
        path = QPainterPath()
        y = text_rect.top() + fm.ascent()
        for line in _wrap_lines(fm, text, text_rect.width()):
            lw = fm.horizontalAdvance(line)
            path.addText(QPointF(text_rect.center().x() - lw / 2, y), font, line)
            y += fm.lineSpacing()
        painter.setPen(
            QPen(
                qcolor(style.get("outline", "#000000")),
                outline_w,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
    painter.setPen(QPen(qcolor(style.get("color", "#FFFFFF"))))
    painter.drawText(text_rect, flags, text)
    painter.restore()
    return rect


def _wrap_lines(fm: QFontMetricsF, text: str, max_width: float) -> list[str]:
    """Découpe approximative en lignes selon la largeur (pour le contour ; Qt gère le rendu final)."""
    out: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for w in words:
            cand = (line + " " + w).strip()
            if line and fm.horizontalAdvance(cand) > max_width:
                out.append(line)
                line = w
            else:
                line = cand
        out.append(line)
    return out


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


def callout_rect(params: dict[str, Any]) -> QRectF:
    """Rectangle local de l'encadré : zone de texte élargie de la marge intérieure."""
    rect, _ = text_layout_rect(params)
    pad = float(params.get("padding", 18.0) or 0.0)
    return rect.adjusted(-pad, -pad, pad, pad)


def _draw_callout(
    painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache
) -> None:
    text = str(node.params.get("text", ""))
    if not text:
        return
    box = callout_rect(node.params)
    radius = float(node.params.get("corner_radius", 10.0) or 0.0)
    stroke_w = float(node.style.get("stroke_width", 0.0) or 0.0)
    painter.setBrush(QBrush(qcolor(node.style.get("fill", "#263238CC"))))
    if stroke_w > 0:
        painter.setPen(QPen(qcolor(node.style.get("stroke", "#F2A93B")), stroke_w))
    else:
        painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(box, radius, radius)
    rect, flags = text_layout_rect(node.params)
    painter.setFont(text_font(node.params))
    painter.setPen(QPen(qcolor(node.style.get("text_color", "#FFFFFF"))))
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


def _draw_formula(
    painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache
) -> None:
    bg = node.style.get("background")
    brush = QBrush(qcolor(bg)) if is_color(bg) and qcolor(bg).alpha() > 0 else None
    paint_formula(painter, node.params, QPen(qcolor(node.style.get("fill", "#FFFFFF"))), brush)


def chart_frame(params: dict[str, Any]) -> QRectF:
    w, h = float(params.get("width", 640.0)), float(params.get("height", 400.0))
    return QRectF(-w / 2, -h / 2, w, h)


def _axis_range(values: list[float], lo: float, hi: float) -> tuple[float, float]:
    """Bornes d'un axe : valeurs forcées (≠ 0) sinon étendue des données avec marge de 5 %."""
    if not values:
        return (0.0, 1.0)
    vmin, vmax = min(values), max(values)
    if vmax <= vmin:
        vmin, vmax = vmin - 1.0, vmax + 1.0
    pad = (vmax - vmin) * 0.05
    return (lo if lo != 0.0 else vmin - pad, hi if hi != 0.0 else vmax + pad)


def _draw_chart(painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache) -> None:
    p = node.params
    frame = chart_frame(p)
    axis_color = qcolor(node.style.get("axis_color", "#CFD8DC"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(qcolor(node.style.get("fill", "#0B102080"))))
    painter.drawRect(frame)
    table: DataTable | None = None
    asset_id = str(p.get("data_asset_id", ""))
    if assets is not None and asset_id:
        path = assets(asset_id)
        if path is not None:
            table = cache.get_table(path)
    font = QFont("DejaVu Sans")
    font.setPointSizeF(max(4.0, float(p.get("font_size", 18.0))))
    painter.setFont(font)
    fm = QFontMetricsF(font)
    x_name, y_name = str(p.get("x_column", "")), str(p.get("y_column", ""))
    points = table.xy(x_name, y_name) if table is not None else []
    if table is None or not points:
        # données absentes ou colonnes inconnues : cadre explicite, jamais de crash
        painter.setPen(QPen(QColor("#FF5555"), 3, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(frame)
        painter.setPen(QPen(axis_color))
        msg = "Données CSV absentes" if table is None else f"Colonnes introuvables : {x_name!r}, {y_name!r}"
        painter.drawText(frame, int(Qt.AlignmentFlag.AlignCenter), msg)
        return
    cx_col, cy_col = table.column(x_name), table.column(y_name)
    assert cx_col is not None and cy_col is not None
    margin_l = fm.horizontalAdvance("-0.000e+00") + fm.height() * 1.4
    margin_b = fm.height() * 2.6
    margin_t = fm.height() * (1.6 if p.get("title") else 0.6)
    plot = QRectF(frame.left() + margin_l, frame.top() + margin_t, frame.width() - margin_l - fm.height(), 0)
    plot.setHeight(frame.height() - margin_t - margin_b)
    xs = [q[0] for q in points]
    ys = [q[1] for q in points]
    x0, x1 = _axis_range(xs, float(p.get("x_min", 0.0)), float(p.get("x_max", 0.0)))
    y0, y1 = _axis_range(ys, float(p.get("y_min", 0.0)), float(p.get("y_max", 0.0)))

    def to_px(x: float, y: float) -> QPointF:
        return QPointF(
            plot.left() + (x - x0) / (x1 - x0) * plot.width(),
            plot.bottom() - (y - y0) / (y1 - y0) * plot.height(),
        )

    def fmt(v: float) -> str:
        return f"{v:g}"

    # grille et graduations
    grid_pen = QPen(QColor(axis_color.red(), axis_color.green(), axis_color.blue(), 50), 1)
    tick_pen = QPen(axis_color, 1.5)
    text_pen = QPen(axis_color)
    for t in nice_ticks(x0, x1):
        pt = to_px(t, y0)
        if bool(p.get("show_grid", True)):
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(pt.x(), plot.top()), QPointF(pt.x(), plot.bottom()))
        painter.setPen(tick_pen)
        painter.drawLine(QPointF(pt.x(), plot.bottom()), QPointF(pt.x(), plot.bottom() + 6))
        painter.setPen(text_pen)
        label = fmt(t)
        painter.drawText(
            QPointF(pt.x() - fm.horizontalAdvance(label) / 2, plot.bottom() + 8 + fm.ascent()), label
        )
    for t in nice_ticks(y0, y1):
        pt = to_px(x0, t)
        if bool(p.get("show_grid", True)):
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(plot.left(), pt.y()), QPointF(plot.right(), pt.y()))
        painter.setPen(tick_pen)
        painter.drawLine(QPointF(plot.left() - 6, pt.y()), QPointF(plot.left(), pt.y()))
        painter.setPen(text_pen)
        label = fmt(t)
        painter.drawText(
            QPointF(plot.left() - 10 - fm.horizontalAdvance(label), pt.y() + fm.ascent() / 2 - 1), label
        )
    painter.setPen(QPen(axis_color, 2))
    painter.drawLine(plot.bottomLeft(), plot.bottomRight())
    painter.drawLine(plot.bottomLeft(), plot.topLeft())
    # libellés d'axes avec unités, titre
    painter.setPen(text_pen)
    xl = cx_col.label
    painter.drawText(
        QPointF(plot.center().x() - fm.horizontalAdvance(xl) / 2, frame.bottom() - fm.descent() - 2), xl
    )
    painter.save()
    painter.translate(frame.left() + fm.ascent() + 2, plot.center().y())
    painter.rotate(-90)
    yl = cy_col.label
    painter.drawText(QPointF(-fm.horizontalAdvance(yl) / 2, 0), yl)
    painter.restore()
    title = str(p.get("title", ""))
    if title:
        painter.drawText(
            QPointF(plot.center().x() - fm.horizontalAdvance(title) / 2, frame.top() + fm.ascent() + 4), title
        )
    # courbe (progression : fraction des points tracés, interpolation du dernier segment)
    progress = max(0.0, min(1.0, float(p.get("progress", 1.0))))
    n = len(points)
    reach = progress * (n - 1)
    k = int(math.floor(reach))
    poly = [to_px(*q) for q in points[: k + 1]]
    if k < n - 1 and reach > k:
        (xa, ya), (xb, yb) = points[k], points[k + 1]
        u = reach - k
        poly.append(to_px(xa + (xb - xa) * u, ya + (yb - ya) * u))
    painter.setClipRect(plot.adjusted(-2, -2, 2, 2))
    lw = float(p.get("line_width", 3.0))
    painter.setPen(
        QPen(
            qcolor(node.style.get("stroke", "#4FC3F7")),
            lw,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if len(poly) >= 2:
        painter.drawPolyline(QPolygonF(poly))
    if bool(p.get("show_points", False)):
        painter.setBrush(QBrush(qcolor(node.style.get("stroke", "#4FC3F7"))))
        painter.setPen(Qt.PenStyle.NoPen)
        for pt in poly[: k + 1]:
            painter.drawEllipse(pt, lw * 1.2, lw * 1.2)
    painter.setClipping(False)


def sequence_frame_path(folder: Path, frame_index: float, frame_count: int) -> Path:
    """Fichier ``frame_NNNN.png`` de la séquence pour un index (arrondi, borné, boucle sur la durée)."""
    n = max(1, int(frame_count))
    idx = int(round(frame_index)) % n
    return folder / f"frame_{idx + 1:04d}.png"


def _draw_image_sequence(
    painter: QPainter, node: NodeState, assets: AssetResolver | None, cache: ImageCache
) -> None:
    p = node.params
    w = float(p.get("width", 400.0))
    h = float(p.get("height", 0.0) or 0.0)
    img: QImage | None = None
    asset_id = str(p.get("sequence_asset_id", ""))
    if assets is not None and asset_id:
        folder = assets(asset_id)
        if folder is not None and folder.is_dir():
            img = cache.get(
                sequence_frame_path(folder, float(p.get("frame_index", 0.0)), int(p.get("frame_count", 1)))
            )
    if img is None or img.width() == 0:
        if h <= 0:
            h = w
        painter.setPen(QPen(QColor("#FF5555"), 3, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(QColor(255, 85, 85, 40)))
        painter.drawRect(QRectF(-w / 2, -h / 2, w, h))
        return
    if h <= 0:
        h = w * img.height() / img.width()
    target = QRectF(-w / 2, -h / 2, w, h)
    painter.drawImage(target, img)
    tint = node.style.get("tint")
    if is_color(tint) and qcolor(tint).alpha() > 0:
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        painter.fillRect(target, qcolor(tint))
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
    "callout": _draw_callout,
    "chart": _draw_chart,
    "formula": _draw_formula,
    "image_sequence": _draw_image_sequence,
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
    if k == "callout":
        return callout_rect(p)
    if k == "chart":
        return chart_frame(p)
    if k == "formula":
        return formula_rect(p)
    if k == "image":
        w = float(p.get("width", 300.0))
        h = float(p.get("height", 0.0) or 0.0) or w * 0.75
        return QRectF(-w / 2, -h / 2, w, h)
    if k == "image_sequence":
        w = float(p.get("width", 400.0))
        h = float(p.get("height", 0.0) or 0.0) or w
        return QRectF(-w / 2, -h / 2, w, h)
    return QRectF(-20, -20, 40, 40)


def render_state_to_image(
    state: SceneState,
    canvas: Canvas,
    width: int,
    height: int,
    assets: AssetResolver | None = None,
    image_cache: ImageCache | None = None,
    subtitle_style: dict[str, Any] | None = None,
) -> QImage:
    """Rastérise un état dans une ``QImage`` RGBA8888 (utilisé par l'export et les tests visuels)."""
    img = QImage(width, height, QImage.Format.Format_RGBA8888)
    img.fill(0)
    painter = QPainter(img)
    try:
        paint_scene_state(
            painter, state, canvas, width, height, assets, image_cache, subtitle_style=subtitle_style
        )
    finally:
        painter.end()
    return img

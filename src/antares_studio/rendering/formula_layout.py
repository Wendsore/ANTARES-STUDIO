"""Mise en page et dessin des formules (arbre de ``science.formula``) avec QPainter, utilisé par l'export."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QFontMetricsF, QPainter, QPen

from antares_studio.science.formula import Node, parse_formula

SCRIPT_SCALE = 0.65
MIN_FONT_PT = 4.0


@dataclass
class Box:
    """Boîte mesurée : largeur, hauteur au-dessus et au-dessous de la ligne de base."""

    width: float
    above: float
    below: float

    @property
    def height(self) -> float:
        return self.above + self.below


def _font(base: QFont, scale: float, italic: bool) -> QFont:
    f = QFont(base)
    f.setPointSizeF(max(MIN_FONT_PT, base.pointSizeF() * scale))
    f.setItalic(italic)
    return f


def _is_variable(text: str) -> bool:
    return bool(text.strip()) and all(ch.isalpha() and ch.isascii() or ch == " " for ch in text)


class FormulaRenderer:
    """Mesure puis dessine ; ``italic_vars`` met les lettres latines en italique (convention ISO 80000-2)."""

    def __init__(self, base_font: QFont, italic_vars: bool = True):
        self.base = base_font
        self.italic_vars = italic_vars

    # --- mesure ---------------------------------------------------------------
    def measure(self, node: Node, scale: float = 1.0) -> Box:
        font = _font(self.base, scale, False)
        fm = QFontMetricsF(font)
        em = fm.height()
        if node.kind == "text":
            f = _font(self.base, scale, self.italic_vars and _is_variable(node.text))
            m = QFontMetricsF(f)
            return Box(m.horizontalAdvance(node.text), m.ascent(), m.descent())
        if node.kind == "row":
            boxes = [self.measure(c, scale) for c in node.children]
            gap = em * 0.04
            width = sum(b.width for b in boxes) + gap * max(0, len(boxes) - 1)
            above = max((b.above for b in boxes), default=fm.ascent())
            below = max((b.below for b in boxes), default=fm.descent())
            return Box(width, above, below)
        if node.kind in ("sup", "sub"):
            child = self.measure(node.children[0], scale * SCRIPT_SCALE)
            shift = fm.ascent() * (0.45 if node.kind == "sup" else -0.25)
            above = max(fm.ascent() * 0.6, child.above + shift) if node.kind == "sup" else fm.ascent() * 0.6
            below = child.below - shift if node.kind == "sub" else fm.descent()
            return Box(child.width + em * 0.05, above, max(below, 0.0))
        if node.kind == "frac":
            num = self.measure(node.children[0], scale * 0.92)
            den = self.measure(node.children[1], scale * 0.92)
            axis = fm.xHeight() * 0.55
            gap = em * 0.12
            width = max(num.width, den.width) + em * 0.3
            return Box(width, axis + gap + num.height, max(0.0, den.height + gap - axis))
        if node.kind == "sqrt":
            child = self.measure(node.children[0], scale)
            return Box(child.width + em * 0.75, child.above + em * 0.18, child.below)
        if node.kind in ("vec", "hat", "bar"):
            child = self.measure(node.children[0], scale)
            return Box(child.width, child.above + em * 0.22, child.below)
        return Box(0.0, fm.ascent(), fm.descent())

    # --- dessin ---------------------------------------------------------------
    def draw(self, painter: QPainter, node: Node, x: float, baseline: float, scale: float = 1.0) -> float:
        """Dessine ``node`` à partir de ``x`` sur ``baseline`` ; retourne la largeur consommée."""
        font = _font(self.base, scale, False)
        fm = QFontMetricsF(font)
        em = fm.height()
        pen = painter.pen()
        if node.kind == "text":
            f = _font(self.base, scale, self.italic_vars and _is_variable(node.text))
            painter.setFont(f)
            painter.drawText(QPointF(x, baseline), node.text)
            return QFontMetricsF(f).horizontalAdvance(node.text)
        if node.kind == "row":
            gap = em * 0.04
            cx = x
            for i, c in enumerate(node.children):
                cx += self.draw(painter, c, cx, baseline, scale) + (gap if i < len(node.children) - 1 else 0)
            return cx - x
        if node.kind in ("sup", "sub"):
            shift = fm.ascent() * (0.45 if node.kind == "sup" else -0.25)
            w = self.draw(painter, node.children[0], x + em * 0.05, baseline - shift, scale * SCRIPT_SCALE)
            return w + em * 0.05
        if node.kind == "frac":
            box = self.measure(node, scale)
            num = self.measure(node.children[0], scale * 0.92)
            den = self.measure(node.children[1], scale * 0.92)
            axis = fm.xHeight() * 0.55
            gap = em * 0.12
            bar_y = baseline - axis
            self.draw(
                painter,
                node.children[0],
                x + (box.width - num.width) / 2,
                bar_y - gap - num.below,
                scale * 0.92,
            )
            self.draw(
                painter,
                node.children[1],
                x + (box.width - den.width) / 2,
                bar_y + gap + den.above,
                scale * 0.92,
            )
            painter.setPen(QPen(pen.color(), max(1.0, em * 0.05)))
            painter.drawLine(QPointF(x + em * 0.1, bar_y), QPointF(x + box.width - em * 0.1, bar_y))
            painter.setPen(pen)
            return box.width
        if node.kind == "sqrt":
            child = self.measure(node.children[0], scale)
            top = baseline - child.above - em * 0.12
            bottom = baseline + child.below
            lw = max(1.0, em * 0.05)
            painter.setPen(QPen(pen.color(), lw))
            x0 = x
            painter.drawLine(QPointF(x0, baseline - child.above * 0.4), QPointF(x0 + em * 0.2, bottom))
            painter.drawLine(QPointF(x0 + em * 0.2, bottom), QPointF(x0 + em * 0.55, top))
            painter.drawLine(QPointF(x0 + em * 0.55, top), QPointF(x0 + em * 0.75 + child.width, top))
            painter.setPen(pen)
            self.draw(painter, node.children[0], x + em * 0.7, baseline, scale)
            return child.width + em * 0.75
        if node.kind in ("vec", "hat", "bar"):
            child = self.measure(node.children[0], scale)
            w = self.draw(painter, node.children[0], x, baseline, scale)
            y = baseline - child.above - em * 0.08
            painter.setPen(QPen(pen.color(), max(1.0, em * 0.045)))
            if node.kind == "vec":
                painter.drawLine(QPointF(x, y), QPointF(x + w, y))
                painter.drawLine(QPointF(x + w - em * 0.15, y - em * 0.1), QPointF(x + w, y))
                painter.drawLine(QPointF(x + w - em * 0.15, y + em * 0.1), QPointF(x + w, y))
            elif node.kind == "bar":
                painter.drawLine(QPointF(x, y), QPointF(x + w, y))
            else:
                painter.drawLine(QPointF(x, y + em * 0.08), QPointF(x + w / 2, y - em * 0.08))
                painter.drawLine(QPointF(x + w / 2, y - em * 0.08), QPointF(x + w, y + em * 0.08))
            painter.setPen(pen)
            return w
        return 0.0


@dataclass(frozen=True)
class Glyph:
    text: str  # un caractère
    font: QFont
    x: float
    baseline: float


@dataclass(frozen=True)
class Stroke:
    a: QPointF
    b: QPointF
    width: float


class _Recorder:
    """Remplace le QPainter pendant ``FormulaRenderer.draw`` : relève glyphes (un par caractère) et traits."""

    def __init__(self) -> None:
        self.glyphs: list[Glyph] = []
        self.strokes: list[Stroke] = []
        self._pen = QPen()
        self._font = QFont()

    def pen(self) -> QPen:
        return self._pen

    def setPen(self, pen: QPen) -> None:
        self._pen = QPen(pen)

    def setFont(self, font: QFont) -> None:
        self._font = QFont(font)

    def drawText(self, pos: QPointF, text: str) -> None:
        fm = QFontMetricsF(self._font)
        x = pos.x()
        for ch in text:
            if not ch.isspace():
                self.glyphs.append(Glyph(ch, self._font, x, pos.y()))
            x += fm.horizontalAdvance(ch)

    def drawLine(self, a: QPointF, b: QPointF) -> None:
        self.strokes.append(Stroke(QPointF(a), QPointF(b), self._pen.widthF()))


def layout_glyphs(params: dict[str, Any], text: str) -> tuple[list[Glyph], list[Stroke]]:
    """Glyphes et traits de la formule ``text`` centrée comme dans ``paint_formula``."""
    renderer = FormulaRenderer(formula_font(params), bool(params.get("italic", True)))
    root = parse_formula(text).root
    rec = _Recorder()
    renderer.draw(rec, root, -renderer.measure(root).width / 2, 0.0)  # type: ignore[arg-type]
    return rec.glyphs, rec.strokes


def morph_pairs(
    source: list[Glyph], target: list[Glyph]
) -> tuple[list[tuple[Glyph, Glyph]], list[Glyph], list[Glyph]]:
    """Appariement des caractères communs dans l'ordre (plus longue sous-suite commune) :
    (paires qui se déplacent, glyphes qui disparaissent, glyphes qui apparaissent)."""
    from difflib import SequenceMatcher

    matcher = SequenceMatcher(None, [g.text for g in source], [g.text for g in target], autojunk=False)
    pairs: list[tuple[Glyph, Glyph]] = []
    gone: list[Glyph] = []
    new: list[Glyph] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            pairs += list(zip(source[i1:i2], target[j1:j2], strict=True))
        else:
            gone += source[i1:i2]
            new += target[j1:j2]
    return pairs, gone, new


def _morph_amount(params: dict[str, Any]) -> float:
    if not str(params.get("morph_to", "")).strip():
        return 0.0
    return max(0.0, min(1.0, float(params.get("morph", 0.0))))


def formula_font(params: dict[str, Any]) -> QFont:
    font = QFont(str(params.get("font_family", "DejaVu Sans")))
    font.setPointSizeF(max(1.0, float(params.get("font_size", 56.0))))
    return font


def _text_rect(params: dict[str, Any], text: str) -> QRectF:
    renderer = FormulaRenderer(formula_font(params), bool(params.get("italic", True)))
    box = renderer.measure(parse_formula(text).root)
    pad = formula_font(params).pointSizeF() * 0.25
    return QRectF(-box.width / 2 - pad, -box.above - pad, box.width + 2 * pad, box.height + 2 * pad)


def formula_rect(params: dict[str, Any]) -> QRectF:
    """Rectangle local centré de la formule (sélection, poignées, export) ; interpolé pendant une
    transformation vers ``morph_to``."""
    src = _text_rect(params, str(params.get("text", "")))
    u = _morph_amount(params)
    if u <= 0.0:
        return src
    dst = _text_rect(params, str(params.get("morph_to", "")))
    if u >= 1.0:
        return dst
    return QRectF(
        src.left() + (dst.left() - src.left()) * u,
        src.top() + (dst.top() - src.top()) * u,
        src.width() + (dst.width() - src.width()) * u,
        src.height() + (dst.height() - src.height()) * u,
    )


def paint_formula(painter: QPainter, params: dict[str, Any], color_pen: QPen, background: Any) -> None:
    u = _morph_amount(params)
    text = str(params.get("morph_to" if u >= 1.0 else "text", ""))
    rect = formula_rect(params)
    if background is not None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 6, 6)
    painter.setPen(color_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if 0.0 < u < 1.0:
        _paint_morph(painter, params, u)
        return
    formula = parse_formula(text)
    renderer = FormulaRenderer(formula_font(params), bool(params.get("italic", True)))
    renderer.draw(painter, formula.root, -renderer.measure(formula.root).width / 2, 0.0)


def _paint_morph(painter: QPainter, params: dict[str, Any], u: float) -> None:
    """Transformation : les caractères communs glissent vers leur place, les autres se fondent."""
    src_glyphs, src_strokes = layout_glyphs(params, str(params.get("text", "")))
    dst_glyphs, dst_strokes = layout_glyphs(params, str(params.get("morph_to", "")))
    pairs, gone, new = morph_pairs(src_glyphs, dst_glyphs)
    color = painter.pen().color()
    base_opacity = painter.opacity()

    def glyph(g: Glyph, x: float, baseline: float, size: float, alpha: float) -> None:
        if alpha <= 0.0:
            return
        font = QFont(g.font)
        font.setPointSizeF(max(MIN_FONT_PT, size))
        painter.setOpacity(base_opacity * alpha)
        painter.setFont(font)
        painter.drawText(QPointF(x, baseline), g.text)

    def strokes(items: list[Stroke], alpha: float) -> None:
        if alpha <= 0.0:
            return
        painter.setOpacity(base_opacity * alpha)
        for s in items:
            painter.setPen(QPen(color, s.width))
            painter.drawLine(s.a, s.b)
        painter.setPen(QPen(color))

    for a, b in pairs:
        size = a.font.pointSizeF() + (b.font.pointSizeF() - a.font.pointSizeF()) * u
        glyph(
            b if u >= 0.5 else a, a.x + (b.x - a.x) * u, a.baseline + (b.baseline - a.baseline) * u, size, 1.0
        )
    # les disparitions se terminent à mi-parcours, les apparitions commencent à mi-parcours
    for g in gone:
        glyph(g, g.x, g.baseline, g.font.pointSizeF(), max(0.0, 1.0 - 2.0 * u))
    for g in new:
        glyph(g, g.x, g.baseline, g.font.pointSizeF(), max(0.0, 2.0 * u - 1.0))
    strokes(src_strokes, max(0.0, 1.0 - 2.0 * u))
    strokes(dst_strokes, max(0.0, 2.0 * u - 1.0))
    painter.setOpacity(base_opacity)

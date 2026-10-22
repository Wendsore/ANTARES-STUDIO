"""Écriture progressive des textes et des formules (paramètre animable ``write`` de 0 à 1).

Le texte est découpé en unités dans l'ordre de lecture : un caractère (contour vectoriel issu de la
police), ou un trait de formule (barre de fraction, racine, flèche de vecteur). Chaque unité a sa propre
progression, décalée de celle de la précédente, comme une main qui écrit. Façons d'écrire :

- ``trace`` : le contour de chaque lettre se dessine, puis la lettre se remplit (animation « Write » des
  vidéos 3Blue1Brown) ;
- ``chalk`` : chaque lettre se découvre de gauche à droite, comme passée à la craie (à combiner avec
  l'effet « Texture craie ») ;
- ``typewriter`` : les caractères arrivent un à un, curseur en bout de ligne ;
- ``letters`` / ``words`` : lettres ou mots en fondu, avec une légère montée.

À ``write`` = 1 le dessin habituel est utilisé tel quel : un texte entièrement écrit est identique à un
texte sans écriture progressive.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF, QTextLayout, QTextOption

# chevauchement des unités : nombre d'unités qui s'écrivent en même temps
_OVERLAP = {"trace": 2.5, "chalk": 1.2, "typewriter": 0.0, "letters": 3.0, "words": 1.0}


@dataclass(frozen=True)
class Unit:
    path: QPainterPath  # forme à remplir (caractère) ou ligne à tracer (trait de formule)
    rect: QRectF
    word: int  # numéro du mot (façon ``words``)
    line: tuple[QPointF, QPointF] | None = None  # trait de formule : extrémités
    width: float = 0.0  # épaisseur du trait
    baseline: float = 0.0  # ligne de base du caractère (curseur de la machine à écrire)


def write_amount(params: dict[str, Any]) -> float:
    try:
        return max(0.0, min(1.0, float(params.get("write", 1.0))))
    except (TypeError, ValueError):
        return 1.0


def is_partial(params: dict[str, Any]) -> bool:
    """Vrai si le texte est en cours d'écriture (sinon : dessin habituel, ou rien à ``write`` = 0)."""
    return write_amount(params) < 1.0


def _font_key(font: QFont) -> str:
    return font.toString()


def text_units(text: str, font: QFont, rect: QRectF, flags: int, max_width: float) -> list[Unit]:
    """Unités d'un texte mis en page comme ``QPainter.drawText(rect, flags, text)``."""
    return list(
        _text_units(text, _font_key(font), rect.left(), rect.top(), rect.width(), flags, max_width > 0)
    )


@lru_cache(maxsize=256)
def _text_units(
    text: str, font_key: str, left: float, top: float, width: float, flags: int, wrap: bool
) -> tuple[Unit, ...]:
    font = QFont()
    font.fromString(font_key)
    layout = QTextLayout(text.replace("\n", " "), font)
    option = QTextOption()
    if flags & int(Qt.AlignmentFlag.AlignLeft):
        option.setAlignment(Qt.AlignmentFlag.AlignLeft)
    elif flags & int(Qt.AlignmentFlag.AlignRight):
        option.setAlignment(Qt.AlignmentFlag.AlignRight)
    else:
        option.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    option.setWrapMode(QTextOption.WrapMode.WordWrap if wrap else QTextOption.WrapMode.NoWrap)
    layout.setTextOption(option)
    layout.beginLayout()
    y = 0.0
    lines = []
    while True:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(width)
        line.setPosition(QPointF(0.0, y))
        y += line.height()
        lines.append(line)
    layout.endLayout()
    units: list[Unit] = []
    word = 0
    prev_space = True
    for line in lines:
        start, end = line.textStart(), line.textStart() + line.textLength()
        baseline = top + line.y() + line.ascent()
        # alignement : QTextLayout aligne dans la largeur de ligne fournie
        for i in range(start, end):
            ch = text[i] if i < len(text) else ""
            if not ch or ch.isspace():
                prev_space = True
                continue
            if prev_space:
                word += 1
                prev_space = False
            x = left + float(line.cursorToX(i)[0])  # type: ignore[index]
            path = QPainterPath()
            path.addText(QPointF(x, baseline), font, ch)
            units.append(Unit(path, path.boundingRect(), word, baseline=baseline))
        prev_space = True  # un retour à la ligne sépare aussi les mots
    return tuple(units)


def formula_units(glyphs: list[Any], strokes: list[Any]) -> list[Unit]:
    """Unités d'une formule à partir de ``formula_layout.layout_glyphs`` : caractères et traits rangés de
    gauche à droite (une barre de fraction s'écrit avant le dénominateur, comme à la main)."""
    items: list[tuple[float, float, Unit]] = []
    for g in glyphs:
        path = QPainterPath()
        path.addText(QPointF(g.x, g.baseline), g.font, g.text)
        r = path.boundingRect()
        items.append((r.left(), r.top(), Unit(path, r, 0, baseline=g.baseline)))
    for s in strokes:
        path = QPainterPath(s.a)
        path.lineTo(s.b)
        r = path.boundingRect().adjusted(-s.width / 2, -s.width / 2, s.width / 2, s.width / 2)
        line = (QPointF(s.a), QPointF(s.b))
        items.append((min(s.a.x(), s.b.x()), r.top(), Unit(path, r, 0, line, s.width, max(s.a.y(), s.b.y()))))
    items.sort(key=lambda t: (round(t[0], 1), t[1]))
    return [Unit(u.path, u.rect, i + 1, u.line, u.width, u.baseline) for i, (_x, _y, u) in enumerate(items)]


def unit_progress(amount: float, index: int, count: int, overlap: float) -> float:
    """Progression (0..1) de l'unité ``index`` sur ``count`` quand l'ensemble en est à ``amount``."""
    if count <= 0:
        return 0.0
    if overlap <= 0.0:  # tout ou rien, un caractère après l'autre
        return 1.0 if amount * count > index + 1e-9 else 0.0
    u = (amount * (count + overlap) - index) / (1.0 + overlap)
    return max(0.0, min(1.0, u))


def _partial_polyline(poly: QPolygonF, fraction: float) -> QPolygonF:
    """Début de la ligne brisée ``poly`` sur ``fraction`` de sa longueur."""
    pts = [poly.at(i) for i in range(poly.count())]
    if fraction >= 1.0 or len(pts) < 2:
        return poly
    lengths = [math.hypot(b.x() - a.x(), b.y() - a.y()) for a, b in zip(pts, pts[1:], strict=False)]
    target = sum(lengths) * max(0.0, fraction)
    out = [pts[0]]
    for (a, b), seg in zip(zip(pts, pts[1:], strict=False), lengths, strict=True):
        if target <= seg:
            t = target / seg if seg > 0 else 0.0
            out.append(QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t))
            break
        out.append(b)
        target -= seg
    return QPolygonF(out)


def paint_units(
    painter: QPainter,
    units: list[Unit],
    amount: float,
    style: str,
    color: QColor,
    font_px: float,
    outline: tuple[QColor, float] | None = None,
) -> None:
    """Dessine les unités à l'étape ``amount`` de l'écriture."""
    if amount <= 0.0 or not units:
        return
    style = style if style in _OVERLAP else "trace"
    base_opacity = painter.opacity()
    words = max(u.word for u in units)
    count = words if style == "words" else len(units)
    overlap = _OVERLAP[style]
    pen_w = max(1.0, font_px * 0.035)
    last_visible: Unit | None = None
    for i, unit in enumerate(units):
        u = unit_progress(amount, (unit.word - 1) if style == "words" else i, count, overlap)
        if u <= 0.0:
            continue
        last_visible = unit
        painter.save()
        if unit.line is not None:  # trait de formule : il se trace dans tous les styles
            reach = u if style in ("trace", "chalk") else 1.0
            painter.setOpacity(base_opacity * (1.0 if style in ("trace", "chalk", "typewriter") else u))
            a, b = unit.line
            painter.setPen(QPen(color, unit.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
            painter.drawLine(a, QPointF(a.x() + (b.x() - a.x()) * reach, a.y() + (b.y() - a.y()) * reach))
            painter.restore()
            continue
        if style == "trace":
            stroke = min(1.0, u / 0.65)  # le contour se dessine sur les deux premiers tiers
            fill = max(0.0, (u - 0.5) / 0.5)  # puis la lettre se remplit
            if fill > 0:
                painter.setOpacity(base_opacity * fill)
                _fill(painter, unit.path, color, outline)
            if fill < 1.0:
                painter.setOpacity(base_opacity * (1.0 - 0.6 * fill))
                painter.setPen(QPen(color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                for poly in unit.path.toSubpathPolygons():
                    painter.drawPolyline(_partial_polyline(poly, stroke))
        elif style == "chalk":
            r = unit.rect.adjusted(-pen_w, -pen_w, pen_w, pen_w)
            # bord légèrement penché : la craie avance en biais
            edge = r.left() + r.width() * u
            slant = r.height() * 0.18 * (1.0 - u)
            clip = QPainterPath()
            clip.moveTo(r.left() - 1, r.top())
            clip.lineTo(edge + slant, r.top())
            clip.lineTo(edge - slant, r.bottom())
            clip.lineTo(r.left() - 1, r.bottom())
            clip.closeSubpath()
            painter.setClipPath(clip, Qt.ClipOperation.IntersectClip)
            _fill(painter, unit.path, color, outline)
        elif style == "typewriter":
            _fill(painter, unit.path, color, outline)
        else:  # letters, words : fondu et légère montée
            painter.setOpacity(base_opacity * u)
            painter.translate(0.0, (1.0 - u) * font_px * 0.25)
            _fill(painter, unit.path, color, outline)
        painter.restore()
    if style == "typewriter" and amount < 1.0 and last_visible is not None:
        r, base = last_visible.rect, last_visible.baseline
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRect(QRectF(r.right() + font_px * 0.08, base - font_px * 0.8, font_px * 0.07, font_px))
        painter.restore()


def _fill(painter: QPainter, path: QPainterPath, color: QColor, outline: tuple[QColor, float] | None) -> None:
    if outline is not None and outline[1] > 0:
        painter.setPen(
            QPen(
                outline[0],
                outline[1],
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(path)

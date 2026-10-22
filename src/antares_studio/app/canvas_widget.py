"""Canvas d'édition : affiche ``SceneState`` via ``paint_scene_state`` ; sélection, déplacement, poignées.

La prévisualisation utilise strictement le même dessin que l'export (ADR-0001). Les calques de sélection,
grille et zones sûres sont dessinés par-dessus et jamais exportés.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
    QResizeEvent,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from antares_studio.app import theme
from antares_studio.app.document import ProjectDocument
from antares_studio.domain.layout import Guide, Rect, snap_rect
from antares_studio.rendering.qt_painter import ImageCache, local_bounds, paint_scene_state
from antares_studio.timeline.evaluator import NodeState, SceneState

HANDLE_PX = 9.0
ROTATE_OFFSET_PX = 28.0


class Handle(Enum):
    NONE = "none"
    MOVE = "move"
    TL = "tl"
    T = "t"
    TR = "tr"
    R = "r"
    BR = "br"
    B = "b"
    BL = "bl"
    L = "l"
    ROTATE = "rotate"


_CURSORS = {
    Handle.TL: Qt.CursorShape.SizeFDiagCursor,
    Handle.BR: Qt.CursorShape.SizeFDiagCursor,
    Handle.TR: Qt.CursorShape.SizeBDiagCursor,
    Handle.BL: Qt.CursorShape.SizeBDiagCursor,
    Handle.T: Qt.CursorShape.SizeVerCursor,
    Handle.B: Qt.CursorShape.SizeVerCursor,
    Handle.L: Qt.CursorShape.SizeHorCursor,
    Handle.R: Qt.CursorShape.SizeHorCursor,
    Handle.ROTATE: Qt.CursorShape.CrossCursor,
    Handle.MOVE: Qt.CursorShape.SizeAllCursor,
}


@dataclass
class _Drag:
    handle: Handle
    start_canvas: QPointF
    node_id: str | None
    start_props: dict[
        str, dict[str, float]
    ]  # node_id -> {position.x, position.y, scale.x, scale.y, rotation_deg}
    first_push: bool = True
    moved: bool = False
    start_rect: Rect | None = None  # boîte englobante des objets déplacés au départ (guides)
    targets: tuple[Rect, ...] = ()  # boîtes des autres objets et du canevas


def _qtransform(world: tuple[float, float, float, float, float, float]) -> QTransform:
    a, b, c, d, tx, ty = world
    return QTransform(a, b, c, d, tx, ty)


class CanvasWidget(QWidget):
    """Widget central : zoom/pan, sélection et transformation directe des objets."""

    zoomChanged = Signal(float)
    cursorMoved = Signal(float, float)  # coordonnées canevas
    nodeDoubleClicked = Signal(str)

    def __init__(self, document: ProjectDocument, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self.zoom = 0.5
        self.offset = QPointF(40, 40)
        self.show_grid = False
        self.show_safe_zones = False
        self.grid_step = 50
        self.snap_to_grid = False
        self.smart_guides = True  # aimantation aux bords et centres des autres objets (Ctrl : désactivée)
        self.guides: list[Guide] = []
        self._drag: _Drag | None = None
        self._pan_start: QPointF | None = None
        self._rubber: QRectF | None = None
        self._hover_handle = Handle.NONE
        self._image_cache = ImageCache()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(320, 180)
        document.changed.connect(self.update)
        document.frameChanged.connect(lambda _f: self.update())
        document.selectionChanged.connect(lambda _s: self.update())
        document.sceneChanged.connect(lambda _s: self.fit_to_view())

    # --- transformations vue --------------------------------------------
    def canvas_to_widget(self, p: QPointF) -> QPointF:
        return QPointF(p.x() * self.zoom + self.offset.x(), p.y() * self.zoom + self.offset.y())

    def widget_to_canvas(self, p: QPointF) -> QPointF:
        return QPointF((p.x() - self.offset.x()) / self.zoom, (p.y() - self.offset.y()) / self.zoom)

    def set_zoom(self, zoom: float, anchor: QPointF | None = None) -> None:
        zoom = max(0.05, min(8.0, zoom))
        if anchor is None:
            anchor = QPointF(self.width() / 2, self.height() / 2)
        before = self.widget_to_canvas(anchor)
        self.zoom = zoom
        after = self.canvas_to_widget(before)
        self.offset += anchor - after
        self.zoomChanged.emit(zoom)
        self.update()

    def fit_to_view(self) -> None:
        c = self.document.project.canvas
        margin = 30
        zx = (self.width() - 2 * margin) / c.width
        zy = (self.height() - 2 * margin) / c.height
        self.zoom = max(0.05, min(zx, zy))
        self.offset = QPointF(
            (self.width() - c.width * self.zoom) / 2, (self.height() - c.height * self.zoom) / 2
        )
        self.zoomChanged.emit(self.zoom)
        self.update()

    # --- géométrie des objets ---------------------------------------------
    def node_world_polygon(self, node: NodeState) -> QPolygonF:
        return _qtransform(node.world).map(QPolygonF(local_bounds(node)))

    def node_widget_polygon(self, node: NodeState) -> QPolygonF:
        poly = self.node_world_polygon(node)
        return QPolygonF([self.canvas_to_widget(poly.at(i)) for i in range(poly.count())])

    def hit_test(self, widget_pos: QPointF) -> NodeState | None:
        state = self.document.state()
        if state is None:
            return None
        canvas_pt = self.widget_to_canvas(widget_pos)
        for node in reversed(state.nodes):
            if not node.visible or node.locked or node.kind == "group":
                continue
            inv, ok = _qtransform(node.world).inverted()
            if not ok:
                continue
            local = inv.map(canvas_pt)
            bounds = local_bounds(node)
            slack = 4.0 / self.zoom
            if bounds.adjusted(-slack, -slack, slack, slack).contains(local):
                return node
        return None

    def _handles(self, node: NodeState) -> dict[Handle, QPointF]:
        """Positions widget des poignées de l'objet sélectionné (bords du rectangle local transformé)."""
        b = local_bounds(node)
        t = _qtransform(node.world)
        pts = {
            Handle.TL: b.topLeft(),
            Handle.T: QPointF(b.center().x(), b.top()),
            Handle.TR: b.topRight(),
            Handle.R: QPointF(b.right(), b.center().y()),
            Handle.BR: b.bottomRight(),
            Handle.B: QPointF(b.center().x(), b.bottom()),
            Handle.BL: b.bottomLeft(),
            Handle.L: QPointF(b.left(), b.center().y()),
        }
        out = {h: self.canvas_to_widget(t.map(p)) for h, p in pts.items()}
        top = out[Handle.T]
        center = self.canvas_to_widget(t.map(b.center()))
        d = top - center
        n = math.hypot(d.x(), d.y()) or 1.0
        out[Handle.ROTATE] = QPointF(
            top.x() + d.x() / n * ROTATE_OFFSET_PX, top.y() + d.y() / n * ROTATE_OFFSET_PX
        )
        return out

    def _handle_at(self, widget_pos: QPointF) -> tuple[Handle, NodeState | None]:
        state = self.document.state()
        sel = self.document.selection
        if state is None or len(sel) != 1:
            return Handle.NONE, None
        try:
            node = state.node(sel[0])
        except KeyError:
            return Handle.NONE, None
        if node.locked:
            return Handle.NONE, None
        for h, p in self._handles(node).items():
            if abs(p.x() - widget_pos.x()) <= HANDLE_PX and abs(p.y() - widget_pos.y()) <= HANDLE_PX:
                return h, node
        return Handle.NONE, None

    # --- dessin -------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), theme.WORKSPACE_BG)
        state = self.document.state()
        c = self.document.project.canvas
        canvas_rect = QRectF(
            self.offset,
            QPointF(self.offset.x() + c.width * self.zoom, self.offset.y() + c.height * self.zoom),
        )
        painter.fillRect(canvas_rect.translated(6, 6), theme.CANVAS_SHADOW)
        if state is not None:
            painter.save()
            painter.setClipRect(canvas_rect)
            painter.translate(self.offset)
            w = max(1, int(round(c.width * self.zoom)))
            h = max(1, int(round(c.height * self.zoom)))
            paint_scene_state(
                painter,
                state,
                c,
                w,
                h,
                self.document.resolve_asset,
                self._image_cache,
                subtitle_style=self.document.project.subtitle_style,
            )
            painter.restore()
        scene = self.document.scene
        if scene is not None and not scene.nodes:
            self._paint_empty_hint(painter, canvas_rect)
        if self.show_grid:
            self._paint_grid(painter, canvas_rect)
        if self.show_safe_zones:
            self._paint_safe_zones(painter, canvas_rect)
        if state is not None:
            self._paint_selection(painter, state)
        if self.guides:
            self._paint_guides(painter)
        if self._rubber is not None:
            painter.setPen(QPen(theme.SELECTION, 1, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(theme.RUBBER_BAND))
            painter.drawRect(self._rubber)
        painter.end()

    EMPTY_HINT = (
        "Scène vide\n\n"
        "Double-cliquez sur un objet de la Bibliothèque (à gauche) pour l'ajouter,\n"
        "ou un modèle de l'onglet « Modèles » pour une scène prête à l'emploi.\n\n"
        "Aide > Tutoriels : apprendre pas à pas · F1 : aide · Ctrl+K : toutes les commandes"
    )

    def _paint_empty_hint(self, painter: QPainter, canvas_rect: QRectF) -> None:
        """Rappel des premiers gestes sur une scène vide (éditeur seulement, jamais exporté)."""
        if canvas_rect.width() < 240 or canvas_rect.height() < 140:
            return
        painter.save()
        font = QFont(painter.font())
        font.setPointSizeF(theme.scaled_pt(11))
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 170))
        painter.drawText(
            canvas_rect.adjusted(24, 24, -24, -24),
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            self.EMPTY_HINT,
        )
        painter.restore()

    def _paint_grid(self, painter: QPainter, rect: QRectF) -> None:
        step = self.grid_step * self.zoom
        if step < 6:
            return
        painter.save()
        painter.setClipRect(rect)
        x = rect.left()
        i = 0
        while x <= rect.right():
            painter.setPen(QPen(theme.GRID_MAJOR if i % 4 == 0 else theme.GRID, 1))
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += step
            i += 1
        y = rect.top()
        i = 0
        while y <= rect.bottom():
            painter.setPen(QPen(theme.GRID_MAJOR if i % 4 == 0 else theme.GRID, 1))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += step
            i += 1
        painter.restore()

    def _paint_guides(self, painter: QPainter) -> None:
        painter.save()
        painter.setPen(QPen(theme.GUIDE, 1))
        for g in self.guides:
            if g.axis == "x":
                a, b = QPointF(g.value, g.start), QPointF(g.value, g.end)
            else:
                a, b = QPointF(g.start, g.value), QPointF(g.end, g.value)
            painter.drawLine(self.canvas_to_widget(a), self.canvas_to_widget(b))
        painter.restore()

    def node_rect(self, node: NodeState) -> Rect:
        """Boîte englobante (repère du canevas) de l'objet tel qu'il est affiché."""
        r = self.node_world_polygon(node).boundingRect()
        return (r.left(), r.top(), r.right(), r.bottom())

    def _snap_targets(self, moving: set[str]) -> tuple[Rect | None, tuple[Rect, ...]]:
        state = self.document.state()
        if state is None:
            return None, ()
        c = self.document.project.canvas
        ours: list[Rect] = []
        targets: list[Rect] = [(0.0, 0.0, float(c.width), float(c.height))]
        for n in state.nodes:
            if not n.visible or n.kind in ("group", "camera"):
                continue
            (ours if n.id in moving else targets).append(self.node_rect(n))
        if not ours:
            return None, tuple(targets)
        return (
            (
                min(r[0] for r in ours),
                min(r[1] for r in ours),
                max(r[2] for r in ours),
                max(r[3] for r in ours),
            ),
            tuple(targets),
        )

    def _paint_safe_zones(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setPen(QPen(theme.SAFE_ZONE, 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        mx, my = rect.width() * 0.05, rect.height() * 0.05
        painter.drawRect(rect.adjusted(mx, my, -mx, -my))
        # bande sous-titres : 20 % inférieurs
        painter.drawLine(
            QPointF(rect.left(), rect.bottom() - rect.height() * 0.2),
            QPointF(rect.right(), rect.bottom() - rect.height() * 0.2),
        )
        painter.restore()

    def _paint_selection(self, painter: QPainter, state: SceneState) -> None:
        sel = self.document.selection
        if not sel:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for nid in sel:
            try:
                node = state.node(nid)
            except KeyError:
                continue
            poly = self.node_widget_polygon(node)
            painter.setPen(QPen(theme.LOCKED if node.locked else theme.SELECTION, 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(poly)
        if len(sel) == 1:
            single: NodeState | None
            try:
                single = state.node(sel[0])
            except KeyError:
                single = None
            if single is not None and not single.locked:
                handles = self._handles(single)
                top = handles[Handle.T]
                rot = handles[Handle.ROTATE]
                painter.setPen(QPen(theme.SELECTION, 1))
                painter.drawLine(top, rot)
                for h, p in handles.items():
                    painter.setPen(QPen(theme.HANDLE_BORDER, 1.2))
                    painter.setBrush(QBrush(theme.ROTATE_HANDLE if h == Handle.ROTATE else theme.HANDLE_FILL))
                    r = HANDLE_PX / 2
                    if h == Handle.ROTATE:
                        painter.drawEllipse(p, r + 1, r + 1)
                    else:
                        painter.drawRect(QRectF(p.x() - r, p.y() - r, 2 * r, 2 * r))
        painter.restore()

    # --- souris -------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.AltModifier
        ):
            self._pan_start = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()
        handle, node = self._handle_at(pos)
        if handle != Handle.NONE and node is not None:
            self._drag = _Drag(handle, self.widget_to_canvas(pos), node.id, self._capture([node.id]))
            return
        hit = self.hit_test(pos)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if hit is None:
            if not shift:
                self.document.set_selection([])
            self._rubber = QRectF(pos, pos)
            self.update()
            return
        sel = self.document.selection
        if shift:
            self.document.set_selection([s for s in sel if s != hit.id] if hit.id in sel else [*sel, hit.id])
        elif hit.id not in sel:
            self.document.set_selection([hit.id])
        ids = [i for i in self.document.selection]
        start_props = self._capture(ids)
        start_rect, targets = self._snap_targets(self._moved_with_descendants(set(start_props)))
        self._drag = _Drag(
            Handle.MOVE,
            self.widget_to_canvas(pos),
            hit.id,
            start_props,
            start_rect=start_rect,
            targets=targets,
        )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        cp = self.widget_to_canvas(pos)
        self.cursorMoved.emit(cp.x(), cp.y())
        if self._pan_start is not None:
            self.offset += pos - self._pan_start
            self._pan_start = pos
            self.update()
            return
        if self._rubber is not None:
            self._rubber = QRectF(self._rubber.topLeft(), pos).normalized()
            self.update()
            return
        if self._drag is not None:
            self._apply_drag(cp, event.modifiers())
            return
        handle, _ = self._handle_at(pos)
        if handle == Handle.NONE and self.hit_test(pos) is not None:
            handle = Handle.MOVE
        if handle != self._hover_handle:
            self._hover_handle = handle
            self.setCursor(_CURSORS.get(handle, Qt.CursorShape.ArrowCursor))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._pan_start is not None:
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        if self._rubber is not None:
            self._finish_rubber(bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            return
        self._drag = None
        if self.guides:
            self.guides = []
            self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        hit = self.hit_test(event.position())
        if hit is not None:
            self.nodeDoubleClicked.emit(hit.id)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1 / 1.15
        self.set_zoom(self.zoom * factor, event.position())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        step = 10.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1.0
        moves = {
            Qt.Key.Key_Left: (-step, 0.0),
            Qt.Key.Key_Right: (step, 0.0),
            Qt.Key.Key_Up: (0.0, -step),
            Qt.Key.Key_Down: (0.0, step),
        }
        key = Qt.Key(event.key())
        if key in moves and self.document.selection:
            dx, dy = moves[key]
            for nid in self.document.selection:
                node = self.document.scene.node(nid) if self.document.scene else None
                if node is None or node.locked:
                    continue
                self.document.set_node_properties(
                    nid,
                    {"position.x": node.position[0] + dx, "position.y": node.position[1] + dy},
                    merge=False,
                )
            return
        if key == Qt.Key.Key_Escape:
            self.document.set_selection([])
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)

    # --- logique de glisser ---------------------------------------------------
    def _capture(self, ids: list[str]) -> dict[str, dict[str, float]]:
        scene = self.document.scene
        out: dict[str, dict[str, float]] = {}
        if scene is None:
            return out
        state = self.document.state()
        for nid in ids:
            node = scene.find_node(nid)
            if node is None or node.locked:
                continue
            st = state.node(nid) if state else None
            out[nid] = {
                "position.x": st.position[0] if st else node.position[0],
                "position.y": st.position[1] if st else node.position[1],
                "scale.x": st.scale[0] if st else node.scale[0],
                "scale.y": st.scale[1] if st else node.scale[1],
                "rotation_deg": st.rotation_deg if st else node.rotation_deg,
            }
        return out

    def _parent_inverse_linear(self, node_id: str) -> QTransform:
        """Inverse de la partie linéaire de la transformation monde du parent (identité sans parent)."""
        scene = self.document.scene
        state = self.document.state()
        if scene is None or state is None:
            return QTransform()
        node = scene.find_node(node_id)
        if node is None or node.parent_id is None:
            return QTransform()
        try:
            p = state.node(node.parent_id)
        except KeyError:
            return QTransform()
        a, b, c, d, _, _ = p.world
        inv, ok = QTransform(a, b, c, d, 0, 0).inverted()
        return inv if ok else QTransform()

    def _moved_with_descendants(self, ids: set[str]) -> set[str]:
        scene = self.document.scene
        out = set(ids)
        if scene is None:
            return out
        changed = True
        while changed:
            changed = False
            for n in scene.nodes:
                if n.parent_id in out and n.id not in out:
                    out.add(n.id)
                    changed = True
        return out

    def _snap(self, v: float) -> float:
        if self.snap_to_grid and self.grid_step > 0:
            return round(v / self.grid_step) * self.grid_step
        return v

    def _apply_drag(self, cp: QPointF, modifiers: Qt.KeyboardModifier) -> None:
        drag = self._drag
        if drag is None:
            return
        delta = cp - drag.start_canvas
        if not drag.moved and abs(delta.x()) < 2 / self.zoom and abs(delta.y()) < 2 / self.zoom:
            return
        drag.moved = True
        merge = not drag.first_push
        drag.first_push = False
        if drag.handle == Handle.MOVE:
            self.guides = []
            if (
                self.smart_guides
                and not self.snap_to_grid
                and drag.start_rect is not None
                and not modifiers & Qt.KeyboardModifier.ControlModifier
            ):
                r = drag.start_rect
                moved = (r[0] + delta.x(), r[1] + delta.y(), r[2] + delta.x(), r[3] + delta.y())
                dx, dy, self.guides = snap_rect(moved, list(drag.targets), 6.0 / self.zoom)
                delta = QPointF(delta.x() + dx, delta.y() + dy)
            # ne déplace que les nœuds dont aucun ancêtre n'est aussi déplacé
            scene = self.document.scene
            ancestors_selected: set[str] = set()
            if scene is not None:
                for nid in drag.start_props:
                    cur = scene.find_node(nid)
                    while cur is not None and cur.parent_id is not None:
                        if cur.parent_id in drag.start_props:
                            ancestors_selected.add(nid)
                            break
                        cur = scene.find_node(cur.parent_id)
            for nid, start in drag.start_props.items():
                if nid in ancestors_selected:
                    continue
                local = self._parent_inverse_linear(nid).map(delta)
                nx = self._snap(start["position.x"] + local.x())
                ny = self._snap(start["position.y"] + local.y())
                self.document.set_node_properties(nid, {"position.x": nx, "position.y": ny}, merge=merge)
            return
        if drag.node_id is None or drag.node_id not in drag.start_props:
            return
        nid = drag.node_id
        start = drag.start_props[nid]
        if drag.handle == Handle.ROTATE:
            state = self.document.state()
            if state is None:
                return
            center_world = QPointF(state.node(nid).world[4], state.node(nid).world[5])
            inv = self._parent_inverse_linear(nid)
            v0 = inv.map(drag.start_canvas - center_world)
            v1 = inv.map(cp - center_world)
            a0 = math.degrees(math.atan2(v0.y(), v0.x()))
            a1 = math.degrees(math.atan2(v1.y(), v1.x()))
            rot = start["rotation_deg"] + (a1 - a0)
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                rot = round(rot / 15.0) * 15.0
            self.document.set_node_properties(nid, {"rotation_deg": rot}, merge=merge)
            return
        # poignées d'échelle : exprimer la souris dans le repère local non mis à l'échelle
        state = self.document.state()
        if state is None:
            return
        ns = state.node(nid)
        bounds = local_bounds(ns)
        a, b, c, d, tx, ty = ns.world
        sx0, sy0 = start["scale.x"], start["scale.y"]
        if abs(sx0) < 1e-9 or abs(sy0) < 1e-9:
            return
        unscaled = QTransform(a / sx0, b / sx0, c / sy0, d / sy0, tx, ty)
        inv, ok = unscaled.inverted()
        if not ok:
            return
        lp = inv.map(cp)
        ref = {
            Handle.TL: (bounds.left(), bounds.top()),
            Handle.TR: (bounds.right(), bounds.top()),
            Handle.BR: (bounds.right(), bounds.bottom()),
            Handle.BL: (bounds.left(), bounds.bottom()),
            Handle.T: (None, bounds.top()),
            Handle.B: (None, bounds.bottom()),
            Handle.L: (bounds.left(), None),
            Handle.R: (bounds.right(), None),
        }[drag.handle]
        new_sx, new_sy = sx0, sy0
        if ref[0] is not None and abs(ref[0]) > 1e-9:
            new_sx = max(0.01, lp.x() / ref[0])
        if ref[1] is not None and abs(ref[1]) > 1e-9:
            new_sy = max(0.01, lp.y() / ref[1])
        if (
            drag.handle in (Handle.TL, Handle.TR, Handle.BR, Handle.BL)
            and modifiers & Qt.KeyboardModifier.ShiftModifier
        ):
            k = max(new_sx / sx0 if sx0 else 1.0, new_sy / sy0 if sy0 else 1.0)
            new_sx, new_sy = sx0 * k, sy0 * k
        if ref[0] is None:
            new_sx = sx0
        if ref[1] is None:
            new_sy = sy0
        self.document.set_node_properties(nid, {"scale.x": new_sx, "scale.y": new_sy}, merge=merge)

    def _finish_rubber(self, additive: bool) -> None:
        rect = self._rubber
        self._rubber = None
        state = self.document.state()
        if rect is None or state is None or (rect.width() < 3 and rect.height() < 3):
            self.update()
            return
        picked = []
        for node in state.nodes:
            if not node.visible or node.locked or node.kind == "group":
                continue
            poly = self.node_widget_polygon(node)
            if rect.contains(poly.boundingRect()):
                picked.append(node.id)
        current = self.document.selection if additive else []
        self.document.set_selection(current + [p for p in picked if p not in current])
        self.update()

    def selection_center_canvas(self) -> QPointF:
        c = self.document.project.canvas
        return QPointF(c.width / 2, c.height / 2)

    def visible_center_canvas(self) -> QPointF:
        return self.widget_to_canvas(QPointF(self.width() / 2, self.height() / 2))

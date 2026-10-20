"""Timeline : règle, tête de lecture, pistes par objet avec losanges de keyframes, lecture/pause/boucle."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollBar,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import theme
from antares_studio.app.document import ProjectDocument
from antares_studio.domain.commands import MoveKeyframe, RemoveKeyframe
from antares_studio.domain.kinds import property_label
from antares_studio.domain.model import Track

RULER_H = 26
ROW_H = 22
LABEL_W = 220


@dataclass
class _Row:
    node_id: str
    node_name: str
    track: Track | None  # None = ligne d'en-tête de l'objet
    label: str


class TimelineView(QWidget):
    """Zone graphique (règle + pistes)."""

    keyframeSelected = Signal(str, str, int)  # node_id, property, frame

    def __init__(self, document: ProjectDocument, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self.px_per_frame = 4.0
        self.scroll_frame = 0
        self.scroll_row = 0
        self.rows: list[_Row] = []
        self.selected_key: tuple[str, str, int] | None = None
        self._drag_key: tuple[str, str, int] | None = None
        self._drag_target: int | None = None
        self._scrubbing = False
        self.show_all_objects = True
        self.setMinimumHeight(120)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        document.changed.connect(self.rebuild_rows)
        document.selectionChanged.connect(lambda _s: self.rebuild_rows())
        document.sceneChanged.connect(lambda _s: self.rebuild_rows())
        document.frameChanged.connect(lambda _f: self.update())
        self.rebuild_rows()

    # --- données ------------------------------------------------------------
    def rebuild_rows(self) -> None:
        self.rows = []
        scene = self.document.scene
        if scene is None:
            self.update()
            return
        sel = set(self.document.selection)
        for node in scene.nodes:
            tracks = scene.tracks_for(node.id)
            if not self.show_all_objects and node.id not in sel:
                continue
            if not tracks and node.id not in sel:
                continue
            self.rows.append(_Row(node.id, node.name, None, node.name))
            for t in sorted(tracks, key=lambda t: t.property):
                self.rows.append(_Row(node.id, node.name, t, "   " + property_label(node.kind, t.property)))
        self.update()

    # --- géométrie ------------------------------------------------------------
    def frame_to_x(self, frame: int | float) -> float:
        return LABEL_W + (frame - self.scroll_frame) * self.px_per_frame

    def x_to_frame(self, x: float) -> int:
        return int(round((x - LABEL_W) / self.px_per_frame + self.scroll_frame))

    def visible_frames(self) -> int:
        return max(1, int((self.width() - LABEL_W) / self.px_per_frame))

    # --- dessin ----------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), theme.TRACK_BG)
        scene = self.document.scene
        if scene is None:
            p.end()
            return
        fps = float(self.document.project.canvas.fps)
        duration = scene.duration_frames
        # pistes
        y = RULER_H
        font = QFont()
        font.setPointSize(9)
        p.setFont(font)
        for i, row in enumerate(self.rows[self.scroll_row :]):
            rect = QRectF(0, y, self.width(), ROW_H)
            p.fillRect(rect, theme.TRACK_ALT_BG if i % 2 else theme.TRACK_BG)
            if row.track is None:
                p.setPen(theme.TEXT)
                f2 = QFont(font)
                f2.setBold(True)
                p.setFont(f2)
            else:
                p.setPen(theme.TEXT_MUTED)
                p.setFont(font)
            p.drawText(QRectF(6, y, LABEL_W - 10, ROW_H), Qt.AlignmentFlag.AlignVCenter, row.label)
            if row.track is not None:
                kfs = row.track.sorted_keyframes()
                if len(kfs) >= 2:
                    p.setPen(QPen(theme.KEYFRAME.darker(150), 2))
                    p.drawLine(
                        QPointF(self.frame_to_x(kfs[0].frame), y + ROW_H / 2),
                        QPointF(self.frame_to_x(kfs[-1].frame), y + ROW_H / 2),
                    )
                for kf in kfs:
                    frame = kf.frame
                    if (
                        self._drag_key == (row.node_id, row.track.property, kf.frame)
                        and self._drag_target is not None
                    ):
                        frame = self._drag_target
                    x = self.frame_to_x(frame)
                    if x < LABEL_W - 6 or x > self.width() + 6:
                        continue
                    selected = self.selected_key == (row.node_id, row.track.property, kf.frame)
                    self._draw_diamond(p, x, y + ROW_H / 2, selected)
            y += ROW_H
            if y > self.height():
                break
        # zone hors durée
        end_x = self.frame_to_x(duration)
        if end_x < self.width():
            p.fillRect(
                QRectF(max(LABEL_W, end_x), 0, self.width() - end_x, self.height()),
                QBrush(theme.CANVAS_SHADOW),
            )
        # règle
        p.fillRect(QRectF(0, 0, self.width(), RULER_H), theme.TRACK_ALT_BG.darker(120))
        p.setPen(theme.TEXT_MUTED)
        step = self._tick_step()
        f = (self.scroll_frame // step) * step
        while True:
            x = self.frame_to_x(f)
            if x > self.width():
                break
            if x >= LABEL_W:
                major = (f // step) % 5 == 0
                p.drawLine(QPointF(x, RULER_H - (10 if major else 5)), QPointF(x, RULER_H))
                if major:
                    secs = f / fps
                    p.drawText(QPointF(x + 3, 12), f"{secs:.1f}s" if step < fps else f"{secs:.0f}s")
            f += step
        # tête de lecture
        x = self.frame_to_x(self.document.frame)
        if x >= LABEL_W:
            p.setPen(QPen(theme.PLAYHEAD, 2))
            p.drawLine(QPointF(x, 0), QPointF(x, self.height()))
            p.setBrush(QBrush(theme.PLAYHEAD))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(QPolygonF([QPointF(x - 6, 0), QPointF(x + 6, 0), QPointF(x, 10)]))
        # séparateur des libellés
        p.setPen(QPen(theme.TEXT_MUTED.darker(150), 1))
        p.drawLine(QPointF(LABEL_W, 0), QPointF(LABEL_W, self.height()))
        p.end()

    def _draw_diamond(self, p: QPainter, x: float, y: float, selected: bool) -> None:
        r = 6.0
        p.setPen(QPen(theme.TRACK_BG, 1))
        p.setBrush(QBrush(theme.KEYFRAME_SELECTED if selected else theme.KEYFRAME))
        p.drawPolygon(QPolygonF([QPointF(x, y - r), QPointF(x + r, y), QPointF(x, y + r), QPointF(x - r, y)]))

    def _tick_step(self) -> int:
        fps = max(1.0, float(self.document.project.canvas.fps))
        target_px = 60.0
        frames = target_px / self.px_per_frame
        for cand in (1, 2, 5, 10, 15, 30, 60, 150, 300, 600, 1800):
            if cand >= frames:
                return cand if cand < fps else int(cand // fps * fps) or cand
        return 3600

    # --- souris ----------------------------------------------------------------
    def _key_at(self, pos: QPointF) -> tuple[str, str, int] | None:
        row_idx = int((pos.y() - RULER_H) // ROW_H) + self.scroll_row
        if pos.y() < RULER_H or row_idx < 0 or row_idx >= len(self.rows):
            return None
        row = self.rows[row_idx]
        if row.track is None:
            return None
        for kf in row.track.keyframes:
            if abs(self.frame_to_x(kf.frame) - pos.x()) <= 7:
                return (row.node_id, row.track.property, kf.frame)
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()
        key = self._key_at(pos)
        if key is not None:
            self.selected_key = key
            self._drag_key = key
            self._drag_target = key[2]
            self.document.set_selection([key[0]])
            self.keyframeSelected.emit(*key)
            self.update()
            return
        row_idx = int((pos.y() - RULER_H) // ROW_H) + self.scroll_row
        if pos.y() >= RULER_H and 0 <= row_idx < len(self.rows) and pos.x() < LABEL_W:
            self.document.set_selection([self.rows[row_idx].node_id])
        self.selected_key = None
        if pos.x() >= LABEL_W:
            self._scrubbing = True
            self.document.set_frame(self.x_to_frame(pos.x()))
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if self._drag_key is not None:
            self._drag_target = max(0, self.x_to_frame(pos.x()))
            self.update()
        elif self._scrubbing:
            self.document.set_frame(self.x_to_frame(pos.x()))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_key is not None and self._drag_target is not None:
            node_id, prop, frame = self._drag_key
            scene = self.document.scene
            if scene is not None and self._drag_target != frame:
                self.document.push(MoveKeyframe(scene.id, node_id, prop, frame, self._drag_target))
                self.selected_key = (node_id, prop, self._drag_target)
        self._drag_key = None
        self._drag_target = None
        self._scrubbing = False
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            anchor_frame = self.x_to_frame(event.position().x())
            self.px_per_frame = max(0.25, min(60.0, self.px_per_frame * factor))
            self.scroll_frame = max(
                0, int(anchor_frame - (event.position().x() - LABEL_W) / self.px_per_frame)
            )
        else:
            delta = -event.angleDelta().y() / 120 * max(1, self.visible_frames() // 10)
            self.scroll_frame = max(0, int(self.scroll_frame + delta))
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = Qt.Key(event.key())
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.selected_key is not None:
            node_id, prop, frame = self.selected_key
            scene = self.document.scene
            if scene is not None:
                self.document.push(RemoveKeyframe(scene.id, node_id, prop, frame))
            self.selected_key = None
            return
        if key == Qt.Key.Key_Left:
            self.document.set_frame(self.document.frame - 1)
            return
        if key == Qt.Key.Key_Right:
            self.document.set_frame(self.document.frame + 1)
            return
        super().keyPressEvent(event)


class TimelineDock(QWidget):
    def __init__(self, document: ProjectDocument, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self.view = TimelineView(document)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._clock = QElapsedTimer()
        self._play_start_frame = 0
        self.playing = False

        bar = QHBoxLayout()
        self.play_btn = QPushButton("▶ Lecture")
        self.play_btn.setToolTip("Espace : lecture / pause")
        self.play_btn.clicked.connect(self.toggle_play)
        self.stop_btn = QToolButton()
        self.stop_btn.setText("⏮")
        self.stop_btn.setToolTip("Retour au début (Début)")
        self.stop_btn.clicked.connect(self.go_start)
        self.end_btn = QToolButton()
        self.end_btn.setText("⏭")
        self.end_btn.setToolTip("Aller à la fin (Fin)")
        self.end_btn.clicked.connect(self.go_end)
        self.loop = QCheckBox("Boucle")
        self.loop.setChecked(True)
        self.auto_key = QCheckBox("Clé auto")
        self.auto_key.setToolTip("Chaque modification pose une image clé à l'image courante")
        self.auto_key.toggled.connect(self._set_auto_key)
        self.all_objects = QCheckBox("Tous les objets")
        self.all_objects.setChecked(True)
        self.all_objects.toggled.connect(self._toggle_all)
        self.frame_spin = QSpinBox()
        self.frame_spin.setRange(0, 10_000_000)
        self.frame_spin.setKeyboardTracking(False)
        self.frame_spin.valueChanged.connect(document.set_frame)
        self.time_label = QLabel("0,00 s")
        self.time_label.setMinimumWidth(80)
        for w in (self.stop_btn, self.play_btn, self.end_btn):
            bar.addWidget(w)
        bar.addWidget(QLabel("Image :"))
        bar.addWidget(self.frame_spin)
        bar.addWidget(self.time_label)
        bar.addStretch(1)
        bar.addWidget(self.loop)
        bar.addWidget(self.auto_key)
        bar.addWidget(self.all_objects)
        self.vscroll = QScrollBar(Qt.Orientation.Vertical)
        self.vscroll.valueChanged.connect(self._scroll_rows)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.addWidget(self.view, 1)
        body.addWidget(self.vscroll)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(bar)
        layout.addLayout(body, 1)
        document.frameChanged.connect(self._on_frame)
        document.changed.connect(self._update_scroll)
        document.sceneChanged.connect(lambda _s: self._update_scroll())
        self._on_frame(document.frame)
        self._update_scroll()

    def _set_auto_key(self, on: bool) -> None:
        self.document.auto_key = on

    def _toggle_all(self, on: bool) -> None:
        self.view.show_all_objects = on
        self.view.rebuild_rows()
        self._update_scroll()

    def _update_scroll(self) -> None:
        visible = max(1, (self.view.height() - RULER_H) // ROW_H)
        self.vscroll.setRange(0, max(0, len(self.view.rows) - visible))
        self.vscroll.setPageStep(visible)

    def _scroll_rows(self, value: int) -> None:
        self.view.scroll_row = value
        self.view.update()

    def _on_frame(self, frame: int) -> None:
        self.frame_spin.blockSignals(True)
        self.frame_spin.setValue(frame)
        self.frame_spin.blockSignals(False)
        fps = float(self.document.project.canvas.fps)
        self.time_label.setText(f"{frame / fps:.2f} s".replace(".", ","))
        # garder la tête de lecture visible
        v = self.view
        if frame < v.scroll_frame or frame > v.scroll_frame + v.visible_frames():
            v.scroll_frame = max(0, frame - v.visible_frames() // 4)
            v.update()

    # --- lecture ------------------------------------------------------------
    def toggle_play(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
        if self.document.frame >= scene.duration_frames - 1:
            self.document.set_frame(0)
        self.playing = True
        self._play_start_frame = self.document.frame
        self._clock.restart()
        self._timer.start(15)
        self.play_btn.setText("⏸ Pause")

    def pause(self) -> None:
        self.playing = False
        self._timer.stop()
        self.play_btn.setText("▶ Lecture")

    def go_start(self) -> None:
        self.pause()
        self.document.set_frame(0)

    def go_end(self) -> None:
        self.pause()
        scene = self.document.scene
        if scene is not None:
            self.document.set_frame(scene.duration_frames - 1)

    def _tick(self) -> None:
        scene = self.document.scene
        if scene is None:
            self.pause()
            return
        fps = float(self.document.project.canvas.fps)
        elapsed = self._clock.elapsed() / 1000.0
        frame = self._play_start_frame + int(math.floor(elapsed * fps))
        if frame >= scene.duration_frames:
            if self.loop.isChecked():
                frame = frame % scene.duration_frames
                self._play_start_frame = 0
                self._clock.restart()
                frame = 0
            else:
                self.document.set_frame(scene.duration_frames - 1)
                self.pause()
                return
        self.document.set_frame(frame)

"""Timeline : règle, tête de lecture, pistes par objet avec losanges de keyframes, lecture/pause/boucle."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QContextMenuEvent,
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
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollBar,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import icons, theme
from antares_studio.app.audio_player import ScenePlayback
from antares_studio.app.document import ProjectDocument
from antares_studio.domain.commands import (
    MoveKeyframe,
    RemoveKeyframe,
    SetAudioClipAttr,
    SetKeyframeEasing,
)
from antares_studio.domain.kinds import property_label
from antares_studio.domain.model import EASINGS, Keyframe, Track
from antares_studio.timeline.easing import EASING_LABELS

RULER_H = 26
ROW_H = 22
LABEL_W = 220


@dataclass
class _Row:
    node_id: str
    node_name: str
    track: Track | None  # None = ligne d'en-tête de l'objet
    label: str
    kind: str = "node"  # node | audio | subtitles
    clip_id: str | None = None


class TimelineView(QWidget):
    """Zone graphique (règle + pistes)."""

    keyframeSelected = Signal(str, str, int)  # node_id, property, frame
    keySelectionChanged = Signal()

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
        self._drag_clip: tuple[str, int, float] | None = None  # (clip_id, offset de départ, x souris)
        self._drag_clip_target: int | None = None
        self.show_all_objects = True
        self.waveforms: dict[str, tuple[Any, float]] = {}  # asset_id -> (pics 50 Hz, durée)
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
        if scene.subtitles:
            self.rows.append(_Row("", "", None, "Sous-titres", kind="subtitles"))
        for clip in scene.audio:
            self.rows.append(
                _Row("", clip.name, None, "♪ " + (clip.name or "audio"), kind="audio", clip_id=clip.id)
            )
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

    def _clip_span_x(self, clip: Any) -> tuple[float, float]:
        fps = float(self.document.project.canvas.fps)
        offset = clip.offset_frames
        if (
            self._drag_clip is not None
            and self._drag_clip[0] == clip.id
            and self._drag_clip_target is not None
        ):
            offset = self._drag_clip_target
        length_s = (clip.out_seconds - clip.in_seconds) if clip.out_seconds is not None else None
        if length_s is None:
            length_s = max(0.0, clip.duration_seconds - clip.in_seconds)
            wf = self.waveforms.get(clip.asset_id)
            if wf is not None and length_s <= 0:
                length_s = max(0.0, wf[1] - clip.in_seconds)
        x0 = self.frame_to_x(offset)
        x1 = self.frame_to_x(offset + length_s * fps)
        return x0, x1

    def _paint_audio_row(self, p: QPainter, clip: Any, y: float) -> None:
        x0, x1 = self._clip_span_x(clip)
        if x1 - x0 < 2:
            x1 = x0 + 2
        rect = QRectF(max(LABEL_W, x0), y + 2, min(self.width(), x1) - max(LABEL_W, x0), ROW_H - 4)
        if rect.width() <= 0:
            return
        color = theme.CLIP if not clip.muted else theme.CLIP_MUTED
        p.fillRect(rect, QBrush(color))
        wf = self.waveforms.get(clip.asset_id)
        if wf is not None and len(wf[0]):
            pk, _dur = wf
            fps = float(self.document.project.canvas.fps)
            p.setPen(QPen(theme.BLOCK_TEXT, 1))
            mid = y + ROW_H / 2
            half = (ROW_H - 6) / 2
            x = int(rect.left())
            while x < rect.right():
                t = (
                    self.x_to_frame(x)
                    - (
                        self._drag_clip_target
                        if self._drag_clip
                        and self._drag_clip[0] == clip.id
                        and self._drag_clip_target is not None
                        else clip.offset_frames
                    )
                ) / fps + clip.in_seconds
                i = int(t * 50)
                if 0 <= i < len(pk):
                    a = float(pk[i]) * clip.gain
                    a = min(1.0, a) * half
                    p.drawLine(QPointF(x, mid - a), QPointF(x, mid + a))
                x += 1

    def _paint_subtitles_row(self, p: QPainter, y: float) -> None:
        scene = self.document.scene
        if scene is None:
            return
        for sub in scene.subtitles:
            x0, x1 = self.frame_to_x(sub.start_frame), self.frame_to_x(sub.end_frame)
            if x1 < LABEL_W or x0 > self.width():
                continue
            rect = QRectF(max(LABEL_W, x0), y + 3, min(self.width(), x1) - max(LABEL_W, x0), ROW_H - 6)
            p.fillRect(rect, QBrush(theme.SUBTITLE_BLOCK))
            p.setPen(theme.BLOCK_TEXT)
            p.drawText(
                rect.adjusted(3, 0, -3, 0), int(Qt.AlignmentFlag.AlignVCenter), sub.text.split("\n")[0]
            )

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
        font.setPointSizeF(theme.scaled_pt(9))
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
            if row.kind == "audio" and row.clip_id is not None:
                clip = scene.audio_clip(row.clip_id)
                if clip is not None:
                    self._paint_audio_row(p, clip, y)
            elif row.kind == "subtitles":
                self._paint_subtitles_row(p, y)
            if row.track is not None:
                kfs = row.track.sorted_keyframes()
                # un segment par paire de clés : plein (interpolé) ou pointillé (palier)
                for k0, k1 in zip(kfs, kfs[1:], strict=False):
                    style = Qt.PenStyle.DotLine if k0.easing == "step" else Qt.PenStyle.SolidLine
                    p.setPen(QPen(theme.KEYFRAME.darker(150), 2, style))
                    p.drawLine(
                        QPointF(self.frame_to_x(k0.frame), y + ROW_H / 2),
                        QPointF(self.frame_to_x(k1.frame), y + ROW_H / 2),
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
                QBrush(theme.OUT_OF_RANGE),
            )
        # règle
        p.fillRect(QRectF(0, 0, self.width(), RULER_H), theme.RULER_BG)
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
        p.setPen(QPen(theme.TEXT_MUTED, 1))
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

    def selected_keyframe(self) -> Keyframe | None:
        """Image clé sélectionnée (ou None si la sélection ne correspond plus à une clé)."""
        scene = self.document.scene
        if scene is None or self.selected_key is None:
            return None
        node_id, prop, frame = self.selected_key
        track = scene.track_for(node_id, prop)
        return next((k for k in track.keyframes if k.frame == frame), None) if track else None

    def _select_key(self, key: tuple[str, str, int] | None) -> None:
        self.selected_key = key
        if key is not None:
            self.document.set_selection([key[0]])
            self.keyframeSelected.emit(*key)
        self.keySelectionChanged.emit()
        self.update()

    def set_selected_easing(self, easing: str, bezier: list[float] | None = None) -> bool:
        """Change l'interpolation de la clé sélectionnée ; « bezier » sans points ouvre l'éditeur."""
        kf = self.selected_keyframe()
        scene = self.document.scene
        if kf is None or scene is None or self.selected_key is None or easing not in EASINGS:
            return False
        if easing == "bezier" and bezier is None:
            from antares_studio.app.curve_editor import CurveEditorDialog

            dlg = CurveEditorDialog(kf.bezier, self)
            if dlg.exec() != CurveEditorDialog.DialogCode.Accepted:
                self.keySelectionChanged.emit()  # rétablir l'affichage de l'interpolation courante
                return False
            bezier = dlg.bezier()
        if kf.easing == easing and (easing != "bezier" or kf.bezier == bezier):
            return False
        node_id, prop, frame = self.selected_key
        self.document.push(SetKeyframeEasing(scene.id, node_id, prop, frame, easing, bezier))
        return True

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        key = self._key_at(QPointF(event.pos()))
        if key is not None:
            self.keyframe_menu(key).exec(event.globalPos())

    def keyframe_menu(self, key: tuple[str, str, int]) -> QMenu:
        """Menu contextuel d'une clé (la sélectionne) : interpolations cochables et suppression."""
        self._select_key(key)
        kf = self.selected_keyframe()
        menu = QMenu(self)
        menu.addSection("Interpolation vers la clé suivante")
        for name in EASINGS:
            act = menu.addAction(EASING_LABELS[name])
            act.setCheckable(True)
            act.setChecked(kf is not None and kf.easing == name)
            act.triggered.connect(lambda _c=False, n=name: self.set_selected_easing(n))
        menu.addSeparator()
        menu.addAction("Supprimer l'image clé").triggered.connect(self.delete_selected_key)
        return menu

    def delete_selected_key(self) -> None:
        scene = self.document.scene
        if scene is not None and self.selected_key is not None:
            node_id, prop, frame = self.selected_key
            self.document.push(RemoveKeyframe(scene.id, node_id, prop, frame))
        self._select_key(None)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()
        key = self._key_at(pos)
        if key is not None:
            self._drag_key = key
            self._drag_target = key[2]
            self._select_key(key)
            return
        row_idx = int((pos.y() - RULER_H) // ROW_H) + self.scroll_row
        if pos.y() >= RULER_H and 0 <= row_idx < len(self.rows):
            row = self.rows[row_idx]
            if row.kind == "audio" and row.clip_id is not None and pos.x() >= LABEL_W:
                scene = self.document.scene
                clip = scene.audio_clip(row.clip_id) if scene else None
                if clip is not None:
                    x0, x1 = self._clip_span_x(clip)
                    if x0 - 4 <= pos.x() <= x1 + 4:
                        self._drag_clip = (clip.id, clip.offset_frames, pos.x())
                        self._drag_clip_target = clip.offset_frames
                        self.update()
                        return
            if pos.x() < LABEL_W and row.kind == "node":
                self.document.set_selection([row.node_id])
        if self.selected_key is not None:
            self._select_key(None)
        if pos.x() >= LABEL_W:
            self._scrubbing = True
            self.document.set_frame(self.x_to_frame(pos.x()))
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if self._drag_clip is not None:
            _cid, start_offset, x_start = self._drag_clip
            delta = (pos.x() - x_start) / self.px_per_frame
            self._drag_clip_target = max(0, int(round(start_offset + delta)))
            self.update()
        elif self._drag_key is not None:
            self._drag_target = max(0, self.x_to_frame(pos.x()))
            self.update()
        elif self._scrubbing:
            self.document.set_frame(self.x_to_frame(pos.x()))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_clip is not None:
            cid, start_offset, _x = self._drag_clip
            scene = self.document.scene
            if (
                scene is not None
                and self._drag_clip_target is not None
                and self._drag_clip_target != start_offset
            ):
                self.document.push(SetAudioClipAttr(scene.id, cid, "offset_frames", self._drag_clip_target))
            self._drag_clip = None
            self._drag_clip_target = None
            self.update()
            return
        if self._drag_key is not None and self._drag_target is not None:
            node_id, prop, frame = self._drag_key
            scene = self.document.scene
            if scene is not None and self._drag_target != frame:
                self.document.push(MoveKeyframe(scene.id, node_id, prop, frame, self._drag_target))
                self._select_key((node_id, prop, self._drag_target))
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
            self.delete_selected_key()
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
        self.playback = ScenePlayback(self)
        self.ffmpeg_path: str = ""

        bar = QHBoxLayout()
        self.play_btn = QPushButton("Lecture")
        self.play_btn.setToolTip("Espace : lecture / pause")
        self.play_btn.clicked.connect(self.toggle_play)
        self.stop_btn = QToolButton()
        self.stop_btn.setText("Début")
        self.stop_btn.setToolTip("Retour au début (Début)")
        self.stop_btn.clicked.connect(self.go_start)
        self.end_btn = QToolButton()
        self.end_btn.setText("Fin")
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
        self.easing_combo = QComboBox()
        self.easing_combo.setObjectName("timeline_easing")
        for name in EASINGS:
            self.easing_combo.addItem(EASING_LABELS[name], name)
        self.easing_combo.setToolTip(
            "Interpolation de l'image clé sélectionnée vers la suivante (clic droit sur un losange : idem)"
        )
        self.easing_combo.setEnabled(False)
        self.easing_combo.activated.connect(self._easing_chosen)
        self.view.keySelectionChanged.connect(self._sync_easing)
        document.changed.connect(self._sync_easing)
        for w in (self.stop_btn, self.play_btn, self.end_btn):
            bar.addWidget(w)
        bar.addWidget(QLabel("Image :"))
        bar.addWidget(self.frame_spin)
        bar.addWidget(self.time_label)
        bar.addStretch(1)
        bar.addWidget(QLabel("Interpolation :"))
        bar.addWidget(self.easing_combo)
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
        document.changed.connect(self.load_waveforms)
        document.sceneChanged.connect(lambda _s: self._update_scroll())
        document.sceneChanged.connect(lambda _s: self.load_waveforms())
        self._on_frame(document.frame)
        self._update_scroll()

    def _sync_easing(self) -> None:
        kf = self.view.selected_keyframe()
        self.easing_combo.setEnabled(kf is not None)
        self.easing_combo.blockSignals(True)
        self.easing_combo.setCurrentIndex(max(0, self.easing_combo.findData(kf.easing if kf else "linear")))
        self.easing_combo.blockSignals(False)

    def _easing_chosen(self, index: int) -> None:
        self.view.set_selected_easing(str(self.easing_combo.itemData(index)))
        self._sync_easing()

    def load_waveforms(self) -> None:
        """Charge (avec cache projet) les formes d'onde des clips de la scène ; silencieux sans FFmpeg."""
        scene = self.document.scene
        if scene is None or not scene.audio:
            return
        from antares_studio.audio.waveform import waveform_for
        from antares_studio.rendering import ffmpeg as ff

        ffmpeg = ff.find_ffmpeg(self.ffmpeg_path or None)
        if ffmpeg is None:
            return
        cache_dir = self.document.paths.cache if self.document.paths else None
        for clip in scene.audio:
            if clip.asset_id in self.view.waveforms:
                continue
            path = self.document.resolve_asset(clip.asset_id)
            if path is None:
                continue
            try:
                self.view.waveforms[clip.asset_id] = waveform_for(ffmpeg, path, cache_dir)
            except (ff.FFmpegError, OSError):
                continue
        self.view.update()

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
        fps = float(self.document.project.canvas.fps)
        self.playback.prepare(list(scene.audio), self.document.resolve_asset, fps)
        self.playback.sync(self.document.frame)
        self._clock.restart()
        self._timer.start(15)
        self.play_btn.setText("Pause")
        self.play_btn.setIcon(icons.icon("pause"))

    def pause(self) -> None:
        self.playing = False
        self._timer.stop()
        self.playback.stop()
        self.play_btn.setText("Lecture")
        self.play_btn.setIcon(icons.icon("play"))

    def restyle(self) -> None:
        """Icônes recolorées après un changement de thème."""
        self.play_btn.setIcon(icons.icon("pause" if self.playing else "play"))
        self.stop_btn.setIcon(icons.icon("skip-back"))
        self.end_btn.setIcon(icons.icon("skip-forward"))
        for b in (self.stop_btn, self.end_btn):
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.view.update()

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
                self._play_start_frame = 0
                self._clock.restart()
                frame = 0
                self.playback.stop()
                self.playback.prepare(list(scene.audio), self.document.resolve_asset, fps)
            else:
                self.document.set_frame(scene.duration_frames - 1)
                self.pause()
                return
        self.document.set_frame(frame)
        self.playback.sync(frame)

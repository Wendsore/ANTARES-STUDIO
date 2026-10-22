"""Éditeur de courbe d'interpolation : Bézier cubique à deux poignées, préréglages et aperçu du mouvement."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QMouseEvent, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import theme
from antares_studio.domain.model import DEFAULT_BEZIER
from antares_studio.timeline.easing import cubic_bezier

# Préréglages (mêmes valeurs que les fonctions CSS du même nom, plus deux effets courants).
CURVE_PRESETS: dict[str, tuple[float, float, float, float]] = {
    "Douce (ease)": DEFAULT_BEZIER,
    "Accélération": (0.42, 0.0, 1.0, 1.0),
    "Décélération": (0.0, 0.0, 0.58, 1.0),
    "Accélère puis ralentit": (0.42, 0.0, 0.58, 1.0),
    "Élan (dépasse puis revient)": (0.34, 1.56, 0.64, 1.0),
    "Recul au départ": (0.36, -0.4, 0.6, 1.0),
}
Y_MIN, Y_MAX = -0.6, 1.6  # marge verticale : les poignées peuvent sortir de [0, 1] (rebond)


class CurveView(QWidget):
    """Graphe temps (x) → progression (y) ; les deux poignées se déplacent à la souris."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.points = list(DEFAULT_BEZIER)
        self._drag: int | None = None  # 0 = poignée 1, 1 = poignée 2
        self.preview_u: float | None = None
        self.setMinimumSize(300, 300)
        self.setMouseTracking(True)
        self.setToolTip("Glissez les deux poignées : la pente de la courbe est la vitesse du mouvement.")

    def _plot(self) -> QRectF:
        m = 22.0
        side = min(self.width(), self.height()) - 2 * m
        return QRectF((self.width() - side) / 2, m, side, side)

    def to_px(self, x: float, y: float) -> QPointF:
        r = self._plot()
        return QPointF(r.left() + x * r.width(), r.bottom() - (y - Y_MIN) / (Y_MAX - Y_MIN) * r.height())

    def from_px(self, p: QPointF) -> tuple[float, float]:
        r = self._plot()
        x = (p.x() - r.left()) / r.width()
        y = Y_MIN + (r.bottom() - p.y()) / r.height() * (Y_MAX - Y_MIN)
        return min(1.0, max(0.0, x)), min(Y_MAX, max(Y_MIN, y))

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), theme.TRACK_BG)
        r = self._plot()
        p.setPen(QPen(theme.TEXT_MUTED, 1, Qt.PenStyle.DotLine))
        for y in (0.0, 1.0):
            p.drawLine(self.to_px(0, y), self.to_px(1, y))
        p.drawLine(self.to_px(0, Y_MIN), self.to_px(0, Y_MAX))
        p.drawLine(self.to_px(1, Y_MIN), self.to_px(1, Y_MAX))
        p.setPen(theme.TEXT_MUTED)
        p.drawText(QRectF(r.left(), r.bottom() + 2, r.width(), 18), Qt.AlignmentFlag.AlignCenter, "temps →")
        p.drawText(self.to_px(0, 1) + QPointF(4, -4), "arrivée")
        p.drawText(self.to_px(0, 0) + QPointF(4, -4), "départ")
        x1, y1, x2, y2 = self.points
        p.setPen(QPen(theme.TEXT_MUTED, 1))
        p.drawLine(self.to_px(0, 0), self.to_px(x1, y1))
        p.drawLine(self.to_px(1, 1), self.to_px(x2, y2))
        path = QPainterPath(self.to_px(0, 0))
        for i in range(1, 101):
            u = i / 100
            path.lineTo(self.to_px(u, cubic_bezier(x1, y1, x2, y2, u)))
        p.setPen(QPen(theme.ACCENT, 3))
        p.drawPath(path)
        for i, (hx, hy) in enumerate(((x1, y1), (x2, y2))):
            p.setPen(QPen(theme.HANDLE_BORDER, 2))
            p.setBrush(QBrush(theme.KEYFRAME_SELECTED if self._drag == i else theme.KEYFRAME))
            p.drawEllipse(self.to_px(hx, hy), 7, 7)
        if self.preview_u is not None:
            u = self.preview_u
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(theme.PLAYHEAD))
            p.drawEllipse(self.to_px(u, cubic_bezier(x1, y1, x2, y2, u)), 5, 5)
        p.end()

    def _handle_at(self, pos: QPointF) -> int | None:
        for i, (hx, hy) in enumerate(((self.points[0], self.points[1]), (self.points[2], self.points[3]))):
            c = self.to_px(hx, hy)
            if abs(c.x() - pos.x()) <= 10 and abs(c.y() - pos.y()) <= 10:
                return i
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._drag = self._handle_at(event.position())
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is None:
            hover = self._handle_at(event.position()) is not None
            self.setCursor(Qt.CursorShape.OpenHandCursor if hover else Qt.CursorShape.ArrowCursor)
            return
        x, y = self.from_px(event.position())
        self.points[2 * self._drag] = round(x, 3)
        self.points[2 * self._drag + 1] = round(y, 3)
        self.changed.emit()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag = None
        self.update()


class CurveEditorDialog(QDialog):
    """Choix d'une courbe x1, y1, x2, y2 ; ``bezier()`` donne la valeur retenue."""

    def __init__(self, bezier: list[float] | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Courbe d'interpolation")
        self.view = CurveView()
        if bezier is not None and len(bezier) == 4:
            self.view.points = [float(v) for v in bezier]
        self.view.changed.connect(self._sync_spins)
        intro = QLabel(
            "La courbe montre la progression entre deux images clés. Pente forte = mouvement rapide, "
            "pente nulle = arrêt. Au-dessus de « arrivée », l'objet dépasse sa cible puis revient."
        )
        intro.setWordWrap(True)
        presets = QGridLayout()
        for i, (name, pts) in enumerate(CURVE_PRESETS.items()):
            b = QPushButton(name)
            b.clicked.connect(lambda _c=False, v=pts: self.set_points(list(v)))
            presets.addWidget(b, i // 2, i % 2)
        self.spins: list[QDoubleSpinBox] = []
        spins_row = QHBoxLayout()
        for i, label in enumerate(("x1", "y1", "x2", "y2")):
            s = QDoubleSpinBox()
            s.setDecimals(3)
            s.setSingleStep(0.05)
            if label.startswith("x"):
                s.setRange(0.0, 1.0)
            else:
                s.setRange(Y_MIN, Y_MAX)
            s.setValue(self.view.points[i])
            s.valueChanged.connect(lambda v, k=i: self._spin_changed(k, v))
            spins_row.addWidget(QLabel(label))
            spins_row.addWidget(s)
            self.spins.append(s)
        self.preview_btn = QPushButton("Aperçu du mouvement")
        self.preview_btn.clicked.connect(self._start_preview)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._t = 0
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Appliquer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.view, 1)
        layout.addLayout(spins_row)
        layout.addLayout(presets)
        layout.addWidget(self.preview_btn)
        layout.addWidget(buttons)
        self.resize(460, 680)

    def bezier(self) -> list[float]:
        return [round(v, 3) for v in self.view.points]

    def set_points(self, pts: list[float]) -> None:
        self.view.points = [float(v) for v in pts]
        self._sync_spins()
        self.view.update()

    def _sync_spins(self) -> None:
        for s, v in zip(self.spins, self.view.points, strict=True):
            s.blockSignals(True)
            s.setValue(v)
            s.blockSignals(False)

    def _spin_changed(self, index: int, value: float) -> None:
        self.view.points[index] = float(value)
        self.view.update()

    def _start_preview(self) -> None:
        self._t = 0
        self._timer.start()

    def _tick(self) -> None:
        self._t += 1
        if self._t > 60:  # une seconde à 60 images/s
            self._timer.stop()
            self.view.preview_u = None
        else:
            self.view.preview_u = self._t / 60
        self.view.update()

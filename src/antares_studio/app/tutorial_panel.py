"""Panneau Tutoriel : étape courante, validation automatique sur l'état réel, « Montre-moi ».

La logique (étapes, vérifications) est dans ``antares_studio.help.tutorials`` ; ce module ne fait que
l'afficher. La fenêtre principale fournit l'état courant via ``context_provider``.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import icons, theme
from antares_studio.help.tutorials import ACTIONS, Tutorial, TutorialContext, TutorialRun

ADVANCE_DELAY_MS = 1200


class TutorialPanel(QWidget):
    showMeRequested = Signal(str)  # nom d'objet du widget à mettre en évidence
    actionRequested = Signal(str)  # identifiant d'action (``ACTIONS``)
    tutorialFinished = Signal(str)  # identifiant du tutoriel terminé
    closeRequested = Signal()

    def __init__(self, context_provider: Callable[[], TutorialContext], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("tutorial_panel")
        self._context = context_provider
        self.run: TutorialRun | None = None
        self._advance = QTimer(self)
        self._advance.setSingleShot(True)
        self._advance.timeout.connect(self._auto_next)

        self.title = QLabel("Aucun tutoriel en cours")
        self.title.setWordWrap(True)
        f = self.title.font()
        f.setBold(True)
        f.setPointSizeF(f.pointSizeF() * 1.15)
        self.title.setFont(f)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setMaximumHeight(8)
        self.counter = QLabel("")
        self.counter.setProperty("role", "hint")
        self.step_title = QLabel("")
        self.step_title.setWordWrap(True)
        sf = self.step_title.font()
        sf.setBold(True)
        self.step_title.setFont(sf)
        self.body = QLabel("")
        self.body.setObjectName("tutorial_body")
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.TextFormat.MarkdownText)
        self.body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.status = QLabel("")
        self.status.setObjectName("tutorial_status")
        self.status.setWordWrap(True)
        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        self.hint.setProperty("role", "hint")
        self.hint.setVisible(False)

        self.show_btn = QPushButton(icons.icon("scan"), "Montre-moi")
        self.show_btn.setToolTip("Fait clignoter la zone de l'interface concernée")
        self.show_btn.clicked.connect(self._show_me)
        self.hint_btn = QPushButton(icons.icon("lightbulb"), "Un indice ?")
        self.hint_btn.clicked.connect(lambda: self.hint.setVisible(True))
        self.action_btn = QPushButton("")
        self.action_btn.setProperty("role", "primary")
        self.action_btn.clicked.connect(self._do_action)
        self.prev_btn = QPushButton(icons.icon("chevron-left"), "Précédent")
        self.prev_btn.clicked.connect(self.previous)
        self.next_btn = QPushButton("Suivant")
        self.next_btn.setObjectName("tutorial_next")
        self.next_btn.setProperty("role", "primary")
        self.next_btn.clicked.connect(self.next)
        self.quit_btn = QPushButton(icons.icon("x"), "Quitter le tutoriel")
        self.quit_btn.setProperty("role", "link")
        self.quit_btn.clicked.connect(self.stop)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(8)
        cl.addWidget(self.title)
        cl.addWidget(self.progress)
        cl.addWidget(self.counter)
        cl.addSpacing(4)
        cl.addWidget(self.step_title)
        cl.addWidget(self.body)
        cl.addWidget(self.status)
        cl.addWidget(self.hint)
        tools = QHBoxLayout()
        tools.addWidget(self.show_btn)
        tools.addWidget(self.hint_btn)
        tools.addStretch(1)
        cl.addLayout(tools)
        cl.addWidget(self.action_btn)
        cl.addStretch(1)
        nav = QHBoxLayout()
        nav.addWidget(self.prev_btn)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)
        cl.addLayout(nav)
        cl.addWidget(self.quit_btn, 0, Qt.AlignmentFlag.AlignRight)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)
        self._render()

    # --- déroulé --------------------------------------------------------------------------------
    def start(self, tutorial: Tutorial) -> None:
        self._advance.stop()
        self.run = TutorialRun(tutorial, self._context())
        self._render()

    def stop(self) -> None:
        self._advance.stop()
        self.run = None
        self._render()
        self.closeRequested.emit()

    def refresh(self) -> None:
        """À appeler quand le projet ou l'interface change : valide l'étape si l'action est faite."""
        if self.run is None or self._advance.isActive():
            return
        if self.run.update(self._context()):
            self._render()
            if self.run.index + 1 < len(self.run.tutorial.steps):
                self._advance.start(ADVANCE_DELAY_MS)
            else:
                self.tutorialFinished.emit(self.run.tutorial.id)

    def next(self) -> None:
        if self.run is None:
            return
        self._advance.stop()
        last = self.run.index + 1 >= len(self.run.tutorial.steps)
        if last:
            if self.run.step.check is None:
                self.run.completed.add(self.run.index)
            self.tutorialFinished.emit(self.run.tutorial.id)
            self.stop()
            return
        self.run.next(self._context())
        self._render()
        self.refresh()

    def previous(self) -> None:
        if self.run is None:
            return
        self._advance.stop()
        self.run.go(self.run.index - 1, self._context())
        self.run.completed.discard(self.run.index)
        self._render()

    def _auto_next(self) -> None:
        if self.run is not None and self.run.index in self.run.completed:
            self.run.go(self.run.index + 1, self._context())
            self._render()
            self.refresh()

    # --- affichage ------------------------------------------------------------------------------
    def _render(self) -> None:
        run = self.run
        active = run is not None
        for w in (self.progress, self.counter, self.step_title, self.body, self.status, self.prev_btn):
            w.setVisible(active)
        self.next_btn.setVisible(active)
        self.quit_btn.setVisible(active)
        if run is None:
            self.title.setText("Aucun tutoriel en cours")
            self.show_btn.setVisible(False)
            self.hint_btn.setVisible(False)
            self.action_btn.setVisible(False)
            self.hint.setVisible(False)
            return
        tut, step, i, n = run.tutorial, run.step, run.index, len(run.tutorial.steps)
        self.title.setText(tut.title)
        self.progress.setRange(0, n)
        self.progress.setValue(len(run.completed))
        self.counter.setText(f"Étape {i + 1} sur {n} · environ {tut.minutes} min au total")
        done = i in run.completed
        self.step_title.setText(("✓ " if done else "") + step.title)
        self.body.setText(step.body)
        if done:
            self.status.setText("✓ Bravo, étape validée." + (" Suite dans un instant…" if i + 1 < n else ""))
            self.status.setStyleSheet(f"color: {theme.active().success}; font-weight: 600;")
        elif step.check is None:
            self.status.setText("Lisez, puis cliquez sur « Suivant ».")
            self.status.setStyleSheet(f"color: {theme.active().text_muted};")
        else:
            self.status.setText("En attente de votre action… (l'étape se valide toute seule)")
            self.status.setStyleSheet(f"color: {theme.active().text_muted};")
        self.show_btn.setVisible(bool(step.target))
        self.hint_btn.setVisible(bool(step.hint))
        self.hint.setText(step.hint)
        self.hint.setVisible(False)
        self.action_btn.setVisible(bool(step.action))
        self.action_btn.setText(ACTIONS.get(step.action, ""))
        self.prev_btn.setEnabled(i > 0)
        self.next_btn.setText("Terminer" if i + 1 >= n else "Suivant")
        self.next_btn.setIcon(
            icons.icon("check" if i + 1 >= n else "chevron-right", theme.active().on_accent)
        )

    def restyle(self) -> None:
        self.show_btn.setIcon(icons.icon("scan"))
        self.hint_btn.setIcon(icons.icon("lightbulb"))
        self.prev_btn.setIcon(icons.icon("chevron-left"))
        self.quit_btn.setIcon(icons.icon("x"))
        self._render()

    def _show_me(self) -> None:
        if self.run is not None and self.run.step.target:
            self.showMeRequested.emit(self.run.step.target)

    def _do_action(self) -> None:
        if self.run is not None and self.run.step.action:
            self.actionRequested.emit(self.run.step.action)


class Highlighter(QWidget):
    """Cadre clignotant posé par-dessus un widget de la fenêtre (transparent aux clics)."""

    def __init__(self, target: QWidget, host: QWidget):
        super().__init__(host)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._target = target
        self._host = host
        self._ticks = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        host.installEventFilter(self)
        self._place()
        self.show()
        self.raise_()
        self._timer.start(220)

    def _place(self) -> None:
        top_left = self._target.mapTo(self._host, self._target.rect().topLeft())
        self.setGeometry(QRect(top_left, self._target.size()).adjusted(-6, -6, 6, 6))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 (API Qt)
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            self._place()
        return False

    def _tick(self) -> None:
        self._ticks += 1
        self.update()
        if self._ticks >= 14:
            self._timer.stop()
            self._host.removeEventFilter(self)
            self.deleteLater()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (API Qt)
        if self._ticks % 2 == 1:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(theme.active().accent)
        p.setPen(QPen(color, 4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 10, 10)
        p.end()

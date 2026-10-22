"""Page d'accueil (master prompt §4.1) : Nouveau, Ouvrir, Récents, Modèles, Apprendre, Diagnostics.

La boîte ne fait rien elle-même : elle mémorise le choix dans ``choice`` (type, argument) et la fenêtre
principale l'exécute, avec ses propres garde-fous (enregistrement des modifications en cours).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from antares_studio import __version__
from antares_studio.app import icons, theme, thumbnails
from antares_studio.help.tutorials import TUTORIALS
from antares_studio.resources.templates import template_labels

DATA_ROLE = Qt.ItemDataRole.UserRole + 1
CARD_W, CARD_H = 208, 117  # vignette 16:9 des cartes de modèle


class _TemplateCard(QFrame):
    def __init__(self, template_id: str, label: str, owner: WelcomeDialog):
        super().__init__()
        self.setProperty("role", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName(f"welcome_template_{template_id}")
        self.setToolTip(f"Nouveau projet à partir du modèle « {label} »")
        self._owner = owner
        self._tid = template_id
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        img = QLabel()
        img.setPixmap(thumbnails.template_pixmap(template_id, CARD_W, CARD_H))
        img.setFixedSize(CARD_W, CARD_H)
        text = QLabel(label.split(" (")[0])
        text.setWordWrap(True)
        lay.addWidget(img)
        lay.addWidget(text)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (API Qt)
        if event.button() == Qt.MouseButton.LeftButton:
            self._owner.choose("template", self._tid)


class WelcomeDialog(QDialog):
    def __init__(
        self,
        recent: list[Path],
        done_tutorials: set[str],
        ffmpeg_found: bool,
        show_at_startup: bool,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("welcome")
        self.setWindowTitle("Accueil — ANTARES Studio")
        self.setWindowIcon(icons.app_icon())
        self.resize(1220, 700)
        self.choice: tuple[str, str] | None = None
        p = theme.active()

        # colonne 1 : identité, actions, récents
        logo = QLabel()
        logo.setPixmap(icons.app_icon().pixmap(QSize(84, 84)))
        name = QLabel("ANTARES Studio")
        name.setProperty("role", "title")
        tagline = QLabel("Vidéos scientifiques animées, sans programmation et hors ligne.")
        tagline.setProperty("role", "subtitle")
        tagline.setWordWrap(True)
        new_btn = QPushButton(icons.icon("file-plus", p.on_accent), "Nouveau projet…")
        new_btn.setObjectName("welcome_new")
        new_btn.setProperty("role", "primary")
        new_btn.clicked.connect(lambda: self.choose("new", ""))
        open_btn = QPushButton(icons.icon("folder-open"), "Ouvrir un projet…")
        open_btn.clicked.connect(lambda: self.choose("open", ""))
        self.recent = QListWidget()
        self.recent.setObjectName("welcome_recent")
        for path in recent:
            item = QListWidgetItem(icons.icon("folder-open"), path.name.removesuffix(".antares"))
            item.setToolTip(str(path))
            item.setData(DATA_ROLE, str(path))
            self.recent.addItem(item)
        if not recent:
            empty = QListWidgetItem("Aucun projet récent")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recent.addItem(empty)
        self.recent.itemActivated.connect(lambda it: self._recent(it))
        self.recent.itemDoubleClicked.connect(lambda it: self._recent(it))
        col1 = QVBoxLayout()
        head = QHBoxLayout()
        head.addWidget(logo)
        titles = QVBoxLayout()
        titles.addWidget(name)
        titles.addWidget(tagline)
        head.addLayout(titles, 1)
        col1.addLayout(head)
        col1.addSpacing(10)
        col1.addWidget(new_btn)
        col1.addWidget(open_btn)
        col1.addSpacing(10)
        col1.addWidget(self._section("Projets récents"))
        col1.addWidget(self.recent, 1)

        # colonne 2 : modèles
        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (tid, label) in enumerate(template_labels().items()):
            grid.addWidget(_TemplateCard(tid, label, self), i // 2, i % 2)
        grid.setRowStretch(grid.rowCount(), 1)  # cartes compactes en haut, pas étirées
        cards = QWidget()
        cards.setLayout(grid)
        scroll = QScrollArea()
        scroll.setWidget(cards)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(grid.sizeHint().width() + scroll.verticalScrollBar().sizeHint().width() + 4)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        col2 = QVBoxLayout()
        col2.addWidget(self._section("Commencer avec un modèle"))
        hint = QLabel("Un clic crée un projet 16:9, 1080p, 30 images/s à partir du modèle.")
        hint.setProperty("role", "hint")
        hint.setWordWrap(True)
        col2.addWidget(hint)
        col2.addWidget(scroll, 1)

        # colonne 3 : apprendre et diagnostics
        self.tutorials = QListWidget()
        self.tutorials.setObjectName("welcome_tutorials")
        self.tutorials.setWordWrap(True)  # titres longs sur deux lignes plutôt que tronqués
        self.tutorials.setSpacing(2)
        self.tutorials.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tutorials.setResizeMode(QListWidget.ResizeMode.Adjust)
        for t in TUTORIALS:
            done = t.id in done_tutorials
            item = QListWidgetItem(
                icons.icon("circle-check" if done else "graduation-cap", p.success if done else None),
                f"{t.title}\n{t.minutes} min" + (" · terminé" if done else ""),
            )
            item.setToolTip(t.summary + ("\nDéjà terminé." if done else ""))
            item.setData(DATA_ROLE, t.id)
            self.tutorials.addItem(item)
        self.tutorials.itemActivated.connect(lambda it: self.choose("tutorial", str(it.data(DATA_ROLE))))
        self.tutorials.itemDoubleClicked.connect(lambda it: self.choose("tutorial", str(it.data(DATA_ROLE))))
        help_btn = QPushButton(icons.icon("book-open"), "Ouvrir le centre d'aide (F1)")
        help_btn.clicked.connect(lambda: self.choose("help", ""))
        diag = QLabel(
            "✓ FFmpeg est prêt : l'export vidéo est disponible."
            if ffmpeg_found
            else "⚠ FFmpeg est introuvable : l'export vidéo est indisponible. Voir Aide > Diagnostics…"
        )
        diag.setObjectName("welcome_ffmpeg")
        diag.setWordWrap(True)
        diag.setProperty("role", "success" if ffmpeg_found else "warning")
        col3 = QVBoxLayout()
        col3.addWidget(self._section("Apprendre"))
        col3.addWidget(self.tutorials, 1)
        col3.addWidget(help_btn)
        col3.addSpacing(10)
        col3.addWidget(self._section("État de l'installation"))
        col3.addWidget(diag)

        cols = QHBoxLayout()
        cols.setSpacing(22)
        cols.addLayout(col1, 3)
        cols.addLayout(col2, 5)
        cols.addLayout(col3, 3)
        self.show_at_startup = QCheckBox("Afficher cette page au démarrage")
        self.show_at_startup.setChecked(show_at_startup)
        version = QLabel(f"Version {__version__} · Aide > Accueil… rouvre cette page")
        version.setProperty("role", "hint")
        close = QPushButton("Fermer")
        close.clicked.connect(self.reject)
        bottom = QHBoxLayout()
        bottom.addWidget(self.show_at_startup)
        bottom.addStretch(1)
        bottom.addWidget(version)
        bottom.addWidget(close)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 14)
        lay.addLayout(cols, 1)
        lay.addLayout(bottom)

    def _section(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "section")
        return label

    def _recent(self, item: QListWidgetItem) -> None:
        path = item.data(DATA_ROLE)
        if path:
            self.choose("recent", str(path))

    def choose(self, kind: str, arg: str) -> None:
        self.choice = (kind, arg)
        self.accept()

"""Bibliothèque : objets à ajouter (double-clic) et animations prédéfinies à appliquer à la sélection."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from antares_studio.domain.kinds import KINDS
from antares_studio.timeline.presets import PRESETS

ID_ROLE = Qt.ItemDataRole.UserRole + 1

CATEGORIES: dict[str, tuple[str, ...]] = {
    "Formes": ("circle", "ellipse", "rect", "polygon", "star"),
    "Diagrammes": ("line", "arrow", "orbit_path"),
    "Texte": ("text",),
    "Images": ("image",),
    "Organisation": ("group",),
}


class LibraryDock(QWidget):
    addRequested = Signal(str)  # kind
    presetRequested = Signal(str)  # preset id
    templateRequested = Signal(str)  # template id

    def __init__(self, templates: dict[str, str], parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher un objet ou une animation…")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self.objects = QListWidget()
        for cat, kinds in CATEGORIES.items():
            header = QListWidgetItem(cat)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setData(ID_ROLE, "")
            f = header.font()
            f.setBold(True)
            header.setFont(f)
            self.objects.addItem(header)
            for kind in kinds:
                item = QListWidgetItem("   " + KINDS[kind].label)
                item.setData(ID_ROLE, kind)
                item.setToolTip("Double-clic : ajouter au centre de la vue")
                self.objects.addItem(item)
        self.objects.itemDoubleClicked.connect(self._on_object_activated)
        self.tabs.addTab(
            self._with_hint(self.objects, "Double-cliquez pour ajouter l'objet à la scène."), "Objets"
        )

        self.presets = QListWidget()
        for pid, spec in PRESETS.items():
            item = QListWidgetItem(spec.label)
            item.setData(ID_ROLE, pid)
            item.setToolTip(spec.description)
            self.presets.addItem(item)
        self.presets.itemDoubleClicked.connect(lambda it: self.presetRequested.emit(it.data(ID_ROLE)))
        self.tabs.addTab(
            self._with_hint(self.presets, "Sélectionnez un objet puis double-cliquez sur une animation."),
            "Animations",
        )

        self.templates = QListWidget()
        for tid, label in templates.items():
            item = QListWidgetItem(label)
            item.setData(ID_ROLE, tid)
            self.templates.addItem(item)
        self.templates.itemDoubleClicked.connect(lambda it: self.templateRequested.emit(it.data(ID_ROLE)))
        self.tabs.addTab(
            self._with_hint(self.templates, "Double-clic : ajouter le modèle comme nouvelle scène."),
            "Modèles",
        )

    def _on_object_activated(self, item: QListWidgetItem) -> None:
        kind = item.data(ID_ROLE)
        if kind:
            self.addRequested.emit(str(kind))

    def _with_hint(self, widget: QWidget, hint: str) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        label = QLabel(hint)
        label.setWordWrap(True)
        label.setStyleSheet("color: #90A4AE; font-size: 11px;")
        lay.addWidget(label)
        lay.addWidget(widget, 1)
        return box

    def _filter(self, text: str) -> None:
        q = text.strip().casefold()
        for lst in (self.objects, self.presets, self.templates):
            for i in range(lst.count()):
                item = lst.item(i)
                is_header = not item.data(ID_ROLE)
                item.setHidden(bool(q) and not is_header and q not in item.text().casefold())

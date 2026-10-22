"""Recherche de commandes (Ctrl+K) : toutes les actions des menus, filtrées au fil de la frappe."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMenuBar,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import icons
from antares_studio.help.topics import fold

ACTION_ROLE = Qt.ItemDataRole.UserRole + 1


def menu_actions(menubar: QMenuBar) -> list[tuple[str, QAction]]:
    """(chemin lisible « Fichier › Exporter la vidéo… », action) pour chaque action exécutable des menus."""
    out: list[tuple[str, QAction]] = []

    def walk(menu: QMenu, path: list[str]) -> None:
        for act in menu.actions():
            if act.isSeparator():
                continue
            text = act.text().replace("&", "")
            sub = act.menu()
            if isinstance(sub, QMenu):
                walk(sub, [*path, text])
            elif text and text != "(aucun)":
                out.append((" › ".join([*path, text]), act))

    for top in menubar.actions():
        sub = top.menu()
        if isinstance(sub, QMenu):
            walk(sub, [top.text().replace("&", "")])
    return out


class CommandPalette(QDialog):
    def __init__(self, menubar: QMenuBar, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("command_palette")
        self.setWindowTitle("Rechercher une commande")
        self.setModal(True)
        self.resize(620, 440)
        self.triggered: QAction | None = None
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Que voulez-vous faire ? (ex. : exporter, orbite, sous-titre, thème)")
        self.edit.addAction(icons.icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        self.edit.textChanged.connect(self._filter)
        self.list = QListWidget()
        self.list.itemActivated.connect(self._run)
        hint = QLabel("↑ ↓ pour choisir · Entrée pour exécuter · Échap pour fermer")
        hint.setProperty("role", "hint")
        lay = QVBoxLayout(self)
        lay.addWidget(self.edit)
        lay.addWidget(self.list, 1)
        lay.addWidget(hint)
        for path, act in menu_actions(menubar):
            shortcut = act.shortcut().toString(act.shortcut().SequenceFormat.NativeText)
            label = f"{path}    {shortcut}" if shortcut else path
            item = QListWidgetItem(act.icon(), label)
            item.setData(ACTION_ROLE, act)
            item.setToolTip(act.statusTip() or path)
            if not act.isEnabled():
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.list.addItem(item)
        self._filter("")
        self.edit.setFocus()

    def _filter(self, text: str) -> None:
        words = fold(text).split()
        first = None
        for i in range(self.list.count()):
            item = self.list.item(i)
            hay = fold(item.text())
            hidden = any(w not in hay for w in words)
            item.setHidden(hidden)
            if not hidden and first is None and item.flags() & Qt.ItemFlag.ItemIsEnabled:
                first = item
        if first is not None:
            self.list.setCurrentItem(first)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (API Qt)
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            self._move(1 if key == Qt.Key.Key_Down else -1)
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.list.currentItem()
            if item is not None and not item.isHidden():
                self._run(item)
            return
        super().keyPressEvent(event)

    def _move(self, delta: int) -> None:
        rows = [
            i
            for i in range(self.list.count())
            if not self.list.item(i).isHidden() and self.list.item(i).flags() & Qt.ItemFlag.ItemIsEnabled
        ]
        if not rows:
            return
        cur = self.list.currentRow()
        pos = rows.index(cur) if cur in rows else -1
        self.list.setCurrentRow(rows[max(0, min(len(rows) - 1, pos + delta))])

    def _run(self, item: QListWidgetItem) -> None:
        act = item.data(ACTION_ROLE)
        if isinstance(act, QAction) and act.isEnabled():
            self.triggered = act
            self.accept()

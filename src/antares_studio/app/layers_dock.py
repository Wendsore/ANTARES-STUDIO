"""Panneau Scènes & objets : liste des scènes et arbre des objets (visibilité, verrou, renommage, ordre)."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app.document import ProjectDocument
from antares_studio.domain.commands import AddScene, RemoveScene, ReorderNode, SetProperty, SetSceneProperty
from antares_studio.domain.kinds import KINDS
from antares_studio.domain.model import Scene

NODE_ID_ROLE = Qt.ItemDataRole.UserRole + 1


class LayersDock(QWidget):
    def __init__(self, document: ProjectDocument, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self._updating = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.scenes = QListWidget()
        self.scenes.setMaximumHeight(120)
        self.scenes.currentRowChanged.connect(self._on_scene_row)
        self.scenes.itemDoubleClicked.connect(self._rename_scene)
        scene_buttons = QHBoxLayout()
        self.add_scene_btn = QPushButton("+ Scène")
        self.add_scene_btn.clicked.connect(self._add_scene)
        self.remove_scene_btn = QPushButton("Supprimer")
        self.remove_scene_btn.clicked.connect(self._remove_scene)
        scene_buttons.addWidget(self.add_scene_btn)
        scene_buttons.addWidget(self.remove_scene_btn)
        layout.addWidget(self.scenes)
        layout.addLayout(scene_buttons)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Objet", "👁", "🔒"])
        self.tree.setColumnWidth(1, 28)
        self.tree.setColumnWidth(2, 28)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.setIconSize(QSize(14, 14))
        layout.addWidget(self.tree, 1)

        order = QHBoxLayout()
        self.up_btn = QToolButton()
        self.up_btn.setText("▲ Monter")
        self.up_btn.clicked.connect(lambda: self._move_selected(-1))
        self.down_btn = QToolButton()
        self.down_btn.setText("▼ Descendre")
        self.down_btn.clicked.connect(lambda: self._move_selected(1))
        order.addWidget(self.up_btn)
        order.addWidget(self.down_btn)
        order.addStretch(1)
        layout.addLayout(order)

        self._refresh_pending = False
        document.changed.connect(self.schedule_refresh)
        document.sceneChanged.connect(lambda _s: self.schedule_refresh())
        document.selectionChanged.connect(self._sync_selection)
        self.refresh()

    # --- rafraîchissement --------------------------------------------------
    def schedule_refresh(self) -> None:
        """Reconstruit l'arbre au prochain tour de boucle : jamais pendant un signal d'item (sinon crash)."""
        if not self._refresh_pending:
            self._refresh_pending = True
            QTimer.singleShot(0, self._deferred_refresh)

    def _deferred_refresh(self) -> None:
        self._refresh_pending = False
        self.refresh()

    def refresh(self) -> None:
        self._updating = True
        try:
            self.scenes.clear()
            for s in self.document.project.scenes:
                item = QListWidgetItem(f"{s.name}  ({s.duration_frames} img.)")
                item.setData(NODE_ID_ROLE, s.id)
                self.scenes.addItem(item)
                if s.id == self.document.scene_id:
                    self.scenes.setCurrentItem(item)
            self.remove_scene_btn.setEnabled(len(self.document.project.scenes) > 1)
            self.tree.clear()
            scene = self.document.scene
            if scene is None:
                return
            items: dict[str, QTreeWidgetItem] = {}
            # ordre d'affichage : du dessus (dernier dessiné) vers le dessous
            ordered = sorted(enumerate(scene.nodes), key=lambda p: (p[1].z_index, p[0]), reverse=True)
            for _, node in ordered:
                label = KINDS[node.kind].label if node.kind in KINDS else node.kind
                titem = QTreeWidgetItem([node.name, "", ""])
                titem.setToolTip(0, f"{label} — {node.id}")
                titem.setData(0, NODE_ID_ROLE, node.id)
                titem.setFlags(titem.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable)
                titem.setCheckState(1, Qt.CheckState.Checked if node.visible else Qt.CheckState.Unchecked)
                titem.setCheckState(2, Qt.CheckState.Checked if node.locked else Qt.CheckState.Unchecked)
                items[node.id] = titem
            for _, node in ordered:
                titem = items[node.id]
                parent = items.get(node.parent_id) if node.parent_id else None
                if parent is not None:
                    parent.addChild(titem)
                else:
                    self.tree.addTopLevelItem(titem)
            self.tree.expandAll()
            self._sync_selection(self.document.selection)
        finally:
            self._updating = False

    def _sync_selection(self, ids: list[str]) -> None:
        self._updating = True
        try:
            wanted = set(ids)
            it = QTreeWidgetItemIterator(self.tree)
            while it.value():
                titem = it.value()
                titem.setSelected(titem.data(0, NODE_ID_ROLE) in wanted)
                it += 1
        finally:
            self._updating = False

    # --- réactions --------------------------------------------------------
    def _on_tree_selection(self) -> None:
        if self._updating:
            return
        ids = [i.data(0, NODE_ID_ROLE) for i in self.tree.selectedItems()]
        self.document.set_selection(ids)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating:
            return
        node_id = item.data(0, NODE_ID_ROLE)
        scene = self.document.scene
        if scene is None or scene.find_node(node_id) is None:
            return
        if column == 0:
            name = item.text(0).strip()
            if name and name != scene.node(node_id).name:
                self.document.push(SetProperty(scene.id, node_id, "name", name, label="Renommer"))
        elif column == 1:
            self.document.push(
                SetProperty(
                    scene.id,
                    node_id,
                    "visible",
                    item.checkState(1) == Qt.CheckState.Checked,
                    label="Visibilité",
                )
            )
        elif column == 2:
            self.document.push(
                SetProperty(
                    scene.id,
                    node_id,
                    "locked",
                    item.checkState(2) == Qt.CheckState.Checked,
                    label="Verrouillage",
                )
            )

    def _on_double_click(self, item: QTreeWidgetItem, column: int) -> None:
        if column == 0:
            self.tree.editItem(item, 0)

    def _move_selected(self, direction: int) -> None:
        scene = self.document.scene
        sel = self.document.selection
        if scene is None or len(sel) != 1:
            return
        node = scene.node(sel[0])
        siblings = [n for n in scene.nodes if n.z_index == node.z_index]
        idx_all = scene.nodes.index(node)
        pos = siblings.index(node)
        target = pos - direction  # « monter » = dessiné après = index supérieur
        if target < 0 or target >= len(siblings):
            # changer de z_index si l'on dépasse le groupe
            self.document.push(
                SetProperty(scene.id, node.id, "z_index", node.z_index - direction, label="Réordonner")
            )
            return
        other = siblings[target]
        new_index = scene.nodes.index(other)
        if new_index == idx_all:
            return
        self.document.push(ReorderNode(scene.id, node.id, new_index))

    def _on_scene_row(self, row: int) -> None:
        if self._updating or row < 0:
            return
        item = self.scenes.item(row)
        if item is not None:
            self.document.set_scene(str(item.data(NODE_ID_ROLE)))

    def _add_scene(self) -> None:
        count = len(self.document.project.scenes) + 1
        fps = float(self.document.project.canvas.fps)
        scene = Scene.create(f"Scène {count}", duration_frames=int(round(10 * fps)))
        self.document.push(AddScene(scene))
        self.document.set_scene(scene.id)

    def _remove_scene(self) -> None:
        scene = self.document.scene
        if scene is None or len(self.document.project.scenes) <= 1:
            return
        answer = QMessageBox.question(
            self,
            "Supprimer la scène",
            f"Supprimer la scène « {scene.name} » et ses {len(scene.nodes)} objets ? (annulable avec Ctrl+Z)",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.document.push(RemoveScene(scene.id))

    def _rename_scene(self, item: QListWidgetItem) -> None:
        scene_id = str(item.data(NODE_ID_ROLE))
        scene = self.document.project.find_scene(scene_id)
        if scene is None:
            return
        name, ok = QInputDialog.getText(self, "Renommer la scène", "Nom :", text=scene.name)
        if ok and name.strip():
            self.document.push(SetSceneProperty(scene_id, "name", name.strip(), label="Renommer la scène"))

"""Bibliothèque : objets à ajouter (double-clic) et animations prédéfinies à appliquer à la sélection."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import theme, thumbnails
from antares_studio.domain.kinds import KINDS
from antares_studio.resources.licenses import STATUS_COMPLETE, InventoryRow, choice_for
from antares_studio.resources.templates import TEMPLATES
from antares_studio.timeline.presets import PRESETS

ID_ROLE = Qt.ItemDataRole.UserRole + 1
FAV_ROLE = (
    Qt.ItemDataRole.UserRole + 2
)  # identifiant de favori « objet:kind », « animation:id », « modèle:id »

CATEGORIES: dict[str, tuple[str, ...]] = {
    "Formes": ("circle", "ellipse", "rect", "polygon", "star"),
    "Diagrammes": ("line", "arrow", "orbit_path"),
    "Texte": ("text", "callout"),
    "Graphiques": ("chart",),
    "Maths": ("formula",),
    "3D (Blender facultatif)": ("image_sequence",),
    "Images": ("image",),
    "Organisation": ("group", "camera"),
}


class LibraryDock(QWidget):
    addRequested = Signal(str)  # kind
    presetRequested = Signal(str)  # preset id
    templateRequested = Signal(str)  # template id
    assetActivated = Signal(str)  # asset id (double-clic dans l'onglet Ressources)
    favoritesChanged = Signal(list)  # identifiants de favoris (persistés par la fenêtre principale)

    def __init__(
        self,
        templates: dict[str, str],
        favorites: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._favorites: set[str] = set(favorites or [])
        self._updating = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher un objet, une animation, un modèle…")
        self.search.textChanged.connect(lambda _t: self._filter())
        top.addWidget(self.search, 1)
        self.fav_only = QToolButton()
        self.fav_only.setText("★")
        self.fav_only.setCheckable(True)
        self.fav_only.setToolTip("N'afficher que les favoris (cochez une case pour marquer un favori)")
        self.fav_only.toggled.connect(lambda _c: self._filter())
        top.addWidget(self.fav_only)
        layout.addLayout(top)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self.objects = QListWidget()
        self.objects.setIconSize(QSize(32, 32))
        for cat, kinds in CATEGORIES.items():
            header = QListWidgetItem(cat)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setData(ID_ROLE, "")
            f = header.font()
            f.setBold(True)
            header.setFont(f)
            self.objects.addItem(header)
            for kind in kinds:
                item = QListWidgetItem(KINDS[kind].label)
                item.setData(ID_ROLE, kind)
                item.setToolTip("Double-clic : ajouter au centre de la vue")
                self._make_favoritable(item, f"objet:{kind}")
                self.objects.addItem(item)
        self.objects.itemDoubleClicked.connect(self._on_object_activated)
        self.objects.itemChanged.connect(self._on_item_changed)
        self.tabs.addTab(
            self._with_hint(self.objects, "Double-cliquez pour ajouter l'objet à la scène."), "Objets"
        )

        self.presets = QListWidget()
        self.presets.setIconSize(QSize(22, 22))
        for pid, spec in PRESETS.items():
            item = QListWidgetItem(spec.label)
            item.setData(ID_ROLE, pid)
            item.setToolTip(spec.description)
            self._make_favoritable(item, f"animation:{pid}")
            self.presets.addItem(item)
        self.presets.itemDoubleClicked.connect(lambda it: self.presetRequested.emit(it.data(ID_ROLE)))
        self.presets.itemChanged.connect(self._on_item_changed)
        self.tabs.addTab(
            self._with_hint(self.presets, "Sélectionnez un objet puis double-cliquez sur une animation."),
            "Animations",
        )

        self.templates = QListWidget()
        self.templates.setIconSize(QSize(96, 54))
        self.templates.setWordWrap(True)
        for tid, label in templates.items():
            item = QListWidgetItem(label)
            item.setData(ID_ROLE, tid)
            self._make_favoritable(item, f"modèle:{tid}")
            self.templates.addItem(item)
        self.templates.itemDoubleClicked.connect(lambda it: self.templateRequested.emit(it.data(ID_ROLE)))
        self.templates.itemChanged.connect(self._on_item_changed)
        self.tabs.addTab(
            self._with_hint(self.templates, "Double-clic : ajouter le modèle comme nouvelle scène."),
            "Modèles",
        )

        self.assets = QTreeWidget()
        self.assets.setHeaderLabels(["Fichier", "Statut", "Licence"])
        self.assets.setRootIsDecorated(False)
        self.assets.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.assets.itemDoubleClicked.connect(
            lambda it, _c: self.assetActivated.emit(str(it.data(0, ID_ROLE)))
        )
        self.tabs.addTab(
            self._with_hint(
                self.assets, "Ressources importées dans le projet. Double-clic : fiche de provenance."
            ),
            "Ressources",
        )

    # --- favoris ------------------------------------------------------------
    def _make_favoritable(self, item: QListWidgetItem, fav_id: str) -> None:
        item.setData(FAV_ROLE, fav_id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if fav_id in self._favorites else Qt.CheckState.Unchecked)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        fav_id = item.data(FAV_ROLE)
        if not fav_id or self._updating:
            return
        if item.checkState() == Qt.CheckState.Checked:
            self._favorites.add(str(fav_id))
        else:
            self._favorites.discard(str(fav_id))
        self.favoritesChanged.emit(sorted(self._favorites))
        self._filter()

    def favorites(self) -> list[str]:
        return sorted(self._favorites)

    def set_favorite(self, fav_id: str, on: bool) -> None:
        """Marque un favori par programme (identifiant « objet:kind », « animation:id », « modèle:id »)."""
        for lst in (self.objects, self.presets, self.templates):
            for i in range(lst.count()):
                item = lst.item(i)
                if item.data(FAV_ROLE) == fav_id:
                    item.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    # --- ressources ---------------------------------------------------------
    def set_inventory(self, rows: list[InventoryRow]) -> None:
        self.assets.clear()
        for row in rows:
            choice = choice_for(row.asset.license.license)
            item = QTreeWidgetItem(
                [
                    row.asset.path.rsplit("/", 1)[-1],
                    row.status,
                    choice.label.split(" — ")[0] if choice else row.asset.license.license or "—",
                ]
            )
            item.setData(0, ID_ROLE, row.asset.id)
            item.setToolTip(0, f"{row.asset.path}\nUtilisée par : {', '.join(row.used_by) or '—'}")
            if row.status != STATUS_COMPLETE:
                item.setForeground(1, theme.WARNING)
                item.setText(1, "⚠ " + row.status)
            self.assets.addTopLevelItem(item)
        self.tabs.setTabText(3, f"Ressources ({len(rows)})" if rows else "Ressources")

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
        label.setProperty("role", "hint")
        lay.addWidget(label)
        lay.addWidget(widget, 1)
        return box

    def refresh_icons(self) -> None:
        """Vignettes réelles (objets, modèles) et icônes d'animation, aux couleurs du thème courant."""
        thumbnails.clear_cache()
        for i in range(self.objects.count()):
            item = self.objects.item(i)
            kind = item.data(ID_ROLE)
            if kind:
                item.setIcon(thumbnails.kind_icon(str(kind), 32))
        for i in range(self.presets.count()):
            item = self.presets.item(i)
            item.setIcon(thumbnails.preset_icon(str(item.data(ID_ROLE))))
        for i in range(self.templates.count()):
            item = self.templates.item(i)
            if not item.icon().isNull():
                continue
            tid = str(item.data(ID_ROLE))
            if tid in TEMPLATES:
                item.setIcon(QIcon(thumbnails.template_pixmap(tid, 96, 54)))

    def _filter(self) -> None:
        q = self.search.text().strip().casefold()
        fav_only = self.fav_only.isChecked()
        for lst in (self.objects, self.presets, self.templates):
            for i in range(lst.count()):
                item = lst.item(i)
                is_header = not item.data(ID_ROLE)
                if is_header:
                    continue
                hidden = bool(q) and q not in item.text().casefold()
                if fav_only and item.data(FAV_ROLE) not in self._favorites:
                    hidden = True
                item.setHidden(hidden)

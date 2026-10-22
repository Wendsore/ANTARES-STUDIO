"""Bibliothèque : objets à ajouter (double-clic), animations, effets et filtres, bruitages, modèles."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import theme, thumbnails
from antares_studio.audio import sfx
from antares_studio.domain.effects import EFFECT_PRESETS, OBJECT_LOOKS, SCENE_LOOKS
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
    "3D": ("model3d", "image_sequence"),
    "Images": ("image",),
    "Organisation": ("group", "camera"),
}


def sound_cache_dir() -> Path:
    """Dossier des bruitages déjà calculés (préférences isolées pendant les tests)."""
    folder = os.environ.get("ANTARES_SETTINGS_DIR", "").strip()
    if folder:
        return Path(folder) / "sons"
    from PySide6.QtCore import QStandardPaths

    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
    return Path(base) / "sons"


def _header(text: str) -> QListWidgetItem:
    item = QListWidgetItem(text)
    item.setFlags(Qt.ItemFlag.NoItemFlags)
    item.setData(ID_ROLE, "")
    f = item.font()
    f.setBold(True)
    item.setFont(f)
    return item


class LibraryDock(QWidget):
    addRequested = Signal(str)  # kind
    presetRequested = Signal(str)  # preset id
    templateRequested = Signal(str)  # template id
    assetActivated = Signal(str)  # asset id (double-clic dans l'onglet Ressources)
    objectLookRequested = Signal(str)  # identifiant OBJECT_LOOKS, appliqué à la sélection
    sceneLookRequested = Signal(str)  # identifiant SCENE_LOOKS, appliqué à la scène courante
    soundRequested = Signal(str)  # identifiant de bruitage, inséré à la tête de lecture
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
            self.objects.addItem(_header(cat))
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

        self.effects = QListWidget()
        self.effects.setWordWrap(True)
        self.effects.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # libellés repliés
        groups: list[tuple[str, str, list[tuple[str, str, str]]]] = [
            (
                "Effets d'objet — sur la sélection",
                "objet",
                [(k, v[0], v[1]) for k, v in OBJECT_LOOKS.items()],
            ),
            (
                "Filtres de scène — sur la scène courante",
                "scène",
                [(k, v[0], v[1]) for k, v in SCENE_LOOKS.items()],
            ),
            (
                "Animations d'effet — sur la sélection",
                "animation",
                [(k, PRESETS[k].label, PRESETS[k].description) for k in EFFECT_PRESETS],
            ),
        ]
        for title, prefix, entries in groups:
            self.effects.addItem(_header(title))
            for key, label, description in entries:
                item = QListWidgetItem(label)
                item.setData(ID_ROLE, f"{prefix}:{key}")
                item.setToolTip(description)
                self._make_favoritable(item, f"effet:{prefix}:{key}")
                self.effects.addItem(item)
        self.effects.itemDoubleClicked.connect(self._on_effect_activated)
        self.effects.itemChanged.connect(self._on_item_changed)
        self.tabs.addTab(
            self._with_hint(
                self.effects,
                "Double-clic : effet sur les objets sélectionnés, ou filtre sur toute la scène. "
                "Réglages fins : Inspecteur, sections « Effets » et « Filtres ».",
            ),
            "Effets",
        )

        self.sounds = QListWidget()
        self.sounds.setWordWrap(True)
        self.sounds.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for cat in sfx.CATEGORIES:
            self.sounds.addItem(_header(cat))
            for sid, sound in sfx.SOUNDS.items():
                if sound.category != cat:
                    continue
                item = QListWidgetItem(sound.label)
                item.setData(ID_ROLE, sid)
                item.setToolTip(sound.description + ("\nAmbiance prévue pour boucler." if sound.loop else ""))
                self._make_favoritable(item, f"son:{sid}")
                self.sounds.addItem(item)
        self.sounds.itemDoubleClicked.connect(self._on_sound_activated)
        self.sounds.itemChanged.connect(self._on_item_changed)
        sound_box = QWidget()
        sound_lay = QVBoxLayout(sound_box)
        sound_lay.setContentsMargins(0, 0, 0, 0)
        sound_lay.addWidget(self.sounds, 1)
        buttons = QHBoxLayout()
        self.listen_btn = QPushButton("▶ Écouter")
        self.listen_btn.setToolTip("Écouter le son sélectionné (sans l'ajouter au projet)")
        self.listen_btn.clicked.connect(self.preview_selected_sound)
        self.insert_sound_btn = QPushButton("Insérer à la tête de lecture")
        self.insert_sound_btn.clicked.connect(self._insert_selected_sound)
        buttons.addWidget(self.listen_btn)
        buttons.addWidget(self.insert_sound_btn, 1)
        sound_lay.addLayout(buttons)
        self._preview: object | None = None
        self.tabs.addTab(
            self._with_hint(
                sound_box,
                "Bruitages et ambiances créés par ANTARES Studio, libres de droits (CC0). "
                "Double-clic : insérer à l'image courante (piste « effet »).",
            ),
            "Sons",
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

    def _lists(self) -> tuple[QListWidget, ...]:
        return (self.objects, self.presets, self.effects, self.sounds, self.templates)

    def favorites(self) -> list[str]:
        return sorted(self._favorites)

    def set_favorite(self, fav_id: str, on: bool) -> None:
        """Marque un favori par programme (identifiant « objet:kind », « animation:id », « modèle:id »)."""
        for lst in self._lists():
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
        self.tabs.setTabText(self.tabs.count() - 1, f"Ressources ({len(rows)})" if rows else "Ressources")

    def _on_object_activated(self, item: QListWidgetItem) -> None:
        kind = item.data(ID_ROLE)
        if kind:
            self.addRequested.emit(str(kind))

    def _on_effect_activated(self, item: QListWidgetItem) -> None:
        key = str(item.data(ID_ROLE) or "")
        prefix, _sep, ident = key.partition(":")
        if prefix == "objet":
            self.objectLookRequested.emit(ident)
        elif prefix == "scène":
            self.sceneLookRequested.emit(ident)
        elif prefix == "animation":
            self.presetRequested.emit(ident)

    # --- sons ---------------------------------------------------------------
    def selected_sound(self) -> str | None:
        item = self.sounds.currentItem()
        sid = item.data(ID_ROLE) if item is not None else None
        return str(sid) if sid else None

    def _on_sound_activated(self, item: QListWidgetItem) -> None:
        sid = item.data(ID_ROLE)
        if sid:
            self.soundRequested.emit(str(sid))

    def _insert_selected_sound(self) -> None:
        sid = self.selected_sound()
        if sid:
            self.soundRequested.emit(sid)

    def preview_selected_sound(self) -> Path | None:
        """Calcule le son (une fois, puis cache) et le joue ; sans sortie audio, rien ne se passe."""
        sid = self.selected_sound()
        if sid is None:
            return None
        path = sfx.write_sound(sid, sound_cache_dir())
        from antares_studio.app.audio_player import HAS_MULTIMEDIA, ClipPlayer

        if HAS_MULTIMEDIA and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            if isinstance(self._preview, ClipPlayer):
                self._preview.dispose()
            self._preview = ClipPlayer(path, 1.0, self)
            self._preview.play_from(0.0)
        return path

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
        for lst in self._lists():
            for i in range(lst.count()):
                item = lst.item(i)
                is_header = not item.data(ID_ROLE)
                if is_header:
                    continue
                hidden = bool(q) and q not in item.text().casefold()
                if fav_only and item.data(FAV_ROLE) not in self._favorites:
                    hidden = True
                item.setHidden(hidden)

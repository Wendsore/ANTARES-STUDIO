"""Fenêtre principale : menus en français, docks, actions fichier/édition, autosave et récupération."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QToolBar,
    QWhatsThis,
    QWidget,
)

from antares_studio.app import icons, theme
from antares_studio.app.canvas_widget import CanvasWidget
from antares_studio.app.command_palette import CommandPalette
from antares_studio.app.diagnostics import diagnostics_report
from antares_studio.app.dialogs import AboutDialog, DiagnosticsDialog, NewProjectDialog
from antares_studio.app.document import ProjectDocument
from antares_studio.app.export_dialog import ExportDialog
from antares_studio.app.export_queue import ExportJob, ExportQueue, ExportsPanel
from antares_studio.app.help_center import HelpCenter
from antares_studio.app.inspector_dock import InspectorDock
from antares_studio.app.layers_dock import LayersDock
from antares_studio.app.library_dock import LibraryDock
from antares_studio.app.narration_dock import NarrationDock
from antares_studio.app.preset_dialog import PresetDialog
from antares_studio.app.provenance_dialog import LicenseInventoryDialog, edit_asset_provenance
from antares_studio.app.settings import AppSettings
from antares_studio.app.timeline_dock import TimelineDock
from antares_studio.app.tutorial_panel import Highlighter, TutorialPanel
from antares_studio.domain.clipboard import MIME_TYPE as CLIPBOARD_MIME
from antares_studio.domain.clipboard import PastePayload, copy_nodes, read_payload, remap_assets
from antares_studio.domain.commands import (
    AddMarker,
    AddNode,
    AddScene,
    RemoveNode,
    ReplaceTracks,
    SetAssetLicense,
    SetProjectMetadata,
    SetProperties,
)
from antares_studio.domain.ids import new_id
from antares_studio.domain.kinds import spec_for
from antares_studio.domain.layout import ALIGN_MODES, align_deltas, distribute_deltas
from antares_studio.domain.model import AssetLicense, Canvas, Marker, Node, Scene
from antares_studio.domain.validation import ProjectValidationError
from antares_studio.help import topics
from antares_studio.help.tutorials import TUTORIALS, TUTORIALS_BY_ID, TutorialContext
from antares_studio.persistence.schema import ProjectFormatError
from antares_studio.persistence.store import PROJECT_SUFFIX, ProjectStore, resolve_project_root
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import ProjectRenderResult, RenderError, audio_plans_for_scene
from antares_studio.rendering.plan import build_render_plan
from antares_studio.rendering.qt_painter import ImageCache
from antares_studio.rendering.transitions import FrameRenderer
from antares_studio.resources.licenses import inventory
from antares_studio.resources.templates import TEMPLATES, create_project, scale_warning_node, template_labels
from antares_studio.timeline.presets import apply_preset

EXAMPLE_CSV = "planetes-periode-distance.csv"
# Rubrique d'aide ouverte par F1 selon le panneau actif (nom d'objet du dock ou du widget).
CONTEXT_TOPICS: dict[str, str] = {
    "canvas": "canevas",
    "dock_library": "bibliotheque",
    "dock_layers": "scenes-et-calques",
    "dock_inspector": "inspecteur",
    "dock_timeline": "images-cles",
    "dock_narration": "narration",
    "dock_tutorial": "tutoriels",
    "dock_exports": "export-video",
}
# Icônes Lucide des actions (recolorées à chaque changement de thème).
ACTION_ICONS: dict[str, str] = {
    "act_new": "file-plus",
    "act_open": "folder-open",
    "act_save": "save",
    "act_export": "clapperboard",
    "act_quick_preview": "fast-forward",
    "act_export_png": "image-down",
    "act_inventory": "shield-check",
    "act_scale_warning": "triangle-alert",
    "act_add_marker": "bookmark",
    "act_camera_view": "video",
    "act_undo": "undo-2",
    "act_redo": "redo-2",
    "act_delete": "trash-2",
    "act_duplicate": "copy-plus",
    "act_copy": "copy",
    "act_cut": "scissors",
    "act_paste": "clipboard-paste",
    "act_group": "group",
    "act_play": "play",
    "act_go_start": "skip-back",
    "act_go_end": "skip-forward",
    "act_zoom_fit": "scan",
    "act_grid": "grid-3x3",
    "act_snap": "magnet",
    "act_help": "circle-help",
    "act_palette": "command",
    "act_welcome": "house",
    "act_shortcuts": "keyboard",
    "act_diag": "wrench",
    "act_about": "info",
    "act_distribute_h": "align-horizontal-distribute-center",
    "act_distribute_v": "align-vertical-distribute-center",
}
ALIGN_ICONS: dict[str, str] = {
    "left": "align-start-vertical",
    "hcenter": "align-center-vertical",
    "right": "align-end-vertical",
    "top": "align-start-horizontal",
    "vcenter": "align-center-horizontal",
    "bottom": "align-end-horizontal",
}


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = AppSettings()
        self.store = ProjectStore()
        app = QApplication.instance()
        if isinstance(app, QApplication):
            theme.apply_theme(app, self.settings.theme(), self.settings.font_scale())
        self.setWindowIcon(icons.app_icon())
        self.ui_counters: dict[str, int] = {
            "palette_used": 0,
            "help_opened": 0,
            "inventory_opened": 0,
            "exports": 0,
            "full_exports": 0,
        }
        self.help_center: HelpCenter | None = None
        self.document = ProjectDocument(create_project("Sans titre", Canvas(), "", 20))
        self.setWindowTitle("ANTARES Studio")
        self.resize(1400, 860)
        self.canvas = CanvasWidget(self.document)
        self.setCentralWidget(self.canvas)
        self._build_docks()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        self._connect_document()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start(max(10, self.settings.autosave_interval_s()) * 1000)
        self._restore_layout()
        self._tutorial_timer = QTimer(self)
        self._tutorial_timer.setInterval(300)
        self._tutorial_timer.timeout.connect(self.tutorial.refresh)
        self._apply_icons()
        self._set_whats_this()
        self.statusBar().showMessage(
            "Astuce : F1 ouvre l'aide, Ctrl+K cherche une commande, Aide > Tutoriels pour apprendre.",
            12000,
        )
        QTimer.singleShot(0, self.canvas.fit_to_view)

    # --- construction UI ---------------------------------------------------
    def _build_docks(self) -> None:
        self.library = LibraryDock(template_labels(), self.settings.favorites())
        self.library.addRequested.connect(self.add_node_of_kind)
        self.library.presetRequested.connect(self.apply_preset_to_selection)
        self.library.templateRequested.connect(self.add_template_scene)
        self.library.assetActivated.connect(self.edit_asset_provenance)
        self.library.favoritesChanged.connect(self.settings.set_favorites)
        self.library_dock = self._dock(
            "Bibliothèque", self.library, Qt.DockWidgetArea.LeftDockWidgetArea, "dock_library"
        )
        self.layers = LayersDock(self.document)
        self.layers_dock = self._dock(
            "Scènes et objets", self.layers, Qt.DockWidgetArea.LeftDockWidgetArea, "dock_layers"
        )
        self.inspector = InspectorDock(self.document)
        self.inspector_dock = self._dock(
            "Inspecteur", self.inspector, Qt.DockWidgetArea.RightDockWidgetArea, "dock_inspector"
        )
        self.timeline = TimelineDock(self.document)
        self.timeline.ffmpeg_path = self.settings.ffmpeg_path()
        self.timeline_dock = self._dock(
            "Timeline", self.timeline, Qt.DockWidgetArea.BottomDockWidgetArea, "dock_timeline"
        )
        self.narration = NarrationDock(self.document, self.settings)
        self.narration.audio.provenance_prompt = lambda asset: edit_asset_provenance(
            self.document, asset, self
        )
        self.narration_dock = self._dock(
            "Narration (audio et sous-titres)",
            self.narration,
            Qt.DockWidgetArea.BottomDockWidgetArea,
            "dock_narration",
        )
        self.tabifyDockWidget(self.timeline_dock, self.narration_dock)
        self.timeline_dock.raise_()
        self.tutorial = TutorialPanel(self.tutorial_context)
        self.tutorial.showMeRequested.connect(self.highlight_widget)
        self.tutorial.actionRequested.connect(self._tutorial_action)
        self.tutorial.tutorialFinished.connect(self._tutorial_finished)
        self.tutorial.closeRequested.connect(self._tutorial_closed)
        self.tutorial_dock = self._dock(
            "Tutoriel", self.tutorial, Qt.DockWidgetArea.RightDockWidgetArea, "dock_tutorial"
        )
        self.splitDockWidget(self.inspector_dock, self.tutorial_dock, Qt.Orientation.Vertical)
        self.tutorial_dock.hide()
        self.export_queue = ExportQueue(self)
        self.export_queue.jobFinished.connect(self._export_job_finished)
        self.exports = ExportsPanel(self.export_queue)
        self.exports_dock = self._dock(
            "Exports", self.exports, Qt.DockWidgetArea.BottomDockWidgetArea, "dock_exports"
        )
        self.tabifyDockWidget(self.narration_dock, self.exports_dock)
        self.exports_dock.hide()
        self.timeline_dock.raise_()
        for widget, name in (
            (self.canvas, "canvas"),
            (self.library.search, "library_search"),
            (self.library.tabs, "library_tabs"),
            (self.layers.tree, "layers_tree"),
            (self.inspector, "inspector"),
            (self.timeline.view, "timeline_view"),
            (self.timeline.play_btn, "timeline_play"),
            (self.narration.audio.import_btn, "narration_import"),
            (self.narration.audio.table, "narration_table"),
            (self.narration.subtitles.add_btn, "subtitles_add"),
            (self.narration.subtitles.table, "subtitles_table"),
        ):
            widget.setObjectName(name)
        for panel, width in ((self.library, 310), (self.layers, 310), (self.inspector, 360)):
            panel.setMinimumWidth(width)
        self.resizeDocks([self.library_dock, self.layers_dock], [360, 420], Qt.Orientation.Vertical)
        self.resizeDocks([self.inspector_dock], [340], Qt.Orientation.Horizontal)
        self.resizeDocks([self.library_dock, self.layers_dock], [300, 300], Qt.Orientation.Horizontal)
        self.resizeDocks([self.timeline_dock], [220], Qt.Orientation.Vertical)

    def _all_docks(self) -> tuple[QDockWidget, ...]:
        return (
            self.library_dock,
            self.layers_dock,
            self.inspector_dock,
            self.timeline_dock,
            self.narration_dock,
            self.tutorial_dock,
            self.exports_dock,
        )

    def _dock(self, title: str, widget: QWidget, area: Qt.DockWidgetArea, name: str) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(area, dock)
        return dock

    def _action(  # type: ignore[no-untyped-def]
        self,
        text: str,
        slot,
        shortcut: str | QKeySequence | QKeySequence.StandardKey | None = None,
        tip: str = "",
    ) -> QAction:
        act = QAction(text, self)
        if shortcut is not None:
            act.setShortcut(QKeySequence(shortcut))
        if tip:
            act.setStatusTip(tip)
        act.triggered.connect(slot)
        return act

    def _build_actions(self) -> None:
        self.act_new = self._action("&Nouveau projet…", self.new_project, QKeySequence.StandardKey.New)
        self.act_open = self._action("&Ouvrir…", self.open_project, QKeySequence.StandardKey.Open)
        self.act_save = self._action("&Enregistrer", self.save_project, QKeySequence.StandardKey.Save)
        self.act_save_as = self._action("Enregistrer &sous…", self.save_project_as, "Ctrl+Shift+S")
        self.act_export = self._action("E&xporter la vidéo…", self.export_video, "Ctrl+E")
        self.act_quick_preview = self._action(
            "Aperçu &rapide (360p)",
            self.quick_preview,
            "Ctrl+Shift+E",
            "Rend la scène en basse définition en arrière-plan puis l'ouvre dans votre lecteur vidéo",
        )
        self.act_export_png = self._action(
            "Exporter l'&image courante (PNG)…",
            self.export_still,
            tip="Enregistre l'image affichée, à la taille du projet (vignette, affiche, diapositive)",
        )
        self.act_inventory = self._action("Inventaire des &licences et crédits…", self.show_inventory)
        self.act_scale_warning = self._action(
            "Avertissement d'é&chelle (« non à l'échelle »)", self.add_scale_warning
        )
        self.act_quit = self._action("&Quitter", self.close, QKeySequence.StandardKey.Quit)
        self.act_undo = self._action("&Annuler", self.document.undo.undo, QKeySequence.StandardKey.Undo)
        self.act_redo = self._action("&Rétablir", self.document.undo.redo, "Ctrl+Y")
        # Ctrl+Y (Windows) et Ctrl+Maj+Z (Linux, macOS) partout ; « Suppr » seule : sous KDE/GNOME le
        # raccourci standard Delete inclut Ctrl+D, déjà pris par « Dupliquer » (conflit = aucune action).
        self.act_redo.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.act_delete = self._action("&Supprimer", self.delete_selection, "Delete")
        self.act_duplicate = self._action("&Dupliquer", self.duplicate_selection, "Ctrl+D")
        self.act_select_all = self._action(
            "&Tout sélectionner", self.select_all, QKeySequence.StandardKey.SelectAll
        )
        self.act_copy = self._action("&Copier", self.copy_selection, QKeySequence.StandardKey.Copy)
        self.act_cut = self._action("Co&uper", self.cut_selection, QKeySequence.StandardKey.Cut)
        self.act_paste = self._action("C&oller", self.paste, QKeySequence.StandardKey.Paste)
        self._paste_count = 0
        QApplication.clipboard().dataChanged.connect(self._on_clipboard_changed)
        self.align_actions: dict[str, QAction] = {
            mode: self._action(label, lambda _c=False, m=mode: self.align_selection(m))
            for mode, label in ALIGN_MODES.items()
        }
        self.act_distribute_h = self._action(
            "Répartir horizontalement",
            lambda: self.distribute_selection("x"),
            tip="Espacement égal (3 objets ou plus)",
        )
        self.act_distribute_v = self._action(
            "Répartir verticalement",
            lambda: self.distribute_selection("y"),
            tip="Espacement égal (3 objets ou plus)",
        )
        self.act_group = self._action("&Grouper", self.group_selection, "Ctrl+G")
        self.act_ungroup = self._action("Dégrou&per", self.ungroup_selection, "Ctrl+Shift+G")
        self.act_play = self._action("&Lecture / pause", self.timeline.toggle_play, "Space")
        self.act_frame_prev = self._action(
            "Image précédente", lambda: self.document.set_frame(self.document.frame - 1), ","
        )
        self.act_frame_next = self._action(
            "Image suivante", lambda: self.document.set_frame(self.document.frame + 1), "."
        )
        self.act_add_marker = self._action(
            "Ajouter un &repère à l'image courante", self.add_marker, "M", "Repère nommé sur la Timeline"
        )
        self.act_prev_marker = self._action("Repère précédent", lambda: self.jump_marker(-1), "[")
        self.act_next_marker = self._action("Repère suivant", lambda: self.jump_marker(1), "]")
        self.act_go_start = self._action("Début", self.timeline.go_start, "Home")
        self.act_go_end = self._action("Fin", self.timeline.go_end, "End")
        self.act_zoom_in = self._action(
            "Zoom avant",
            lambda: self.canvas.set_zoom(self.canvas.zoom * 1.25),
            QKeySequence.StandardKey.ZoomIn,
        )
        self.act_zoom_out = self._action(
            "Zoom arrière",
            lambda: self.canvas.set_zoom(self.canvas.zoom / 1.25),
            QKeySequence.StandardKey.ZoomOut,
        )
        self.act_zoom_fit = self._action("Ajuster à la fenêtre", self.canvas.fit_to_view, "Ctrl+0")
        self.act_grid = self._action("Afficher la &grille", self.toggle_grid, "Ctrl+'")
        self.act_grid.setCheckable(True)
        self.act_snap = self._action("&Aimanter à la grille", self.toggle_snap, "Ctrl+Shift+'")
        self.act_snap.setCheckable(True)
        self.act_guides = self._action(
            "Guides d'a&lignement (bords et centres)",
            self.toggle_guides,
            tip="Aimante un objet déplacé aux autres objets et au centre ; maintenir Ctrl pour l'ignorer",
        )
        self.act_guides.setCheckable(True)
        self.act_guides.setChecked(True)
        self.act_safe = self._action("Zones &sûres (sous-titres)", self.toggle_safe_zones)
        self.act_safe.setCheckable(True)
        self.act_camera_view = self._action(
            "Voir à travers la &caméra",
            self.toggle_camera_view,
            tip="Décoché : toute la scène est visible et le cadre de la caméra est dessiné par-dessus",
        )
        self.act_camera_view.setCheckable(True)
        self.act_camera_view.setChecked(True)
        self.act_reset_layout = self._action("Réinitialiser la disposition", self.reset_layout)
        self.act_about = self._action("À &propos d'ANTARES Studio", lambda: AboutDialog(self).exec())
        self.act_diag = self._action("&Diagnostics…", self.show_diagnostics)
        self.act_ffmpeg = self._action("Chemin de &FFmpeg…", self.configure_ffmpeg)
        self.act_help = self._action(
            "&Centre d'aide",
            self.show_context_help,
            QKeySequence.StandardKey.HelpContents,
            "Ouvre l'aide à la rubrique du panneau actif",
        )
        self.act_whats_this = self._action(
            "&Qu'est-ce que c'est ?", QWhatsThis.enterWhatsThisMode, QKeySequence.StandardKey.WhatsThis
        )
        self.act_palette = self._action(
            "Rechercher une &commande…", self.show_command_palette, "Ctrl+K", "Toutes les commandes"
        )
        self.act_welcome = self._action("&Accueil…", self.show_welcome)
        self.act_shortcuts = self._action("&Raccourcis clavier", lambda: self.show_help("raccourcis"))
        self.theme_group = QActionGroup(self)
        self.theme_actions: dict[str, QAction] = {}
        for pal in theme.THEMES.values():
            act = self._action(pal.label, lambda _c=False, n=pal.name: self.set_theme(n))
            act.setCheckable(True)
            act.setChecked(pal.name == theme.active().name)
            self.theme_group.addAction(act)
            self.theme_actions[pal.name] = act
        self.scale_group = QActionGroup(self)
        self.scale_actions: dict[int, QAction] = {}
        for pct in theme.FONT_SCALES:
            act = self._action(f"{pct} %", lambda _c=False, v=pct: self.set_font_scale(v))
            act.setCheckable(True)
            act.setChecked(pct == theme.font_scale())
            self.scale_group.addAction(act)
            self.scale_actions[pct] = act
        for act in (
            self.act_play,
            self.act_frame_prev,
            self.act_frame_next,
            self.act_go_start,
            self.act_go_end,
            self.act_add_marker,
            self.act_prev_marker,
            self.act_next_marker,
        ):
            act.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            self.addAction(act)

    def _build_menus(self) -> None:
        mb = self.menuBar()
        m_file = mb.addMenu("&Fichier")
        for a in (self.act_new, self.act_open):
            m_file.addAction(a)
        self.menu_recent = m_file.addMenu("Projets &récents")
        self._fill_recent()
        m_file.addSeparator()
        for a in (self.act_save, self.act_save_as):
            m_file.addAction(a)
        m_file.addSeparator()
        for a in (self.act_export, self.act_quick_preview, self.act_export_png):
            m_file.addAction(a)
        m_file.addAction(self.act_inventory)
        m_file.addSeparator()
        m_file.addAction(self.act_quit)
        m_edit = mb.addMenu("&Édition")
        for a in (self.act_undo, self.act_redo):
            m_edit.addAction(a)
        m_edit.addSeparator()
        for a in (self.act_cut, self.act_copy, self.act_paste):
            m_edit.addAction(a)
        m_edit.addSeparator()
        for a in (self.act_select_all, self.act_duplicate, self.act_delete):
            m_edit.addAction(a)
        m_edit.addSeparator()
        for a in (self.act_group, self.act_ungroup):
            m_edit.addAction(a)
        m_align = m_edit.addMenu("&Aligner et répartir")
        for mode in ("left", "hcenter", "right"):
            m_align.addAction(self.align_actions[mode])
        m_align.addSeparator()
        for mode in ("top", "vcenter", "bottom"):
            m_align.addAction(self.align_actions[mode])
        m_align.addSeparator()
        m_align.addAction(self.act_distribute_h)
        m_align.addAction(self.act_distribute_v)
        m_edit.addSeparator()
        m_edit.addAction(self.act_palette)
        m_add = mb.addMenu("&Objet")
        for kind in (
            "circle",
            "ellipse",
            "rect",
            "polygon",
            "star",
            "line",
            "arrow",
            "orbit_path",
            "text",
            "callout",
            "image",
            "group",
            "camera",
        ):
            spec = spec_for(kind)
            m_add.addAction(self._action(spec.label, lambda _c=False, k=kind: self.add_node_of_kind(k)))
        m_add.addSeparator()
        m_add.addAction(self.act_scale_warning)
        m_add.addAction(self._action("Importer une &image…", self.import_image, "Ctrl+I"))
        m_add.addAction(self._action("Importer des &données (CSV) en graphique…", self.import_data))
        m_add.addAction(self._action("&Planète 3D (Blender, facultatif)…", self.add_blender_planet))
        m_anim = mb.addMenu("&Animation")
        from antares_studio.timeline.presets import PRESETS

        for pid, pspec in PRESETS.items():
            m_anim.addAction(
                self._action(pspec.label + "…", lambda _c=False, p=pid: self.apply_preset_to_selection(p))
            )
        m_anim.addSeparator()
        for a in (
            self.act_play,
            self.act_go_start,
            self.act_go_end,
            self.act_frame_prev,
            self.act_frame_next,
        ):
            m_anim.addAction(a)
        m_anim.addSeparator()
        for a in (self.act_add_marker, self.act_prev_marker, self.act_next_marker):
            m_anim.addAction(a)
        m_narr = mb.addMenu("&Narration")
        m_narr.addAction(self._action("Importer une &narration audio…", self.narration.audio.import_audio))
        m_narr.addAction(
            self._action(
                "Ajouter un &sous-titre à l'image courante", self.narration.subtitles.add_at_current_frame
            )
        )
        m_narr.addAction(
            self._action("Importer des sous-titres (SRT/VTT)…", self.narration.subtitles.import_file)
        )
        m_narr.addAction(
            self._action("Exporter les sous-titres (SRT)…", self.narration.subtitles.export_file)
        )
        m_view = mb.addMenu("&Affichage")
        for a in (self.act_zoom_in, self.act_zoom_out, self.act_zoom_fit):
            m_view.addAction(a)
        m_view.addSeparator()
        for a in (self.act_grid, self.act_snap, self.act_guides, self.act_safe, self.act_camera_view):
            m_view.addAction(a)
        m_view.addSeparator()
        for dock in self._all_docks():
            m_view.addAction(dock.toggleViewAction())
        m_view.addSeparator()
        m_theme = m_view.addMenu("&Thème")
        for act in self.theme_actions.values():
            m_theme.addAction(act)
        m_scale = m_view.addMenu("Taille du te&xte")
        for act in self.scale_actions.values():
            m_scale.addAction(act)
        m_view.addAction(self.act_reset_layout)
        m_help = mb.addMenu("&Aide")
        m_help.addAction(self.act_help)
        self.menu_tutorials = m_help.addMenu("&Tutoriels")
        self._fill_tutorials_menu()
        for a in (self.act_shortcuts, self.act_whats_this, self.act_welcome):
            m_help.addAction(a)
        m_help.addSeparator()
        m_help.addAction(self.act_diag)
        m_help.addAction(self.act_ffmpeg)
        m_help.addSeparator()
        m_help.addAction(self.act_about)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Principal", self)
        tb.setObjectName("toolbar_main")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        short = {
            "act_new": "Nouveau",
            "act_open": "Ouvrir",
            "act_save": "Enregistrer",
            "act_export": "Exporter",
            "act_undo": "Annuler",
            "act_redo": "Rétablir",
            "act_zoom_fit": "Ajuster",
            "act_grid": "Grille",
            "act_palette": "Commandes",
            "act_help": "Aide",
        }
        groups = (
            ("act_new", "act_open", "act_save", "act_export"),
            ("act_undo", "act_redo"),
            ("act_zoom_fit", "act_grid"),
        )
        for gi, group in enumerate(groups):
            if gi:
                tb.addSeparator()
            for name in group:
                tb.addAction(getattr(self, name))
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)
        tb.addAction(self.act_palette)
        tb.addAction(self.act_help)
        for name, label in short.items():
            act: QAction = getattr(self, name)
            act.setIconText(label)
            keys = act.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            act.setToolTip(f"{act.text().replace('&', '').split('  ')[0]}" + (f" ({keys})" if keys else ""))
        self.toolbar = tb
        self.addToolBar(tb)

    def _build_statusbar(self) -> None:
        self.status_pos = QLabel("x : –  y : –")
        self.status_zoom = QLabel("zoom 100 %")
        self.status_sel = QLabel("")
        sb = self.statusBar()
        sb.addPermanentWidget(self.status_sel)
        sb.addPermanentWidget(self.status_pos)
        sb.addPermanentWidget(self.status_zoom)
        self.canvas.cursorMoved.connect(lambda x, y: self.status_pos.setText(f"x : {x:.0f}  y : {y:.0f}"))
        self.canvas.zoomChanged.connect(lambda z: self.status_zoom.setText(f"zoom {z * 100:.0f} %"))
        self.canvas.nodeDoubleClicked.connect(self._edit_text_inline)

    def _connect_document(self) -> None:
        d = self.document
        d.changed.connect(self._refresh_actions)
        d.dirtyChanged.connect(lambda _d: self._refresh_title())
        d.pathChanged.connect(self._refresh_title)
        d.selectionChanged.connect(lambda _s: self._refresh_actions())
        d.changed.connect(self._refresh_inventory)
        self._refresh_inventory()
        self._refresh_actions()
        self._refresh_title()

    def _refresh_actions(self) -> None:
        d = self.document
        self.act_undo.setEnabled(d.undo.can_undo)
        self.act_undo.setText(f"&Annuler {d.undo.undo_label}" if d.undo.can_undo else "&Annuler")
        self.act_redo.setEnabled(d.undo.can_redo)
        self.act_redo.setText(f"&Rétablir {d.undo.redo_label}" if d.undo.can_redo else "&Rétablir")
        has_sel = bool(d.selection)
        for a in (self.act_delete, self.act_duplicate, self.act_group, self.act_copy, self.act_cut):
            a.setEnabled(has_sel)
        for a in self.align_actions.values():
            a.setEnabled(has_sel)
        for a in (self.act_distribute_h, self.act_distribute_v):
            a.setEnabled(len(d.selection) >= 3)
        self.act_ungroup.setEnabled(any(n.kind == "group" for n in d.selected_nodes))
        n = len(d.selection)
        self.status_sel.setText(
            "" if n == 0 else f"{n} objet{'s' if n > 1 else ''} sélectionné{'s' if n > 1 else ''}"
        )

    def _refresh_title(self) -> None:
        star = "*" if self.document.is_dirty else ""
        where = f" — {self.document.root}" if self.document.root else ""
        self.setWindowTitle(f"{self.document.title}{star}{where} — ANTARES Studio")

    # --- disposition --------------------------------------------------------
    def _restore_layout(self) -> None:
        geo = self.settings.window_geometry()
        state = self.settings.window_state()
        if not geo.isEmpty():
            self.restoreGeometry(geo)
        if not state.isEmpty():
            self.restoreState(state)

    def reset_layout(self) -> None:
        self.settings.reset_window()
        for dock in self._all_docks():
            dock.setFloating(False)
            dock.show()
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.library_dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.layers_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.timeline_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.narration_dock)
        self.tabifyDockWidget(self.timeline_dock, self.narration_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.exports_dock)
        self.tabifyDockWidget(self.narration_dock, self.exports_dock)
        self.timeline_dock.raise_()
        self.resize(1400, 860)
        self.canvas.fit_to_view()

    def toggle_grid(self, on: bool) -> None:
        self.canvas.show_grid = on
        self.canvas.update()

    def toggle_snap(self, on: bool) -> None:
        self.canvas.snap_to_grid = on

    def toggle_guides(self, on: bool) -> None:
        self.canvas.smart_guides = on

    def toggle_camera_view(self, on: bool) -> None:
        self.document.preview_camera = on
        self.canvas.update()
        self.inspector.refresh_values()

    # --- repères --------------------------------------------------------------------
    def add_marker(self, label: str | None = None) -> Marker | None:
        scene = self.document.scene
        if scene is None:
            return None
        frame = self.document.frame
        existing = next((m for m in scene.markers if m.frame == frame), None)
        if existing is not None:
            self.statusBar().showMessage(f"Un repère existe déjà ici : « {existing.label} ».", 4000)
            return existing
        if label is None:
            label = f"Repère {len(scene.markers) + 1}"
        marker = Marker.create(frame, label)
        self.document.push(AddMarker(scene.id, marker))
        self.statusBar().showMessage(
            f"Repère « {label} » ajouté. Double-clic dessus dans la règle de la Timeline pour le renommer.",
            5000,
        )
        return marker

    def jump_marker(self, direction: int) -> bool:
        """Place la tête de lecture sur le repère précédent (-1) ou suivant (+1)."""
        scene = self.document.scene
        if scene is None:
            return False
        frames = sorted({m.frame for m in scene.markers})
        f = self.document.frame
        target = (
            next((x for x in frames if x > f), None)
            if direction > 0
            else next((x for x in reversed(frames) if x < f), None)
        )
        if target is None:
            return False
        self.timeline.pause()
        self.document.set_frame(target)
        return True

    def toggle_safe_zones(self, on: bool) -> None:
        self.canvas.show_safe_zones = on
        self.canvas.update()

    # --- projet --------------------------------------------------------------
    def _set_document(self, document: ProjectDocument) -> None:
        old = self.document
        self.document = document
        self.canvas.document = document
        self.layers.document = document
        self.inspector.document = document
        self.timeline.document = document
        self.timeline.view.document = document
        self.timeline.view.waveforms.clear()
        self.narration.document = document
        self.narration.audio.document = document
        self.narration.subtitles.document = document
        document.preview_camera = self.act_camera_view.isChecked()
        self.act_undo.triggered.disconnect()
        self.act_redo.triggered.disconnect()
        self.act_undo.triggered.connect(document.undo.undo)
        self.act_redo.triggered.connect(document.undo.redo)
        for sig_src in (old,):
            try:
                sig_src.changed.disconnect()
                sig_src.frameChanged.disconnect()
                sig_src.selectionChanged.disconnect()
                sig_src.sceneChanged.disconnect()
                sig_src.dirtyChanged.disconnect()
                sig_src.pathChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
        # reconnexions des widgets
        document.changed.connect(self.canvas.update)
        document.frameChanged.connect(lambda _f: self.canvas.update())
        document.selectionChanged.connect(lambda _s: self.canvas.update())
        document.sceneChanged.connect(lambda _s: self.canvas.fit_to_view())
        document.changed.connect(self.layers.schedule_refresh)
        document.sceneChanged.connect(lambda _s: self.layers.schedule_refresh())
        document.selectionChanged.connect(self.layers._sync_selection)
        document.selectionChanged.connect(lambda _s: self.inspector.rebuild())
        document.changed.connect(self.inspector.refresh_values)
        document.frameChanged.connect(lambda _f: self.inspector.refresh_values())
        document.sceneChanged.connect(lambda _s: self.inspector.rebuild())
        tv = self.timeline.view
        document.changed.connect(tv.rebuild_rows)
        document.selectionChanged.connect(lambda _s: tv.rebuild_rows())
        document.sceneChanged.connect(lambda _s: tv.rebuild_rows())
        document.frameChanged.connect(lambda _f: tv.update())
        document.frameChanged.connect(self.timeline._on_frame)
        document.changed.connect(self.timeline._update_scroll)
        document.changed.connect(self.timeline._sync_easing)
        document.sceneChanged.connect(lambda _s: self.timeline._update_scroll())
        document.changed.connect(self.timeline.load_waveforms)
        document.sceneChanged.connect(lambda _s: self.timeline.load_waveforms())
        document.changed.connect(self.narration.audio.refresh)
        document.sceneChanged.connect(lambda _s: self.narration.audio.refresh())
        document.changed.connect(self.narration.subtitles.refresh)
        document.sceneChanged.connect(lambda _s: self.narration.subtitles.refresh())
        self._connect_document()
        self.timeline.pause()
        self.timeline.auto_key.setChecked(False)
        self.layers.refresh()
        self.inspector.rebuild()
        self.narration.audio.refresh()
        self.narration.subtitles.refresh()
        tv.rebuild_rows()
        self.timeline._on_frame(0)
        self.timeline.load_waveforms()
        self.canvas.fit_to_view()
        if document.root is not None:
            self.settings.add_recent(document.root)
            self._fill_recent()

    def maybe_save(self) -> bool:
        """Propose d'enregistrer si nécessaire ; False si l'utilisateur annule."""
        if not self.document.is_dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Modifications non enregistrées",
            f"Le projet « {self.document.title} » a été modifié. Voulez-vous l'enregistrer ?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return answer == QMessageBox.StandardButton.Discard

    def new_project(self) -> None:
        if not self.maybe_save():
            return
        dlg = NewProjectDialog(template_labels(), self)
        if dlg.exec() != NewProjectDialog.DialogCode.Accepted:
            return
        ch = dlg.choice()
        project = create_project(ch.title, ch.canvas, ch.template_id, ch.duration_s)
        self._set_document(ProjectDocument(project))
        self.statusBar().showMessage("Nouveau projet créé. Pensez à l'enregistrer (Ctrl+S).", 5000)

    def open_project(self) -> None:
        if not self.maybe_save():
            return
        path = QFileDialog.getExistingDirectory(
            self, "Ouvrir un projet (dossier .antares)", self.settings.last_directory()
        )
        if path:
            self.open_project_path(Path(path))

    def open_project_path(self, path: Path) -> bool:
        root = resolve_project_root(path)
        try:
            project = self.store.load(root)
        except FileNotFoundError:
            QMessageBox.warning(self, "Ouverture impossible", f"Aucun fichier project.json dans :\n{root}")
            self.settings.remove_recent(root)
            self._fill_recent()
            return False
        except (ProjectFormatError, ProjectValidationError) as exc:
            return self._offer_recovery(root, str(exc))
        document = ProjectDocument(project, root)
        self._set_document(document)
        self.settings.set_last_directory(str(root.parent))
        self._check_newer_autosave(document)
        self.statusBar().showMessage(f"Projet ouvert : {root}", 5000)
        return True

    def _offer_recovery(self, root: Path, error: str) -> bool:
        found = self.store.latest_valid_autosave(root)
        if found is None:
            QMessageBox.critical(
                self,
                "Projet illisible",
                f"Fichier de projet invalide et aucune sauvegarde automatique valide.\n\n{error}\n\n"
                "Le fichier d'origine n'a pas été modifié.",
            )
            return False
        autosave_path, project = found
        answer = QMessageBox.question(
            self,
            "Projet illisible — récupération possible",
            f"Le fichier de projet est invalide :\n{error}\n\nUne sauvegarde automatique valide existe "
            f"({autosave_path.name}). L'ouvrir ? Le fichier d'origine sera conservé dans autosaves/.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        self.store.backup_project_file(root, label="corrompu")
        document = ProjectDocument(project, root)
        self._set_document(document)
        document.undo.clean_index = -1  # forcer l'état « modifié » pour inciter à enregistrer
        document._on_stack_changed()
        return True

    def _check_newer_autosave(self, document: ProjectDocument) -> None:
        if document.paths is None:
            return
        autosaves = self.store.list_autosaves(document.paths.root)
        if not autosaves:
            return
        try:
            if autosaves[0].stat().st_mtime <= document.paths.project_file.stat().st_mtime + 1:
                return
        except OSError:
            return
        found = self.store.latest_valid_autosave(document.paths.root)
        if found is None:
            return
        answer = QMessageBox.question(
            self,
            "Récupération après interruption",
            f"Une sauvegarde automatique plus récente que le projet existe ({found[0].name}).\n"
            "Voulez-vous la restaurer ? (Le projet enregistré reste intact jusqu'au prochain Enregistrer.)",
        )
        if answer == QMessageBox.StandardButton.Yes:
            doc = ProjectDocument(found[1], document.paths.root)
            self._set_document(doc)
            doc.undo.clean_index = -1
            doc._on_stack_changed()

    def save_project(self) -> bool:
        if self.document.paths is None:
            return self.save_project_as()
        try:
            self.document.save()
        except (OSError, ProjectValidationError) as exc:
            QMessageBox.critical(self, "Enregistrement impossible", str(exc))
            return False
        self.statusBar().showMessage("Projet enregistré.", 3000)
        return True

    def save_project_as(self) -> bool:
        suggested = Path(self.settings.last_directory()) / (
            self.document.title.replace("/", "-") + PROJECT_SUFFIX
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le projet sous (un dossier .antares sera créé)",
            str(suggested),
            "Projet ANTARES (*.antares)",
        )
        if not path:
            return False
        root = Path(path)
        if root.suffix != PROJECT_SUFFIX:
            root = root.with_name(root.name + PROJECT_SUFFIX)
        try:
            if root.exists() and any(root.iterdir()) and not (root / "project.json").exists():
                QMessageBox.warning(
                    self, "Dossier non vide", f"{root} existe et n'est pas un projet ANTARES."
                )
                return False
            self.document.save(root)
        except (OSError, ProjectValidationError, FileExistsError) as exc:
            QMessageBox.critical(self, "Enregistrement impossible", str(exc))
            return False
        self.settings.set_last_directory(str(root.parent))
        self.settings.add_recent(root)
        self._fill_recent()
        self.statusBar().showMessage(f"Projet enregistré dans {root}", 4000)
        return True

    def _autosave(self) -> None:
        try:
            path = self.document.autosave()
        except OSError as exc:
            self.statusBar().showMessage(f"Sauvegarde automatique impossible : {exc}", 5000)
            return
        if path is not None:
            self.statusBar().showMessage("Sauvegarde automatique effectuée.", 2000)

    def _fill_recent(self) -> None:
        self.menu_recent.clear()
        recents = self.settings.recent_projects()
        if not recents:
            a = self.menu_recent.addAction("(aucun)")
            a.setEnabled(False)
            return
        for p in recents:
            self.menu_recent.addAction(self._action(str(p), lambda _c=False, path=p: self._open_recent(path)))

    def _open_recent(self, path: Path) -> None:
        if self.maybe_save():
            self.open_project_path(path)

    def export_video(self) -> None:
        self.timeline.pause()
        dlg = ExportDialog(self.document, self.settings, self, queue=self.export_queue)
        dlg.exec()
        if dlg.queued_job is not None:
            self.show_exports()
        if dlg.render_result is not None:
            self._count_export(dlg.render_result)

    def _count_export(self, result: object) -> None:
        self.ui_counters["exports"] += 1
        if isinstance(result, ProjectRenderResult):
            self.ui_counters["full_exports"] += 1

    def _export_job_finished(self, job: ExportJob) -> None:
        self._count_export(job.result)
        self.statusBar().showMessage(f"Export terminé : {job.output_path}", 8000)

    def show_exports(self) -> None:
        self.exports_dock.show()
        self.exports_dock.raise_()

    def quick_preview(self) -> ExportJob | None:
        """Rend la scène courante en 360p en arrière-plan, puis l'ouvre dans le lecteur du système."""
        scene = self.document.scene
        if scene is None:
            return None
        folder = self.document.paths.renders if self.document.paths else Path(tempfile.gettempdir())
        out = folder / f"Aperçu - {scene.name.replace('/', '-').replace(chr(92), '-')}.mp4"
        try:
            audio = audio_plans_for_scene(self.document.project, scene.id, self.document.resolve_asset)
            plan = build_render_plan(self.document.project, scene.id, "preview_360p", str(out), audio=audio)
        except (RenderError, ValueError) as exc:
            QMessageBox.warning(self, "Aperçu rapide", str(exc))
            return None
        if ff.find_ffmpeg(self.settings.ffmpeg_path() or None) is None:
            QMessageBox.warning(
                self,
                "Aperçu rapide",
                "FFmpeg est introuvable : indiquez son emplacement (Aide > Chemin de FFmpeg…).",
            )
            return None
        job = ExportJob.from_document(
            self.document, out.name, out, plan, ffmpeg_path=self.settings.ffmpeg_path(), open_when_done=True
        )
        self.export_queue.submit(job)
        self.show_exports()
        return job

    def export_still(self, path: str | None = None) -> Path | None:
        """Enregistre l'image courante en PNG, à la résolution du projet (caméra et transition comprises)."""
        scene = self.document.scene
        if scene is None:
            return None
        if path is None:
            folder = (
                self.document.paths.renders if self.document.paths else Path(self.settings.last_directory())
            )
            default = folder / f"{scene.name} - image {self.document.frame}.png"
            path, _ = QFileDialog.getSaveFileName(self, "Exporter l'image", str(default), "Image PNG (*.png)")
            if not path:
                return None
        target = Path(path if path.lower().endswith(".png") else path + ".png")
        c = self.document.project.canvas
        renderer = FrameRenderer(self.document.project, self.document.resolve_asset, ImageCache())
        image = renderer.render(scene.id, self.document.frame, c.width, c.height)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not image.save(str(target)):  # format déduit de l'extension .png
            QMessageBox.warning(self, "Exporter l'image", f"Impossible d'écrire {target}.")
            return None
        self.statusBar().showMessage(f"Image enregistrée : {target}", 6000)
        return target

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self.maybe_save():
            event.ignore()
            return
        if self.export_queue.pending():
            answer = QMessageBox.question(
                self,
                "Exports en cours",
                f"{len(self.export_queue.pending())} export(s) non terminé(s). Les annuler et quitter ?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.export_queue.wait_idle()
        self.timeline.pause()
        self.settings.save_window(self.saveGeometry(), self.saveState())
        super().closeEvent(event)

    # --- objets ---------------------------------------------------------------
    def add_node_of_kind(self, kind: str, at: QPointF | None = None) -> Node | None:
        scene = self.document.scene
        if scene is None:
            return None
        spec = spec_for(kind)
        c = self.document.project.canvas
        if kind == "camera":  # cadre initial = image entière : rien ne change tant qu'on ne l'anime pas
            at = QPointF(c.width / 2, c.height / 2)
            if any(n.kind == "camera" for n in scene.nodes):
                self.statusBar().showMessage(
                    "Cette scène a déjà une caméra : seule la première caméra visible filme.", 6000
                )
        center = at or self.canvas.visible_center_canvas()
        x = max(0.0, min(float(c.width), center.x()))
        y = max(0.0, min(float(c.height), center.y()))
        count = sum(1 for n in scene.nodes if n.kind == kind) + 1
        node = Node.create(
            kind,
            f"{spec.label} {count}",
            position=[x, y],
            style=spec.default_style(),
            params=spec.default_params(),
        )
        if kind == "text":
            node.params["text"] = "Votre texte"
        self.document.push(AddNode(scene.id, node))
        self.document.set_selection([node.id])
        return node

    def import_image(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
        if self.document.paths is None:
            QMessageBox.information(
                self,
                "Importer une image",
                "Enregistrez d'abord le projet : l'image sera copiée dans son dossier assets/.",
            )
            if not self.save_project_as():
                return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer une image",
            self.settings.last_directory(),
            "Images (*.png *.jpg *.jpeg *.svg *.bmp *.webp)",
        )
        if not path:
            return
        from antares_studio.resources.assets import import_asset

        try:
            asset = import_asset(self.document, Path(path), kind="image")
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Import impossible", str(exc))
            return
        node = self.add_node_of_kind("image")
        if node is not None:
            self.document.push(
                SetProperties(scene.id, node.id, {"params.asset_id": asset.id, "name": Path(path).stem})
            )
        edit_asset_provenance(self.document, asset, self)

    def import_data(self) -> None:
        """Importe un CSV (unités dans l'en-tête) et ajoute un graphique sur ses deux premières colonnes."""
        scene = self.document.scene
        if scene is None:
            return
        if self.document.paths is None:
            QMessageBox.information(
                self,
                "Importer des données",
                "Enregistrez d'abord le projet : le CSV sera copié dans assets/.",
            )
            if not self.save_project_as():
                return
        path, _ = QFileDialog.getOpenFileName(
            self, "Importer des données", self.settings.last_directory(), "Données (*.csv *.tsv *.txt)"
        )
        if not path:
            return
        node = self.add_chart_from_csv(Path(path))
        if node is not None:
            asset = self.document.project.asset(str(node.params["data_asset_id"]))
            if asset is not None:
                edit_asset_provenance(self.document, asset, self)

    def add_blender_planet(self) -> None:
        """Rend une planète en rotation avec Blender (s'il est installé) et l'insère en séquence d'images."""
        from antares_studio.app.blender_dialog import BlenderPlanetDialog

        if self.document.scene is None:
            return
        if self.document.paths is None:
            QMessageBox.information(
                self, "Planète 3D", "Enregistrez d'abord le projet : la séquence est rendue dans assets/."
            )
            if not self.save_project_as():
                return
        BlenderPlanetDialog(self.document, self).exec()

    def add_chart_from_csv(self, path: Path) -> Node | None:
        from antares_studio.resources.assets import import_asset
        from antares_studio.science.data import load_csv

        scene = self.document.scene
        if scene is None:
            return None
        try:
            asset = import_asset(self.document, path, kind="data")
            table = load_csv(path)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Import impossible", str(exc))
            return None
        numeric = [c.name for c in table.columns if c.finite()]
        x_name = numeric[0]
        y_name = numeric[1] if len(numeric) > 1 else numeric[0]
        node = self.add_node_of_kind("chart")
        if node is not None:
            self.document.push(
                SetProperties(
                    scene.id,
                    node.id,
                    {
                        "params.data_asset_id": asset.id,
                        "params.x_column": x_name,
                        "params.y_column": y_name,
                        "params.title": path.stem,
                        "name": f"Graphique {path.stem}",
                    },
                )
            )
            if table.diagnostics:
                self.statusBar().showMessage("CSV : " + " ; ".join(table.diagnostics), 8000)
        return node

    def edit_asset_provenance(self, asset_id: str) -> None:
        asset = self.document.project.asset(asset_id)
        if asset is not None:
            edit_asset_provenance(self.document, asset, self)

    def _refresh_inventory(self) -> None:
        self.library.set_inventory(inventory(self.document.project))

    def show_inventory(self) -> None:
        self.ui_counters["inventory_opened"] += 1
        LicenseInventoryDialog(self.document, self).exec()

    def add_scale_warning(self) -> Node | None:
        """Ajoute l'encadré « non à l'échelle » (SCI-07) et marque le projet comme schématique."""
        scene = self.document.scene
        if scene is None:
            return None
        node = scale_warning_node(self.document.project.canvas)
        self.document.push(AddNode(scene.id, node))
        if self.document.project.scientific_metadata.get("to_scale") is not False:
            self.document.push(SetProjectMetadata("to_scale", False))
        self.document.set_selection([node.id])
        return node

    def delete_selection(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
        with self.document.macro("Supprimer la sélection"):
            for nid in self.document.selection:
                if scene.find_node(nid) is not None:
                    self.document.push(RemoveNode(scene.id, nid))
            self.document.set_selection([])

    def duplicate_selection(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
        with self.document.macro("Dupliquer"):
            new_ids = []
            for nid in self.document.selection:
                node = scene.find_node(nid)
                if node is None:
                    continue
                clone = copy.deepcopy(node)
                clone.id = new_id("node")
                clone.name = node.name + " (copie)"
                clone.position = [node.position[0] + 20, node.position[1] + 20]
                self.document.push(AddNode(scene.id, clone))
                tracks = [copy.deepcopy(t) for t in scene.tracks_for(nid)]
                for t in tracks:
                    t.target_id = clone.id
                if tracks:
                    self.document.push(
                        ReplaceTracks(scene.id, clone.id, tracks, label="Dupliquer l'animation")
                    )
                new_ids.append(clone.id)
            self.document.set_selection(new_ids)

    # --- presse-papiers ----------------------------------------------------------
    def _on_clipboard_changed(self) -> None:
        self._paste_count = 0

    def copy_selection(self) -> bool:
        scene = self.document.scene
        if scene is None or not self.document.selection:
            return False
        data = copy_nodes(
            self.document.project,
            scene,
            self.document.selection,
            str(self.document.root) if self.document.root else None,
        )
        mime = QMimeData()
        mime.setData(CLIPBOARD_MIME, json.dumps(data, ensure_ascii=False).encode("utf-8"))
        QApplication.clipboard().setMimeData(mime)
        self._paste_count = 0
        n = len(data["nodes"])
        self.statusBar().showMessage(f"{n} objet{'s' if n > 1 else ''} copié{'s' if n > 1 else ''}.", 3000)
        return True

    def cut_selection(self) -> None:
        if self.copy_selection():
            with self.document.macro("Couper"):
                self.delete_selection()

    def paste(self) -> list[str]:
        """Colle les objets du presse-papiers dans la scène courante ; retourne les racines collées."""
        scene = self.document.scene
        mime = QApplication.clipboard().mimeData()
        if scene is None or mime is None or not mime.hasFormat(CLIPBOARD_MIME):
            self.statusBar().showMessage("Le presse-papiers ne contient pas d'objets ANTARES Studio.", 4000)
            return []
        self._paste_count += 1
        step = 20.0 * self._paste_count
        try:
            raw = json.loads(bytes(mime.data(CLIPBOARD_MIME).data()).decode("utf-8"))
            payload = read_payload(raw, self.document.project, offset=(step, step))
        except (ValueError, UnicodeDecodeError) as exc:
            QMessageBox.warning(self, "Coller", f"Collage impossible : {exc}")
            return []
        warnings = list(payload.warnings)
        remap_assets(payload, self._paste_assets(payload, warnings))
        with self.document.macro("Coller"):
            for node in payload.nodes:
                self.document.push(AddNode(scene.id, node))
            for node in payload.nodes:
                tracks = [t for t in payload.tracks if t.target_id == node.id]
                if tracks:
                    self.document.push(ReplaceTracks(scene.id, node.id, tracks, label="Coller l'animation"))
        roots = [n.id for n in payload.nodes if n.parent_id is None]
        self.document.set_selection(roots)
        n = len(payload.nodes)
        msg = f"{n} objet{'s' if n > 1 else ''} collé{'s' if n > 1 else ''}."
        self.statusBar().showMessage(msg + (" " + " ; ".join(warnings) if warnings else ""), 8000)
        return roots

    def _paste_assets(self, payload: PastePayload, warnings: list[str]) -> dict[str, str]:
        """Ressources d'un autre projet : réutilise un fichier identique, sinon le recopie dans celui-ci."""
        from antares_studio.persistence.paths import UnsafePathError, resolve_under
        from antares_studio.resources.assets import import_asset

        project = self.document.project
        mapping: dict[str, str] = {}
        for asset in payload.assets:
            mine = project.asset(asset.id)
            if mine is not None and (payload.same_project or mine.sha256 == asset.sha256):
                continue
            twin = next((a for a in project.assets if asset.sha256 and a.sha256 == asset.sha256), None)
            if twin is not None:
                mapping[asset.id] = twin.id
                continue
            source = None
            if payload.root_path and asset.kind in ("image", "data", "audio"):
                try:
                    source = resolve_under(Path(payload.root_path), asset.path)
                except UnsafePathError:
                    source = None
            if source is None or not source.is_file():
                mapping[asset.id] = ""
                warnings.append(f"ressource introuvable, référence retirée : {asset.path}")
                continue
            if self.document.paths is None:
                QMessageBox.information(
                    self, "Coller", "Enregistrez d'abord le projet : les ressources collées y seront copiées."
                )
                if not self.save_project_as():
                    mapping[asset.id] = ""
                    warnings.append(f"projet non enregistré, ressource non copiée : {asset.path}")
                    continue
            try:
                new = import_asset(self.document, source, kind=asset.kind)
            except (OSError, ValueError) as exc:
                mapping[asset.id] = ""
                warnings.append(f"copie impossible de {asset.path} : {exc}")
                continue
            mapping[asset.id] = new.id
            if asset.license != new.license:
                self.document.push(SetAssetLicense(new.id, copy.deepcopy(asset.license)))
        return mapping

    # --- aligner et répartir ------------------------------------------------------
    def _movable_rects(self) -> list[tuple[Node, tuple[float, float, float, float]]]:
        """Objets sélectionnés déplaçables (non verrouillés, sans ancêtre aussi sélectionné) et leur boîte."""
        scene = self.document.scene
        state = self.document.state()
        if scene is None or state is None:
            return []
        sel = set(self.document.selection)
        out = []
        for node in self.document.selected_nodes:
            if node.locked:
                continue
            parent, nested = node.parent_id, False
            while parent is not None:
                if parent in sel:
                    nested = True
                    break
                p = scene.find_node(parent)
                parent = p.parent_id if p else None
            if not nested:
                out.append((node, self.canvas.node_rect(state.node(node.id))))
        return out

    def _move_by(self, items: list[tuple[Node, tuple[float, float]]], label: str) -> None:
        state = self.document.state()
        if state is None:
            return
        with self.document.macro(label):
            for node, (dx, dy) in items:
                if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                    continue
                local = self.canvas._parent_inverse_linear(node.id).map(QPointF(dx, dy))
                st = state.node(node.id)
                self.document.set_node_properties(
                    node.id,
                    {"position.x": st.position[0] + local.x(), "position.y": st.position[1] + local.y()},
                )

    def align_selection(self, mode: str) -> None:
        """Aligne la sélection sur sa boîte englobante ; un objet seul s'aligne sur le canevas."""
        items = self._movable_rects()
        if not items:
            return
        c = self.document.project.canvas
        ref = (0.0, 0.0, float(c.width), float(c.height)) if len(items) == 1 else None
        deltas = align_deltas([r for _n, r in items], mode, ref)
        self._move_by([(n, d) for (n, _r), d in zip(items, deltas, strict=True)], ALIGN_MODES[mode])

    def distribute_selection(self, axis: str) -> None:
        items = self._movable_rects()
        if len(items) < 3:
            self.statusBar().showMessage("Répartir : sélectionnez au moins trois objets.", 4000)
            return
        deltas = distribute_deltas([r for _n, r in items], axis)
        label = "Répartir horizontalement" if axis == "x" else "Répartir verticalement"
        self._move_by([(n, d) for (n, _r), d in zip(items, deltas, strict=True)], label)

    def select_all(self) -> None:
        scene = self.document.scene
        if scene is not None:
            self.document.set_selection([n.id for n in scene.nodes if not n.locked])

    def group_selection(self) -> None:
        scene = self.document.scene
        sel = self.document.selected_nodes
        if scene is None or not sel:
            return
        with self.document.macro("Grouper"):
            xs = [n.position[0] for n in sel]
            ys = [n.position[1] for n in sel]
            gx, gy = sum(xs) / len(xs), sum(ys) / len(ys)
            group = Node.create("group", "Groupe", position=[gx, gy])
            self.document.push(AddNode(scene.id, group, index=min(scene.nodes.index(n) for n in sel)))
            for n in sel:
                if n.parent_id is None:
                    self.document.push(
                        SetProperties(
                            scene.id,
                            n.id,
                            {
                                "parent_id": group.id,
                                "position.x": n.position[0] - gx,
                                "position.y": n.position[1] - gy,
                            },
                            label="Grouper",
                        )
                    )
            self.document.set_selection([group.id])

    def ungroup_selection(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
        with self.document.macro("Dégrouper"):
            for g in [n for n in self.document.selected_nodes if n.kind == "group"]:
                for child in scene.children_of(g.id):
                    self.document.push(
                        SetProperties(
                            scene.id,
                            child.id,
                            {
                                "parent_id": g.parent_id,
                                "position.x": child.position[0] + g.position[0],
                                "position.y": child.position[1] + g.position[1],
                            },
                            label="Dégrouper",
                        )
                    )
                self.document.push(RemoveNode(scene.id, g.id))
            self.document.set_selection([])

    def _edit_text_inline(self, node_id: str) -> None:
        scene = self.document.scene
        if scene is None:
            return
        node = scene.find_node(node_id)
        if node is None or node.kind not in ("text", "callout", "formula"):
            return
        title, label = (
            ("Modifier la formule", "Formule (voir Aide > Centre d'aide, rubrique Équations) :")
            if node.kind == "formula"
            else ("Modifier le texte", "Texte :")
        )
        text, ok = QInputDialog.getMultiLineText(self, title, label, str(node.params.get("text", "")))
        if ok:
            self.document.set_node_property(node.id, "params.text", text)

    # --- animations ------------------------------------------------------------
    def apply_preset_to_selection(self, preset_id: str) -> None:
        scene = self.document.scene
        sel = self.document.selected_nodes
        if scene is None or not sel:
            QMessageBox.information(
                self, "Animation", "Sélectionnez d'abord un objet sur le canevas ou dans la liste."
            )
            return
        dlg = PresetDialog(preset_id, self.document, sel[0], self)
        if dlg.exec() != PresetDialog.DialogCode.Accepted:
            return
        params = dlg.values()
        for node in sel:
            try:
                tracks = apply_preset(preset_id, node, params)
            except ValueError as exc:
                QMessageBox.warning(self, "Animation", str(exc))
                return
            existing = [
                t for t in scene.tracks_for(node.id) if t.property not in {t2.property for t2 in tracks}
            ]
            self.document.push(
                ReplaceTracks(scene.id, node.id, existing + tracks, label=f"Animation : {preset_id}")
            )

    def add_template_scene(self, template_id: str) -> None:
        if template_id not in TEMPLATES:
            return
        label, builder = TEMPLATES[template_id]
        fps = float(self.document.project.canvas.fps)
        scene = Scene.create(label.split(" (")[0], duration_frames=int(round(20 * fps)))
        builder(self.document.project, scene)
        self.document.push(AddScene(scene))
        self.document.set_scene(scene.id)

    # --- apparence ----------------------------------------------------------------
    def _apply_icons(self) -> None:
        for name, icon_name in ACTION_ICONS.items():
            getattr(self, name).setIcon(icons.icon(icon_name))
        for mode, icon_name in ALIGN_ICONS.items():
            self.align_actions[mode].setIcon(icons.icon(icon_name))
        self.menu_tutorials.menuAction().setIcon(icons.icon("graduation-cap"))
        self.timeline.restyle()
        self.library.refresh_icons()

    def set_theme(self, name: str) -> None:
        app = QApplication.instance()
        if not isinstance(app, QApplication) or name not in theme.THEMES:
            return
        theme.apply_theme(app, name, theme.font_scale())
        self.settings.set_theme(name)
        self._restyle()

    def set_font_scale(self, percent: int) -> None:
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        theme.apply_theme(app, theme.active().name, percent)
        self.settings.set_font_scale(percent)
        self._restyle()

    def _restyle(self) -> None:
        icons.clear_cache()
        self._apply_icons()
        for n, act in self.theme_actions.items():
            act.setChecked(n == theme.active().name)
        for pct, act in self.scale_actions.items():
            act.setChecked(pct == theme.font_scale())
        self.inspector.rebuild()
        self.tutorial.restyle()
        self.canvas.update()
        self.timeline.view.update()
        if self.help_center is not None:
            self.help_center.restyle()

    def _set_whats_this(self) -> None:
        texts = {
            self.canvas: "Canevas : l'image de la scène, identique à la vidéo exportée. Clic pour "
            "sélectionner, glisser pour déplacer, molette pour zoomer. F1 : aide détaillée.",
            self.library: "Bibliothèque : objets, animations, modèles et ressources. Double-clic pour "
            "ajouter ou appliquer ; cochez une case pour marquer un favori.",
            self.layers: "Scènes et objets : liste des scènes, puis des objets de la scène (œil : visible, "
            "cadenas : verrouillé, double-clic : renommer).",
            self.inspector: "Inspecteur : propriétés de la sélection. Le losange ◆ pose une image clé à "
            "l'image courante. Sans sélection : scène et métadonnées scientifiques.",
            self.timeline: "Timeline : tête de lecture, images clés (losanges), pistes audio et sous-titres. "
            "Ctrl + molette : zoom temporel.",
            self.narration: "Narration : clips audio (début, gain, fondus) et sous-titres (SRT/VTT, "
            "contrôles de lisibilité).",
            self.tutorial: "Tutoriel : chaque étape se valide toute seule quand l'action est faite.",
        }
        for widget, text in texts.items():
            widget.setWhatsThis(text)

    # --- aide ---------------------------------------------------------------------
    def _shortcuts_markdown(self) -> str:
        from antares_studio.app.command_palette import menu_actions

        rows = ["| Commande | Raccourci |", "|---|---|"]
        for path, act in menu_actions(self.menuBar()):
            keys = ", ".join(
                k.toString(QKeySequence.SequenceFormat.NativeText) for k in act.shortcuts() if not k.isEmpty()
            )
            if keys:
                rows.append(f"| {path} | {keys} |")
        return "\n".join(rows)

    def help_extra(self) -> dict[str, str]:
        return {"raccourcis": self._shortcuts_markdown()}

    def show_help(self, topic_id: str = "") -> HelpCenter:
        if self.help_center is None:
            self.help_center = HelpCenter(self.help_extra, self)
        self.ui_counters["help_opened"] += 1
        self.help_center.show_topic(topic_id or self.help_center.current_topic or topics.DEFAULT_TOPIC)
        self.help_center.show()
        self.help_center.raise_()
        self.help_center.activateWindow()
        return self.help_center

    def context_topic(self) -> str:
        """Rubrique liée au panneau qui a le focus (F1), ou la page d'accueil de l'aide."""
        w = QApplication.focusWidget()
        while w is not None:
            name = w.objectName()
            if name == "dock_narration" and self.narration.tabs.currentWidget() is self.narration.subtitles:
                return "sous-titres"
            if name in CONTEXT_TOPICS:
                return CONTEXT_TOPICS[name]
            w = w.parentWidget()
        return topics.DEFAULT_TOPIC

    def show_context_help(self) -> None:
        self.show_help(self.context_topic())

    def show_command_palette(self) -> None:
        self.ui_counters["palette_used"] += 1
        dlg = CommandPalette(self.menuBar(), self)
        if dlg.exec() and dlg.triggered is not None:
            dlg.triggered.trigger()

    def show_welcome(self) -> None:
        from antares_studio.app.welcome import WelcomeDialog
        from antares_studio.rendering.ffmpeg import find_ffmpeg

        dlg = WelcomeDialog(
            self.settings.recent_projects(),
            self.settings.tutorials_done(),
            find_ffmpeg(self.settings.ffmpeg_path() or None) is not None,
            self.settings.show_welcome(),
            self,
        )
        dlg.exec()
        self.settings.set_show_welcome(dlg.show_at_startup.isChecked())
        if dlg.choice is None:
            return
        kind, arg = dlg.choice
        if kind == "new":
            self.new_project()
        elif kind == "open":
            self.open_project()
        elif kind == "recent":
            self._open_recent(Path(arg))
        elif kind == "template":
            self.new_project_from_template(arg)
        elif kind == "tutorial":
            self.start_tutorial(arg)
        elif kind == "help":
            self.show_help()

    def new_project_from_template(self, template_id: str) -> bool:
        """Nouveau projet 16:9, 1080p, 30 images/s, 20 s à partir d'un modèle (accueil)."""
        if template_id not in TEMPLATES or not self.maybe_save():
            return False
        title = TEMPLATES[template_id][0].split(" (")[0]
        self._set_document(ProjectDocument(create_project(title, Canvas(), template_id, 20)))
        self.statusBar().showMessage(f"Projet « {title} » créé. Pensez à l'enregistrer (Ctrl+S).", 6000)
        return True

    # --- tutoriels ----------------------------------------------------------------
    def _fill_tutorials_menu(self) -> None:
        self.menu_tutorials.clear()
        done = self.settings.tutorials_done()
        for t in TUTORIALS:
            label = ("✓ " if t.id in done else "") + f"{t.title} ({t.minutes} min)"
            act = self.menu_tutorials.addAction(label)
            act.setStatusTip(t.summary)
            act.triggered.connect(lambda _c=False, tid=t.id: self.start_tutorial(tid))
        self.menu_tutorials.addSeparator()
        self.menu_tutorials.addAction("À propos des tutoriels…").triggered.connect(
            lambda: self.show_help("tutoriels")
        )

    def tutorial_context(self) -> TutorialContext:
        """État observé par les tutoriels : copie du projet (pour comparer avant/après) et de l'interface."""
        d = self.document
        return TutorialContext(
            project=copy.deepcopy(d.project),
            scene_id=d.scene_id,
            selection=tuple(d.selection),
            frame=d.frame,
            saved=d.root is not None and not d.is_dirty,
            has_folder=d.root is not None,
            ui={
                "library_query": self.library.search.text(),
                "zoom": self.canvas.zoom,
                "playing": self.timeline.playing,
                "auto_key": d.auto_key,
                "safe_zones": self.act_safe.isChecked(),
                "grid": self.act_grid.isChecked(),
                **self.ui_counters,
            },
        )

    def start_tutorial(self, tutorial_id: str) -> bool:
        tut = TUTORIALS_BY_ID.get(tutorial_id)
        if tut is None:
            return False
        if tut.setup_template is not None:
            if not self.maybe_save():
                return False
            project = create_project(f"Tutoriel — {tut.title[3:]}", Canvas(), tut.setup_template, 20)
            self._set_document(ProjectDocument(project))
        self.tutorial_dock.show()
        self.tutorial_dock.raise_()
        # sous l'Inspecteur : une hauteur de lecture confortable (le dock s'ouvre sinon écrasé)
        column = max(400, self.inspector_dock.height() + self.tutorial_dock.height())
        sizes = [column * 9 // 20, column * 11 // 20]
        self.resizeDocks([self.inspector_dock, self.tutorial_dock], sizes, Qt.Orientation.Vertical)
        self.tutorial.start(tut)
        self._tutorial_timer.start()
        return True

    def _tutorial_finished(self, tutorial_id: str) -> None:
        self.settings.mark_tutorial_done(tutorial_id)
        self._fill_tutorials_menu()
        tut = TUTORIALS_BY_ID.get(tutorial_id)
        self.statusBar().showMessage(f"Tutoriel terminé : {tut.title if tut else tutorial_id}. Bravo !", 8000)

    def _tutorial_closed(self) -> None:
        self._tutorial_timer.stop()
        self.tutorial_dock.hide()

    def _tutorial_action(self, action: str) -> None:
        if action == "import_example_csv":
            self.import_example_data()
        elif action == "open_help":
            run = self.tutorial.run
            self.show_help(run.tutorial.help_topic if run else "")

    def import_example_data(self) -> Node | None:
        """Importe le CSV d'exemple (NASA) en graphique, avec sa provenance déjà renseignée."""
        if self.document.scene is None:
            return None
        if self.document.paths is None:
            QMessageBox.information(
                self, "Données d'exemple", "Enregistrez d'abord le projet : le CSV sera copié dans assets/."
            )
            if not self.save_project_as():
                return None
        node = self.add_chart_from_csv(topics.EXAMPLES_DIR / EXAMPLE_CSV)
        if node is None:
            return None
        asset_id = str(node.params.get("data_asset_id", ""))
        scene = self.document.scene
        if scene is not None:
            current = scene.find_node(node.id)
            asset_id = str(current.params.get("data_asset_id", "")) if current else asset_id
        asset = self.document.project.asset(asset_id)
        if asset is not None:
            self.document.push(
                SetAssetLicense(
                    asset.id,
                    AssetLicense(
                        author="NASA NSSDCA (D. R. Williams), Planetary Fact Sheet",
                        source_url="https://nssdc.gsfc.nasa.gov/planetary/factsheet/",
                        license="public-domain",
                        attribution_required=False,
                        redistribution_allowed=True,
                        verified_on="2026-10-22",
                    ),
                )
            )
            edit_asset_provenance(self.document, asset, self)
        return node

    def reveal_widget(self, widget: QWidget) -> None:
        """Rend visible un widget : affiche son panneau et sélectionne les onglets qui le contiennent."""
        w: QWidget | None = widget
        while w is not None:
            parent = w.parentWidget()
            if isinstance(parent, QStackedWidget) and isinstance(parent.parentWidget(), QTabWidget):
                tabs = parent.parentWidget()
                assert isinstance(tabs, QTabWidget)
                tabs.setCurrentWidget(w)
            if isinstance(w, QDockWidget):
                w.show()
                w.raise_()
            w = parent

    def highlight_widget(self, object_name: str) -> Highlighter | None:
        target = self.findChild(QWidget, object_name)
        if target is None:
            return None
        self.reveal_widget(target)
        return Highlighter(target, self)

    def show_diagnostics(self) -> None:
        DiagnosticsDialog(diagnostics_report(self.settings.ffmpeg_path()), self).exec()

    def configure_ffmpeg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner l'exécutable FFmpeg", self.settings.ffmpeg_path() or ""
        )
        if path:
            self.settings.set_ffmpeg_path(path)
            self.statusBar().showMessage(f"FFmpeg : {path}", 4000)

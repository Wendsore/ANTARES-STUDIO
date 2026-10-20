"""Fenêtre principale : menus en français, docks, actions fichier/édition, autosave et récupération."""

from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
    QWidget,
)

from antares_studio.app.canvas_widget import CanvasWidget
from antares_studio.app.diagnostics import diagnostics_report
from antares_studio.app.dialogs import AboutDialog, DiagnosticsDialog, NewProjectDialog
from antares_studio.app.document import ProjectDocument
from antares_studio.app.export_dialog import ExportDialog
from antares_studio.app.inspector_dock import InspectorDock
from antares_studio.app.layers_dock import LayersDock
from antares_studio.app.library_dock import LibraryDock
from antares_studio.app.narration_dock import NarrationDock
from antares_studio.app.preset_dialog import PresetDialog
from antares_studio.app.provenance_dialog import LicenseInventoryDialog, edit_asset_provenance
from antares_studio.app.settings import AppSettings
from antares_studio.app.timeline_dock import TimelineDock
from antares_studio.domain.commands import (
    AddNode,
    AddScene,
    RemoveNode,
    ReplaceTracks,
    SetProjectMetadata,
    SetProperties,
)
from antares_studio.domain.ids import new_id
from antares_studio.domain.kinds import spec_for
from antares_studio.domain.model import Canvas, Node, Scene
from antares_studio.domain.validation import ProjectValidationError
from antares_studio.persistence.schema import ProjectFormatError
from antares_studio.persistence.store import PROJECT_SUFFIX, ProjectStore, resolve_project_root
from antares_studio.resources.licenses import inventory
from antares_studio.resources.templates import TEMPLATES, create_project, scale_warning_node, template_labels
from antares_studio.timeline.presets import apply_preset


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = AppSettings()
        self.store = ProjectStore()
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
        self.act_save_as = self._action(
            "Enregistrer &sous…", self.save_project_as, QKeySequence.StandardKey.SaveAs
        )
        self.act_export = self._action("E&xporter la vidéo…", self.export_video, "Ctrl+E")
        self.act_inventory = self._action("Inventaire des &licences et crédits…", self.show_inventory)
        self.act_scale_warning = self._action(
            "Avertissement d'é&chelle (« non à l'échelle »)", self.add_scale_warning
        )
        self.act_quit = self._action("&Quitter", self.close, QKeySequence.StandardKey.Quit)
        self.act_undo = self._action("&Annuler", self.document.undo.undo, QKeySequence.StandardKey.Undo)
        self.act_redo = self._action("&Rétablir", self.document.undo.redo, QKeySequence.StandardKey.Redo)
        self.act_delete = self._action("&Supprimer", self.delete_selection, QKeySequence.StandardKey.Delete)
        self.act_duplicate = self._action("&Dupliquer", self.duplicate_selection, "Ctrl+D")
        self.act_select_all = self._action(
            "&Tout sélectionner", self.select_all, QKeySequence.StandardKey.SelectAll
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
        self.act_safe = self._action("Zones &sûres (sous-titres)", self.toggle_safe_zones)
        self.act_safe.setCheckable(True)
        self.act_reset_layout = self._action("Réinitialiser la disposition", self.reset_layout)
        self.act_about = self._action("À &propos d'ANTARES Studio", lambda: AboutDialog(self).exec())
        self.act_diag = self._action("&Diagnostics…", self.show_diagnostics)
        self.act_ffmpeg = self._action("Chemin de &FFmpeg…", self.configure_ffmpeg)
        for act in (
            self.act_play,
            self.act_frame_prev,
            self.act_frame_next,
            self.act_go_start,
            self.act_go_end,
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
        m_file.addAction(self.act_export)
        m_file.addAction(self.act_inventory)
        m_file.addSeparator()
        m_file.addAction(self.act_quit)
        m_edit = mb.addMenu("&Édition")
        for a in (self.act_undo, self.act_redo):
            m_edit.addAction(a)
        m_edit.addSeparator()
        for a in (self.act_select_all, self.act_duplicate, self.act_delete):
            m_edit.addAction(a)
        m_edit.addSeparator()
        for a in (self.act_group, self.act_ungroup):
            m_edit.addAction(a)
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
        ):
            spec = spec_for(kind)
            m_add.addAction(self._action(spec.label, lambda _c=False, k=kind: self.add_node_of_kind(k)))
        m_add.addSeparator()
        m_add.addAction(self.act_scale_warning)
        m_add.addAction(self._action("Importer une &image…", self.import_image, "Ctrl+I"))
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
        for a in (self.act_grid, self.act_snap, self.act_safe):
            m_view.addAction(a)
        m_view.addSeparator()
        for dock in self._all_docks():
            m_view.addAction(dock.toggleViewAction())
        m_view.addSeparator()
        m_view.addAction(self.act_reset_layout)
        m_help = mb.addMenu("&Aide")
        m_help.addAction(self.act_diag)
        m_help.addAction(self.act_ffmpeg)
        m_help.addSeparator()
        m_help.addAction(self.act_about)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Principal", self)
        tb.setObjectName("toolbar_main")
        tb.setMovable(False)
        for a in (self.act_new, self.act_open, self.act_save, self.act_export):
            tb.addAction(a)
        tb.addSeparator()
        for a in (self.act_undo, self.act_redo):
            tb.addAction(a)
        tb.addSeparator()
        for a in (self.act_zoom_fit, self.act_grid):
            tb.addAction(a)
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
        for a in (self.act_delete, self.act_duplicate, self.act_group):
            a.setEnabled(has_sel)
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
        self.timeline_dock.raise_()
        self.resize(1400, 860)
        self.canvas.fit_to_view()

    def toggle_grid(self, on: bool) -> None:
        self.canvas.show_grid = on
        self.canvas.update()

    def toggle_snap(self, on: bool) -> None:
        self.canvas.snap_to_grid = on

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
        dlg = ExportDialog(self.document, self.settings, self)
        dlg.exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self.maybe_save():
            event.ignore()
            return
        self.timeline.pause()
        self.settings.save_window(self.saveGeometry(), self.saveState())
        super().closeEvent(event)

    # --- objets ---------------------------------------------------------------
    def add_node_of_kind(self, kind: str, at: QPointF | None = None) -> Node | None:
        scene = self.document.scene
        if scene is None:
            return None
        spec = spec_for(kind)
        center = at or self.canvas.visible_center_canvas()
        c = self.document.project.canvas
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

    def edit_asset_provenance(self, asset_id: str) -> None:
        asset = self.document.project.asset(asset_id)
        if asset is not None:
            edit_asset_provenance(self.document, asset, self)

    def _refresh_inventory(self) -> None:
        self.library.set_inventory(inventory(self.document.project))

    def show_inventory(self) -> None:
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
        for nid in self.document.selection:
            if scene.find_node(nid) is not None:
                self.document.push(RemoveNode(scene.id, nid))
        self.document.set_selection([])

    def duplicate_selection(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
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
                self.document.push(ReplaceTracks(scene.id, clone.id, tracks, label="Dupliquer l'animation"))
            new_ids.append(clone.id)
        self.document.set_selection(new_ids)

    def select_all(self) -> None:
        scene = self.document.scene
        if scene is not None:
            self.document.set_selection([n.id for n in scene.nodes if not n.locked])

    def group_selection(self) -> None:
        scene = self.document.scene
        sel = self.document.selected_nodes
        if scene is None or not sel:
            return
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
        if node is None or node.kind != "text":
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "Modifier le texte", "Texte :", str(node.params.get("text", ""))
        )
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

    # --- aide ---------------------------------------------------------------------
    def show_diagnostics(self) -> None:
        DiagnosticsDialog(diagnostics_report(self.settings.ffmpeg_path()), self).exec()

    def configure_ffmpeg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner l'exécutable FFmpeg", self.settings.ffmpeg_path() or ""
        )
        if path:
            self.settings.set_ffmpeg_path(path)
            self.statusBar().showMessage(f"FFmpeg : {path}", 4000)

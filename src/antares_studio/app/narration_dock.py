"""Panneau Narration : pistes audio (import, décalage, gain, fondus) et sous-titres (SRT/VTT, diagnostics)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app.document import ProjectDocument
from antares_studio.app.settings import AppSettings
from antares_studio.audio.subtitles import (
    SubtitleFormatError,
    check_subtitles,
    format_srt,
    format_vtt,
    parse_subtitles,
)
from antares_studio.domain.commands import (
    AddAudioClip,
    AddSubtitle,
    RemoveAudioClip,
    RemoveSubtitle,
    ReplaceSubtitles,
    SetAudioClipAttr,
    SetSubtitleAttr,
)
from antares_studio.domain.model import Asset, AudioClip, Subtitle
from antares_studio.rendering import ffmpeg as ff

ID_ROLE = Qt.ItemDataRole.UserRole + 1


class AudioTab(QWidget):
    COLS = ("Nom", "Début (s)", "Gain", "Fondu entrée (s)", "Fondu sortie (s)", "Muet", "Durée (s)")

    def __init__(self, document: ProjectDocument, settings: AppSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self.provenance_prompt: Callable[[Asset], object] | None = None  # posé par la fenêtre principale
        self.document = document
        self.settings = settings
        self._updating = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        hint = QLabel(
            "Importez une narration (WAV/MP3) : elle est copiée dans le dossier audio/ du projet et placée "
            "à l'image courante. L'original n'est jamais modifié."
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "hint")
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        self.import_btn = QPushButton("Importer une narration…")
        self.import_btn.clicked.connect(self.import_audio)
        self.place_btn = QPushButton("Placer à l'image courante")
        self.place_btn.clicked.connect(self.place_at_current_frame)
        self.remove_btn = QPushButton("Supprimer")
        self.remove_btn.clicked.connect(self.remove_selected)
        for b in (self.import_btn, self.place_btn, self.remove_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(list(self.COLS))
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table, 1)
        document.changed.connect(self.refresh)
        document.sceneChanged.connect(lambda _s: self.refresh())
        self.refresh()

    def _clip_at_row(self, row: int) -> AudioClip | None:
        scene = self.document.scene
        item = self.table.item(row, 0)
        if scene is None or item is None:
            return None
        return scene.audio_clip(str(item.data(ID_ROLE)))

    def selected_clip(self) -> AudioClip | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return self._clip_at_row(rows[0].row()) if rows else None

    def refresh(self) -> None:
        scene = self.document.scene
        self._updating = True
        try:
            selected = self.selected_clip()
            self.table.setRowCount(0)
            if scene is None:
                return
            fps = float(self.document.project.canvas.fps)
            for row, clip in enumerate(scene.audio):
                self.table.insertRow(row)
                name = QTableWidgetItem(clip.name)
                name.setData(ID_ROLE, clip.id)
                self.table.setItem(row, 0, name)
                self.table.setCellWidget(
                    row, 1, self._spin(clip.offset_frames / fps, 0, 36000, 0.05, clip.id, "offset")
                )
                self.table.setCellWidget(row, 2, self._spin(clip.gain, 0, 4, 0.05, clip.id, "gain"))
                self.table.setCellWidget(
                    row, 3, self._spin(clip.fade_in_seconds, 0, 60, 0.1, clip.id, "fade_in_seconds")
                )
                self.table.setCellWidget(
                    row, 4, self._spin(clip.fade_out_seconds, 0, 60, 0.1, clip.id, "fade_out_seconds")
                )
                mute = QCheckBox()
                mute.setChecked(clip.muted)
                mute.toggled.connect(lambda v, cid=clip.id: self._set(cid, "muted", bool(v)))
                self.table.setCellWidget(row, 5, mute)
                dur = QTableWidgetItem(f"{clip.duration_seconds:.2f}")
                dur.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(row, 6, dur)
                if selected is not None and clip.id == selected.id:
                    self.table.selectRow(row)
        finally:
            self._updating = False

    def _spin(
        self, value: float, lo: float, hi: float, step: float, clip_id: str, attr: str
    ) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(lo, hi)
        sb.setDecimals(2)
        sb.setSingleStep(step)
        sb.setValue(value)
        sb.setKeyboardTracking(False)
        sb.valueChanged.connect(lambda v, cid=clip_id, a=attr: self._set(cid, a, float(v)))
        return sb

    def _set(self, clip_id: str, attr: str, value: float | bool | str) -> None:
        if self._updating:
            return
        scene = self.document.scene
        if scene is None or scene.audio_clip(clip_id) is None:
            return
        if attr == "offset":
            fps = float(self.document.project.canvas.fps)
            frames = int(round(float(value) * fps))
            self.document.push(SetAudioClipAttr(scene.id, clip_id, "offset_frames", frames))
        else:
            self.document.push(SetAudioClipAttr(scene.id, clip_id, attr, value))

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating or item.column() != 0:
            return
        clip = self._clip_at_row(item.row())
        scene = self.document.scene
        if clip is not None and scene is not None and item.text().strip() and item.text() != clip.name:
            self.document.push(
                SetAudioClipAttr(scene.id, clip.id, "name", item.text().strip(), label="Renommer")
            )

    def import_audio(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
        if self.document.paths is None:
            QMessageBox.information(self, "Importer une narration", "Enregistrez d'abord le projet (Ctrl+S).")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer une narration",
            self.settings.last_directory(),
            "Audio (*.wav *.mp3 *.flac *.ogg *.m4a *.aac)",
        )
        if not path:
            return
        clip = self.add_audio_file(Path(path))
        if clip is not None and self.provenance_prompt is not None:
            asset = self.document.project.asset(clip.asset_id)
            if asset is not None:
                self.provenance_prompt(asset)

    def add_audio_file(self, path: Path) -> AudioClip | None:
        """Importe le fichier dans ``audio/``, mesure sa durée et crée le clip à l'image courante."""
        scene = self.document.scene
        if scene is None or self.document.paths is None:
            return None
        from antares_studio.resources.assets import import_asset

        ffmpeg = ff.find_ffmpeg(self.settings.ffmpeg_path() or None)
        ffprobe = ff.find_ffprobe(ffmpeg=ffmpeg) if ffmpeg else None
        duration = 0.0
        if ffprobe is not None:
            try:
                duration = ff.probe_audio_duration(ffprobe, path)
            except ff.FFmpegError as exc:
                QMessageBox.critical(
                    self, "Import impossible", f"Ce fichier n'est pas un audio lisible :\n{exc}"
                )
                return None
        try:
            asset = import_asset(self.document, path, kind="audio")
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Import impossible", str(exc))
            return None
        clip = AudioClip.create(
            asset.id, path.stem, offset_frames=self.document.frame, duration_seconds=duration
        )
        self.document.push(AddAudioClip(scene.id, clip))
        self.settings.set_last_directory(str(path.parent))
        return clip

    def place_at_current_frame(self) -> None:
        clip = self.selected_clip()
        scene = self.document.scene
        if clip is not None and scene is not None:
            self.document.push(SetAudioClipAttr(scene.id, clip.id, "offset_frames", self.document.frame))

    def remove_selected(self) -> None:
        clip = self.selected_clip()
        scene = self.document.scene
        if clip is not None and scene is not None:
            self.document.push(RemoveAudioClip(scene.id, clip.id))


class SubtitlesTab(QWidget):
    COLS = ("Début (s)", "Fin (s)", "Texte")

    def __init__(self, document: ProjectDocument, settings: AppSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self.settings = settings
        self._updating = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        buttons = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter à l'image courante")
        self.add_btn.clicked.connect(self.add_at_current_frame)
        self.remove_btn = QPushButton("Supprimer")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.import_btn = QPushButton("Importer SRT/VTT…")
        self.import_btn.clicked.connect(self.import_file)
        self.export_btn = QPushButton("Exporter SRT…")
        self.export_btn.clicked.connect(self.export_file)
        for b in (self.add_btn, self.remove_btn, self.import_btn, self.export_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(list(self.COLS))
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self.table, 1)
        self.diag = QLabel("")
        self.diag.setWordWrap(True)
        self.diag.setProperty("role", "warning")
        layout.addWidget(self.diag)
        document.changed.connect(self.refresh)
        document.sceneChanged.connect(lambda _s: self.refresh())
        self.refresh()

    def _fps(self) -> float:
        return float(self.document.project.canvas.fps)

    def refresh(self) -> None:
        scene = self.document.scene
        self._updating = True
        try:
            self.table.setRowCount(0)
            if scene is None:
                return
            fps = self._fps()
            for row, sub in enumerate(scene.subtitles):
                self.table.insertRow(row)
                start = QTableWidgetItem(f"{sub.start_frame / fps:.2f}")
                start.setData(ID_ROLE, sub.id)
                end = QTableWidgetItem(f"{sub.end_frame / fps:.2f}")
                text = QTableWidgetItem(sub.text.replace("\n", " / "))
                for col, item in enumerate((start, end, text)):
                    self.table.setItem(row, col, item)
            issues = check_subtitles(scene.subtitles, scene.duration_frames, self.document.project.canvas.fps)
            self.diag.setText(
                ""
                if not issues
                else "À vérifier : " + " ; ".join(f"n° {i.index + 1} : {i.message}" for i in issues[:6])
            )
        finally:
            self._updating = False

    def _sub_at_row(self, row: int) -> Subtitle | None:
        scene = self.document.scene
        item = self.table.item(row, 0)
        if scene is None or item is None:
            return None
        sid = str(item.data(ID_ROLE))
        return next((s for s in scene.subtitles if s.id == sid), None)

    def _on_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows or self._updating:
            return
        sub = self._sub_at_row(rows[0].row())
        if sub is not None:
            self.document.set_frame(sub.start_frame)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        sub = self._sub_at_row(item.row())
        scene = self.document.scene
        if sub is None or scene is None:
            return
        col = item.column()
        try:
            if col == 0:
                frame = int(round(float(item.text().replace(",", ".")) * self._fps()))
                if frame < 0 or frame >= sub.end_frame:
                    raise ValueError
                self.document.push(SetSubtitleAttr(scene.id, sub.id, "start_frame", frame))
            elif col == 1:
                frame = int(round(float(item.text().replace(",", ".")) * self._fps()))
                if frame <= sub.start_frame:
                    raise ValueError
                self.document.push(SetSubtitleAttr(scene.id, sub.id, "end_frame", frame))
            else:
                self.document.push(
                    SetSubtitleAttr(scene.id, sub.id, "text", item.text().replace(" / ", "\n"))
                )
        except ValueError:
            self.refresh()

    def add_at_current_frame(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
        start = self.document.frame
        end = min(scene.duration_frames, start + int(round(2 * self._fps())))
        if end <= start:
            end = start + 1
        sub = Subtitle.create(start, end, "Nouveau sous-titre")
        self.document.push(AddSubtitle(scene.id, sub))
        for row in range(self.table.rowCount()):
            first = self.table.item(row, 0)
            text_item = self.table.item(row, 2)
            if first is not None and text_item is not None and first.data(ID_ROLE) == sub.id:
                self.table.editItem(text_item)
                break

    def remove_selected(self) -> None:
        scene = self.document.scene
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if scene is None or not rows:
            return
        sub = self._sub_at_row(rows[0].row())
        if sub is not None:
            self.document.push(RemoveSubtitle(scene.id, sub.id))

    def import_file(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Importer des sous-titres", self.settings.last_directory(), "Sous-titres (*.srt *.vtt)"
        )
        if not path:
            return
        self.import_path(Path(path))

    def import_path(self, path: Path) -> bool:
        scene = self.document.scene
        if scene is None:
            return False
        try:
            text = path.read_text(encoding="utf-8")
            subs = parse_subtitles(text, self.document.project.canvas.fps)
        except UnicodeDecodeError:
            QMessageBox.critical(self, "Import impossible", "Le fichier doit être encodé en UTF-8.")
            return False
        except (OSError, SubtitleFormatError) as exc:
            QMessageBox.critical(self, "Import impossible", str(exc))
            return False
        if scene.subtitles:
            answer = QMessageBox.question(
                self, "Importer des sous-titres", "Remplacer les sous-titres existants de cette scène ?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False
        self.document.push(ReplaceSubtitles(scene.id, subs))
        return True

    def export_file(self) -> None:
        scene = self.document.scene
        if scene is None or not scene.subtitles:
            QMessageBox.information(self, "Exporter", "Aucun sous-titre dans cette scène.")
            return
        path, chosen = QFileDialog.getSaveFileName(
            self, "Exporter les sous-titres", self.settings.last_directory(), "SubRip (*.srt);;WebVTT (*.vtt)"
        )
        if not path:
            return
        fps = self.document.project.canvas.fps
        if path.lower().endswith(".vtt") or "vtt" in chosen.lower():
            Path(path).write_text(format_vtt(scene.subtitles, fps), encoding="utf-8")
        else:
            if not path.lower().endswith(".srt"):
                path += ".srt"
            Path(path).write_text(format_srt(scene.subtitles, fps), encoding="utf-8")


class NarrationDock(QWidget):
    def __init__(self, document: ProjectDocument, settings: AppSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.audio = AudioTab(document, settings)
        self.subtitles = SubtitlesTab(document, settings)
        self.tabs.addTab(self.audio, "Audio")
        self.tabs.addTab(self.subtitles, "Sous-titres")
        layout.addWidget(self.tabs)

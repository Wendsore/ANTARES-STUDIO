"""Dialogue d'export : profil, destination, progression, annulation ; rendu dans un thread séparé."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app.document import ProjectDocument
from antares_studio.app.settings import AppSettings
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import (
    ProjectRenderResult,
    RenderCancelledError,
    RenderError,
    RenderResult,
    audio_plans_for_scene,
    export_project,
    export_video,
)
from antares_studio.rendering.plan import PROFILES, RenderPlan, build_render_plan


class _Worker(QObject):
    progress = Signal(int, int)
    finished = Signal(object)  # RenderResult
    failed = Signal(str, str)
    cancelled = Signal()

    def __init__(
        self,
        document: ProjectDocument,
        plan: RenderPlan | None,
        ffmpeg_path: str,
        whole_project: tuple[str, str] | None = None,  # (profil, fichier de sortie) : toutes les scènes
    ):
        super().__init__()
        self.document = document
        self.plan = plan
        self.ffmpeg_path = ffmpeg_path
        self.whole_project = whole_project
        self.cancel = threading.Event()

    def run(self) -> None:
        try:
            result: RenderResult | ProjectRenderResult
            if self.whole_project is not None:
                result = export_project(
                    self.document.project,
                    self.whole_project[0],
                    self.whole_project[1],
                    progress=lambda i, n: self.progress.emit(i, n),
                    cancel=self.cancel,
                    assets=self.document.resolve_asset,
                    ffmpeg_path=self.ffmpeg_path or None,
                )
            else:
                assert self.plan is not None
                result = export_video(
                    self.document.project,
                    self.plan,
                    progress=lambda i, n: self.progress.emit(i, n),
                    cancel=self.cancel,
                    assets=self.document.resolve_asset,
                    ffmpeg_path=self.ffmpeg_path or None,
                )
        except RenderCancelledError:
            self.cancelled.emit()
        except (RenderError, ff.FFmpegError, ff.FFmpegNotFoundError) as exc:
            self.failed.emit(str(exc), getattr(exc, "details", "") or getattr(exc, "stderr", ""))
        except Exception as exc:  # noqa: BLE001 — remonter toute erreur à l'utilisateur
            self.failed.emit(f"Erreur inattendue : {exc}", "")
        else:
            self.finished.emit(result)


class ExportDialog(QDialog):
    def __init__(self, document: ProjectDocument, settings: AppSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self.settings = settings
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self.render_result: RenderResult | ProjectRenderResult | None = None
        self.setWindowTitle("Exporter la vidéo")
        self.setModal(True)
        form = QFormLayout()
        self.profile = QComboBox()
        for pid, prof in PROFILES.items():
            self.profile.addItem(f"{prof.label} — {prof.width}×{prof.height}", pid)
        idx = self.profile.findData(settings.last_export_profile())
        self.profile.setCurrentIndex(max(0, idx))
        form.addRow("Profil :", self.profile)
        self.all_scenes = QCheckBox("Toutes les scènes à la suite (vidéo complète)")
        self.all_scenes.setToolTip(
            "Rend chaque scène puis les enchaîne sans ré-encodage ; sous-titres fusionnés et crédits à côté."
        )
        self.all_scenes.toggled.connect(self._refresh_default_path)
        form.addRow("", self.all_scenes)
        scene = document.scene
        fps = float(document.project.canvas.fps)
        if scene is not None:
            form.addRow(
                "Scène :",
                QLabel(
                    f"{scene.name} — {scene.duration_frames} images ({scene.duration_frames / fps:.1f} s)"
                ),
            )
        path_row = QHBoxLayout()
        self.path_edit = QLineEdit(str(self._default_path()))
        browse = QPushButton("Parcourir…")
        browse.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)
        form.addRow("Fichier de sortie :", path_row)
        ffmpeg = ff.find_ffmpeg(settings.ffmpeg_path() or None)
        self.ffmpeg_label = QLabel(
            f"FFmpeg : {ffmpeg}"
            if ffmpeg
            else "FFmpeg : introuvable — installez-le ou renseignez son chemin (Préférences)."
        )
        self.ffmpeg_label.setWordWrap(True)
        form.addRow(self.ffmpeg_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        buttons = QHBoxLayout()
        self.start_btn = QPushButton("Exporter")
        self.start_btn.setDefault(True)
        self.start_btn.clicked.connect(self.start)
        self.start_btn.setEnabled(ffmpeg is not None)
        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.clicked.connect(self._cancel_or_close)
        buttons.addStretch(1)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.cancel_btn)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addLayout(buttons)
        self.resize(560, 260)

    def _refresh_default_path(self) -> None:
        self.path_edit.setText(str(self._default_path()))

    def _default_path(self) -> Path:
        scene = self.document.scene
        base = (scene.name if scene else "scene").replace("/", "-").replace("\\", "-")
        title = (self.document.project.title or "video").replace("/", "-").replace("\\", "-")
        folder = self.document.paths.renders if self.document.paths else Path(self.settings.last_directory())
        if getattr(self, "all_scenes", None) is not None and self.all_scenes.isChecked():
            return folder / f"{title}.mp4"
        return folder / f"{title} - {base}.mp4"

    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer la vidéo", self.path_edit.text(), "Vidéo MP4 (*.mp4)"
        )
        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"
            self.path_edit.setText(path)

    def start(self) -> None:
        scene = self.document.scene
        if scene is None:
            return
        out = Path(self.path_edit.text().strip())
        if not out.name:
            QMessageBox.warning(self, "Export", "Indiquez un fichier de sortie.")
            return
        pid = str(self.profile.currentData())
        self.settings.set_last_export_profile(pid)
        if self.all_scenes.isChecked():
            self._worker = _Worker(
                self.document, None, self.settings.ffmpeg_path(), whole_project=(pid, str(out))
            )
        else:
            try:
                audio = audio_plans_for_scene(self.document.project, scene.id, self.document.resolve_asset)
            except RenderError as exc:
                QMessageBox.warning(self, "Export", str(exc))
                return
            try:
                plan = build_render_plan(self.document.project, scene.id, pid, str(out), audio=audio)
            except ValueError as exc:
                QMessageBox.warning(self, "Export", str(exc))
                return
            if plan.warnings:
                self.status.setText("Avertissement : " + " ".join(plan.warnings))
            self._worker = _Worker(self.document, plan, self.settings.ffmpeg_path())
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)
        self.start_btn.setEnabled(False)
        self.profile.setEnabled(False)
        self.path_edit.setEnabled(False)
        self.cancel_btn.setText("Annuler l'export")
        self.status.setText("Export en cours…")
        self._thread.start()

    def _on_progress(self, i: int, n: int) -> None:
        self.progress.setValue(int(i * 100 / max(1, n)))
        self.status.setText(f"Image {i} / {n}")

    def _finish_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(5000)
            self._thread = None
        self._worker = None
        self.cancel_btn.setText("Fermer")
        self.start_btn.setEnabled(True)
        self.profile.setEnabled(True)
        self.path_edit.setEnabled(True)

    def _on_finished(self, result: object) -> None:
        self._finish_thread()
        assert isinstance(result, RenderResult | ProjectRenderResult)
        self.render_result = result
        pr = result.probe
        self.progress.setValue(100)
        self.status.setText(
            f"Terminé en {result.elapsed_seconds:.1f} s : {pr.width}×{pr.height}, {pr.nb_frames} images, "
            f"{pr.duration:.2f} s{', audio' if pr.has_audio else ''}.\n{result.output_path}"
        )
        self.settings.set_last_directory(str(result.output_path.parent))

    def _on_failed(self, message: str, details: str) -> None:
        self._finish_thread()
        self.status.setText("Échec : " + message)
        if details:
            QMessageBox.critical(self, "Export impossible", f"{message}\n\nDétails :\n{details[-2000:]}")
        else:
            QMessageBox.critical(self, "Export impossible", message)

    def _on_cancelled(self) -> None:
        self._finish_thread()
        self.progress.setValue(0)
        self.status.setText("Export annulé. Aucun fichier partiel n'a été conservé.")

    def _cancel_or_close(self) -> None:
        if self._worker is not None:
            self._worker.cancel.set()
            self.status.setText("Annulation…")
            return
        self.accept() if self.render_result else self.reject()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._worker is not None:
            self._worker.cancel.set()
            event.ignore()
            return
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key() == Qt.Key.Key_Escape and self._worker is not None:
            self._worker.cancel.set()
            return
        super().keyPressEvent(event)

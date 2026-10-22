"""Dialogue d'export : profil, destination, progression, annulation ; rendu dans un thread séparé.

« En arrière-plan » confie le travail à la file d'exports (projet figé) et rend la main à l'éditeur.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices
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

from antares_studio.app import icons, theme
from antares_studio.app.document import ProjectDocument
from antares_studio.app.export_queue import ExportJob, ExportQueue, RenderWorker
from antares_studio.app.settings import AppSettings
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import (
    ProjectRenderResult,
    RenderError,
    RenderResult,
    audio_plans_for_scene,
)
from antares_studio.rendering.plan import PROFILES, RenderPlan, build_render_plan

FILE_FILTERS = {
    "mp4": "Vidéo MP4 (*.mp4)",
    "webm": "Vidéo WebM (*.webm)",
    "gif": "Image animée GIF (*.gif)",
    "mov": "Vidéo QuickTime ProRes (*.mov)",
    "png": "Dossier de la séquence d'images (*)",
    "wav": "Son WAV (*.wav)",
    "mp3": "Son MP3 (*.mp3)",
}
KNOWN_SUFFIXES = (".mp4", ".webm", ".gif", ".mov", ".wav", ".mp3")


def with_video_suffix(path: str, suffix: str) -> str:
    """Remplace l'extension d'export connue (.mp4, .mov, .wav…) ; les autres points du nom sont gardés."""
    low = path.lower()
    for known in KNOWN_SUFFIXES:
        if low.endswith(known):
            return path[: -len(known)] + suffix
    return path + suffix


def profile_items() -> list[tuple[str, str | None]]:
    """Entrées de la liste des profils, regroupées (``None`` = séparateur entre groupes)."""
    items: list[tuple[str, str | None]] = []
    group = None
    for pid, prof in PROFILES.items():
        if group is not None and prof.group != group:
            items.append(("", None))
        group = prof.group
        size = f"{prof.width}×{prof.height}" if prof.has_video else "son seul"
        items.append((f"{prof.group} · {prof.label} — {size}", pid))
    return items


class ExportDialog(QDialog):
    def __init__(
        self,
        document: ProjectDocument,
        settings: AppSettings,
        parent: QWidget | None = None,
        queue: ExportQueue | None = None,
    ):
        super().__init__(parent)
        self.document = document
        self.settings = settings
        self.queue = queue
        self.queued_job: ExportJob | None = None
        self._thread: QThread | None = None
        self._worker: RenderWorker | None = None
        self.render_result: RenderResult | ProjectRenderResult | None = None
        self.setWindowTitle("Exporter la vidéo")
        self.setModal(True)
        form = QFormLayout()
        self.profile = QComboBox()
        self.profile.setObjectName("export_profile")
        for text, pid in profile_items():
            if pid is None:
                self.profile.insertSeparator(self.profile.count())
            else:
                self.profile.addItem(text, pid)
        idx = self.profile.findData(settings.last_export_profile())
        self.profile.setCurrentIndex(max(0, idx))
        self.profile.currentIndexChanged.connect(self._profile_changed)
        form.addRow("Profil :", self.profile)
        self.profile_hint = QLabel()
        self.profile_hint.setWordWrap(True)
        self.profile_hint.setProperty("role", "hint")
        form.addRow("", self.profile_hint)
        self.all_scenes = QCheckBox("Toutes les scènes à la suite (vidéo complète)")
        self.all_scenes.setToolTip(
            "Rend chaque scène puis les enchaîne sans ré-encodage ; sous-titres fusionnés et crédits à côté."
        )
        self.all_scenes.toggled.connect(self._refresh_default_path)
        form.addRow("", self.all_scenes)
        self.transparent = QCheckBox("Fond transparent (pour incruster la vidéo dans un montage)")
        self.transparent.setObjectName("export_transparent")
        self.transparent.setToolTip(
            "Le fond de la scène n'est pas peint : seuls les objets restent, sur un canal alpha. "
            "Profils ProRes 4444 et séquence PNG uniquement."
        )
        form.addRow("", self.transparent)
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
            else "FFmpeg : introuvable — installez-le, puis indiquez son emplacement avec "
            "Aide > Chemin de FFmpeg… (voir Aide > Centre d'aide, rubrique Installation)."
        )
        self.ffmpeg_label.setWordWrap(True)
        self.ffmpeg_label.setProperty("role", "hint" if ffmpeg else "warning")
        form.addRow(self.ffmpeg_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status = QLabel("Prêt.")
        self.status.setWordWrap(True)
        buttons = QHBoxLayout()
        self.start_btn = QPushButton(icons.icon("clapperboard", theme.active().on_accent), "Exporter")
        self.start_btn.setProperty("role", "primary")
        self.start_btn.setDefault(True)
        self.start_btn.clicked.connect(self.start)
        self.start_btn.setEnabled(ffmpeg is not None)
        self.background_btn = QPushButton(icons.icon("list-video"), "En arrière-plan")
        self.background_btn.setObjectName("export_background")
        self.background_btn.setToolTip(
            "Ajoute l'export à la file (panneau Exports) et ferme ce dialogue : vous continuez d'éditer, "
            "la vidéo est rendue telle que le projet est maintenant."
        )
        self.background_btn.clicked.connect(self.start_in_background)
        self.background_btn.setEnabled(ffmpeg is not None and queue is not None)
        self.background_btn.setVisible(queue is not None)
        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.clicked.connect(self._cancel_or_close)
        self.open_folder_btn = QPushButton(icons.icon("folder-open"), "Ouvrir le dossier")
        self.open_folder_btn.setToolTip("Affiche la vidéo exportée dans l'explorateur de fichiers")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_folder_btn.setVisible(False)
        buttons.addWidget(self.open_folder_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.background_btn)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.cancel_btn)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addLayout(buttons)
        self.resize(620, 280)
        self._profile_changed()

    def current_profile_id(self) -> str:
        return str(self.profile.currentData())

    def _profile_changed(self) -> None:
        prof = PROFILES[self.current_profile_id()]
        hints = []
        self.transparent.setEnabled(prof.alpha)
        if not prof.alpha:
            self.transparent.setChecked(False)
        elif prof.video_codec == "prores_ks":
            self.transparent.setChecked(True)  # raison d'être du ProRes 4444
        if prof.is_sequence:
            hints.append(
                "Un dossier d'images numérotées image_00000.png… ; la bande-son de la scène (s'il y en a) "
                "est écrite à côté, en WAV."
            )
        if prof.video_codec == "prores_ks":
            hints.append("Pour les logiciels de montage ; environ 30 Mo par seconde en 1080p.")
        if not prof.has_video:
            hints.append("Bande-son seule : voix, musique et bruitages mixés, sans image.")
        if prof.height >= 2160:
            hints.append("Rendu environ quatre fois plus long qu'en 1080p.")
        if prof.has_audio:
            loud = bool(self.document.project.settings.get("loudnorm", True))
            hints.append(
                "Volume normalisé à −14 LUFS."
                if loud
                else "Volume non normalisé (réglage du panneau Narration)."
            )
        if prof.fixed_frame:
            hints.append(
                f"Cadre imposé {prof.width}×{prof.height} : bandes noires si le projet a un autre format."
            )
        if not prof.has_audio and not prof.is_sequence:
            hints.append("Sans son.")
        if prof.max_fps is not None:
            hints.append(f"Cadence limitée à {prof.max_fps:g} images/s.")
        if prof.container == "webm":
            hints.append("Encodage VP9 plus lent que le MP4.")
        self.profile_hint.setText(" ".join(hints))
        self.profile_hint.setVisible(bool(hints))
        current = self.path_edit.text().strip()
        if Path(current).name:
            self.path_edit.setText(with_video_suffix(current, prof.suffix))
        self.all_scenes.setEnabled(not prof.is_sequence)
        if prof.is_sequence:
            self.all_scenes.setChecked(False)

    def _refresh_default_path(self) -> None:
        self.path_edit.setText(str(self._default_path()))

    def _default_path(self) -> Path:
        scene = self.document.scene
        base = (scene.name if scene else "scene").replace("/", "-").replace("\\", "-")
        title = (self.document.project.title or "video").replace("/", "-").replace("\\", "-")
        folder = self.document.paths.renders if self.document.paths else Path(self.settings.last_directory())
        suffix = PROFILES[self.current_profile_id()].suffix if hasattr(self, "profile") else ".mp4"
        if getattr(self, "all_scenes", None) is not None and self.all_scenes.isChecked():
            return folder / f"{title}{suffix}"
        return folder / f"{title} - {base}{suffix}"

    def _browse(self) -> None:
        prof = PROFILES[self.current_profile_id()]
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer la vidéo", self.path_edit.text(), FILE_FILTERS[prof.container]
        )
        if path:
            if not path.lower().endswith(prof.suffix):
                path += prof.suffix
            self.path_edit.setText(path)

    def _prepare(self) -> tuple[Path, RenderPlan | None] | None:
        """Fichier de sortie et plan (``None`` pour toutes les scènes) ; ``None`` si impossible."""
        scene = self.document.scene
        if scene is None:
            return None
        out = Path(self.path_edit.text().strip())
        if not out.name:
            QMessageBox.warning(self, "Export", "Indiquez un fichier de sortie.")
            return None
        pid = self.current_profile_id()
        self.settings.set_last_export_profile(pid)
        if self.all_scenes.isChecked():
            return out, None
        try:
            audio = audio_plans_for_scene(self.document.project, scene.id, self.document.resolve_asset)
            plan = build_render_plan(
                self.document.project,
                scene.id,
                pid,
                str(out),
                audio=audio,
                transparent=self.transparent.isChecked(),
            )
        except (RenderError, ValueError) as exc:
            QMessageBox.warning(self, "Export", str(exc))
            return None
        if plan.warnings:
            self.status.setText("Avertissement : " + " ".join(plan.warnings))
        return out, plan

    def start_in_background(self) -> None:
        """Confie l'export à la file (projet figé maintenant) et ferme le dialogue."""
        if self.queue is None:
            return
        prepared = self._prepare()
        if prepared is None:
            return
        out, plan = prepared
        label = out.name + (" (toutes les scènes)" if plan is None else "")
        job = ExportJob.from_document(
            self.document,
            label,
            out,
            plan,
            None if plan is not None else self.current_profile_id(),
            self.settings.ffmpeg_path(),
        )
        job.transparent = self.transparent.isChecked()
        self.queued_job = self.queue.submit(job)
        self.accept()

    def start(self) -> None:
        prepared = self._prepare()
        if prepared is None:
            return
        out, plan = prepared
        whole = (self.current_profile_id(), str(out)) if plan is None else None
        self._worker = RenderWorker(
            self.document.project,
            self.document.resolve_asset,
            plan,
            self.settings.ffmpeg_path(),
            whole,
            transparent=self.transparent.isChecked(),
        )
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)
        self.start_btn.setEnabled(False)
        self.background_btn.setEnabled(False)
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
        self.background_btn.setEnabled(self.queue is not None)
        self.profile.setEnabled(True)
        self.path_edit.setEnabled(True)

    def _on_finished(self, result: object) -> None:
        self._finish_thread()
        assert isinstance(result, RenderResult | ProjectRenderResult)
        self.render_result = result
        pr = result.probe
        self.progress.setValue(100)
        what = f"{pr.width}×{pr.height}, {pr.nb_frames} images, " if pr.width else "bande-son, "
        self.status.setText(
            f"Terminé en {result.elapsed_seconds:.1f} s : {what}"
            f"{pr.duration:.2f} s{', audio' if pr.has_audio and pr.width else ''}.\n{result.output_path}"
        )
        self.settings.set_last_directory(str(result.output_path.parent))
        self.open_folder_btn.setVisible(True)

    def open_output_folder(self) -> bool:
        """Ouvre le dossier de la dernière vidéo exportée dans le gestionnaire de fichiers du système."""
        if self.render_result is None:
            return False
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.render_result.output_path.parent)))

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

"""File d'exports en arrière-plan : le projet est figé à l'envoi, on continue d'éditer pendant le rendu.

Chaque travail emporte une copie du projet (``copy.deepcopy``) et un résolveur de fichiers lié au dossier
du projet au moment de l'envoi : les modifications faites ensuite dans l'éditeur ne changent pas une
vidéo déjà en file. Les travaux s'exécutent un par un dans un thread (le rendu Qt est mono-cœur ici).
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import icons
from antares_studio.app.document import ProjectDocument
from antares_studio.domain.model import Project
from antares_studio.persistence.paths import UnsafePathError, resolve_under
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import (
    ProjectRenderResult,
    RenderCancelledError,
    RenderError,
    RenderResult,
    export_project,
    export_video,
)
from antares_studio.rendering.plan import RenderPlan
from antares_studio.rendering.qt_painter import AssetResolver

STATUS_LABELS = {
    "waiting": "En attente",
    "running": "En cours",
    "done": "Terminé",
    "failed": "Échec",
    "cancelled": "Annulé",
}


def snapshot_resolver(project: Project, root: Path | None) -> AssetResolver:
    """Résolveur de ressources figé : chemins du projet copié, sous le dossier du projet uniquement."""

    def resolve(asset_id: str) -> Path | None:
        asset = project.asset(asset_id)
        if asset is None or root is None:
            return None
        try:
            return resolve_under(root, asset.path)
        except UnsafePathError:
            return None

    return resolve


@dataclass
class ExportJob:
    label: str
    project: Project
    assets: AssetResolver
    output_path: Path
    plan: RenderPlan | None = None
    whole_project_profile: str | None = None  # toutes les scènes, avec ce profil
    ffmpeg_path: str = ""
    open_when_done: bool = False  # aperçu rapide : lecture dès la fin
    status: str = "waiting"
    done_frames: int = 0
    total_frames: int = 0
    message: str = ""
    result: RenderResult | ProjectRenderResult | None = None
    cancel: threading.Event = field(default_factory=threading.Event)

    @classmethod
    def from_document(
        cls,
        document: ProjectDocument,
        label: str,
        output_path: Path,
        plan: RenderPlan | None = None,
        whole_project_profile: str | None = None,
        ffmpeg_path: str = "",
        open_when_done: bool = False,
    ) -> ExportJob:
        project = copy.deepcopy(document.project)
        root = document.paths.root if document.paths else None
        return cls(
            label,
            project,
            snapshot_resolver(project, root),
            output_path,
            plan,
            whole_project_profile,
            ffmpeg_path,
            open_when_done,
        )

    def status_text(self) -> str:
        text = f"{STATUS_LABELS[self.status]} — {self.label}"
        if self.status == "running" and self.total_frames:
            text += f" ({int(self.done_frames * 100 / self.total_frames)} %)"
        if self.message:
            text += f" : {self.message}"
        return text


class RenderWorker(QObject):
    """Exécute un export (une scène ou toutes) hors du thread de l'interface."""

    progress = Signal(int, int)
    finished = Signal(object)  # RenderResult | ProjectRenderResult
    failed = Signal(str, str)
    cancelled = Signal()

    def __init__(
        self,
        project: Project,
        assets: AssetResolver,
        plan: RenderPlan | None,
        ffmpeg_path: str,
        whole_project: tuple[str, str] | None = None,  # (profil, fichier de sortie) : toutes les scènes
        cancel: threading.Event | None = None,
    ):
        super().__init__()
        self.project = project
        self.assets = assets
        self.plan = plan
        self.ffmpeg_path = ffmpeg_path
        self.whole_project = whole_project
        self.cancel = cancel or threading.Event()

    def run(self) -> None:
        try:
            result: RenderResult | ProjectRenderResult
            if self.whole_project is not None:
                result = export_project(
                    self.project,
                    self.whole_project[0],
                    self.whole_project[1],
                    progress=lambda i, n: self.progress.emit(i, n),
                    cancel=self.cancel,
                    assets=self.assets,
                    ffmpeg_path=self.ffmpeg_path or None,
                )
            else:
                assert self.plan is not None
                result = export_video(
                    self.project,
                    self.plan,
                    progress=lambda i, n: self.progress.emit(i, n),
                    cancel=self.cancel,
                    assets=self.assets,
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


class ExportQueue(QObject):
    """Travaux exécutés un par un ; ``changed`` est émis à chaque évolution d'un travail."""

    changed = Signal(object)  # ExportJob
    jobFinished = Signal(object)  # ExportJob terminé avec succès

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.jobs: list[ExportJob] = []
        self._thread: QThread | None = None
        self._worker: RenderWorker | None = None
        self._current: ExportJob | None = None
        self.opener: Callable[[QUrl], bool] = QDesktopServices.openUrl

    @property
    def busy(self) -> bool:
        return self._current is not None

    def pending(self) -> list[ExportJob]:
        return [j for j in self.jobs if j.status in ("waiting", "running")]

    def submit(self, job: ExportJob) -> ExportJob:
        self.jobs.append(job)
        self.changed.emit(job)
        self._start_next()
        return job

    def cancel(self, job: ExportJob) -> None:
        if job.status == "waiting":
            job.status = "cancelled"
            self.changed.emit(job)
        elif job.status == "running":
            job.cancel.set()
            job.message = "annulation…"
            self.changed.emit(job)

    def cancel_all(self) -> None:
        for job in self.pending():
            self.cancel(job)

    def wait_idle(self, timeout_ms: int = 5000) -> None:
        """Arrêt propre (fermeture de la fenêtre) : annule tout et attend le thread en cours."""
        self.cancel_all()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(timeout_ms)

    def _start_next(self) -> None:
        if self._current is not None:
            return
        job = next((j for j in self.jobs if j.status == "waiting"), None)
        if job is None:
            return
        self._current = job
        job.status = "running"
        whole = (job.whole_project_profile, str(job.output_path)) if job.whole_project_profile else None
        self._worker = RenderWorker(job.project, job.assets, job.plan, job.ffmpeg_path, whole, job.cancel)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        conn = Qt.ConnectionType.QueuedConnection
        self._worker.progress.connect(self._on_progress, conn)
        self._worker.finished.connect(self._on_finished, conn)
        self._worker.failed.connect(self._on_failed, conn)
        self._worker.cancelled.connect(self._on_cancelled, conn)
        self.changed.emit(job)
        self._thread.start()

    def _end(self) -> ExportJob:
        job = self._current
        assert job is not None
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(5000)
        self._thread = None
        self._worker = None
        self._current = None
        return job

    def _on_progress(self, i: int, n: int) -> None:
        if self._current is not None:
            self._current.done_frames, self._current.total_frames = i, n
            self.changed.emit(self._current)

    def _on_finished(self, result: object) -> None:
        job = self._end()
        assert isinstance(result, RenderResult | ProjectRenderResult)
        job.status, job.result, job.message = "done", result, str(result.output_path)
        self.changed.emit(job)
        self.jobFinished.emit(job)
        if job.open_when_done:
            self.opener(QUrl.fromLocalFile(str(result.output_path)))
        self._start_next()

    def _on_failed(self, message: str, _details: str) -> None:
        job = self._end()
        job.status, job.message = "failed", message
        self.changed.emit(job)
        self._start_next()

    def _on_cancelled(self) -> None:
        job = self._end()
        job.status, job.message = "cancelled", ""
        self.changed.emit(job)
        self._start_next()


class ExportsPanel(QWidget):
    """Panneau « Exports » : état des travaux, annulation, ouverture du dossier de la vidéo."""

    def __init__(self, queue: ExportQueue, parent: QWidget | None = None):
        super().__init__(parent)
        self.queue = queue
        self.list = QListWidget()
        self.list.setObjectName("exports_list")
        self.list.currentRowChanged.connect(lambda _r: self._sync_buttons())
        self.cancel_btn = QPushButton(icons.icon("x"), "Annuler")
        self.cancel_btn.clicked.connect(self.cancel_selected)
        self.open_btn = QPushButton(icons.icon("folder-open"), "Ouvrir le dossier")
        self.open_btn.clicked.connect(self.open_selected_folder)
        self.clear_btn = QPushButton("Retirer les travaux finis")
        self.clear_btn.clicked.connect(self.clear_finished)
        buttons = QHBoxLayout()
        for b in (self.cancel_btn, self.open_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        buttons.addWidget(self.clear_btn)
        layout = QVBoxLayout(self)
        layout.addWidget(self.list, 1)
        layout.addLayout(buttons)
        queue.changed.connect(self._job_changed)
        self._sync_buttons()

    def _row_of(self, job: ExportJob) -> int:
        return next(
            (i for i in range(self.list.count()) if self.list.item(i).data(Qt.ItemDataRole.UserRole) is job),
            -1,
        )

    def _job_changed(self, job: ExportJob) -> None:
        row = self._row_of(job)
        if row < 0:
            item = QListWidgetItem(job.status_text())
            item.setData(Qt.ItemDataRole.UserRole, job)
            self.list.addItem(item)
            self.list.setCurrentItem(item)
        else:
            self.list.item(row).setText(job.status_text())
        self._sync_buttons()

    def selected(self) -> ExportJob | None:
        item = self.list.currentItem()
        job = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return job if isinstance(job, ExportJob) else None

    def _sync_buttons(self) -> None:
        job = self.selected()
        self.cancel_btn.setEnabled(job is not None and job.status in ("waiting", "running"))
        self.open_btn.setEnabled(job is not None and job.status == "done")

    def cancel_selected(self) -> None:
        job = self.selected()
        if job is not None:
            self.queue.cancel(job)

    def open_selected_folder(self) -> bool:
        job = self.selected()
        if job is None or job.result is None:
            return False
        return self.queue.opener(QUrl.fromLocalFile(str(job.result.output_path.parent)))

    def clear_finished(self) -> None:
        self.queue.jobs = [j for j in self.queue.jobs if j.status in ("waiting", "running")]
        for row in reversed(range(self.list.count())):
            job = self.list.item(row).data(Qt.ItemDataRole.UserRole)
            if job not in self.queue.jobs:
                self.list.takeItem(row)
        self._sync_buttons()

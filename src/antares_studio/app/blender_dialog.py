"""Planète 3D (Blender facultatif) : paramètres, rendu en arrière-plan, insertion d'une séquence d'images."""

from __future__ import annotations

import shutil
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app.document import ProjectDocument
from antares_studio.app.inspector_dock import ColorButton
from antares_studio.domain.commands import AddNode, ReplaceTracks
from antares_studio.domain.ids import new_id
from antares_studio.domain.model import Asset, AssetLicense, Node, Track
from antares_studio.rendering.blender import (
    BlenderError,
    blender_version,
    find_blender,
    render_planet_sequence,
)


class _Worker(QObject):
    progress = Signal(int, int)
    finished = Signal(object)  # list[Path]
    failed = Signal(str, str)

    def __init__(self, folder: Path, frames: int, size: int, turns: float, c1: str, c2: str, samples: int):
        super().__init__()
        self.args = (folder, frames, size, turns, c1, c2, samples)
        self.cancel = threading.Event()

    def run(self) -> None:
        folder, frames, size, turns, c1, c2, samples = self.args
        try:
            files = render_planet_sequence(
                folder,
                frames,
                size,
                size,
                turns,
                c1,
                c2,
                samples,
                progress=lambda i, n: self.progress.emit(i, n),
                cancel=self.cancel,
            )
        except BlenderError as exc:
            self.failed.emit(str(exc), exc.details)
        except Exception as exc:  # noqa: BLE001 — remonter toute erreur à l'utilisateur
            self.failed.emit(f"Erreur inattendue : {exc}", "")
        else:
            self.finished.emit(files)


def insert_sequence_node(
    document: ProjectDocument, folder_rel: str, frames: int, size: int, name: str
) -> Node:
    """Enregistre la séquence comme ressource (dossier) et crée l'objet animé sur la durée de la scène."""
    scene = document.scene
    assert scene is not None
    asset = Asset(
        id=new_id("asset"),
        path=folder_rel,
        kind="sequence",
        license=AssetLicense(
            author="ANTARES Studio (géométrie générée par Blender)",
            license="own-work",
            attribution_required=False,
            redistribution_allowed=True,
            verified_on="",
        ),
    )
    document.project.assets.append(asset)
    c = document.project.canvas
    node = Node.create(
        "image_sequence",
        name,
        position=[c.width / 2, c.height / 2],
        params={
            "sequence_asset_id": asset.id,
            "frame_count": frames,
            "frame_index": 0.0,
            "width": float(size),
            "height": 0.0,
        },
        style={"tint": "#FFFFFF00"},
    )
    document.push(AddNode(scene.id, node))
    track = Track(node.id, "params.frame_index")
    track.set_keyframe(0, 0.0, "linear")
    track.set_keyframe(max(1, scene.duration_frames - 1), float(frames - 1), "linear")
    document.push(ReplaceTracks(scene.id, node.id, [track], label="Planète 3D"))
    document.set_selection([node.id])
    return node


class BlenderPlanetDialog(QDialog):
    def __init__(self, document: ProjectDocument, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self.created: Node | None = None
        self._rel = ""
        self.setWindowTitle("Planète 3D (Blender)")
        self.setModal(True)
        lay = QVBoxLayout(self)
        blender = find_blender()
        if blender is None:
            self.info = QLabel(
                "Blender est introuvable. Installez-le (https://www.blender.org, GPL) ou indiquez son chemin "
                "via la variable ANTARES_BLENDER. Toutes les fonctions 2D restent disponibles sans Blender."
            )
        else:
            self.info = QLabel(f"Blender détecté : {blender_version(blender)}")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        form = QFormLayout()
        scene = document.scene
        self.frames = QSpinBox()
        self.frames.setRange(1, 2000)
        self.frames.setValue(min(120, scene.duration_frames if scene else 60))
        form.addRow("Images rendues :", self.frames)
        self.size_px = QSpinBox()
        self.size_px.setRange(64, 2048)
        self.size_px.setValue(512)
        self.size_px.setSuffix(" px")
        form.addRow("Taille :", self.size_px)
        self.turns = QDoubleSpinBox()
        self.turns.setRange(0.01, 20.0)
        self.turns.setValue(1.0)
        form.addRow("Tours sur la durée :", self.turns)
        self.samples = QSpinBox()
        self.samples.setRange(1, 256)
        self.samples.setValue(16)
        form.addRow("Échantillons Cycles :", self.samples)
        self.c1 = ColorButton()
        self.c1.set_value("#0D3380")
        self.c2 = ColorButton()
        self.c2.set_value("#2E7D32")
        form.addRow("Couleur océans :", self.c1)
        form.addRow("Couleur continents :", self.c2)
        lay.addLayout(form)
        self.progress = QProgressBar()
        self.status = QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.progress)
        lay.addWidget(self.status)
        row = QHBoxLayout()
        self.start_btn = QPushButton("Rendre et insérer")
        self.start_btn.setEnabled(blender is not None and document.paths is not None)
        self.start_btn.clicked.connect(self.start)
        self.cancel_btn = QPushButton("Fermer")
        self.cancel_btn.clicked.connect(self._cancel_or_close)
        row.addStretch(1)
        row.addWidget(self.start_btn)
        row.addWidget(self.cancel_btn)
        lay.addLayout(row)
        if document.paths is None:
            self.status.setText(
                "Enregistrez d'abord le projet : la séquence est rendue dans son dossier assets/."
            )
        self.resize(480, 360)

    def start(self) -> None:
        if self.document.paths is None:
            return
        rel = f"assets/planete-3d-{new_id('seq')[-6:]}"
        folder = self.document.paths.root / rel
        self._rel = rel
        self._worker = _Worker(
            folder,
            self.frames.value(),
            self.size_px.value(),
            self.turns.value(),
            self.c1.value(),
            self.c2.value(),
            self.samples.value(),
        )
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self.start_btn.setEnabled(False)
        self.cancel_btn.setText("Annuler le rendu")
        self.status.setText("Rendu Blender en cours…")
        self._thread.start()

    def _on_progress(self, i: int, n: int) -> None:
        self.progress.setValue(int(i * 100 / max(1, n)))
        self.status.setText(f"Image {i} / {n}")

    def _finish_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(10000)
            self._thread = None
        self._worker = None
        self.cancel_btn.setText("Fermer")
        self.start_btn.setEnabled(True)

    def _on_finished(self, files: object) -> None:
        self._finish_thread()
        n = len(files) if isinstance(files, list) else 0
        self.created = insert_sequence_node(self.document, self._rel, n, self.size_px.value(), "Planète 3D")
        self.progress.setValue(100)
        self.status.setText(f"{n} images rendues et insérées (objet « Planète 3D »).")
        self.accept()

    def _on_failed(self, message: str, details: str) -> None:
        self._finish_thread()
        self.status.setText("Échec : " + message + ("\n" + details[-600:] if details else ""))
        if self.document.paths is not None:
            shutil.rmtree(self.document.paths.root / self._rel, ignore_errors=True)

    def _cancel_or_close(self) -> None:
        if self._worker is not None:
            self._worker.cancel.set()
            self.status.setText("Annulation…")
            return
        self.reject()

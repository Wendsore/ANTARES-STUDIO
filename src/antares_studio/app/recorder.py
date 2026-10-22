"""Enregistrement d'une narration au micro (QtMultimedia), en WAV, ajoutée comme piste à l'image courante.

Sans micro ou sans QtMultimedia, le dialogue l'explique et le bouton reste désactivé : l'éditeur ne
dépend jamais d'un périphérique audio.
"""

from __future__ import annotations

import contextlib
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import icons

try:  # QtMultimedia peut manquer (paquet allégé) ou échouer sans backend
    from PySide6.QtMultimedia import (
        QAudioInput,
        QMediaCaptureSession,
        QMediaDevices,
        QMediaFormat,
        QMediaRecorder,
    )

    HAS_MULTIMEDIA = True
except Exception:  # noqa: BLE001
    HAS_MULTIMEDIA = False


def input_devices() -> list[Any]:
    """Micros disponibles (liste vide sans QtMultimedia)."""
    if not HAS_MULTIMEDIA:
        return []
    try:
        return list(QMediaDevices.audioInputs())
    except Exception:  # noqa: BLE001 — backend audio absent : pas de micro
        return []


class RecordDialog(QDialog):
    """Enregistre dans un fichier temporaire ; ``recorded_path`` est rempli à l'arrêt si le fichier existe."""

    def __init__(self, parent: QWidget | None = None, devices: list[Any] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Enregistrer une narration")
        self.recorded_path: Path | None = None
        self._tmpdir = Path(tempfile.mkdtemp(prefix="antares-micro-"))
        self._session: Any = None
        self._recorder: Any = None
        self._input: Any = None
        self.devices = input_devices() if devices is None else devices
        self.device = QComboBox()
        self.device.setObjectName("record_device")
        for d in self.devices:
            self.device.addItem(d.description(), d)
        self.elapsed = QLabel("0,0 s")
        self.elapsed.setProperty("role", "title")
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.record_btn = QPushButton(icons.icon("mic"), "Enregistrer")
        self.record_btn.setObjectName("record_start")
        self.record_btn.setProperty("role", "primary")
        self.record_btn.clicked.connect(self.toggle)
        self.close_btn = QPushButton("Fermer")
        self.close_btn.clicked.connect(self.reject)
        form = QFormLayout()
        form.addRow("Micro :", self.device)
        form.addRow("Durée :", self.elapsed)
        hint = QLabel(
            "Parlez près du micro, dans une pièce calme. À l'arrêt, l'enregistrement (WAV) est copié dans "
            "le dossier audio/ du projet et placé à l'image courante ; sa fiche de provenance indique "
            "« œuvre personnelle »."
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "hint")
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.record_btn)
        buttons.addWidget(self.close_btn)
        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addLayout(form)
        layout.addWidget(self.status)
        layout.addLayout(buttons)
        if not self.devices:
            self.device.setEnabled(False)
            self.record_btn.setEnabled(False)
            self.status.setProperty("role", "warning")
            self.status.setText(
                "Aucun micro détecté. Branchez un micro (ou autorisez son accès dans les paramètres de "
                "confidentialité du système), puis rouvrez ce dialogue. Vous pouvez aussi importer un "
                "fichier audio enregistré ailleurs."
            )
        self.resize(520, 240)

    @property
    def recording(self) -> bool:
        return self._recorder is not None

    def toggle(self) -> None:
        if self.recording:
            self.stop()
        else:
            self.start()

    def start(self) -> bool:
        if not self.devices or not HAS_MULTIMEDIA:
            return False
        target = self._tmpdir / f"narration-{datetime.now():%Y%m%d-%H%M%S}.wav"
        self._input = QAudioInput(self.device.currentData(), self)
        self._session = QMediaCaptureSession(self)
        self._session.setAudioInput(self._input)
        self._recorder = QMediaRecorder(self)
        self._session.setRecorder(self._recorder)
        fmt = QMediaFormat(QMediaFormat.FileFormat.Wave)
        fmt.setAudioCodec(QMediaFormat.AudioCodec.Wave)
        self._recorder.setMediaFormat(fmt)
        self._recorder.setQuality(QMediaRecorder.Quality.HighQuality)
        self._recorder.setOutputLocation(QUrl.fromLocalFile(str(target)))
        self._recorder.durationChanged.connect(self._on_duration)
        self._recorder.errorOccurred.connect(self._on_error)
        self._recorder.recorderStateChanged.connect(self._on_state)
        self._recorder.record()
        self._target = target
        self.record_btn.setText("Arrêter")
        self.record_btn.setIcon(icons.icon("square"))
        self.device.setEnabled(False)
        self.status.setText("Enregistrement en cours…")
        return True

    def stop(self) -> None:
        """Demande l'arrêt ; le fichier est repris quand l'enregistreur a fini de l'écrire."""
        if self._recorder is None:
            return
        self.record_btn.setEnabled(False)
        self.status.setText("Finalisation du fichier…")
        self._recorder.stop()
        stopped = QMediaRecorder.RecorderState.StoppedState
        if self._recorder is not None and self._recorder.recorderState() == stopped:
            self._finish()

    def _on_state(self, state: Any) -> None:
        if state == QMediaRecorder.RecorderState.StoppedState and self._recorder is not None:
            self._finish()

    def _finish(self) -> None:
        recorder = self._recorder
        if recorder is None:
            return
        actual = recorder.actualLocation().toLocalFile() or str(self._target)
        self._recorder = None
        self._session = None
        self._input = None
        self.record_btn.setText("Enregistrer")
        self.record_btn.setIcon(icons.icon("mic"))
        self.record_btn.setEnabled(True)
        self.device.setEnabled(True)
        path = Path(actual)
        if path.is_file() and path.stat().st_size > 44:  # en-tête WAV seul : rien d'enregistré
            self.recorded_path = path
            self.accept()
            return
        self.status.setText("Aucun son n'a été enregistré : vérifiez le micro choisi.")

    def _on_duration(self, ms: int) -> None:
        self.elapsed.setText(f"{ms / 1000:.1f} s".replace(".", ","))

    def _on_error(self, _error: Any, message: str) -> None:
        self.status.setText(f"Erreur d'enregistrement : {message}")

    def reject(self) -> None:
        if self.recording:
            with contextlib.suppress(Exception):
                self._recorder.stop()
            self._recorder = None
        super().reject()

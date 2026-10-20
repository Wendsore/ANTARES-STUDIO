"""Lecture audio de prévisualisation (QtMultimedia), au mieux : sans sortie audio, l'éditeur fonctionne."""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QUrl

log = logging.getLogger(__name__)

try:  # QtMultimedia peut manquer (paquet allégé) ou échouer sans backend
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

    HAS_MULTIMEDIA = True
except Exception:  # noqa: BLE001
    HAS_MULTIMEDIA = False


class ClipPlayer:
    def __init__(self, path: Path, gain: float, parent: QObject | None):
        self.player: Any = QMediaPlayer(parent)
        self.output: Any = QAudioOutput(parent)
        self.player.setAudioOutput(self.output)
        self.output.setVolume(max(0.0, min(1.0, gain)))
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.started = False

    def play_from(self, seconds: float) -> None:
        self.player.setPosition(int(max(0.0, seconds) * 1000))
        self.player.play()
        self.started = True

    def stop(self) -> None:
        with contextlib.suppress(Exception):
            self.player.stop()
        self.started = False

    def dispose(self) -> None:
        self.stop()
        with contextlib.suppress(Exception):
            self.player.setSource(QUrl())
            self.player.deleteLater()
            self.output.deleteLater()


class ScenePlayback(QObject):
    """Démarre/arrête les clips d'une scène en fonction du temps de lecture de la timeline."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._players: list[tuple[Any, ClipPlayer]] = []  # (AudioClip, ClipPlayer)
        self.available = HAS_MULTIMEDIA
        self._fps = 30.0

    def prepare(self, clips: list[Any], resolve: Any, fps: float) -> None:
        self.stop()
        self._fps = fps
        if not self.available:
            return
        for clip in clips:
            if clip.muted or clip.gain <= 0:
                continue
            path = resolve(clip.asset_id)
            if path is None:
                continue
            try:
                self._players.append((clip, ClipPlayer(path, clip.gain, self)))
            except Exception as exc:  # noqa: BLE001
                log.warning("lecture audio indisponible pour %s : %s", clip.name, exc)

    def sync(self, frame: int) -> None:
        """À appeler à chaque tick de lecture : lance les clips dont la fenêtre contient ``frame``."""
        t = frame / self._fps
        for clip, player in self._players:
            start = clip.offset_frames / self._fps
            length = (clip.out_seconds - clip.in_seconds) if clip.out_seconds is not None else None
            end = start + length if length is not None else float("inf")
            inside = start <= t < end
            if inside and not player.started:
                player.play_from(clip.in_seconds + (t - start))
            elif not inside and player.started:
                player.stop()

    def stop(self) -> None:
        for _, player in self._players:
            player.dispose()
        self._players.clear()

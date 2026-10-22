"""Enregistrement d'une narration au micro : refus explicite sans micro, enregistrement réel sinon."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from antares_studio.app.main_window import MainWindow
from antares_studio.app.recorder import RecordDialog, input_devices
from antares_studio.rendering import ffmpeg as ff

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot, tmp_path: Path):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.show()
    qtbot.waitExposed(w)
    w.document.save(tmp_path / "Micro.antares")
    return w


def test_without_microphone_the_dialog_explains_and_cannot_record(qtbot) -> None:  # type: ignore[no-untyped-def]
    dlg = RecordDialog(devices=[])
    qtbot.addWidget(dlg)
    assert not dlg.record_btn.isEnabled() and "Aucun micro" in dlg.status.text()
    assert dlg.start() is False and dlg.recorded_path is None


@pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffprobe nécessaire pour mesurer la durée")
def test_real_recording_becomes_a_documented_clip(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    if not input_devices():  # interrogé après la création de l'application Qt
        pytest.skip("aucun micro sur cette machine")
    dlg = RecordDialog(window)
    qtbot.addWidget(dlg)
    assert dlg.start()
    qtbot.wait(1200)
    dlg.stop()
    qtbot.waitUntil(lambda: not dlg.recording, timeout=10000)
    assert dlg.recorded_path is not None, dlg.status.text()
    temp_dir = dlg.recorded_path.parent
    clip = window.narration.audio.record_narration(dlg)
    assert clip is not None and 0.9 < clip.duration_seconds < 2.5
    asset = window.document.project.asset(clip.asset_id)
    assert asset is not None and asset.path.startswith("audio/") and asset.path.endswith(".wav")
    assert asset.license.license == "own-work" and asset.license.redistribution_allowed
    assert not temp_dir.exists()  # le fichier temporaire est supprimé après la copie
    assert time.strftime("%Y") in asset.license.verified_on

"""Gate 6 (interface) — narration audio, sous-titres, timeline et export avec audio + SRT compagnon."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from antares_studio.app.main_window import MainWindow
from antares_studio.rendering import ffmpeg as ff
from tests.integration.test_audio import make_wav

pytestmark = pytest.mark.ui
needs_ffmpeg = pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg absent")


@pytest.fixture
def window(qtbot, tmp_path: Path):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    w.add_template_scene("moon_phases")
    w.document.scene.duration_frames = 150
    w.document.version += 1
    w.document.save(tmp_path / "Narration.antares")
    return w


def test_subtitles_tab_add_edit_and_timeline_row(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    tab = window.narration.subtitles
    window.document.set_frame(30)
    tab.add_at_current_frame()
    scene = window.document.scene
    assert (
        len(scene.subtitles) == 1
        and scene.subtitles[0].start_frame == 30
        and scene.subtitles[0].end_frame == 90
    )
    qtbot.wait(20)
    item = tab.table.item(0, 2)
    item.setText("Pourquoi la Lune change-t-elle de forme ?")
    assert scene.subtitles[0].text == "Pourquoi la Lune change-t-elle de forme ?"
    tab.table.item(0, 1).setText("1,50")
    assert scene.subtitles[0].end_frame == 45
    assert window.document.state().subtitle == "Pourquoi la Lune change-t-elle de forme ?"  # 30 ∈ [30, 45)
    window.document.set_frame(50)
    assert window.document.state().subtitle is None
    assert any(r.kind == "subtitles" for r in window.timeline.view.rows)
    window.act_undo.trigger()
    assert scene.subtitles[0].end_frame == 90
    tab.table.selectRow(0)
    tab.remove_selected()
    assert scene.subtitles == []


def test_subtitles_import_export_roundtrip(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    srt = tmp_path / "voix.srt"
    srt.write_text("1\n00:00:00,500 --> 00:00:02,000\nÉclairée par le Soleil\n", encoding="utf-8")
    assert window.narration.subtitles.import_path(srt)
    scene = window.document.scene
    assert (
        len(scene.subtitles) == 1
        and scene.subtitles[0].start_frame == 15
        and scene.subtitles[0].end_frame == 60
    )
    bad = tmp_path / "bad.srt"
    bad.write_bytes("1\n00:00:00,500 --> 00:00:02,000\nlatin-1 é\n".encode("latin-1"))
    seen: list[str] = []
    from PySide6.QtWidgets import QMessageBox

    orig = QMessageBox.critical
    QMessageBox.critical = staticmethod(lambda *a, **k: seen.append(a[2]))  # type: ignore[method-assign]
    try:
        assert not window.narration.subtitles.import_path(bad)
    finally:
        QMessageBox.critical = orig  # type: ignore[method-assign]
    assert seen and "UTF-8" in seen[0]


@needs_ffmpeg
def test_audio_import_place_drag_and_export_with_srt(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    src = tmp_path / "narration.wav"
    make_wav(src, 2.0, lead_silence=0.0)
    window.document.set_frame(15)
    clip = window.narration.audio.add_audio_file(src)
    assert clip is not None and clip.offset_frames == 15 and abs(clip.duration_seconds - 2.0) < 0.05
    assert (window.document.root / "audio" / "narration.wav").is_file()
    qtbot.wait(50)
    view = window.timeline.view
    assert any(r.kind == "audio" for r in view.rows)
    assert clip.asset_id in view.waveforms and len(view.waveforms[clip.asset_id][0]) == 100
    # glisser le clip dans la timeline : décalage modifié en une étape d'annulation
    row_index = next(i for i, r in enumerate(view.rows) if r.kind == "audio")
    from antares_studio.app.timeline_dock import ROW_H, RULER_H

    y = int(RULER_H + ROW_H * row_index + ROW_H / 2)
    x0 = int(view.frame_to_x(20))
    QTest.mousePress(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x0, y))
    QTest.mouseMove(view, QPoint(x0 + int(10 * view.px_per_frame), y))
    QTest.mouseRelease(
        view,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(x0 + int(10 * view.px_per_frame), y),
    )
    assert clip.offset_frames == 25
    window.act_undo.trigger()
    assert clip.offset_frames == 15
    # sous-titre + export : audio présent et SRT compagnon
    window.narration.subtitles.add_at_current_frame()
    from antares_studio.app.export_dialog import ExportDialog

    dlg = ExportDialog(window.document, window.settings, window)
    qtbot.addWidget(dlg)
    dlg.profile.setCurrentIndex(dlg.profile.findData("draft_720p"))
    out = tmp_path / "narr.mp4"
    dlg.path_edit.setText(str(out))
    dlg.start()
    qtbot.waitUntil(lambda: dlg._worker is None, timeout=90000)
    assert dlg.render_result is not None, dlg.status.text()
    assert dlg.render_result.probe.has_audio and dlg.render_result.probe.nb_frames == 150
    assert (
        (tmp_path / "narr.srt").read_text(encoding="utf-8").startswith("1\n00:00:00,500 --> 00:00:02,500\n")
    )
    manifest = json.loads(dlg.render_result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["result"]["has_audio"] is True
    # lecture : la préparation audio n'échoue pas même sans sortie audio
    window.timeline.play()
    qtbot.wait(120)
    window.timeline.pause()


def test_audio_tab_edits_clip_fields(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.domain.commands import AddAudioClip
    from antares_studio.domain.model import Asset, AudioClip

    scene = window.document.scene
    window.document.project.assets.append(Asset(id="asset-0123456789ab", path="audio/x.wav", kind="audio"))
    window.document.push(AddAudioClip(scene.id, AudioClip.create("asset-0123456789ab", "Voix")))
    qtbot.wait(20)
    tab = window.narration.audio
    assert tab.table.rowCount() == 1
    tab.table.cellWidget(0, 2).setValue(0.5)
    assert scene.audio[0].gain == 0.5
    tab.table.cellWidget(0, 1).setValue(1.0)
    assert scene.audio[0].offset_frames == 30
    tab.table.cellWidget(0, 5).setChecked(True)
    assert scene.audio[0].muted is True
    tab.table.selectRow(0)
    window.document.set_frame(45)
    tab.place_at_current_frame()
    assert scene.audio[0].offset_frames == 45
    tab.remove_selected()
    assert scene.audio == []
    window.act_undo.trigger()
    assert len(scene.audio) == 1

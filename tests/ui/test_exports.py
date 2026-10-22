"""File d'exports en arrière-plan, aperçu rapide, image PNG, profils groupés, rôles audio et atténuation."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from antares_studio.app.export_dialog import ExportDialog, profile_items, with_video_suffix
from antares_studio.app.export_queue import ExportJob
from antares_studio.app.main_window import MainWindow
from antares_studio.domain.commands import AddAudioClip
from antares_studio.domain.model import AudioClip
from antares_studio.persistence.schema import project_to_dict
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.plan import PROFILES, build_render_plan

pytestmark = pytest.mark.ui
needs_ffmpeg = pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg absent")


@pytest.fixture
def window(qtbot):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    return w


def _short_scene(window: MainWindow, frames: int = 12) -> None:
    window.add_template_scene("moon_phases")
    window.document.scene.duration_frames = frames  # type: ignore[union-attr]
    window.document.version += 1


def test_profiles_are_grouped_and_suffix_follows_the_format(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    items = profile_items()
    assert sum(1 for _t, pid in items if pid is None) == 4  # Usage | Plateforme | Format | Montage | Audio
    assert {pid for _t, pid in items if pid} == set(PROFILES)
    dlg = ExportDialog(window.document, window.settings, window, queue=window.export_queue)
    qtbot.addWidget(dlg)
    dlg.path_edit.setText(str(tmp_path / "Lune v1.2 - Orbite.mp4"))
    dlg.profile.setCurrentIndex(dlg.profile.findData("gif_480"))
    assert dlg.path_edit.text().endswith("Lune v1.2 - Orbite.gif")  # les autres points sont gardés
    assert "Sans son" in dlg.profile_hint.text() and "15" in dlg.profile_hint.text()
    dlg.profile.setCurrentIndex(dlg.profile.findData("vertical_1080x1920"))
    assert "bandes noires" in dlg.profile_hint.text()
    assert dlg.path_edit.text().endswith(".mp4")
    assert with_video_suffix("a.WEBM", ".gif") == "a.gif" and with_video_suffix("a", ".mp4") == "a.mp4"
    assert not dlg.background_btn.isHidden()
    # transparence : seulement pour les profils à canal alpha ; ProRes 4444 la coche d'office
    assert not dlg.transparent.isEnabled()
    dlg.profile.setCurrentIndex(dlg.profile.findData("prores_4444"))
    assert dlg.transparent.isEnabled() and dlg.transparent.isChecked()
    assert dlg.path_edit.text().endswith(".mov")
    dlg.profile.setCurrentIndex(dlg.profile.findData("png_sequence"))
    assert dlg.path_edit.text().endswith("Lune v1.2 - Orbite")  # un dossier
    assert not dlg.all_scenes.isEnabled() and "image_00000.png" in dlg.profile_hint.text()
    dlg.profile.setCurrentIndex(dlg.profile.findData("audio_mp3"))
    assert dlg.path_edit.text().endswith(".mp3") and not dlg.transparent.isEnabled()
    assert "Bande-son seule" in dlg.profile_hint.text() and "−14 LUFS" in dlg.profile_hint.text()
    assert any(t.endswith("son seul") for t, pid in items if pid == "audio_wav")


@pytest.mark.render
@needs_ffmpeg
def test_background_export_uses_a_snapshot_and_frees_the_editor(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _short_scene(window, 12)
    dlg = ExportDialog(window.document, window.settings, window, queue=window.export_queue)
    qtbot.addWidget(dlg)
    dlg.profile.setCurrentIndex(dlg.profile.findData("draft_720p"))
    out = tmp_path / "fond.mp4"
    dlg.path_edit.setText(str(out))
    dlg.start_in_background()
    job = dlg.queued_job
    assert job is not None and dlg.result() == dlg.DialogCode.Accepted
    # l'utilisateur continue d'éditer : la vidéo garde l'état du projet au moment de l'envoi
    window.document.scene.duration_frames = 40  # type: ignore[union-attr]
    window.add_node_of_kind("circle")
    qtbot.waitUntil(lambda: job.status in ("done", "failed"), timeout=60000)
    assert job.status == "done", job.message
    assert job.result is not None and job.result.probe.nb_frames == 12
    assert out.is_file() and window.ui_counters["exports"] == 1
    window.show_exports()
    panel = window.exports
    assert panel.list.count() == 1 and "Terminé" in panel.list.item(0).text()
    opened: list[str] = []
    window.export_queue.opener = lambda url: opened.append(url.toLocalFile()) or True
    assert panel.open_btn.isEnabled() and panel.open_selected_folder()
    assert [Path(p) for p in opened] == [tmp_path]  # QUrl : barres obliques, y compris sous Windows
    panel.clear_finished()
    assert panel.list.count() == 0 and window.export_queue.jobs == []


@pytest.mark.render
@needs_ffmpeg
def test_queue_runs_one_job_at_a_time_and_cancels(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _short_scene(window, 60)
    doc = window.document
    queue = window.export_queue

    def job(name: str, profile: str = "final_1080p") -> ExportJob:
        plan = build_render_plan(doc.project, doc.scene.id, profile, str(tmp_path / name))  # type: ignore[union-attr]
        return ExportJob.from_document(doc, name, tmp_path / name, plan)

    first, second, third = job("un.mp4"), job("deux.mp4"), job("trois.mp4", "draft_720p")
    for j in (first, second, third):
        queue.submit(j)
    assert first.status == "running" and second.status == "waiting" and third.status == "waiting"
    queue.cancel(second)  # en attente : retiré sans être rendu
    assert second.status == "cancelled"
    qtbot.waitUntil(lambda: first.done_frames > 0, timeout=30000)
    queue.cancel(first)  # en cours : arrêté, aucun fichier partiel
    qtbot.waitUntil(lambda: third.status in ("done", "failed"), timeout=60000)
    assert first.status == "cancelled" and third.status == "done", third.message
    assert not (tmp_path / "un.mp4").exists() and not (tmp_path / "deux.mp4").exists()
    assert (tmp_path / "trois.mp4").is_file() and not list(tmp_path.glob(".*.part"))
    assert not queue.busy and queue.pending() == []


@pytest.mark.render
@needs_ffmpeg
def test_quick_preview_renders_360p_and_opens_it(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    _short_scene(window, 10)
    opened: list[str] = []
    window.export_queue.opener = lambda url: opened.append(url.toLocalFile()) or True
    job = window.quick_preview()
    assert job is not None and window.act_quick_preview.shortcut().toString() == "Ctrl+Shift+E"
    qtbot.waitUntil(lambda: job.status in ("done", "failed"), timeout=60000)
    assert job.status == "done", job.message
    assert job.result is not None and (job.result.probe.width, job.result.probe.height) == (640, 360)
    assert [Path(p) for p in opened] == [job.output_path]
    job.output_path.unlink()


def test_export_still_writes_the_current_frame_at_project_size(window, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    window.add_template_scene("moon_phases")
    window.document.set_frame(30)
    target = window.export_still(str(tmp_path / "vignette"))
    assert target == tmp_path / "vignette.png"
    img = QImage(str(target))
    c = window.document.project.canvas
    assert (img.width(), img.height()) == (c.width, c.height)
    colors = {img.pixel(x, y) for x in range(0, c.width, 97) for y in range(0, c.height, 89)}
    assert len(colors) > 1  # la scène est dessinée, pas une image vide


def test_audio_role_and_ducking_are_undoable_and_saved_only_when_changed(window) -> None:  # type: ignore[no-untyped-def]
    doc = window.document
    scene = doc.scene
    doc.push(AddAudioClip(scene.id, AudioClip.create("asset-0123456789ab", "Musique de fond")))
    audio = window.narration.audio
    assert audio.COLS[-1] == "Rôle"
    combo = audio.table.cellWidget(0, len(audio.COLS) - 1)
    assert combo.currentData() == "voice"
    combo.setCurrentIndex(combo.findData("music"))
    assert scene.audio[0].role == "music"
    assert project_to_dict(doc.project)["scenes"][-1]["audio"][0]["role"] == "music"
    doc.undo.undo()
    assert scene.audio[0].role == "voice"
    assert audio.ducking.isChecked() and "ducking" not in doc.project.settings
    audio.ducking.setChecked(False)
    assert doc.project.settings["ducking"] is False
    assert build_render_plan(doc.project, scene.id, "draft_720p", "x.mp4").ducking is False
    doc.undo.undo()
    assert "ducking" not in doc.project.settings and audio.ducking.isChecked()

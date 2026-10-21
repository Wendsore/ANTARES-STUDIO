"""Gate 7 — planète 3D rendue par Blender (facultatif) intégrée à une scène 2D avec audio ; absence tolérée."""

from __future__ import annotations

from pathlib import Path

import pytest

from antares_studio.app.diagnostics import diagnostics_report
from antares_studio.app.main_window import MainWindow
from antares_studio.domain.model import Asset, Canvas, Project, Scene
from antares_studio.persistence.schema import project_from_dict, project_to_dict
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.blender import BlenderError, find_blender, render_planet_sequence
from antares_studio.rendering.exporter import export_video
from antares_studio.rendering.plan import build_render_plan
from antares_studio.rendering.qt_painter import ImageCache, render_state_to_image, sequence_frame_path
from antares_studio.timeline.evaluator import evaluate
from tests.integration.test_audio import make_wav
from tests.unit.helpers import make_node

pytestmark = pytest.mark.slow
needs_blender = pytest.mark.skipif(find_blender() is None, reason="blender absent")
needs_ffmpeg = pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg absent")


def test_sequence_frame_path_wraps_and_rounds(tmp_path: Path) -> None:
    assert sequence_frame_path(tmp_path, 0.0, 10).name == "frame_0001.png"
    assert sequence_frame_path(tmp_path, 9.4, 10).name == "frame_0010.png"
    assert sequence_frame_path(tmp_path, 10.0, 10).name == "frame_0001.png"  # boucle
    assert sequence_frame_path(tmp_path, 3.0, 0).name == "frame_0001.png"  # jamais de division par zéro


def test_missing_blender_is_reported_not_fatal(qapp, monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("ANTARES_BLENDER", raising=False)
    assert find_blender() is None
    assert "Blender : absent" in diagnostics_report()
    with pytest.raises(BlenderError, match="introuvable"):
        render_planet_sequence(tmp_path / "out", 2, 64, 64)
    # une séquence absente se dessine comme un cadre explicite, la scène 2D reste exportable
    project = Project.create("Sans Blender", Canvas(640, 360, 30, 1))
    scene = Scene.create("S", duration_frames=3)
    project.scenes.append(scene)
    project.assets.append(Asset(id="asset-0000000000ff", path="assets/planete", kind="sequence"))
    node = make_node("image_sequence", "Planète", position=[320.0, 180.0])
    node.params.update({"sequence_asset_id": "asset-0000000000ff", "frame_count": 4})
    scene.nodes.append(node)
    img = render_state_to_image(
        evaluate(project, scene.id, 1), project.canvas, 640, 360, lambda _a: None, ImageCache()
    )
    edge = max(img.pixelColor(x, 180).red() for x in range(118, 124))
    assert edge > 150  # bordure rouge du cadre « séquence absente » (largeur 400 px centrée)


@needs_blender
@needs_ffmpeg
def test_gate7_blender_planet_in_2d_scene_with_audio(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.app.blender_dialog import insert_sequence_node

    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.document.save(tmp_path / "Planete.antares")
    scene = w.document.scene
    assert scene is not None
    scene.duration_frames = 6
    w.document.version += 1
    seen: list[int] = []
    folder = w.document.paths.root / "assets" / "planete-3d-test"  # type: ignore[union-attr]
    files = render_planet_sequence(
        folder, 6, 96, 96, turns=1.0, samples=4, progress=lambda i, _n: seen.append(i)
    )
    assert len(files) == 6 and seen == [1, 2, 3, 4, 5, 6]
    node = insert_sequence_node(w.document, "assets/planete-3d-test", 6, 200, "Planète 3D")
    star = w.add_node_of_kind("text")
    w.document.set_node_properties(star.id, {"params.text": "Jour et nuit", "position.y": 900.0})  # type: ignore[union-attr]
    voice = tmp_path / "voix.wav"
    make_wav(voice, 0.3)
    w.document.set_frame(0)
    clip = w.narration.audio.add_audio_file(voice)
    assert clip is not None
    # la séquence suit la timeline : image 0 → frame_0001, dernière image → frame_0006 ; durée identique
    st0 = evaluate(w.document.project, scene.id, 0).node(node.id)
    st5 = evaluate(w.document.project, scene.id, 5).node(node.id)
    assert round(float(st0.params["frame_index"])) == 0 and round(float(st5.params["frame_index"])) == 5
    frame_a = render_state_to_image(
        evaluate(w.document.project, scene.id, 0),
        w.document.project.canvas,
        1920,
        1080,
        w.document.resolve_asset,
        ImageCache(),
    )
    frame_b = render_state_to_image(
        evaluate(w.document.project, scene.id, 3),
        w.document.project.canvas,
        1920,
        1080,
        w.document.resolve_asset,
        ImageCache(),
    )
    assert (
        frame_a.pixelColor(960, 540).alpha() == 255 and frame_a != frame_b
    )  # planète visible et en rotation
    # aller-retour projet et export MP4 avec audio
    assert project_from_dict(project_to_dict(w.document.project)).assets[-2].kind == "sequence"
    out = tmp_path / "planete.mp4"
    from antares_studio.rendering.exporter import audio_plans_for_scene

    audio = audio_plans_for_scene(w.document.project, scene.id, w.document.resolve_asset)
    plan = build_render_plan(w.document.project, scene.id, "draft_720p", str(out), audio=audio)
    result = export_video(w.document.project, plan, assets=w.document.resolve_asset)
    assert result.probe.nb_frames == 6 and result.probe.has_audio
    w.document.undo.mark_clean()  # la fermeture est gérée par qtbot (sans boîte « enregistrer ? »)

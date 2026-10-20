"""REN-01, REN-02, REN-03, REN-07, REN-08, REN-12, SEC-03 — export MP4 réel vérifié par ffprobe."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import RenderCancelledError, export_video
from antares_studio.rendering.plan import build_render_plan
from antares_studio.rendering.qt_painter import render_state_to_image
from antares_studio.timeline.evaluator import evaluate
from antares_studio.timeline.presets import apply_preset
from tests.unit.helpers import earth_moon_project, make_node

pytestmark = pytest.mark.render

FFMPEG = ff.find_ffmpeg()
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg absent")


@pytest.fixture(scope="module")
def qapp():  # type: ignore[no-untyped-def]
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


def _project(duration: int = 150):  # type: ignore[no-untyped-def]
    project, scene, earth, moon = earth_moon_project(duration_frames=duration)
    scene.tracks += apply_preset(
        "orbit",
        moon,
        {
            "center_x": 960,
            "center_y": 540,
            "radius": 300,
            "duration_frames": duration,
            "samples_per_turn": 360,
        },
    )
    arrow = make_node("arrow", "Vitesse", parent_id=moon.id)
    arrow.params["end"] = [0.0, -100.0]
    scene.nodes.append(arrow)
    label = make_node("text", "Légende", position=[960.0, 1000.0])
    label.params["text"] = "Schéma non à l'échelle — Terre et Lune"
    scene.nodes.append(label)
    scene.tracks += apply_preset("appear", label, {"duration_frames": 15})
    return project, scene, earth, moon


@needs_ffmpeg
def test_ren01_02_12_export_5s_1080p_verified(tmp_path: Path, qapp) -> None:  # type: ignore[no-untyped-def]
    project, scene, _, moon = _project(150)
    out = tmp_path / "sortie été.mp4"
    plan = build_render_plan(project, scene.id, "final_1080p", str(out))
    seen: list[tuple[int, int]] = []
    result = export_video(project, plan, progress=lambda i, n: seen.append((i, n)))
    assert out.is_file() and result.output_path == out
    assert (result.probe.width, result.probe.height) == (1920, 1080)
    assert result.probe.nb_frames == 150
    assert result.probe.fps == 30
    assert abs(result.probe.duration - 5.0) < 0.05
    assert result.probe.video_codec == "h264"
    assert seen[-1] == (150, 150)
    assert ff.decode_check(FFMPEG, out)  # type: ignore[arg-type]
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["result"]["nb_frames"] == 150 and manifest["plan"]["profile_id"] == "final_1080p"
    assert not list(tmp_path.glob(".*.part"))


@needs_ffmpeg
def test_ren02_draft_720p(tmp_path: Path, qapp) -> None:  # type: ignore[no-untyped-def]
    project, scene, _, _ = _project(30)
    plan = build_render_plan(project, scene.id, "draft_720p", str(tmp_path / "d.mp4"))
    result = export_video(project, plan)
    assert (result.probe.width, result.probe.height) == (1280, 720)
    assert result.probe.nb_frames == 30


def test_ren03_keyframes_match_logical_state(qapp) -> None:  # type: ignore[no-untyped-def]
    project, scene, earth, moon = _project(150)
    for frame, expected in ((0, (1260, 540)), (75, (660, 540)), (149, None)):
        state = evaluate(project, scene.id, frame)
        img = render_state_to_image(state, project.canvas, 1920, 1080)
        ms = state.node(moon.id)
        if expected:
            assert ms.position == pytest.approx(expected, abs=1e-6)
        # échantillon décalé de 12 px vers la gauche : dans la Lune (rayon 25), hors de la flèche verticale
        x, y = int(ms.position[0]) - 12, int(ms.position[1])
        c = img.pixelColor(x, y)
        assert (c.red(), c.green(), c.blue()) == (0xD9, 0xD9, 0xD9), (frame, c.name())
        ex, ey = int(earth.position[0]), int(earth.position[1])
        ce = img.pixelColor(ex, ey)
        assert (ce.red(), ce.green(), ce.blue()) == (0x26, 0x77, 0xB8)
        bg = img.pixelColor(10, 10)
        assert (bg.red(), bg.green(), bg.blue()) == (0x0B, 0x10, 0x20)


@needs_ffmpeg
def test_ren08_cancel_keeps_previous_export(tmp_path: Path, qapp) -> None:  # type: ignore[no-untyped-def]
    project, scene, _, _ = _project(300)
    out = tmp_path / "film.mp4"
    out.write_bytes(b"ancien export valide")
    cancel = threading.Event()

    def progress(i: int, n: int) -> None:
        if i >= n // 2:
            cancel.set()

    plan = build_render_plan(project, scene.id, "draft_720p", str(out))
    with pytest.raises(RenderCancelledError):
        export_video(project, plan, progress=progress, cancel=cancel)
    assert out.read_bytes() == b"ancien export valide"
    assert not list(tmp_path.glob(".*.part"))


def test_ren07_missing_ffmpeg_gives_actionable_error(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    project, scene, _, _ = _project(10)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv(ff.ENV_FFMPEG, raising=False)
    plan = build_render_plan(project, scene.id, "draft_720p", str(tmp_path / "x.mp4"))
    with pytest.raises(ff.FFmpegNotFoundError, match="introuvable"):
        export_video(project, plan)
    assert not (tmp_path / "x.mp4").exists()


def test_sec03_ffmpeg_arguments_are_a_list_without_shell(tmp_path: Path) -> None:
    from antares_studio.rendering.exporter import _build_ffmpeg_command

    project, scene, _, _ = _project(10)
    evil = tmp_path / "a; rm -rf ~.mp4"
    plan = build_render_plan(project, scene.id, "draft_720p", str(evil))
    cmd = _build_ffmpeg_command(Path("/usr/bin/ffmpeg"), plan, evil)
    assert isinstance(cmd, list) and cmd[-1] == str(evil)
    assert "-nostdin" in cmd and "libx264" in cmd


def test_empty_range_rejected() -> None:
    project, scene, _, _ = _project(10)
    with pytest.raises(ValueError, match="vide"):
        build_render_plan(project, scene.id, "draft_720p", "x.mp4", start_frame=10)

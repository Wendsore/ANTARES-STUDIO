"""Export complet (toutes les scènes) : enchaînement sans ré-encodage, audio homogène, SRT fusionné."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from antares_studio.app.main import main
from antares_studio.domain.model import Asset, AudioClip, Canvas, Scene, Subtitle
from antares_studio.persistence.store import ProjectStore
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import RenderError, export_project
from antares_studio.resources.templates import create_project
from tests.integration.test_audio import make_wav

pytestmark = pytest.mark.render
needs_ffmpeg = pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg/ffprobe absents")


def _three_scene_project(tmp_path: Path):  # type: ignore[no-untyped-def]
    project = create_project("Complet", Canvas(1280, 720, 30, 1), "intro", 1)
    s1 = project.scenes[0]
    s1.duration_frames = 12
    s1.subtitles.append(Subtitle.create(3, 9, "Première scène"))
    s2 = Scene.create("Silence", duration_frames=9)
    s3 = Scene.create("Voix", duration_frames=15)
    s3.subtitles.append(Subtitle.create(0, 15, "Troisième scène"))
    project.scenes += [s2, s3]
    wav = tmp_path / "voix.wav"
    make_wav(wav, 1.0)
    root = ProjectStore().create(tmp_path / "Complet", project).root
    (root / "audio").mkdir(exist_ok=True)
    (root / "audio" / "voix.wav").write_bytes(wav.read_bytes())
    project.assets.append(Asset(id="asset-00000000aaaa", path="audio/voix.wav", kind="audio"))
    s3.audio.append(AudioClip.create("asset-00000000aaaa", "voix", offset_frames=0, duration_seconds=1.0))
    ProjectStore().save_atomic(project, root / "project.json")
    return project, root


@needs_ffmpeg
def test_export_project_concatenates_all_scenes(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, root = _three_scene_project(tmp_path)
    seen: list[tuple[int, int]] = []
    out = tmp_path / "complet.mp4"
    result = export_project(
        project,
        "draft_720p",
        str(out),
        progress=lambda i, n: seen.append((i, n)),
        assets=lambda aid: (root / "audio" / "voix.wav") if aid == "asset-00000000aaaa" else None,
    )
    assert (
        result.probe.nb_frames == 36
        and result.probe.has_audio
        and (result.probe.width, result.probe.height) == (1280, 720)
    )
    assert abs(result.probe.duration - 36 / 30) < 0.1  # pas de dérive audio/vidéo
    assert seen[-1] == (36, 36) and all(n == 36 for _i, n in seen)
    assert [p.scene_name for p in result.plans] == ["Scène 1", "Silence", "Voix"]
    assert [p.silent_audio for p in result.plans] == [True, True, False]
    srt = (tmp_path / "complet.srt").read_text(encoding="utf-8")
    assert "00:00:00,100 --> 00:00:00,300\nPremière scène" in srt
    assert "00:00:00,700 --> 00:00:01,200\nTroisième scène" in srt  # décalée de 21 images
    assert (tmp_path / "complet.credits.txt").is_file()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert [s["frames"] for s in manifest["scenes"]] == [12, 9, 15] and manifest["result"]["nb_frames"] == 36
    assert not list(tmp_path.glob(".*.part")) and not list(tmp_path.glob(".antares-export-*"))
    assert ff.decode_check(ff.find_ffmpeg(), out)  # type: ignore[arg-type]


@needs_ffmpeg
def test_export_project_cli_flag(qapp, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    _project, root = _three_scene_project(tmp_path)
    out = tmp_path / "cli-complet.mp4"
    code = main(
        ["antares-studio", "--export", str(root), str(out), "--profile", "draft_720p", "--all-scenes"]
    )
    assert code == 0, capsys.readouterr().err
    assert out.is_file() and "36 images" in capsys.readouterr().out


def test_export_project_without_scene_is_an_error(qapp) -> None:  # type: ignore[no-untyped-def]
    project = create_project("Vide", Canvas(1280, 720, 30, 1), "", 1)
    project.scenes.clear()
    with pytest.raises(RenderError):
        export_project(project, "draft_720p", "/tmp/x.mp4")


@needs_ffmpeg
def test_vertical_project_exports_vertical_video(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.rendering.exporter import export_video
    from antares_studio.rendering.plan import build_render_plan

    project = create_project("Vertical", Canvas(1080, 1920, 30, 1), "intro", 1)
    project.scenes[0].duration_frames = 6
    plan = build_render_plan(project, project.scenes[0].id, "draft_720p", str(tmp_path / "v.mp4"))
    result = export_video(project, plan, write_manifest=False)
    assert (result.probe.width, result.probe.height) == (720, 1280)


def decode_frame_rgb(video: Path, index: int, width: int, height: int) -> bytes:
    """Image ``index`` de la vidéo décodée par FFmpeg (RGB 8 bits), pour mesurer ce qui a été encodé."""
    import subprocess

    ffmpeg = ff.require_ffmpeg()
    out = subprocess.run(
        [
            str(ffmpeg),
            "-v",
            "error",
            "-i",
            str(video),
            "-vf",
            f"select=eq(n\\,{index})",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    ).stdout
    assert len(out) == width * height * 3
    return out


@needs_ffmpeg
def test_export_project_renders_scene_transition(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Fondu enchaîné rouge → bleu sur 10 images : mélange mesuré au milieu, durée totale inchangée."""
    from antares_studio.domain.model import SceneTransition

    project = create_project("Transition", Canvas(1280, 720, 30, 1), "", 1)
    red = project.scenes[0]
    red.duration_frames, red.background = 12, "#FF0000"
    blue = Scene.create("Bleu", duration_frames=12, background="#0000FF")
    blue.transition = SceneTransition("fade", 9)
    project.scenes.append(blue)
    out = tmp_path / "fondu.mp4"
    result = export_project(project, "draft_720p", str(out))
    assert result.probe.nb_frames == 24
    w, h = result.probe.width, result.probe.height

    def center(index: int) -> tuple[int, int, int]:
        px = decode_frame_rgb(out, index, w, h)
        i = (h // 2 * w + w // 2) * 3
        return px[i], px[i + 1], px[i + 2]

    r0, _g0, b0 = center(11)  # dernière image rouge
    rm, _gm, bm = center(12 + 4)  # milieu du fondu (u = 0,5)
    r1, _g1, b1 = center(12 + 11)  # après le fondu : bleu
    assert r0 > 200 and b0 < 50
    assert 90 < rm < 170 and 90 < bm < 170  # tolérance : compression H.264 et conversion YUV
    assert r1 < 50 and b1 > 200

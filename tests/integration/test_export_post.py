"""Post-production à l'export, avec le vrai FFmpeg : 1440p/4K, ProRes, transparence, séquence PNG,
bande-son seule, volume normalisé (mesuré en EBU R128), effets et filtres dans le fichier final."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtGui import QImage

from antares_studio.domain.model import Asset, AudioClip, Canvas, Scene
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import (
    LOUDNESS_FILTER,
    SEQUENCE_AUDIO,
    RenderError,
    _build_ffmpeg_command,
    audio_plans_for_scene,
    export_project,
    export_video,
)
from antares_studio.rendering.plan import PROFILES, build_render_plan, output_size
from tests.integration.test_audio import make_wav
from tests.integration.test_export_project import decode_frame_rgb
from tests.unit.helpers import earth_moon_project

pytestmark = pytest.mark.render
FFMPEG = ff.find_ffmpeg()
FFPROBE = ff.find_ffprobe(ffmpeg=FFMPEG) if FFMPEG else None
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None or FFPROBE is None, reason="ffmpeg/ffprobe absents")
ASSET = "asset-0123456789ab"


def _has(codec: str) -> bool:
    return FFMPEG is not None and ff.has_encoder(FFMPEG, codec)


def _with_voice(project, scene, src: Path, gain: float = 1.0):  # type: ignore[no-untyped-def]
    project.assets.append(Asset(id=ASSET, path="audio/voix.wav", kind="audio"))
    scene.audio.append(AudioClip.create(ASSET, "Voix", gain=gain))
    return audio_plans_for_scene(project, scene.id, lambda _i: src)


def _stream(path: Path, kind: str) -> dict:  # type: ignore[type-arg]
    out = subprocess.run(
        [str(FFPROBE), "-v", "error", "-print_format", "json", "-show_streams", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return next(s for s in json.loads(out.stdout)["streams"] if s["codec_type"] == kind)


def _integrated_lufs(path: Path) -> float:
    out = subprocess.run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-map",
            "0:a",
            "-af",
            "ebur128",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out.stderr)[-1])


# --- plans (sans FFmpeg) ------------------------------------------------------------------------------
def test_new_profiles_sizes_and_capabilities() -> None:
    canvas = Canvas(1920, 1080)
    assert output_size(PROFILES["final_1440p"], canvas) == (2560, 1440)
    assert output_size(PROFILES["final_2160p"], canvas) == (3840, 2160)
    assert output_size(PROFILES["final_2160p"], Canvas(1080, 1920)) == (2160, 3840)  # vertical
    assert (
        PROFILES["prores_4444"].alpha and PROFILES["png_sequence"].alpha and not PROFILES["prores_hq"].alpha
    )
    assert PROFILES["png_sequence"].suffix == "" and not PROFILES["png_sequence"].has_audio
    assert not PROFILES["audio_wav"].has_video and PROFILES["audio_mp3"].suffix == ".mp3"
    project, scene, *_ = earth_moon_project(duration_frames=10)
    with pytest.raises(ValueError, match="transparence"):
        build_render_plan(project, scene.id, "final_1080p", "x.mp4", transparent=True)
    assert build_render_plan(project, scene.id, "audio_wav", "x.wav").silent_audio  # silence, jamais vide


def test_loudness_filter_is_on_by_default_and_follows_the_setting() -> None:
    project, scene, *_ = earth_moon_project(duration_frames=10)
    clip = (
        __import__("antares_studio.rendering.plan", fromlist=["AudioClipPlan"]).AudioClipPlan("/v.wav", 0),
    )
    cmd = " ".join(
        _build_ffmpeg_command(
            Path("ffmpeg"), build_render_plan(project, scene.id, "draft_720p", "o.mp4", audio=clip), Path("o")
        )
    )
    assert LOUDNESS_FILTER in cmd and "I=-14" in cmd and "TP=-1.5" in cmd
    project.settings["loudnorm"] = False
    cmd = " ".join(
        _build_ffmpeg_command(
            Path("ffmpeg"), build_render_plan(project, scene.id, "draft_720p", "o.mp4", audio=clip), Path("o")
        )
    )
    assert "loudnorm" not in cmd
    audio_only = _build_ffmpeg_command(
        Path("ffmpeg"), build_render_plan(project, scene.id, "audio_wav", "o.wav", audio=clip), Path("o")
    )
    assert "pipe:0" not in audio_only and "0:v:0" not in audio_only and "pcm_s16le" in audio_only


# --- fichiers réels -----------------------------------------------------------------------------------
@needs_ffmpeg
def test_loudness_is_normalized_to_minus_14_lufs(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=150)  # 5 s
    src = tmp_path / "voix.wav"
    make_wav(src, 5.0)
    audio = _with_voice(project, scene, src, gain=0.1)  # voix très faible : ≈ −33 LUFS
    loud = export_video(
        project,
        build_render_plan(project, scene.id, "audio_wav", str(tmp_path / "n.wav"), audio=audio),
        assets=lambda _i: src,
    )
    project.settings["loudnorm"] = False
    raw = export_video(
        project,
        build_render_plan(project, scene.id, "audio_wav", str(tmp_path / "b.wav"), audio=audio),
        assets=lambda _i: src,
    )
    assert _integrated_lufs(loud.output_path) == pytest.approx(-14.0, abs=1.0)
    assert _integrated_lufs(raw.output_path) < -25.0
    assert abs(loud.probe.duration - 5.0) < 0.05 and loud.probe.width == 0


@needs_ffmpeg
@pytest.mark.skipif(not _has("libmp3lame"), reason="encodeur MP3 absent")
def test_audio_only_mp3_and_whole_project_soundtrack(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=60)  # 2 s
    src = tmp_path / "voix.wav"
    make_wav(src, 1.0)
    audio = _with_voice(project, scene, src)
    mp3 = export_video(
        project,
        build_render_plan(project, scene.id, "audio_mp3", str(tmp_path / "s.mp3"), audio=audio),
        assets=lambda _i: src,
    )
    assert mp3.probe.audio_codec == "mp3" and abs(mp3.probe.duration - 2.0) < 0.1
    project.scenes.append(Scene.create("Silence", duration_frames=30))  # 1 s sans clip : silence
    whole = export_project(project, "audio_wav", str(tmp_path / "tout.wav"), assets=lambda _i: src)
    assert whole.probe.audio_codec == "pcm_s16le" and abs(whole.probe.duration - 3.0) < 0.1


@needs_ffmpeg
@pytest.mark.skipif(not _has("prores_ks"), reason="ProRes absent de FFmpeg")
def test_prores_hq_and_4444_with_alpha(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=6)
    scene.background = "#3366CC"
    src = tmp_path / "voix.wav"
    make_wav(src, 0.2)
    audio = _with_voice(project, scene, src)
    hq = export_video(
        project,
        build_render_plan(project, scene.id, "prores_hq", str(tmp_path / "hq.mov"), audio=audio),
        assets=lambda _i: src,
    )
    assert (
        hq.probe.video_codec == "prores" and hq.probe.audio_codec == "pcm_s16le" and hq.probe.nb_frames == 6
    )
    assert _stream(hq.output_path, "video")["pix_fmt"] == "yuv422p10le"
    plan = build_render_plan(project, scene.id, "prores_4444", str(tmp_path / "alpha.mov"), transparent=True)
    alpha = export_video(project, plan)
    assert _stream(alpha.output_path, "video")["pix_fmt"].startswith("yuva444p")
    rgba = subprocess.run(
        [
            str(FFMPEG),
            "-v",
            "error",
            "-i",
            str(alpha.output_path),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    ).stdout
    a = np.frombuffer(rgba, np.uint8).reshape(1080, 1920, 4)[:, :, 3]
    assert a[10, 10] < 5 and a[540, 960] > 250  # fond transparent, Terre opaque


@needs_ffmpeg
def test_png_sequence_with_transparency_and_soundtrack(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=5)
    src = tmp_path / "voix.wav"
    make_wav(src, 0.1)
    audio = _with_voice(project, scene, src)
    out = tmp_path / "Orbite"
    plan = build_render_plan(project, scene.id, "png_sequence", str(out), audio=(), transparent=True)
    plan = __import__("dataclasses").replace(plan, audio=audio)  # la séquence garde la bande-son à côté
    result = export_video(project, plan, assets=lambda _i: src)
    frames = sorted(out.glob("image_*.png"))
    assert [f.name for f in frames] == [f"image_{i:05d}.png" for i in range(5)]
    img = QImage(str(frames[0]))
    assert (
        img.hasAlphaChannel()
        and img.pixelColor(10, 10).alpha() == 0
        and img.pixelColor(960, 540).alpha() == 255
    )
    assert (out / SEQUENCE_AUDIO).is_file() and result.probe.has_audio
    assert not list(tmp_path.glob(".*part"))
    (out / "image_00004.png").unlink()
    export_video(project, build_render_plan(project, scene.id, "png_sequence", str(out)))  # remplacement
    assert len(list(out.glob("image_*.png"))) == 5 and not (out / SEQUENCE_AUDIO).exists()
    with pytest.raises(RenderError, match="scène par scène"):
        export_project(project, "png_sequence", str(tmp_path / "tout"))


@needs_ffmpeg
def test_png_sequence_refuses_to_overwrite_a_foreign_folder(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=2)
    out = tmp_path / "Documents"
    out.mkdir()
    (out / "rapport.odt").write_text("ne pas effacer")
    with pytest.raises(RenderError, match="pas une séquence"):
        export_video(project, build_render_plan(project, scene.id, "png_sequence", str(out)))
    assert (out / "rapport.odt").read_text() == "ne pas effacer" and not list(tmp_path.glob(".*part"))


@needs_ffmpeg
def test_effects_and_scene_filter_reach_the_video_file(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, earth, _moon = earth_moon_project(duration_frames=3)
    project.canvas = Canvas(1280, 720, 30, 1)
    earth.position = [640.0, 360.0]
    earth.style.update(
        {"fill": "#FF0000", "fx_glow": 30.0, "fx_glow_color": "#00FF00", "fx_glow_strength": 2.0}
    )
    scene.background = "#000000"
    out = tmp_path / "fx.mp4"
    export_video(project, build_render_plan(project, scene.id, "draft_720p", str(out)))
    rgb = np.frombuffer(decode_frame_rgb(out, 0, 1280, 720), np.uint8).reshape(720, 1280, 3).astype(int)
    assert rgb[360, 640 + 95][1] > 40  # halo vert hors du disque (rayon 80)
    scene.post = {"saturation": 0.0}
    export_video(project, build_render_plan(project, scene.id, "draft_720p", str(out)))
    rgb = np.frombuffer(decode_frame_rgb(out, 0, 1280, 720), np.uint8).reshape(720, 1280, 3).astype(int)
    r, g, b = rgb[360, 640]
    assert abs(r - g) < 12 and abs(g - b) < 12 and r > 30  # disque rouge devenu gris


@needs_ffmpeg
def test_4k_export_has_the_right_size(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=2)
    result = export_video(
        project, build_render_plan(project, scene.id, "final_2160p", str(tmp_path / "4k.mp4"))
    )
    assert (result.probe.width, result.probe.height) == (3840, 2160) and result.probe.nb_frames == 2

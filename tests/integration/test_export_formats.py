"""Formats d'export : GIF (cadence réduite), WebM VP9/Opus, cadres de plateforme, atténuation musique."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from antares_studio.audio.waveform import decode_mono
from antares_studio.domain.model import Asset, AudioClip, Scene
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import audio_plans_for_scene, export_project, export_video
from antares_studio.rendering.plan import build_render_plan
from tests.integration.test_audio import make_wav
from tests.integration.test_export_project import decode_frame_rgb
from tests.unit.helpers import earth_moon_project

pytestmark = pytest.mark.render
FFMPEG = ff.find_ffmpeg()
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg/ffprobe absents")


def _has(codec: str) -> bool:
    return FFMPEG is not None and ff.has_encoder(FFMPEG, codec)


@needs_ffmpeg
def test_gif_halves_the_frame_rate_and_has_no_audio(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=30)  # 1 s à 30 i/s
    src = tmp_path / "voix.wav"
    make_wav(src, 1.0)
    project.assets.append(Asset(id="asset-0123456789ab", path="audio/voix.wav", kind="audio"))
    scene.audio.append(AudioClip.create("asset-0123456789ab", "Voix"))
    out = tmp_path / "anim.gif"
    plan = build_render_plan(
        project, scene.id, "gif_480", str(out), audio=audio_plans_for_scene(project, scene.id, lambda _i: src)
    )
    assert plan.frame_step == 2 and plan.total_frames == 15 and plan.audio == ()
    result = export_video(project, plan, assets=lambda _i: src)
    assert result.probe.video_codec == "gif" and not result.probe.has_audio
    assert (result.probe.width, result.probe.height) == (854, 480)
    assert result.probe.nb_frames == 15
    assert abs(result.probe.duration - 1.0) < 0.08


@needs_ffmpeg
@pytest.mark.skipif(not (_has("libvpx-vp9") and _has("libopus")), reason="VP9/Opus absents de FFmpeg")
def test_webm_is_vp9_with_opus(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=20)
    out = tmp_path / "web.webm"
    plan = build_render_plan(project, scene.id, "webm_1080p", str(out), silent_audio=True)
    result = export_video(project, plan)
    assert result.probe.video_codec == "vp9" and result.probe.audio_codec == "opus"
    assert result.probe.nb_frames == 20


@needs_ffmpeg
def test_platform_frame_adds_black_bars(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=6)  # projet 16:9
    scene.background = "#3366CC"
    out = tmp_path / "vertical.mp4"
    plan = build_render_plan(project, scene.id, "vertical_1080x1920", str(out))
    assert plan.content_rect == (0, 656, 1080, 608)
    assert any("bandes noires" in w for w in plan.warnings)
    result = export_video(project, plan)
    assert (result.probe.width, result.probe.height) == (1080, 1920)
    rgb = decode_frame_rgb(out, 0, 1080, 1920)

    def pixel(x: int, y: int) -> tuple[int, ...]:
        i = (y * 1080 + x) * 3
        return tuple(rgb[i : i + 3])

    assert max(pixel(540, 100)) < 20 and max(pixel(540, 1800)) < 20  # bandes noires
    r, g, b = pixel(20, 700)  # coin du contenu : fond de scène
    assert b > 150 and r < 100


def _tone_level(samples: np.ndarray, start: float, end: float, freq: float, rate: int = 8000) -> float:
    seg = samples[int(start * rate) : int(end * rate)]
    spectrum = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), 1 / rate)
    return float(spectrum[np.abs(freqs - freq) < 15].max())


def _ducking_export(tmp_path: Path, ducking: bool) -> np.ndarray:
    project, scene, *_ = earth_moon_project(duration_frames=90)  # 3 s
    music, voice = tmp_path / "musique.wav", tmp_path / "voix.wav"
    make_wav(music, 3.0, freq=440.0)
    make_wav(voice, 1.5, freq=1000.0)
    project.assets.append(Asset(id="asset-00000000mmmm", path="audio/musique.wav", kind="audio"))
    project.assets.append(Asset(id="asset-00000000vvvv", path="audio/voix.wav", kind="audio"))
    clip_m = AudioClip.create("asset-00000000mmmm", "Musique", gain=0.5)
    clip_m.role = "music"
    scene.audio += [clip_m, AudioClip.create("asset-00000000vvvv", "Voix", offset_frames=45)]  # 1,5 s
    project.settings["ducking"] = ducking

    def files(asset_id: str) -> Path:
        return music if asset_id.endswith("mmmm") else voice

    out = tmp_path / f"duck-{ducking}.mp4"
    plan = build_render_plan(
        project, scene.id, "draft_720p", str(out), audio=audio_plans_for_scene(project, scene.id, files)
    )
    export_video(project, plan, assets=files)
    return decode_mono(FFMPEG, out)  # type: ignore[arg-type]


@needs_ffmpeg
def test_music_is_ducked_under_the_voice_only_when_enabled(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    on = _ducking_export(tmp_path, True)
    off = _ducking_export(tmp_path, False)
    before_on, during_on = _tone_level(on, 0.3, 1.3, 440), _tone_level(on, 1.9, 2.8, 440)
    before_off, during_off = _tone_level(off, 0.3, 1.3, 440), _tone_level(off, 1.9, 2.8, 440)
    assert during_on < before_on * 0.35  # musique atténuée d'au moins 9 dB pendant la voix
    assert during_off > before_off * 0.8  # sans atténuation : niveau inchangé
    assert _tone_level(on, 1.9, 2.8, 1000) > 0.8 * _tone_level(off, 1.9, 2.8, 1000)  # voix intacte


@needs_ffmpeg
def test_whole_project_gif_concatenates_scenes(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=10)
    project.scenes.append(Scene.create("Deux", duration_frames=8))
    out = tmp_path / "complet.gif"
    result = export_project(project, "gif_480", str(out))
    assert result.probe.video_codec == "gif" and not result.probe.has_audio
    assert result.probe.nb_frames == 5 + 4

"""AUD-01 … AUD-05, AUD-09 — import audio, forme d'onde, mixage à l'export mesuré, décalage, dérive."""

from __future__ import annotations

import math
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from antares_studio.audio.waveform import decode_mono, peaks, waveform_for
from antares_studio.domain.model import AudioClip
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import RenderError, audio_plans_for_scene, export_video
from antares_studio.rendering.plan import build_render_plan
from tests.unit.helpers import earth_moon_project

pytestmark = pytest.mark.render
FFMPEG = ff.find_ffmpeg()
FFPROBE = ff.find_ffprobe(ffmpeg=FFMPEG) if FFMPEG else None
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None or FFPROBE is None, reason="ffmpeg/ffprobe absents")


def make_wav(
    path: Path,
    seconds: float,
    channels: int = 1,
    rate: int = 48000,
    freq: float = 440.0,
    lead_silence: float = 0.0,
) -> None:
    n = int(seconds * rate)
    t = np.arange(n) / rate
    tone = (0.6 * np.sin(2 * math.pi * freq * t)).astype(np.float32)
    tone[: int(lead_silence * rate)] = 0.0
    pcm = (tone * 32767).astype("<i2")
    if channels == 2:
        pcm = np.column_stack([pcm, pcm])
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


@needs_ffmpeg
def test_aud01_wav_mono_and_stereo_metadata(tmp_path: Path) -> None:
    mono, stereo = tmp_path / "m.wav", tmp_path / "s.wav"
    make_wav(mono, 2.0, 1)
    make_wav(stereo, 2.0, 2)
    assert abs(ff.probe_audio_duration(FFPROBE, mono) - 2.0) < 0.01  # type: ignore[arg-type]
    assert abs(ff.probe_audio_duration(FFPROBE, stereo) - 2.0) < 0.01  # type: ignore[arg-type]
    samples = decode_mono(FFMPEG, stereo)  # type: ignore[arg-type]
    assert abs(len(samples) / 8000 - 2.0) < 0.01
    pk = peaks(samples, 8000)
    assert len(pk) == 100 and pk.max() > 0.5


@needs_ffmpeg
def test_aud02_mp3_import_when_encoder_available(tmp_path: Path) -> None:
    if not ff.has_encoder(FFMPEG, "libmp3lame"):  # type: ignore[arg-type]
        pytest.skip("encodeur MP3 absent")
    src = tmp_path / "v.wav"
    make_wav(src, 1.5)
    mp3 = tmp_path / "v.mp3"
    subprocess.run(
        [str(FFMPEG), "-v", "error", "-y", "-i", str(src), "-c:a", "libmp3lame", "-q:a", "4", str(mp3)],
        check=True,
    )
    assert abs(ff.probe_audio_duration(FFPROBE, mp3) - 1.5) < 0.1  # type: ignore[arg-type]
    assert len(decode_mono(FFMPEG, mp3)) > 8000  # type: ignore[arg-type]


@needs_ffmpeg
def test_aud09_invalid_media_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "pas-un-son.wav"
    bad.write_bytes(b"ceci n'est pas de l'audio" * 100)
    with pytest.raises(ff.FFmpegError):
        decode_mono(FFMPEG, bad)  # type: ignore[arg-type]
    with pytest.raises(ff.FFmpegError):
        ff.probe_audio_duration(FFPROBE, bad)  # type: ignore[arg-type]


@needs_ffmpeg
def test_waveform_cache_and_silence_detection(tmp_path: Path) -> None:
    src = tmp_path / "w.wav"
    make_wav(src, 1.0, lead_silence=0.5)
    pk, duration = waveform_for(FFMPEG, src, tmp_path / "cache")  # type: ignore[arg-type]
    assert abs(duration - 1.0) < 0.01 and len(pk) == 50
    assert pk[:24].max() < 0.01 and pk[26:].min() > 0.3
    assert list((tmp_path / "cache").glob("waveform-*.json"))
    pk2, _ = waveform_for(FFMPEG, src, tmp_path / "cache")  # type: ignore[arg-type]
    assert np.allclose(pk, pk2, atol=1e-3)


def _first_sound_second(path: Path, threshold: float = 0.05) -> float:
    samples = decode_mono(FFMPEG, path)  # type: ignore[arg-type]
    idx = int(np.argmax(np.abs(samples) > threshold))
    return idx / 8000.0


@needs_ffmpeg
def test_aud03_aud05_export_with_offset_gain_and_no_drift(tmp_path: Path, qapp) -> None:  # type: ignore[no-untyped-def]
    project, scene, earth, moon = earth_moon_project(duration_frames=120)  # 4 s à 30 i/s
    src = tmp_path / "voix.wav"
    make_wav(src, 2.0)
    from antares_studio.domain.model import Asset

    project.assets.append(Asset(id="asset-0123456789ab", path="audio/voix.wav", kind="audio"))
    scene.audio.append(AudioClip.create("asset-0123456789ab", "Voix", offset_frames=36, gain=0.5))  # 1,2 s
    out = tmp_path / "mix.mp4"
    plans = audio_plans_for_scene(project, scene.id, lambda _id: src)
    plan = build_render_plan(project, scene.id, "draft_720p", str(out), audio=plans)
    result = export_video(project, plan, assets=lambda _id: src)
    assert result.probe.has_audio and result.probe.audio_codec == "aac"
    assert result.probe.nb_frames == 120
    # AUD-03 : premier son à ~1,2 s ; AUD-05 : durée audio ≈ durée vidéo (4 s), pas de dérive
    assert abs(_first_sound_second(out) - 1.2) < 0.06
    assert abs(ff.probe_audio_duration(FFPROBE, out) - 4.0) < 0.15  # type: ignore[arg-type]
    samples = decode_mono(FFMPEG, out)  # type: ignore[arg-type]
    assert 0.2 < np.abs(samples[int(1.5 * 8000) : int(3.0 * 8000)]).max() < 0.45  # gain 0,5 appliqué


@needs_ffmpeg
def test_aud04_fades_shape_envelope(tmp_path: Path, qapp) -> None:  # type: ignore[no-untyped-def]
    project, scene, *_ = earth_moon_project(duration_frames=90)
    src = tmp_path / "musique.wav"
    make_wav(src, 3.0)
    from antares_studio.domain.model import Asset

    project.assets.append(Asset(id="asset-0123456789ab", path="audio/musique.wav", kind="audio"))
    scene.audio.append(
        AudioClip.create(
            "asset-0123456789ab", "Musique", out_seconds=3.0, fade_in_seconds=1.0, fade_out_seconds=1.0
        )
    )
    out = tmp_path / "fade.mp4"
    plan = build_render_plan(
        project,
        scene.id,
        "draft_720p",
        str(out),
        audio=audio_plans_for_scene(project, scene.id, lambda _i: src),
    )
    export_video(project, plan, assets=lambda _i: src)
    s = decode_mono(FFMPEG, out)  # type: ignore[arg-type]
    early = np.abs(s[int(0.1 * 8000) : int(0.3 * 8000)]).max()
    middle = np.abs(s[int(1.3 * 8000) : int(1.7 * 8000)]).max()
    late = np.abs(s[int(2.7 * 8000) : int(2.9 * 8000)]).max()
    assert early < middle * 0.5 and late < middle * 0.5


def test_missing_audio_file_is_an_actionable_error() -> None:
    project, scene, *_ = earth_moon_project()
    scene.audio.append(AudioClip.create("asset-000000000000", "Absent"))
    with pytest.raises(RenderError, match="introuvable"):
        audio_plans_for_scene(project, scene.id, lambda _i: None)
    scene.audio[0].muted = True
    assert audio_plans_for_scene(project, scene.id, lambda _i: None) == ()

"""Bibliothèque de bruitages : sons calculés localement, reproductibles, propres (ni saturation ni clic)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from antares_studio.audio import sfx


@pytest.mark.parametrize("sound_id", list(sfx.SOUNDS))
def test_sound_is_clean_and_normalized(sound_id: str) -> None:
    spec = sfx.SOUNDS[sound_id]
    x = sfx.render_sound(sound_id)
    assert np.isfinite(x).all() and len(x) > sfx.RATE * 0.02
    peak_db = 20 * np.log10(np.max(np.abs(x)))
    assert peak_db == pytest.approx(spec.peak_db, abs=0.01)  # jamais de saturation
    assert abs(float(np.mean(x))) < 5e-3  # pas de composante continue (inaudible au-dessous)
    assert abs(x[0]) < 1e-9 and abs(x[-1]) < 1e-9  # fondus : ni clic au départ ni coupure sèche
    assert spec.category in sfx.CATEGORIES and spec.label and spec.description


def test_catalogue_covers_every_category_and_ambiences_loop() -> None:
    assert len(sfx.SOUNDS) >= 25
    for cat in sfx.CATEGORIES:
        assert sum(1 for s in sfx.SOUNDS.values() if s.category == cat) >= 4
    ambiences = [s for s in sfx.SOUNDS.values() if s.category == "Ambiances"]
    assert all(s.loop and s.peak_db <= -9.0 for s in ambiences)  # discrètes sous la voix
    assert all(sfx.sound_duration(s.id) >= 19.9 for s in ambiences)


def test_rendering_is_deterministic() -> None:
    for sound_id in ("whoosh", "geiger", "shimmer"):
        assert np.array_equal(sfx.render_sound(sound_id), sfx.render_sound(sound_id))
    assert not np.array_equal(sfx.render_sound("whoosh")[:1000], sfx.render_sound("whoosh_down")[:1000])


def test_wav_file_is_16_bit_mono_and_reused(tmp_path: Path) -> None:
    path = sfx.write_sound("beep", tmp_path)
    with wave.open(str(path), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, sfx.RATE)
        assert w.getnframes() == len(sfx.render_sound("beep"))
    data = path.read_bytes()
    assert sfx.write_sound("beep", tmp_path) == path and path.read_bytes() == data
    assert sfx.wav_bytes(sfx.render_sound("beep")) == data  # octet pour octet
    assert not list(tmp_path.glob("*.part"))

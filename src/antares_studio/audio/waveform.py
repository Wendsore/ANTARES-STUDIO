"""Forme d'onde dérivée (pics par tranche) via décodage FFmpeg en PCM mono 8 kHz ; cache régénérable."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from antares_studio.rendering import ffmpeg as ff

SAMPLE_RATE = 8000


def decode_mono(
    ffmpeg: Path, source: Path, sample_rate: int = SAMPLE_RATE, timeout: float = 600
) -> np.ndarray:
    """Décode ``source`` en float32 mono normalisé [-1, 1] ; ``FFmpegError`` si le fichier est illisible."""
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        "pipe:1",
    ]
    out = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False, creationflags=ff._NO_WINDOW)
    if out.returncode != 0 or not out.stdout:
        raise ff.FFmpegError(
            f"impossible de décoder l'audio : {source.name}", out.stderr.decode("utf-8", "replace")
        )
    data = np.frombuffer(out.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return data


def peaks(samples: np.ndarray, sample_rate: int, seconds_per_bin: float = 0.02) -> np.ndarray:
    """Amplitude maximale par tranche de ``seconds_per_bin`` (float32 dans [0, 1])."""
    size = max(1, int(round(sample_rate * seconds_per_bin)))
    n = len(samples) // size
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    trimmed = np.abs(samples[: n * size]).reshape(n, size)
    return trimmed.max(axis=1).astype(np.float32)


def waveform_for(ffmpeg: Path, source: Path, cache_dir: Path | None = None) -> tuple[np.ndarray, float]:
    """Retourne (pics à 50 Hz, durée en secondes) ; met en cache sous ``cache_dir`` (JSON) si fourni."""
    key = None
    if cache_dir is not None:
        try:
            st = source.stat()
            key = hashlib.sha256(f"{source.resolve()}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[
                :24
            ]
            cached = cache_dir / f"waveform-{key}.json"
            if cached.is_file():
                data = json.loads(cached.read_text(encoding="utf-8"))
                return np.asarray(data["peaks"], dtype=np.float32), float(data["duration"])
        except (OSError, ValueError, KeyError):
            key = None
    samples = decode_mono(ffmpeg, source)
    pk = peaks(samples, SAMPLE_RATE)
    duration = len(samples) / SAMPLE_RATE
    if cache_dir is not None and key is not None:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / f"waveform-{key}.json").write_text(
                json.dumps({"peaks": [round(float(v), 4) for v in pk], "duration": duration}),
                encoding="utf-8",
            )
        except OSError:
            pass
    return pk, duration

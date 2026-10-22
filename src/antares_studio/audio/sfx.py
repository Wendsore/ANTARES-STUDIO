"""Bibliothèque de bruitages et d'ambiances, synthétisés localement (aucun fichier tiers, hors ligne).

Chaque son est calculé par une fonction déterministe (graine fixe) : le même identifiant donne toujours
le même fichier, octet pour octet. Pas de licence tierce à vérifier : ces sons sont produits par ANTARES
Studio et versés au domaine public (CC0 1.0). Format : WAV PCM 16 bits, mono, 48 kHz, crête normalisée.
"""

from __future__ import annotations

import io
import math
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

RATE = 48_000
Signal = np.ndarray[Any, np.dtype[np.float64]]


@dataclass(frozen=True)
class SoundSpec:
    id: str
    label: str
    category: str
    description: str
    synth: Callable[[np.random.Generator], Signal]
    peak_db: float = -1.0  # crête visée (dBFS) : les ambiances restent discrètes sous la voix
    loop: bool = False  # ambiance pensée pour boucler (début et fin raccordés)


# --- briques -------------------------------------------------------------------------------------------
def _t(seconds: float) -> Signal:
    return np.arange(int(round(seconds * RATE)), dtype=np.float64) / RATE


def _env(n: int, attack: float, release: float, curve: float = 2.0) -> Signal:
    """Enveloppe attaque linéaire puis décroissance en puissance ``curve`` jusqu'à 0."""
    a = max(1, int(attack * RATE))
    env = np.ones(n)
    env[:a] = np.linspace(0.0, 1.0, a)
    rest = n - a
    if rest > 0:
        env[a:] = np.linspace(1.0, 0.0, rest) ** curve
    rel = int(release * RATE)
    if 0 < rel < n:
        env[-rel:] *= np.linspace(1.0, 0.0, rel)
    return env


def _sweep(f0: float, f1: float, seconds: float, exp: bool = True) -> Signal:
    """Sinusoïde dont la fréquence glisse de ``f0`` à ``f1`` (phase continue)."""
    n = int(round(seconds * RATE))
    f = np.geomspace(f0, f1, n) if exp else np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / RATE)


def _lowpass(x: Signal, cutoff: float | Signal) -> Signal:
    """Passe-bas d'ordre 1 (coupure fixe ou variable dans le temps)."""
    c = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), x.shape)
    alpha = 1.0 - np.exp(-2 * np.pi * c / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # boucle simple : sons courts, calcul unique puis cache
        acc += alpha[i] * (x[i] - acc)
        y[i] = acc
    return y


def _lowpass_fast(x: Signal, cutoff: float) -> Signal:
    """Passe-bas d'ordre 1 à coupure fixe, vectorisé par blocs (ambiances longues)."""
    from numpy.lib.stride_tricks import sliding_window_view

    alpha = 1.0 - math.exp(-2 * math.pi * cutoff / RATE)
    k = int(min(len(x), max(16, 6.0 / alpha)))
    kernel = alpha * (1 - alpha) ** np.arange(k)
    padded = np.concatenate([np.zeros(k - 1), x])
    return np.asarray(sliding_window_view(padded, k) @ kernel[::-1], dtype=np.float64)


def _noise(rng: np.random.Generator, seconds: float) -> Signal:
    return rng.uniform(-1.0, 1.0, int(round(seconds * RATE)))


def _pink(rng: np.random.Generator, seconds: float) -> Signal:
    """Bruit rose (−3 dB/octave) par filtrage spectral d'un bruit blanc."""
    n = int(round(seconds * RATE))
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / RATE)
    f[0] = f[1]
    return np.fft.irfft(spec / np.sqrt(f), n)


def _tone(freq: float, seconds: float, harmonics: tuple[float, ...] = (1.0,)) -> Signal:
    t = _t(seconds)
    return sum(a * np.sin(2 * np.pi * freq * (i + 1) * t) for i, a in enumerate(harmonics))  # type: ignore[return-value]


def _fade_edges(x: Signal, fade_in_ms: float = 1.0, fade_out_ms: float = 4.0) -> Signal:
    """Fondus très courts aux deux bouts : ni clic au départ, ni coupure sèche à la fin."""
    a = min(len(x) // 2, int(fade_in_ms / 1000 * RATE))
    b = min(len(x) // 2, int(fade_out_ms / 1000 * RATE))
    if a > 0:
        x[:a] *= np.linspace(0.0, 1.0, a)
    if b > 0:
        x[-b:] *= np.linspace(1.0, 0.0, b)
    return x


def _loopable(x: Signal, seconds: float = 1.0) -> Signal:
    """Fond enchaîné : la fin se fond dans le début, la boucle ne claque pas."""
    n = int(seconds * RATE)
    head, body = x[:n], x[n:].copy()
    ramp = np.linspace(0.0, 1.0, n)
    body[-n:] = body[-n:] * (1 - ramp) + head * ramp
    return body


# --- sons ----------------------------------------------------------------------------------------------
def whoosh(rng: np.random.Generator, rising: bool = True) -> Signal:
    d = 0.9
    n = int(d * RATE)
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    cutoff = np.geomspace(300, 4000, n) if rising else np.geomspace(4000, 300, n)
    return np.asarray(_lowpass(_noise(rng, d), cutoff) * shape, dtype=np.float64)


def riser(rng: np.random.Generator) -> Signal:
    d = 2.5
    n = int(d * RATE)
    up = np.linspace(0, 1, n) ** 2
    tone = _sweep(110, 880, d) * 0.5 + _sweep(165, 1320, d) * 0.3
    hiss = _lowpass(_noise(rng, d), np.geomspace(500, 8000, n)) * 0.6
    return (tone + hiss) * up * _env(n, 0.01, 0.05, 0.0)


def downer(rng: np.random.Generator) -> Signal:
    d = 1.6
    n = int(d * RATE)
    return (_sweep(900, 60, d) * 0.8 + _lowpass(_noise(rng, d), np.geomspace(3000, 200, n)) * 0.4) * _env(
        n, 0.005, 0.2, 1.2
    )


def shimmer(rng: np.random.Generator) -> Signal:
    d = 1.8
    out = np.zeros(int(d * RATE))
    for _ in range(28):  # petites clochettes aléatoires, aiguës
        start = int(rng.uniform(0, d - 0.4) * RATE)
        f = rng.uniform(2200, 5200)
        g = _tone(f, 0.4, (1.0, 0.3)) * _env(int(0.4 * RATE), 0.002, 0.05, 3.0) * rng.uniform(0.3, 1.0)
        out[start : start + len(g)] += g
    return out * np.sin(np.linspace(0, np.pi, len(out)))


def click(rng: np.random.Generator) -> Signal:
    n = int(0.03 * RATE)
    return _lowpass(_noise(rng, 0.03), 6000) * _env(n, 0.0005, 0.0, 6.0)


def pop(rng: np.random.Generator) -> Signal:
    d = 0.12
    n = int(d * RATE)
    return _sweep(900, 180, d) * _env(n, 0.002, 0.01, 3.0)


def beep(rng: np.random.Generator) -> Signal:
    d = 0.18
    return _tone(1000, d, (1.0, 0.15)) * _env(int(d * RATE), 0.005, 0.03, 0.3)


def double_beep(rng: np.random.Generator) -> Signal:
    one = beep(rng)
    gap = np.zeros(int(0.08 * RATE))
    return np.concatenate([one, gap, one])


def notification(rng: np.random.Generator) -> Signal:
    a = _tone(880, 0.25, (1.0, 0.2, 0.05)) * _env(int(0.25 * RATE), 0.005, 0.05, 2.0)
    b = _tone(1318.5, 0.5, (1.0, 0.2, 0.05)) * _env(int(0.5 * RATE), 0.005, 0.1, 2.0)
    out = np.zeros(int(0.7 * RATE))
    out[: len(a)] += a
    out[int(0.15 * RATE) : int(0.15 * RATE) + len(b)] += b
    return out


def ding(rng: np.random.Generator) -> Signal:
    d = 1.6
    # cloche : partiels inharmoniques, les aigus s'éteignent plus vite
    t = _t(d)
    parts = [(1.0, 1.0, 1.5), (2.76, 0.5, 3.0), (5.4, 0.25, 5.0), (8.9, 0.12, 8.0)]
    return sum(a * np.sin(2 * np.pi * 1046.5 * r * t) * np.exp(-k * t) for r, a, k in parts) * _env(
        len(t), 0.002, 0.05, 0.0
    )


def error(rng: np.random.Generator) -> Signal:
    d = 0.22
    one = (np.sign(np.sin(2 * np.pi * 220 * _t(d))) * 0.5) * _env(int(d * RATE), 0.005, 0.04, 0.5)
    one = _lowpass(one, 2500)
    return np.concatenate([one, np.zeros(int(0.06 * RATE)), one * 0.8])


def thud(rng: np.random.Generator) -> Signal:
    d = 0.7
    n = int(d * RATE)
    body = _sweep(120, 40, d) * _env(n, 0.002, 0.05, 3.0)
    hit = _lowpass(_noise(rng, d), 800) * _env(n, 0.001, 0.0, 12.0)
    return body + hit * 0.6


def explosion(rng: np.random.Generator) -> Signal:
    d = 3.0
    n = int(d * RATE)
    rumble = _lowpass(_noise(rng, d), np.geomspace(1500, 120, n)) * _env(n, 0.005, 0.3, 2.2)
    boom = _sweep(70, 30, d) * _env(n, 0.003, 0.3, 3.0)
    return rumble * 1.4 + boom * 0.8


def thunder(rng: np.random.Generator) -> Signal:
    d = 5.0
    n = int(d * RATE)
    base = _lowpass(_noise(rng, d), 400)
    # roulements : modulation lente irrégulière
    mod = _lowpass(np.abs(_noise(rng, d)), 3.0)
    mod = mod / (float(np.max(mod)) or 1.0)
    return base * (0.3 + mod) * _env(n, 0.05, 0.6, 1.5)


def gong(rng: np.random.Generator) -> Signal:
    d = 4.0
    t = _t(d)
    parts = [(1.0, 1.0, 0.8), (1.48, 0.6, 1.1), (2.03, 0.45, 1.6), (2.76, 0.3, 2.2), (3.9, 0.2, 3.0)]
    sig = sum(
        a * np.sin(2 * np.pi * 98.0 * r * t + rng.uniform(0, 6.28)) * np.exp(-k * t) for r, a, k in parts
    )
    return sig * _env(len(t), 0.01, 0.1, 0.0)


def sonar(rng: np.random.Generator) -> Signal:
    d = 2.2
    t = _t(d)
    ping = np.sin(2 * np.pi * 1500 * t) * np.exp(-2.2 * t)
    echo = np.zeros_like(ping)
    lag = int(0.45 * RATE)
    echo[lag:] = ping[:-lag] * 0.35
    return np.asarray((ping + echo) * _env(len(t), 0.003, 0.1, 0.0), dtype=np.float64)


def pulsar(rng: np.random.Generator) -> Signal:
    d = 4.0
    out = np.zeros(int(d * RATE))
    period = 0.25  # 4 battements par seconde, comme l'écoute radio d'un pulsar rapide
    tick = _lowpass(_noise(rng, 0.04), 3000) * _env(int(0.04 * RATE), 0.0005, 0.0, 5.0)
    tick += _tone(180, 0.04) * _env(int(0.04 * RATE), 0.001, 0.0, 4.0)
    for k in range(int(d / period)):
        s = int(k * period * RATE)
        out[s : s + len(tick)] += tick
    return out


def radio(rng: np.random.Generator) -> Signal:
    d = 2.5
    n = int(d * RATE)
    hiss = _lowpass(_noise(rng, d), 5000) * 0.5
    t = _t(d)
    carrier = np.sin(2 * np.pi * (700 + 150 * np.sin(2 * np.pi * 1.3 * t)) * t) * 0.35
    flutter = 0.6 + 0.4 * np.sin(2 * np.pi * 7 * t)
    return (hiss + carrier) * flutter * _env(n, 0.05, 0.3, 0.0)


def laser(rng: np.random.Generator) -> Signal:
    d = 0.35
    n = int(d * RATE)
    return (_sweep(2400, 300, d) + 0.4 * _sweep(4800, 600, d)) * _env(n, 0.002, 0.02, 1.5)


def rocket(rng: np.random.Generator) -> Signal:
    d = 4.0
    n = int(d * RATE)
    roar = _lowpass(_noise(rng, d), 900) + 0.5 * _lowpass(_noise(rng, d), 250)
    crackle = (rng.uniform(0, 1, n) > 0.9993) * rng.uniform(-1, 1, n)
    return (roar + crackle * 2.0) * _env(n, 0.6, 0.6, 0.0)


def geiger(rng: np.random.Generator) -> Signal:
    d = 3.0
    out = np.zeros(int(d * RATE))
    clk = _lowpass(_noise(rng, 0.006), 7000) * _env(int(0.006 * RATE), 0.0002, 0.0, 4.0)
    times = np.cumsum(rng.exponential(1 / 9.0, 60))  # désintégrations : processus de Poisson, 9 par s
    for s in times[times < d - 0.01]:
        i = int(s * RATE)
        out[i : i + len(clk)] += clk
    return out


def deep_space(rng: np.random.Generator) -> Signal:
    d = 31.0
    t = _t(d)
    drone = sum(
        a * np.sin(2 * np.pi * f * t + 0.3 * np.sin(2 * np.pi * lfo * t))
        for f, a, lfo in ((55, 0.5, 0.05), (82.4, 0.35, 0.07), (110.3, 0.2, 0.03), (164.8, 0.1, 0.11))
    )
    air = _lowpass_fast(_pink(rng, d), 1200) * 0.4
    swell = 0.75 + 0.25 * np.sin(2 * np.pi * t / 10.0)
    return _loopable((drone + air) * swell)


def laboratory(rng: np.random.Generator) -> Signal:
    d = 21.0
    t = _t(d)
    hum = (
        0.4 * np.sin(2 * np.pi * 50 * t)
        + 0.2 * np.sin(2 * np.pi * 100 * t)
        + 0.08 * np.sin(2 * np.pi * 150 * t)
    )
    fans = _lowpass_fast(_pink(rng, d), 2500) * 0.5
    return _loopable(hum + fans)


def cosmic_wind(rng: np.random.Generator) -> Signal:
    d = 21.0
    t = _t(d)
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * t / 7.0) * np.sin(2 * np.pi * t / 3.1)
    return _loopable(_lowpass_fast(_pink(rng, d), 700) * gust)


def soft_noise(rng: np.random.Generator) -> Signal:
    return _loopable(_lowpass_fast(_pink(rng, 21.0), 4000))


CATEGORIES: tuple[str, ...] = ("Transitions", "Interface", "Impacts", "Sciences et espace", "Ambiances")

SOUNDS: dict[str, SoundSpec] = {
    s.id: s
    for s in (
        SoundSpec(
            "whoosh",
            "Souffle (whoosh)",
            "Transitions",
            "Passage rapide montant : changement de plan.",
            whoosh,
        ),
        SoundSpec(
            "whoosh_down",
            "Souffle descendant",
            "Transitions",
            "Passage rapide qui retombe : sortie d'un objet.",
            lambda r: whoosh(r, rising=False),
        ),
        SoundSpec(
            "riser",
            "Montée de tension",
            "Transitions",
            "Son qui monte pendant 2,5 s avant une révélation.",
            riser,
        ),
        SoundSpec(
            "downer", "Chute", "Transitions", "Descente grave : fin d'une idée, chute d'un objet.", downer
        ),
        SoundSpec(
            "shimmer",
            "Scintillement",
            "Transitions",
            "Pluie de clochettes : apparition magique, étoiles.",
            shimmer,
        ),
        SoundSpec("click", "Clic", "Interface", "Clic sec et bref.", click),
        SoundSpec("pop", "Pop", "Interface", "Petite bulle : apparition d'une étiquette.", pop),
        SoundSpec("beep", "Bip", "Interface", "Bip électronique à 1 kHz.", beep),
        SoundSpec("double_beep", "Double bip", "Interface", "Deux bips : attention, mesure.", double_beep),
        SoundSpec("notification", "Notification", "Interface", "Deux notes montantes, douces.", notification),
        SoundSpec(
            "ding",
            "Cloche (bonne réponse)",
            "Interface",
            "Cloche claire : réponse juste, étape réussie.",
            ding,
        ),
        SoundSpec("error", "Erreur", "Interface", "Double buzz grave : réponse fausse.", error),
        SoundSpec(
            "thud", "Impact sourd", "Impacts", "Choc grave et court : objet qui tombe, météorite.", thud
        ),
        SoundSpec(
            "explosion",
            "Explosion lointaine",
            "Impacts",
            "Grondement qui s'éteint en 3 s : supernova, impact.",
            explosion,
        ),
        SoundSpec("thunder", "Tonnerre", "Impacts", "Roulements de tonnerre sur 5 s.", thunder),
        SoundSpec("gong", "Gong", "Impacts", "Gong grave et long : moment solennel, titre.", gong),
        SoundSpec(
            "sonar",
            "Sonar",
            "Sciences et espace",
            "Impulsion et son écho : détection, mesure de distance.",
            sonar,
        ),
        SoundSpec(
            "pulsar",
            "Pulsar (battements)",
            "Sciences et espace",
            "Battements réguliers, 4 par seconde, comme l'écoute d'un pulsar.",
            pulsar,
        ),
        SoundSpec(
            "radio",
            "Signal radio",
            "Sciences et espace",
            "Souffle et porteuse qui ondule : transmission lointaine.",
            radio,
        ),
        SoundSpec("laser", "Laser", "Sciences et espace", "Tir bref descendant.", laser),
        SoundSpec(
            "rocket",
            "Moteur de fusée",
            "Sciences et espace",
            "Grondement continu de 4 s : décollage.",
            rocket,
        ),
        SoundSpec(
            "geiger",
            "Compteur Geiger",
            "Sciences et espace",
            "Clics aléatoires (9 par seconde en moyenne) : radioactivité.",
            geiger,
        ),
        SoundSpec(
            "deep_space",
            "Espace profond",
            "Ambiances",
            "Nappe grave et lente de 30 s, en boucle.",
            deep_space,
            -9.0,
            True,
        ),
        SoundSpec(
            "laboratory",
            "Laboratoire",
            "Ambiances",
            "Bourdonnement électrique et ventilation, 20 s en boucle.",
            laboratory,
            -12.0,
            True,
        ),
        SoundSpec(
            "cosmic_wind",
            "Vent cosmique",
            "Ambiances",
            "Souffle qui va et vient, 20 s en boucle.",
            cosmic_wind,
            -10.0,
            True,
        ),
        SoundSpec(
            "soft_noise",
            "Bruit rose doux",
            "Ambiances",
            "Fond neutre et régulier, 20 s en boucle.",
            soft_noise,
            -16.0,
            True,
        ),
    )
}


def render_sound(sound_id: str) -> Signal:
    """Échantillons (−1..1) du son, crête à ``peak_db`` ; graine fixe par son : résultat reproductible."""
    spec = SOUNDS[sound_id]
    seed = sum((i + 1) * ord(c) for i, c in enumerate(sound_id))
    x = np.asarray(spec.synth(np.random.default_rng(seed)), dtype=np.float64)
    x = _fade_edges(x - float(np.mean(x)))  # pas de composante continue
    peak = float(np.max(np.abs(x))) or 1.0
    return x * (10 ** (spec.peak_db / 20.0) / peak)


def wav_bytes(samples: Signal) -> bytes:
    pcm = np.clip(np.round(samples * 32767.0), -32768, 32767).astype("<i2")
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return out.getvalue()


def write_sound(sound_id: str, folder: Path) -> Path:
    """Écrit ``<folder>/<identifiant>.wav`` (réutilisé s'il existe déjà) et retourne son chemin."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sound_id}.wav"
    if not path.is_file():
        tmp = path.with_suffix(".wav.part")
        tmp.write_bytes(wav_bytes(render_sound(sound_id)))
        tmp.replace(path)
    return path


def sound_duration(sound_id: str) -> float:
    return len(render_sound(sound_id)) / RATE

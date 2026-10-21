"""Construit et exporte une vidéo de démonstration ≥ 2 min (Gate 6) à partir des modèles intégrés.

Usage : ``QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/demo_gate6.py DOSSIER [--profile draft_720p]``.
La narration est un **signal synthétique** (tonalité douce) faute de voix enregistrée : il tient lieu de
piste de narration pour mesurer la synchronisation, pas de contenu pédagogique. Les sous-titres et les
crédits sont réels (générés depuis les métadonnées des modèles).
"""

from __future__ import annotations

import argparse
import math
import sys
import time
import wave
from pathlib import Path

import numpy as np

from antares_studio.app.main import create_app
from antares_studio.domain.model import Asset, AudioClip, Canvas, Scene, Subtitle
from antares_studio.persistence.store import ProjectStore
from antares_studio.rendering.exporter import export_project
from antares_studio.resources.templates import TEMPLATES, create_project

SCENES = [  # (modèle, durée s, sous-titres)
    ("intro", 12, ["Pourquoi la Lune change-t-elle de forme ?", "Une animation ANTARES Studio"]),
    (
        "moon_phases",
        40,
        [
            "La Lune tourne autour de la Terre en un peu plus de 27 jours.",
            "Le Soleil éclaire toujours la moitié de la Lune.",
            "Depuis la Terre, nous voyons une part variable de cette moitié éclairée.",
        ],
    ),
    (
        "scale_comparison",
        30,
        [
            "Une année-lumière : la distance parcourue par la lumière en un an.",
            "Soit environ 9 461 milliards de kilomètres.",
        ],
    ),
    (
        "kepler_orbit",
        30,
        [
            "Sur une orbite elliptique, la planète accélère près de l'étoile.",
            "C'est la deuxième loi de Kepler.",
        ],
    ),
    ("credits", 14, []),
]


def tone(path: Path, seconds: float, freq: float) -> None:
    rate = 48000
    t = np.arange(int(seconds * rate)) / rate
    env = np.minimum(1.0, np.minimum(t / 0.5, (seconds - t) / 0.5))
    pcm = (0.25 * env * np.sin(2 * math.pi * freq * t) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--profile", default="draft_720p")
    args = parser.parse_args()
    create_app([])
    folder = Path(args.folder)
    folder.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(1920, 1080, 30, 1)
    project = create_project("Pourquoi la Lune change-t-elle de forme ?", canvas, SCENES[0][0], SCENES[0][1])
    project.scenes[0].name = "Introduction"
    for tid, dur, _subs in SCENES[1:]:
        scene = Scene.create(TEMPLATES[tid][0].split(" (")[0], duration_frames=dur * 30)
        TEMPLATES[tid][1](project, scene)
        project.scenes.append(scene)
    root = ProjectStore().create(folder / "Demo Gate 6", project).root
    (root / "audio").mkdir(exist_ok=True)
    for i, (scene, (_tid, dur, subs)) in enumerate(zip(project.scenes, SCENES, strict=True)):
        if subs:
            step = scene.duration_frames // len(subs)
            for k, text in enumerate(subs):
                scene.subtitles.append(Subtitle.create(k * step + 15, (k + 1) * step - 15, text))
        wav = root / "audio" / f"narration-{i + 1}.wav"
        tone(wav, dur - 1.0, 220.0 + 55 * i)
        asset = Asset(id=f"asset-{i:012x}", path=f"audio/narration-{i + 1}.wav", kind="audio")
        asset.license.author = "signal synthétique de démonstration"
        asset.license.license = "own-work"
        asset.license.redistribution_allowed = True
        project.assets.append(asset)
        scene.audio.append(
            AudioClip.create(
                asset.id,
                f"Narration {i + 1}",
                offset_frames=15,
                duration_seconds=dur - 1.0,
                fade_out_seconds=0.5,
            )
        )
    ProjectStore().save_atomic(project, root / "project.json")
    out = folder / "demo-gate6.mp4"
    t0 = time.perf_counter()

    def progress(i: int, n: int) -> None:
        if i % 300 == 0 or i == n:
            print(f"{i}/{n} images ({time.perf_counter() - t0:.0f} s)", flush=True)

    result = export_project(
        project,
        args.profile,
        str(out),
        progress=progress,
        assets=lambda aid: next((root / a.path for a in project.assets if a.id == aid), None),
    )
    pr = result.probe
    print(
        f"OK {out} : {pr.width}x{pr.height}, {pr.nb_frames} images, {pr.duration:.2f} s, audio={pr.has_audio}"
    )
    print(f"rendu : {result.elapsed_seconds:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

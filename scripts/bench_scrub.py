"""Mesure la latence de scrubbing (évaluation + dessin d'une image) sur un projet de 100 objets animés.

Usage : ``QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/bench_scrub.py [--objects 100] [--frames 120]``.
Sans interface : reproduit exactement le chemin ``ProjectDocument.state()`` → ``paint_scene_state`` du canevas
(à la taille d'une vue d'éditeur 1280×720) et l'export 1080p.
"""

from __future__ import annotations

import argparse
import random
import statistics
import time

from PySide6.QtGui import QImage, QPainter

from antares_studio.app.main import create_app
from antares_studio.domain.kinds import KINDS, spec_for
from antares_studio.domain.model import Canvas, Node, Project, Scene
from antares_studio.rendering.qt_painter import paint_scene_state
from antares_studio.timeline.evaluator import evaluate
from antares_studio.timeline.presets import apply_preset


def build_project(n_objects: int, duration: int, seed: int = 7) -> Project:
    rng = random.Random(seed)
    project = Project.create("Banc de scrubbing", Canvas(1920, 1080, 30, 1))
    scene = Scene.create("Charge", duration_frames=duration)
    kinds = [k for k in KINDS if k not in ("group", "image")]
    presets = ["translate", "rotate", "pulse", "appear", "orbit"]
    for i in range(n_objects):
        kind = kinds[i % len(kinds)]
        spec = spec_for(kind)
        node = Node.create(
            kind,
            f"{spec.label} {i}",
            position=[rng.uniform(100, 1820), rng.uniform(100, 980)],
            style=spec.default_style(),
            params=spec.default_params(),
        )
        if kind in ("text", "callout"):
            node.params["text"] = f"Objet {i} — ∑ αβγ"
        scene.nodes.append(node)
        preset = presets[i % len(presets)]
        params: dict[str, object] = {"duration_frames": duration}
        if preset == "translate":
            params.update({"dx": rng.uniform(-300, 300), "dy": rng.uniform(-200, 200)})
        if preset == "orbit":
            params.update({"center_x": 960, "center_y": 540, "radius": rng.uniform(100, 400), "turns": 1})
        scene.tracks += apply_preset(preset, node, params)
    project.scenes.append(scene)
    return project


def bench(project: Project, frames: int, width: int, height: int) -> dict[str, float]:
    scene = project.scenes[0]
    img = QImage(width, height, QImage.Format.Format_RGBA8888)
    eval_ms: list[float] = []
    paint_ms: list[float] = []
    for f in range(frames):
        frame = (f * 7) % scene.duration_frames  # sauts aléatoires comme un scrubbing
        t0 = time.perf_counter()
        state = evaluate(project, scene.id, frame)
        t1 = time.perf_counter()
        painter = QPainter(img)
        try:
            paint_scene_state(painter, state, project.canvas, width, height, None, None)
        finally:
            painter.end()
        t2 = time.perf_counter()
        eval_ms.append((t1 - t0) * 1000)
        paint_ms.append((t2 - t1) * 1000)
    total = [a + b for a, b in zip(eval_ms, paint_ms, strict=True)]
    q = statistics.quantiles(total, n=20)
    return {
        "eval_p50_ms": statistics.median(eval_ms),
        "paint_p50_ms": statistics.median(paint_ms),
        "total_p50_ms": statistics.median(total),
        "total_p95_ms": q[18],
        "total_max_ms": max(total),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects", type=int, default=100)
    parser.add_argument("--frames", type=int, default=120)
    args = parser.parse_args()
    create_app([])
    project = build_project(args.objects, 300)
    print(f"{args.objects} objets, {len(project.scenes[0].tracks)} pistes, {args.frames} images mesurées")
    for label, w, h in (("vue éditeur 1280×720", 1280, 720), ("export 1920×1080", 1920, 1080)):
        r = bench(project, args.frames, w, h)
        print(
            f"{label} : évaluation p50 {r['eval_p50_ms']:.1f} ms, dessin p50 {r['paint_p50_ms']:.1f} ms, "
            f"total p50 {r['total_p50_ms']:.1f} ms, p95 {r['total_p95_ms']:.1f} ms, "
            f"max {r['total_max_ms']:.1f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

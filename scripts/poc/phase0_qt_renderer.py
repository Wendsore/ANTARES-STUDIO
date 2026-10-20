"""Phase 0 PoC — rendu 2D Qt (QPainter hors écran) + encodage FFmpeg.

Scène de référence : cercle (Terre), petite Lune en orbite 360° sur 5 s,
flèche de vitesse tangentielle, texte « Schéma non à l'échelle ».
L'état est calculé par une fonction pure ``evaluate(frame)`` : aucune
dépendance au temps réel. Les frames RGBA sont envoyées sur stdin de ffmpeg.

Usage :
    python scripts/poc/phase0_qt_renderer.py OUT.mp4 [--width 1920 --height 1080 --fps 30 --seconds 5]
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
import time
from dataclasses import dataclass

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF, QGuiApplication


@dataclass(frozen=True)
class SceneState:
    earth: tuple[float, float]
    moon: tuple[float, float]
    arrow_from: tuple[float, float]
    arrow_to: tuple[float, float]
    label_opacity: float


def evaluate(frame: int, total_frames: int, w: int, h: int) -> SceneState:
    """frame -> état, déterministe. Orbite d'un tour complet sur la durée."""
    cx, cy = w / 2, h / 2
    radius = min(w, h) * 0.3
    theta = 2 * math.pi * frame / total_frames
    mx, my = cx + radius * math.cos(theta), cy + radius * math.sin(theta)
    # vitesse tangentielle (sens trigonométrique écran : y vers le bas)
    tx, ty = -math.sin(theta), math.cos(theta)
    arrow_len = radius * 0.35
    fade_frames = max(1, total_frames // 10)
    opacity = min(1.0, frame / fade_frames)
    return SceneState(
        earth=(cx, cy),
        moon=(mx, my),
        arrow_from=(mx, my),
        arrow_to=(mx + tx * arrow_len, my + ty * arrow_len),
        label_opacity=opacity,
    )


def draw(img: QImage, st: SceneState, w: int, h: int) -> None:
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(0, 0, w, h, QColor("#0b1020"))
    # Terre
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#2677B8"))
    r_e = min(w, h) * 0.08
    p.drawEllipse(QPointF(*st.earth), r_e, r_e)
    # orbite (trait fin)
    pen = QPen(QColor(255, 255, 255, 60), 2)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    radius = min(w, h) * 0.3
    p.drawEllipse(QPointF(*st.earth), radius, radius)
    # Lune
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#D9D9D9"))
    r_m = min(w, h) * 0.025
    p.drawEllipse(QPointF(*st.moon), r_m, r_m)
    # Flèche
    pen = QPen(QColor("#F2A93B"), max(2.0, w / 480))
    p.setPen(pen)
    a, b = QPointF(*st.arrow_from), QPointF(*st.arrow_to)
    p.drawLine(a, b)
    ang = math.atan2(b.y() - a.y(), b.x() - a.x())
    head = max(8.0, w / 120)
    p.setBrush(QColor("#F2A93B"))
    p.drawPolygon(QPolygonF([
        b,
        QPointF(b.x() - head * math.cos(ang - 0.5), b.y() - head * math.sin(ang - 0.5)),
        QPointF(b.x() - head * math.cos(ang + 0.5), b.y() - head * math.sin(ang + 0.5)),
    ]))
    # Texte
    font = QFont("DejaVu Sans", max(10, int(h / 30)))
    p.setFont(font)
    c = QColor("#FFFFFF")
    c.setAlphaF(st.label_opacity)
    p.setPen(c)
    p.drawText(int(w * 0.04), int(h * 0.94), "Schéma non à l'échelle — Terre et Lune")
    p.end()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ns = ap.parse_args()

    # QGuiApplication requis pour les polices ; plateforme offscreen.
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication(sys.argv[:1])  # noqa: F841
    w, h, fps = ns.width, ns.height, ns.fps
    total = int(round(ns.seconds * fps))

    cmd = [
        ns.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", str(fps), "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", ns.out,
    ]
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    img = QImage(w, h, QImage.Format.Format_RGBA8888)
    t_draw = 0.0
    for f in range(total):
        st = evaluate(f, total, w, h)
        td = time.perf_counter()
        draw(img, st, w, h)
        t_draw += time.perf_counter() - td
        proc.stdin.write(img.constBits().tobytes())
    proc.stdin.close()
    rc = proc.wait()
    t1 = time.perf_counter()
    print(f"frames={total} size={w}x{h} fps={fps} draw_s={t_draw:.2f} total_s={t1 - t0:.2f} ffmpeg_rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

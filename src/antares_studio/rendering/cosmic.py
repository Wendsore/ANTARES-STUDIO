"""Phénomènes cosmiques et lumière : particules, trou noir, sources de lumière (ADR-0009).

- **Particules** (graine fixe, donc chaque image est reproductible) : explosion, coquille de supernova
  en expansion (bord turbulent façon *Outer Wilds*), nébuleuse résiduelle, disque d'accrétion
  (rotation képlérienne ω ∝ r^-3/2). Tout est piloté par ``time_s``.
- **Trou noir** : horizon noir, anneau de photons, disque d'accrétion incliné dont la partie arrière
  est vue au-dessus et au-dessous de l'horizon (image déviée par la lentille gravitationnelle,
  approximation visuelle) et côté approchant plus brillant (effet Doppler relativiste, « beaming »).
- **Lumière** : halo, projecteur (cône), pénombre (tout s'assombrit sauf un cercle éclairé), rayons.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from functools import lru_cache
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPolygonF, QRadialGradient

from antares_studio.domain.colors import parse_color
from antares_studio.rendering.celestial import _qimage

Array = Any


@lru_cache(maxsize=16)
def _seeds(mode: str, count: int, seed: int) -> dict[str, Array]:
    rng = np.random.default_rng(seed * 7919 + sum(map(ord, mode)))  # hash() varie d'un lancement à l'autre
    u = rng.normal(size=(count, 3))
    u /= np.maximum(np.linalg.norm(u, axis=1), 1e-9)[:, None]
    return {
        "dir": u,
        "speed": rng.uniform(0.25, 1.0, count) ** 0.6,
        "size": rng.uniform(0.5, 1.4, count),
        "mix": rng.uniform(0, 1, count),
        "phase": rng.uniform(0, 2 * math.pi, count),
        "rad": np.sqrt(rng.uniform(0, 1, count)),
        "theta": rng.uniform(0, 2 * math.pi, count),
        "noise": rng.normal(size=count),
    }


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor.fromRgbF(
        a.redF() + (b.redF() - a.redF()) * t,
        a.greenF() + (b.greenF() - a.greenF()) * t,
        a.blueF() + (b.blueF() - a.blueF()) * t,
        a.alphaF() + (b.alphaF() - a.alphaF()) * t,
    )


def particle_state(params: dict[str, Any]) -> tuple[Array, Array, Array, Array]:
    """Positions (N, 2), tailles (N,), opacités (N,), mélange de couleur (N,) au temps ``time_s``."""
    mode = str(params.get("mode", "explosion"))
    n = max(1, min(6000, int(params.get("count", 800))))
    s = _seeds(mode, n, int(params.get("seed", 1)))
    t = max(0.0, float(params.get("time_s", 0.0)))
    radius = max(1.0, float(params.get("radius", 400.0)))
    speed = float(params.get("speed", 300.0))
    size = max(0.3, float(params.get("size", 4.0)))
    life = max(1e-3, float(params.get("lifetime", 3.0)))
    turb = float(params.get("turbulence", 0.3))
    d = s["dir"]
    if mode == "explosion":
        drag = max(0.0, float(params.get("drag", 1.2)))
        travel = speed * (1 - math.exp(-drag * t)) / drag if drag > 0 else speed * t
        r = travel * s["speed"]
        pos = d[:, :2] * r[:, None]
        alpha = np.full(n, max(0.0, 1.0 - t / life) ** 1.4)
        mix = np.clip(t / life + 0.25 * s["mix"], 0, 1)
        sizes = size * s["size"] * (1 + 0.6 * min(1.0, t / life))
    elif mode == "shell":
        big_r = speed * t
        wob = 1 + turb * 0.12 * np.sin(3 * s["theta"] + s["phase"] + 1.7 * t) + turb * 0.05 * s["noise"]
        r = big_r * wob
        pos = d[:, :2] * r[:, None]
        rim = 1.0 - np.abs(d[:, 2])  # brillance du limbe : la coquille est vue par la tranche sur le bord
        alpha = np.clip(0.25 + 0.75 * rim**1.5, 0, 1) * max(0.0, 1.0 - t / life) ** 0.5
        mix = np.clip(1 - rim + 0.3 * s["mix"], 0, 1)
        sizes = size * s["size"] * (1 + 0.5 * rim)
    elif mode == "nebula":
        grow = 1 + float(params.get("expansion", 0.05)) * t
        th = s["theta"]
        rr = radius * (0.3 + 0.7 * s["rad"]) * (1 + turb * 0.35 * np.sin(5 * th + s["phase"])) * grow
        pos = np.stack([np.cos(th) * rr, np.sin(th) * rr * 0.85], axis=1)
        pos += s["dir"][:, :2] * radius * 0.08 * turb
        alpha = np.clip(0.3 + 0.7 * s["mix"], 0, 1) * np.clip(t / max(life * 0.2, 1e-3), 0, 1)
        mix = np.clip(s["rad"] + 0.2 * s["noise"], 0, 1)
        sizes = size * s["size"] * 3.0
    else:  # accretion
        inner, outer = 0.25, 1.0
        rho = radius * (inner + (outer - inner) * s["rad"] ** 1.3)
        inflow = float(params.get("inflow", 0.02))
        rho = radius * inner + (rho - radius * inner) * ((1 - inflow * t) % 1.0 or 1.0)
        omega = speed / radius * (rho / radius) ** -1.5
        th = s["theta"] + omega * t
        tilt = math.radians(float(params.get("tilt_deg", 70.0)))
        pos = np.stack([np.cos(th) * rho, np.sin(th) * rho * math.cos(tilt)], axis=1)
        alpha = np.clip(0.35 + 0.65 * (1 - s["rad"]), 0, 1)
        mix = s["rad"]
        sizes = size * s["size"] * (1.3 - 0.6 * s["rad"])
    return pos, sizes, alpha, mix


_NEB_CACHE: OrderedDict[tuple[Any, ...], QImage] = OrderedDict()


def _blur(a: Array, sigma: float) -> Array:
    """Flou gaussien séparable (numpy seul)."""
    r = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 0, a)
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 1, out)
    return out


def nebula_image(params: dict[str, Any], ca: QColor, cb: QColor, px: int) -> QImage:
    """Nébuleuse : les particules sont accumulées dans une grille puis floutées (volutes continues)."""
    pos, _sizes, alpha, mix = particle_state(params)
    bounds = particles_bounds(params)
    half = bounds.width() / 2
    key = (
        px,
        round(half, 1),
        round(float(params.get("time_s", 0.0)), 2),
        int(params.get("count", 800)),
        int(params.get("seed", 1)),
        round(float(params.get("turbulence", 0.3)), 3),
        ca.rgba(),
        cb.rgba(),
        round(float(params.get("size", 4.0)), 2),
    )
    img = _NEB_CACHE.get(key)
    if img is not None:
        return img
    n = max(16, px)
    ix = np.clip(((pos[:, 0] + half) / (2 * half) * n).astype(int), 0, n - 1)
    iy = np.clip(((pos[:, 1] + half) / (2 * half) * n).astype(int), 0, n - 1)
    acc = np.zeros((n, n, 4), dtype=np.float64)
    cols = np.array(
        [
            [
                ca.redF() + (cb.redF() - ca.redF()) * m,
                ca.greenF() + (cb.greenF() - ca.greenF()) * m,
                ca.blueF() + (cb.blueF() - ca.blueF()) * m,
            ]
            for m in mix
        ]
    )
    np.add.at(acc, (iy, ix), np.concatenate([cols * alpha[:, None], alpha[:, None]], axis=1))
    sigma = max(1.0, float(params.get("size", 4.0)) * 2.2 * n / (2 * half))
    for c in range(4):
        acc[..., c] = _blur(acc[..., c], sigma)
    dens = acc[..., 3]
    norm = max(1e-9, float(np.percentile(dens[dens > 0], 99.5))) if (dens > 0).any() else 1.0
    a = np.clip(dens / norm, 0, 1) ** 0.8
    rgb = acc[..., :3] / np.maximum(dens, 1e-12)[..., None]
    img = _qimage(
        np.concatenate([np.clip(rgb * (0.6 + 0.6 * a[..., None]), 0, 1), a[..., None] * 0.9], axis=-1)
    )
    _NEB_CACHE[key] = img
    if len(_NEB_CACHE) > 12:
        _NEB_CACHE.popitem(last=False)
    return img


def paint_particles(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    ca = qcolor(style.get("color_a", "#FFFFFF"))
    cb = qcolor(style.get("color_b", "#FF7A3D"))
    mode = str(params.get("mode", "explosion"))
    t = max(0.0, float(params.get("time_s", 0.0)))
    if mode == "nebula":
        bounds = particles_bounds(params)
        tr = painter.worldTransform()
        dev = max(1e-3, math.hypot(tr.m11(), tr.m12()))
        px = int(min(1100, max(32, round(bounds.width() * dev * 0.7))))
        painter.save()
        if bool(params.get("additive", True)):
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        painter.drawImage(bounds, nebula_image(params, ca, cb, px))
        painter.restore()
        return
    pos, sizes, alpha, mix = particle_state(params)
    painter.save()
    if bool(params.get("additive", True)):
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    if mode == "shell" and float(params.get("speed", 300.0)) * t > 1:
        big_r = float(params.get("speed", 300.0)) * t
        life = max(1e-3, float(params.get("lifetime", 3.0)))
        fade = max(0.0, 1.0 - t / life) ** 0.5
        grad = QRadialGradient(QPointF(0, 0), big_r * 1.08)
        inner, edge = QColor(cb), QColor(ca)
        inner.setAlphaF(0.10 * fade)
        edge.setAlphaF(0.55 * fade)
        clear = QColor(ca)
        clear.setAlphaF(0.0)
        grad.setColorAt(0.0, inner)
        grad.setColorAt(0.78, inner)
        grad.setColorAt(0.93, edge)
        grad.setColorAt(1.0, clear)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPointF(0, 0), big_r * 1.08, big_r * 1.08)
    painter.setPen(Qt.PenStyle.NoPen)
    order = np.argsort(sizes)[::-1]
    for i in order:
        a = float(alpha[i])
        if a <= 0.01:
            continue
        c = _lerp_color(ca, cb, float(mix[i]))
        x, y, r = float(pos[i, 0]), float(pos[i, 1]), float(sizes[i])
        halo = QColor(c)
        halo.setAlphaF(a * 0.22 * c.alphaF())
        painter.setBrush(halo)
        painter.drawEllipse(QPointF(x, y), r * 2.4, r * 2.4)
        c.setAlphaF(a * c.alphaF())
        painter.setBrush(c)
        painter.drawEllipse(QPointF(x, y), r, r)
    painter.restore()


def particles_bounds(params: dict[str, Any]) -> QRectF:
    mode = str(params.get("mode", "explosion"))
    t = max(0.0, float(params.get("time_s", 0.0)))
    r = max(1.0, float(params.get("radius", 400.0)))
    if mode in ("explosion", "shell"):
        r = max(r, abs(float(params.get("speed", 300.0))) * max(t, 0.5) * 1.3)
    elif mode == "nebula":
        r *= (1.6 + float(params.get("turbulence", 0.3)) * 0.5) * (
            1 + float(params.get("expansion", 0.05)) * t
        )
    return QRectF(-r, -r, 2 * r, 2 * r)


# --- trou noir -------------------------------------------------------------------------------------

_BH_CACHE: OrderedDict[tuple[Any, ...], QImage] = OrderedDict()


def black_hole_image(params: dict[str, Any], style: dict[str, Any], px: int) -> QImage:
    inner = max(1.2, float(params.get("disk_inner", 2.2)))
    outer = max(inner + 0.2, float(params.get("disk_outer", 5.5)))
    incl = math.radians(max(0.0, min(89.0, float(params.get("inclination_deg", 78.0)))))
    t = float(params.get("time_s", 0.0))
    beaming = max(0.0, min(1.0, float(params.get("beaming", 0.6))))
    lensing = bool(params.get("lensing", True))
    bright = float(params.get("brightness", 1.0))
    hot = QColor.fromRgbF(*parse_color(str(style.get("disk_hot", "#FFF4D6"))))
    cool = QColor.fromRgbF(*parse_color(str(style.get("disk_cool", "#FF7A2E"))))
    key = (
        px,
        round(inner, 3),
        round(outer, 3),
        round(incl, 4),
        round(t, 3),
        round(beaming, 3),
        lensing,
        round(bright, 3),
        hot.rgba(),
        cool.rgba(),
        round(float(params.get("spin_speed", 1.0)), 3),
    )
    img = _BH_CACHE.get(key)
    if img is not None:
        return img
    ext = outer * 1.02
    n = max(16, px)
    lin = (np.arange(n, dtype=np.float32) + 0.5 - n / 2) / (n / 2) * ext
    x, y = np.meshgrid(lin, lin)  # y vers le bas, unités : rayon de l'horizon
    q = max(math.cos(incl), 0.02)
    rho = np.sqrt(x**2 + (y / q) ** 2)  # rayon dans le plan du disque
    phi = np.arctan2(y / q, x)
    spin = float(params.get("spin_speed", 1.0))

    def disk_color(rr: Array, ph: Array, gain: float) -> Array:
        on = (rr >= inner) & (rr <= outer)
        u = np.clip((rr - inner) / (outer - inner), 0, 1)
        # ω ∝ r^-3/2 (Kepler) ; r borné : au centre exact, 0^-1,5 donnerait NaN (même hors du disque)
        ang = ph - spin * t * (np.maximum(rr, 1e-3) / inner) ** -1.5 * 2.0
        bands = (
            0.72 + 0.18 * np.sin(rr * 9.0 + 2.0 * np.sin(ang * 3.0)) + 0.10 * np.sin(ang * 7.0 + rr * 23.0)
        )
        prof = (1 - u) ** 1.6 * np.clip((rr - inner) * 6, 0, 1) * np.clip((outer - rr) * 3, 0, 1)
        beam = 1.0 + beaming * np.cos(ph + math.pi)  # côté gauche (qui s'approche) plus brillant
        k = (prof * bands * beam * gain * bright)[..., None] * on[..., None]
        hc = np.array([hot.redF(), hot.greenF(), hot.blueF()])
        cc = np.array([cool.redF(), cool.greenF(), cool.blueF()])
        col: Array = (hc * (1 - u[..., None]) + cc * u[..., None]) * k
        return col

    r_screen = np.sqrt(x**2 + y**2)
    rgb = np.zeros((n, n, 3), dtype=np.float32)
    back = y < 0
    rgb += disk_color(rho, phi, 1.0) * back[..., None]
    if lensing:
        # partie arrière du disque déviée au-dessus (et, plus faible, au-dessous) de l'horizon
        # (approximation visuelle : anneaux circulaires autour de l'horizon, d'autant plus visibles que
        # le disque est vu par la tranche ; fondu vers le plan du disque pour éviter toute couture)
        lr = r_screen + (inner - 1.15)
        strength = math.sin(incl) ** 2
        fade_top = np.clip(-y / 0.6, 0, 1) * np.clip(1 - (r_screen - 1.05) / (outer * 0.55), 0, 1)
        rgb += disk_color(lr, np.arctan2(-y, x), 0.75 * strength) * (fade_top * (r_screen > 1.05))[..., None]
        fade_bot = np.clip(y / 0.25, 0, 1) * np.clip((1.3 - r_screen) / 0.25, 0, 1) * (r_screen > 1.02)
        rgb += disk_color(lr, np.arctan2(y, x), 0.22 * strength) * fade_bot[..., None]
    horizon = r_screen < 1.0
    rgb[horizon] = 0.0
    ring = np.exp(-(((r_screen - 1.04) / 0.035) ** 2)) * (1.0 + 0.5 * beaming * -np.sign(x)) * 0.9 * bright
    rgb += ring[..., None] * np.array([hot.redF(), hot.greenF(), hot.blueF()])
    front = y >= 0
    # le disque avant passe devant l'horizon
    rgb = np.where((front & (rho >= inner) & (rho <= outer))[..., None], disk_color(rho, phi, 1.0), rgb)
    lum = np.clip(rgb.max(axis=-1), 0, 1)
    alpha = np.maximum(lum, horizon.astype(np.float32))
    alpha = np.maximum(alpha, np.clip((1.06 - r_screen) * 40, 0, 1))
    rgba = np.concatenate([np.clip(rgb, 0, 1), alpha[..., None]], axis=-1)
    img = _qimage(rgba)
    _BH_CACHE[key] = img
    if len(_BH_CACHE) > 24:
        _BH_CACHE.popitem(last=False)
    return img


def paint_black_hole(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    size = max(2.0, float(params.get("size", 160.0)))  # diamètre apparent de l'horizon
    outer = max(1.4, float(params.get("disk_outer", 5.5)))
    half = size / 2 * outer * 1.02
    t = painter.worldTransform()
    dev = max(1e-3, math.hypot(t.m11(), t.m12()))
    px = int(min(2000, max(32, round(2 * half * dev * float(params.get("resolution", 0.6))))))
    painter.drawImage(QRectF(-half, -half, 2 * half, 2 * half), black_hole_image(params, style, px))


def black_hole_bounds(params: dict[str, Any]) -> QRectF:
    size = max(2.0, float(params.get("size", 160.0)))
    half = size / 2 * max(1.4, float(params.get("disk_outer", 5.5))) * 1.02
    return QRectF(-half, -half, 2 * half, 2 * half)


# --- lumière ---------------------------------------------------------------------------------------


def paint_light(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    mode = str(params.get("mode", "halo"))
    radius = max(1.0, float(params.get("radius", 300.0)))
    k = max(0.0, float(params.get("intensity", 1.0)))
    color = qcolor(style.get("fill", "#FFE9B0"))
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    if mode == "darken":
        dark = QColor(qcolor(style.get("shade_color", "#000000")))
        dark.setAlphaF(max(0.0, min(1.0, float(params.get("darkness", 0.75)))))
        soft = max(0.01, min(0.95, float(params.get("softness", 0.35))))
        big = max(4000.0, radius * 6)
        grad = QRadialGradient(QPointF(0, 0), radius)
        clear = QColor(dark)
        clear.setAlphaF(0.0)
        grad.setColorAt(0.0, clear)
        grad.setColorAt(1.0 - soft, clear)
        grad.setColorAt(1.0, dark)
        grad.setSpread(QRadialGradient.Spread.PadSpread)
        painter.setBrush(QBrush(grad))
        painter.drawRect(QRectF(-big, -big, 2 * big, 2 * big))
        painter.restore()
        return
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    c0, c1 = QColor(color), QColor(color)
    c0.setAlphaF(min(1.0, 0.9 * k))
    c1.setAlphaF(0.0)
    if mode == "halo":
        grad = QRadialGradient(QPointF(0, 0), radius)
        mid = QColor(color)
        mid.setAlphaF(min(1.0, 0.25 * k))
        grad.setColorAt(0.0, c0)
        grad.setColorAt(0.25, mid)
        grad.setColorAt(1.0, c1)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPointF(0, 0), radius, radius)
    elif mode == "spot":
        ang = math.radians(float(params.get("angle_deg", 0.0)))
        spread = math.radians(max(1.0, min(170.0, float(params.get("spread_deg", 30.0)))))
        path = QPainterPath(QPointF(0, 0))
        for i in range(33):
            a = ang - spread / 2 + spread * i / 32
            path.lineTo(QPointF(math.cos(a) * radius, -math.sin(a) * radius))
        path.closeSubpath()
        grad = QRadialGradient(QPointF(0, 0), radius)
        grad.setColorAt(0.0, c0)
        grad.setColorAt(1.0, c1)
        painter.setBrush(QBrush(grad))
        painter.drawPath(path)
    else:  # rays
        count = max(2, int(params.get("count", 12)))
        rot = math.radians(float(params.get("angle_deg", 0.0)))
        width = math.radians(max(0.5, float(params.get("spread_deg", 6.0))))
        grad = QRadialGradient(QPointF(0, 0), radius)
        grad.setColorAt(0.0, c0)
        grad.setColorAt(1.0, c1)
        painter.setBrush(QBrush(grad))
        for i in range(count):
            a = rot + 2 * math.pi * i / count
            ln = radius * (0.75 + 0.25 * math.sin(i * 2.399))
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(0, 0),
                        QPointF(math.cos(a - width / 2) * ln, -math.sin(a - width / 2) * ln),
                        QPointF(math.cos(a + width / 2) * ln, -math.sin(a + width / 2) * ln),
                    ]
                )
            )
    painter.restore()


def light_bounds(params: dict[str, Any]) -> QRectF:
    r = max(1.0, float(params.get("radius", 300.0)))
    return QRectF(-r, -r, 2 * r, 2 * r)

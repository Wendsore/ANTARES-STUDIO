"""Astres texturés : sphère projetée pixel par pixel depuis une carte équirectangulaire (ADR-0009).

Repère de vue : x à droite, y en haut, z vers l'observateur ; projection orthographique. Le corps tourne
autour de son axe (``spin_deg``, sens direct : les reliefs vont de gauche à droite), son axe est
incliné dans le plan de l'image (``tilt_deg``) puis basculé vers l'observateur (``pitch_deg``).
La lumière vient de ``light_az_deg`` (0 = de derrière l'observateur : astre plein ; 180 = de derrière
l'astre : nouvelle lune) et ``light_el_deg`` (hauteur). L'image est calculée à la résolution réelle de
sortie (échelle du painter) et mise en cache : l'aperçu reste léger, l'export reste net.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient

from antares_studio.domain.colors import is_color, parse_color
from antares_studio.resources.astro import (
    BODIES,
    SATURN_RING_RADII,
    SATURN_RING_TEXTURE,
    texture_path,
)
from antares_studio.science.light import blackbody_rgb

Array = Any

MAX_PIXELS = 2400  # diamètre maximal calculé (au-delà : mise à l'échelle par le painter)
_CACHE: OrderedDict[tuple[Any, ...], QImage] = OrderedDict()
_CACHE_SIZE = 48


@lru_cache(maxsize=24)
def load_texture(path: str) -> Array:
    """Texture → tableau float32 (H, W, C) dans [0, 1] ; C = 4 si l'image a une transparence."""
    img = QImage(path)
    if img.isNull():
        raise FileNotFoundError(path)
    alpha = img.hasAlphaChannel()
    img = img.convertToFormat(QImage.Format.Format_RGBA8888 if alpha else QImage.Format.Format_RGB888)
    c = 4 if alpha else 3
    raw = np.frombuffer(img.constBits(), dtype=np.uint8, count=img.sizeInBytes())
    arr = raw.reshape(img.height(), img.bytesPerLine())[:, : img.width() * c].reshape(
        img.height(), img.width(), c
    )
    return arr.astype(np.float32) / 255.0


def _sample(tex: Array, u: Array, v: Array) -> Array:
    """Échantillonnage bilinéaire, ``u`` périodique (longitude), ``v`` borné (latitude)."""
    h, w = tex.shape[:2]
    x = (u % 1.0) * w - 0.5
    y = np.clip(v * h - 0.5, 0, h - 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    x0 %= w
    x1 = (x0 + 1) % w
    y1 = np.minimum(y0 + 1, h - 1)
    top = tex[y0, x0] * (1 - fx) + tex[y0, x1] * fx
    bot = tex[y1, x0] * (1 - fx) + tex[y1, x1] * fx
    out: Array = top * (1 - fy) + bot * fy
    return out


def body_matrix(rotation: float, tilt: float, pitch: float) -> Array:
    """Repère du corps → repère de vue (degrés)."""
    s, t, p = (math.radians(a) for a in (rotation, tilt, pitch))
    ry = np.array([[math.cos(s), 0, math.sin(s)], [0, 1, 0], [-math.sin(s), 0, math.cos(s)]])
    rz = np.array([[math.cos(t), math.sin(t), 0], [-math.sin(t), math.cos(t), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    out: Array = rx @ rz @ ry
    return out


def light_vector(az_deg: float, el_deg: float) -> Array:
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)])


def phase_fraction(light_az_deg: float, light_el_deg: float = 0.0) -> float:
    """Fraction éclairée du disque vu par l'observateur : (1 + cos α) / 2, α angle de phase."""
    cos_alpha = float(light_vector(light_az_deg, light_el_deg)[2])
    return (1.0 + cos_alpha) / 2.0


def _smoothstep(e0: float, e1: float, x: Array) -> Array:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _qimage(rgba: Array) -> QImage:
    data = np.ascontiguousarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8))
    h, w = data.shape[:2]
    return QImage(data.data, w, h, 4 * w, QImage.Format.Format_RGBA8888).copy()


def render_body(params: dict[str, Any], diameter_px: int, texture_override: Path | None = None) -> QImage:
    """Image RGBA du disque de l'astre (et de ses anneaux) ; le centre de l'image est le centre de
    l'astre, la demi-largeur vaut ``extent(params)`` rayons."""
    body_id = str(params.get("body", "earth"))
    body = BODIES.get(body_id)
    star = body_id == "star"
    emissive = star or (body is not None and body.emissive)
    ext = extent(params)
    n = max(8, int(round(diameter_px * ext)))
    r_px = diameter_px / 2.0
    lin = (np.arange(n, dtype=np.float32) + 0.5 - n / 2) / r_px
    x, yd = np.meshgrid(lin, lin)
    y = -yd
    r2 = x * x + y * y
    inside = r2 <= 1.0
    edge = np.clip((1.0 - np.sqrt(r2)) * r_px + 0.5, 0.0, 1.0)  # bord anti-crénelé
    z = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
    m = body_matrix(
        float(params.get("spin_deg", 0.0)),
        float(params.get("tilt_deg", 0.0)),
        float(params.get("pitch_deg", 0.0)),
    )
    nrm = np.stack([x, y, z], axis=-1)
    v = nrm @ m  # repère du corps (m orthogonale : vᵀ = nᵀ m)
    lat = np.arcsin(np.clip(v[..., 1], -1, 1))
    lon = np.arctan2(v[..., 0], v[..., 2])
    u = lon / (2 * math.pi) + 0.5
    vv = 0.5 - lat / math.pi

    if texture_override is not None:
        tex_file = str(texture_override)
    elif star or body is None:
        tex_file = str(texture_path("sun.jpg"))
    elif body.alt_texture and bool(params.get("surface", False)):
        tex_file = str(texture_path(body.alt_texture))
    else:
        tex_file = str(texture_path(body.texture))
    try:
        color = _sample(load_texture(tex_file), u, vv)[..., :3]
    except FileNotFoundError:
        color = np.full(u.shape + (3,), 0.5, dtype=np.float32)

    rgba = np.zeros((n, n, 4), dtype=np.float32)
    if emissive:
        if star:
            # luminance de la granulation solaire × couleur du corps noir
            lum = color @ np.array([0.30, 0.59, 0.11], dtype=np.float32)
            mean = float(lum[inside].mean()) if inside.any() else 0.5
            # granulation discrète : une étoile n'a pas de « taches » sombres
            lum = 0.95 + 0.45 * (lum - mean)
            tint = np.array(blackbody_rgb(float(params.get("temperature_k", 5772.0))), dtype=np.float32)
            # surface très lumineuse : la couleur du corps noir tire vers le blanc au centre
            color = np.clip(lum[..., None] * (0.55 * tint + 0.45), 0, 1.0) * (0.7 + 0.3 * tint)
        ld = float(params.get("limb_darkening", 0.6))
        color = color * (1.0 - ld * (1.0 - z))[..., None]
    else:
        lit = bool(params.get("lit", True))
        ambient = float(params.get("ambient", 0.04))
        if lit:
            lv = light_vector(
                float(params.get("light_az_deg", 50.0)), float(params.get("light_el_deg", 10.0))
            )
            d = nrm @ lv
            day = _smoothstep(-0.04, 0.06, d)
            shade = day * np.clip(d + 0.04, 0.0, 1.0) ** 0.8
        else:
            d = np.ones_like(z)
            day = np.ones_like(z)
            shade = np.ones_like(z)
        if body is not None and body.clouds_texture and float(params.get("clouds", 0.8)) > 0:
            shift = float(params.get("cloud_shift_deg", 0.0)) / 360.0
            try:
                cl = _sample(load_texture(str(texture_path(body.clouds_texture))), u + shift, vv)[..., :1]
                a = np.clip(cl * float(params.get("clouds", 0.8)), 0, 1)
                color = color * (1 - a) + a * 0.97
            except FileNotFoundError:
                pass
        color = color * (ambient + (1 - ambient) * shade)[..., None]
        if lit and body is not None and body.night_texture and bool(params.get("night_lights", True)):
            try:
                night = _sample(load_texture(str(texture_path(body.night_texture))), u, vv)
                color = color + night * ((1.0 - day) * 1.1)[..., None]
            except FileNotFoundError:
                pass
        atm = float(params.get("atmosphere", 1.0))
        if atm > 0 and body is not None and body.atmosphere:
            ac = QColor(body.atmosphere)
            acol = np.array([ac.redF(), ac.greenF(), ac.blueF()], dtype=np.float32)
            rim = (1.0 - z) ** 3 * atm * np.clip(d + 0.35, 0.0, 1.0) * 0.9
            color = color + rim[..., None] * acol
            # halo hors du disque (fin liseré éclairé)
            rr = np.sqrt(r2)
            radial = np.stack([x, y, np.zeros_like(x)], axis=-1) / np.maximum(rr, 1e-6)[..., None]
            lit_side = np.clip(radial @ (lv if lit else np.array([0, 0, 1.0])) + 0.45, 0.0, 1.0)
            halo = np.clip(1.0 - (rr - 1.0) / 0.045, 0.0, 1.0) ** 2 * atm * lit_side * (rr > 1.0)
            rgba[..., :3] += halo[..., None] * acol
            rgba[..., 3] = np.maximum(rgba[..., 3], halo * 0.85)
    tint_hex = params.get("_tint")
    if isinstance(tint_hex, str) and is_color(tint_hex):
        tr, tg, tb, ta = parse_color(tint_hex)  # #RRGGBBAA du projet (QColor lirait #AARRGGBB)
        color = color * (1 - ta) + color * np.array([tr, tg, tb], dtype=np.float32) * ta
    a = edge * inside
    rgba[..., :3] = rgba[..., :3] * (1 - a[..., None]) + color * a[..., None]
    rgba[..., 3] = np.maximum(rgba[..., 3], a)

    if body is not None and body.rings and bool(params.get("rings", True)):
        _paint_rings(rgba, x, y, z, inside, m, params)
    return _qimage(rgba)


def _paint_rings(
    rgba: Array, x: Array, y: Array, z: Array, inside: Array, m: Array, params: dict[str, Any]
) -> None:
    try:
        tex = load_texture(str(texture_path(SATURN_RING_TEXTURE)))
    except FileNotFoundError:
        return
    profile = tex[tex.shape[0] // 2]  # (W, 4) : profil radial
    normal = m @ np.array([0.0, 1.0, 0.0])
    if abs(normal[2]) < 1e-3:
        return  # anneaux vus exactement par la tranche : invisibles
    zr = -(normal[0] * x + normal[1] * y) / normal[2]
    radius = np.sqrt(x * x + y * y + zr * zr)
    ri, ro = SATURN_RING_RADII
    t = (radius - ri) / (ro - ri)
    on = (t >= 0) & (t <= 1)
    idx = np.clip((t * (profile.shape[0] - 1)).astype(np.int64), 0, profile.shape[0] - 1)
    ring = profile[idx]
    alpha = ring[..., 3] * on * 0.95
    visible = alpha * (~inside | (zr > z))  # devant la planète ou hors du disque
    lit = bool(params.get("lit", True))
    shade = np.ones_like(x)
    if lit:
        lv = light_vector(float(params.get("light_az_deg", 50.0)), float(params.get("light_el_deg", 10.0)))
        px, py, pz = x, y, zr
        b = px * lv[0] + py * lv[1] + pz * lv[2]
        c = radius * radius - 1.0
        shadowed = (b * b - c > 0) & (b < 0)  # le rayon vers le Soleil traverse la planète
        ambient = float(params.get("ambient", 0.04))
        face = abs(float(normal @ lv)) ** 0.35
        shade = np.where(shadowed, ambient, ambient + (1 - ambient) * face)
    lum = ring[..., :3] @ np.array([0.30, 0.59, 0.11], dtype=np.float32)
    beige = np.array([0.86, 0.78, 0.64], dtype=np.float32)
    col = (beige * (0.45 + 0.7 * lum)[..., None]) * shade[..., None]
    rgba[..., :3] = rgba[..., :3] * (1 - visible[..., None]) + col * visible[..., None]
    rgba[..., 3] = visible + rgba[..., 3] * (1 - visible)


def extent(params: dict[str, Any]) -> float:
    """Demi-largeur de l'image calculée, en rayons de l'astre."""
    body = BODIES.get(str(params.get("body", "earth")))
    if body is not None and body.rings and bool(params.get("rings", True)):
        return SATURN_RING_RADII[1] + 0.05
    return 1.06


def _device_scale(painter: QPainter) -> float:
    t = painter.worldTransform()
    return max(1e-3, math.hypot(t.m11(), t.m12()))


def _key(params: dict[str, Any], px: int, tex: Path | None) -> tuple[Any, ...]:
    def q(name: str, default: float, step: float) -> float:
        return round(float(params.get(name, default)) / step) * step

    return (
        str(params.get("body", "earth")),
        px,
        str(tex or ""),
        q("spin_deg", 0.0, 0.1) % 360.0,
        q("tilt_deg", 0.0, 0.1),
        q("pitch_deg", 0.0, 0.1),
        q("light_az_deg", 50.0, 0.25),
        q("light_el_deg", 10.0, 0.25),
        q("ambient", 0.04, 0.005),
        bool(params.get("lit", True)),
        bool(params.get("night_lights", True)),
        q("clouds", 0.8, 0.01),
        q("cloud_shift_deg", 0.0, 0.1) % 360.0,
        q("atmosphere", 1.0, 0.01),
        q("temperature_k", 5772.0, 10.0),
        q("limb_darkening", 0.6, 0.01),
        bool(params.get("surface", False)),
        bool(params.get("rings", True)),
        str(params.get("_tint", "")),
    )


def cached_body_image(params: dict[str, Any], px: int, tex: Path | None = None) -> QImage:
    key = _key(params, px, tex)
    img = _CACHE.get(key)
    if img is None:
        img = render_body(params, px, tex)
        _CACHE[key] = img
        if len(_CACHE) > _CACHE_SIZE:
            _CACHE.popitem(last=False)
    else:
        _CACHE.move_to_end(key)
    return img


def tide_outline(radius: float, amount: float, angle_deg: float, samples: int = 180) -> QPolygonF:
    """Enveloppe de marée exagérée : r(θ) = R·(1 + a·P₂(cos(θ − φ))), deux bourrelets alignés sur φ
    (côté astre perturbateur et côté opposé), creux à 90°."""
    phi = math.radians(angle_deg)
    pts = []
    for i in range(samples):
        th = 2 * math.pi * i / samples
        c = math.cos(th - phi)
        r = radius * (1.0 + amount * 0.5 * (3 * c * c - 1.0))
        pts.append(QPointF(r * math.cos(th), -r * math.sin(th)))
    return QPolygonF(pts)


def paint_celestial(
    painter: QPainter,
    params: dict[str, Any],
    style: dict[str, Any],
    qcolor: Any,
    texture_override: Path | None = None,
) -> None:
    size = max(1.0, float(params.get("size", 300.0)))
    radius = size / 2
    body_id = str(params.get("body", "earth"))
    corona = _corona(params)
    if corona > 0:
        if body_id == "star":
            r, g, b = blackbody_rgb(float(params.get("temperature_k", 5772.0)))
            cc = QColor.fromRgbF(r, g, b)
        else:
            cc = QColor("#FFC766")
        grad = QRadialGradient(QPointF(0, 0), radius * (1.0 + 1.6 * corona))
        c0, c1 = QColor(cc), QColor(cc)
        c0.setAlphaF(min(1.0, 0.85 * corona))
        c1.setAlphaF(0.0)
        grad.setColorAt(0.0, c0)
        grad.setColorAt(1.0 / (1.0 + 1.6 * corona), c0)
        mid = QColor(cc)
        mid.setAlphaF(0.25 * corona)
        grad.setColorAt(0.5 + 0.5 / (1.0 + 1.6 * corona), mid)
        grad.setColorAt(1.0, c1)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        rr = radius * (1.0 + 1.6 * corona)
        painter.drawEllipse(QRectF(-rr, -rr, 2 * rr, 2 * rr))
        painter.restore()
    tide = float(params.get("tide_amount", 0.0))
    tide_angle = float(params.get("tide_angle_deg", 0.0))
    mode = str(params.get("tide_mode", "ocean"))
    px = int(min(MAX_PIXELS, max(8, round(size * _device_scale(painter)))))
    p = dict(params)
    tint = style.get("tint")
    if isinstance(tint, str) and is_color(tint) and parse_color(tint)[3] > 0:
        p["_tint"] = tint
    img = cached_body_image(p, px, texture_override)
    half = radius * extent(params)
    painter.save()
    if tide > 0 and mode == "body":
        # déformation de l'astre lui-même (exagérée) : étirement le long de l'axe de marée
        painter.rotate(-tide_angle)
        painter.scale(1.0 + tide, 1.0 / (1.0 + tide))
        painter.rotate(tide_angle)
    painter.drawImage(QRectF(-half, -half, 2 * half, 2 * half), img)
    painter.restore()
    if tide > 0 and mode == "ocean":
        ocean = qcolor(style.get("ocean_color", "#3FA9F5A0"))
        env = QPainterPath()
        env.addPolygon(tide_outline(radius, tide, tide_angle))
        env.closeSubpath()
        disc = QPainterPath()
        disc.addEllipse(QRectF(-radius, -radius, 2 * radius, 2 * radius))
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        faint = QColor(ocean)
        faint.setAlphaF(ocean.alphaF() * 0.25)
        painter.setBrush(faint)
        painter.drawPath(env.intersected(disc))
        painter.setBrush(ocean)
        painter.drawPath(env.subtracted(disc))
        edge = QColor(ocean)
        edge.setAlphaF(min(1.0, ocean.alphaF() + 0.35))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(edge, max(1.0, size * 0.006)))
        painter.drawPath(env)
        painter.restore()


def _corona(params: dict[str, Any]) -> float:
    """Halo des astres lumineux seulement : le défaut du type (0,6) ne doit pas auréoler une planète."""
    body_id = str(params.get("body", "earth"))
    body = BODIES.get(body_id)
    emissive = body_id == "star" or (body is not None and body.emissive)
    return float(params.get("corona", 0.6)) if emissive else 0.0


def celestial_bounds(params: dict[str, Any]) -> QRectF:
    size = max(1.0, float(params.get("size", 300.0)))
    half = size / 2 * extent(params)
    corona = _corona(params)
    half = max(half, size / 2 * (1.0 + 1.6 * corona))
    tide = float(params.get("tide_amount", 0.0))
    half = max(half, size / 2 * (1.0 + tide))
    return QRectF(-half, -half, 2 * half, 2 * half)

"""Traitement d'image des effets : flou, lueur, ombre portée, réglages de couleur, filtres de scène.

Calculs en NumPy sur des images RGBA prémultipliées (format de travail de ``QPainter``). Le flou est une
gaussienne approchée par trois flous en boîte successifs (erreur < 3 %), en O(pixels) quel que soit le
rayon. Aucune source de hasard non maîtrisée : le grain dépend de la scène et du numéro d'image, si bien
qu'un même export donne deux fois la même vidéo.
"""

from __future__ import annotations

import math
import zlib
from functools import lru_cache
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QTransform

from antares_studio.domain.effects import effect_values, post_values

MAX_EFFECT_PIXELS = 4096 * 4096  # garde-fou : un objet immense zoomé n'alloue pas des gigaoctets

Float = np.ndarray[Any, np.dtype[np.float32]]


# --- conversions --------------------------------------------------------------------------------------
def image_to_array(img: QImage) -> Float:
    """QImage -> tableau (h, w, 4) float32 RGBA **prémultiplié**, valeurs 0..1."""
    src = img.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
    w, h = src.width(), src.height()
    buf = np.frombuffer(src.constBits(), dtype=np.uint8, count=src.bytesPerLine() * h)
    arr = buf.reshape(h, src.bytesPerLine())[:, : w * 4].reshape(h, w, 4)
    return arr.astype(np.float32) / 255.0


def array_to_image(arr: Float) -> QImage:
    h, w = arr.shape[:2]
    data = np.ascontiguousarray((np.clip(arr, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
    img = QImage(data.data, w, h, w * 4, QImage.Format.Format_RGBA8888_Premultiplied)
    return img.copy()  # détache l'image du tampon NumPy


# --- flou -----------------------------------------------------------------------------------------------
def _box_blur_axis(a: Float, r: int, axis: int) -> Float:
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="constant"), axis=axis, dtype=np.float32)
    n = a.shape[axis]
    hi = [slice(None)] * a.ndim
    lo = [slice(None)] * a.ndim
    hi[axis] = slice(2 * r + 1, 2 * r + 1 + n)
    lo[axis] = slice(0, n)
    out = c[tuple(hi)] - c[tuple(lo)]
    out *= 1.0 / (2 * r + 1)
    return out


def box_radii(sigma: float, passes: int = 3) -> list[int]:
    """Rayons de boîtes dont l'enchaînement approche une gaussienne d'écart type ``sigma``."""
    if sigma <= 0.0:
        return [0] * passes
    ideal = math.sqrt(12.0 * sigma * sigma / passes + 1.0)
    lower = int(math.floor(ideal))
    if lower % 2 == 0:
        lower -= 1
    upper = lower + 2
    m = round(
        (12 * sigma * sigma - passes * lower * lower - 4 * passes * lower - 3 * passes) / (-4 * lower - 4)
    )
    return [max(0, ((lower if i < m else upper) - 1) // 2) for i in range(passes)]


def gaussian_blur(a: Float, sigma: float) -> Float:
    """Flou gaussien (approché) d'un tableau (h, w, c) ; bords prolongés par de la transparence."""
    if sigma < 0.3:
        return a
    out = a
    for r in box_radii(sigma):
        out = _box_blur_axis(out, r, 0)
        out = _box_blur_axis(out, r, 1)
    return out


# --- couleur --------------------------------------------------------------------------------------------
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)  # Rec. 709


def color_matrix(
    brightness: float = 0.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    temperature: float = 0.0,
    sepia: float = 0.0,
) -> tuple[Float, Float]:
    """Réglages enchaînés (saturation, sépia, température, contraste, luminosité) sous forme d'une seule
    transformation affine ``rgb @ m + b`` : ils sont tous linéaires et l'écrêtage n'a lieu qu'à la fin."""
    m = np.eye(3, dtype=np.float32)
    b = np.zeros(3, dtype=np.float32)
    luma = np.repeat(LUMA[:, None], 3, axis=1)  # rgb @ luma = gris répété sur les trois canaux

    def then(m2: Float, b2: Float) -> None:
        nonlocal m, b
        m = m @ m2
        b = b @ m2 + b2

    if saturation != 1.0:
        then(luma + (np.eye(3, dtype=np.float32) - luma) * saturation, np.zeros(3, dtype=np.float32))
    if sepia > 0.0:
        tone = LUMA[:, None] * np.array([1.07, 0.95, 0.74], dtype=np.float32)
        then(
            np.eye(3, dtype=np.float32) * (1.0 - sepia) + tone * sepia,
            np.array([0.06, 0.02, 0.0], dtype=np.float32) * sepia,
        )
    if temperature != 0.0:
        then(np.eye(3, dtype=np.float32), np.array([0.12, 0.02, -0.12], dtype=np.float32) * temperature)
    if contrast != 1.0:
        then(np.eye(3, dtype=np.float32) * contrast, np.full(3, 0.5 * (1.0 - contrast), dtype=np.float32))
    if brightness != 0.0:
        then(np.eye(3, dtype=np.float32), np.full(3, brightness, dtype=np.float32))
    return m.astype(np.float32), b.astype(np.float32)


def adjust_colors(
    a: Float,
    brightness: float = 0.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    temperature: float = 0.0,
    sepia: float = 0.0,
) -> Float:
    """Réglages sur RGBA prémultiplié : appliqués à la couleur non prémultipliée, alpha inchangé."""
    m, b = color_matrix(brightness, contrast, saturation, temperature, sepia)
    alpha = a[..., 3:4]
    opaque = bool(np.min(alpha) >= 1.0)
    if opaque:  # cas courant d'une image de scène : pas de division
        rgb = a[..., :3] @ m + b
        np.clip(rgb, 0.0, 1.0, out=rgb)
        return np.concatenate([rgb, alpha], axis=-1)
    rgb = np.divide(a[..., :3], alpha, out=np.zeros_like(a[..., :3]), where=alpha > 1e-6)
    rgb = rgb @ m + b
    np.clip(rgb, 0.0, 1.0, out=rgb)
    rgb *= alpha
    return np.concatenate([rgb, alpha], axis=-1)


def tinted_alpha(alpha: Float, color: QColor, strength: float) -> Float:
    """Calque d'une seule couleur dont l'opacité suit ``alpha`` (ombre, lueur), prémultiplié."""
    a = np.clip(alpha * strength * color.alphaF(), 0.0, 1.0)
    rgb = np.array([color.redF(), color.greenF(), color.blueF()], dtype=np.float32)
    return np.concatenate([a[..., None] * rgb, a[..., None]], axis=-1).astype(np.float32)


# --- effets d'objet -------------------------------------------------------------------------------------
def effect_margin(fx: dict[str, Any]) -> float:
    """Débord des effets autour de l'objet, en unités de l'objet (avant mise à l'échelle)."""
    glow = 3.0 * float(fx["fx_glow"]) if float(fx["fx_glow_strength"]) > 0 else 0.0
    shadow = 0.0
    if float(fx["fx_shadow"]) > 0:
        shadow = 3.0 * float(fx["fx_shadow_blur"]) + max(
            abs(float(fx["fx_shadow_dx"])), abs(float(fx["fx_shadow_dy"]))
        )
    return max(3.0 * float(fx["fx_blur"]), glow, shadow) + 2.0


def device_scale(t: QTransform) -> float:
    """Facteur d'échelle moyen d'une transformation (rayons des effets en pixels de l'image produite)."""
    return math.sqrt(abs(t.m11() * t.m22() - t.m12() * t.m21())) or 1.0


CHALK_TILE = 256  # côté du motif de grain de craie, répété sur toute l'image


@lru_cache(maxsize=1)
def _chalk_texture() -> Float:
    """Grain du tableau, valeurs 0..1 : bruit fin mêlé d'amas plus larges, raccord sans couture
    (flou circulaire). Graine fixe : le même texte a le même grain à chaque export."""
    rng = np.random.default_rng(1729)
    n = CHALK_TILE
    fine = rng.random((n, n), dtype=np.float32)
    coarse = rng.random((n, n), dtype=np.float32)
    for r, axis in ((3, 0), (3, 1), (1, 0)):
        acc = np.zeros_like(coarse)
        for k in range(-r, r + 1):
            acc += np.roll(coarse, k, axis=axis)
        coarse = acc / np.float32(2 * r + 1)
    lo, hi = float(np.min(coarse)), float(np.max(coarse))
    coarse = (coarse - lo) / np.float32(max(1e-6, hi - lo))
    tex = np.asarray(0.55 * fine + 0.45 * coarse, dtype=np.float32)
    tex.setflags(write=False)
    return tex


def chalk_mask(h: int, w: int, x0: int, y0: int, amount: float) -> Float:
    """Facteur d'opacité (h, w) du grain de craie. Le motif est fixé à l'image (pas à l'objet) : comme
    sur un vrai tableau, c'est la surface qui retient plus ou moins la poudre."""
    tex = _chalk_texture()
    n = CHALK_TILE
    ys = (np.arange(h) + y0) % n
    xs = (np.arange(w) + x0) % n
    t = tex[ys[:, None], xs[None, :]]
    cut = 0.42 * amount  # sous ce seuil, la craie n'a pas accroché
    factor = np.clip((t - cut) / 0.3, 0.0, 1.0) * (1.0 - 0.25 * amount) + 0.25 * amount * t
    return np.asarray(factor, dtype=np.float32)


def apply_object_effects(
    layer: Float, style: dict[str, Any], scale: float, origin: tuple[int, int] = (0, 0)
) -> list[tuple[Float, float, float]]:
    """Calques à superposer, du fond vers l'avant : (image, décalage x, décalage y) en pixels.
    ``origin`` : position du calque dans l'image (ancre le grain de craie)."""
    fx = effect_values(style)
    out: list[tuple[Float, float, float]] = []
    if float(fx["fx_chalk"]) > 0:
        h, w = layer.shape[:2]
        layer = layer * chalk_mask(h, w, origin[0], origin[1], float(fx["fx_chalk"]))[..., None]
    alpha = layer[..., 3]
    if float(fx["fx_shadow"]) > 0:
        blurred = gaussian_blur(alpha[..., None], float(fx["fx_shadow_blur"]) * scale / 2.0)[..., 0]
        shadow = tinted_alpha(blurred, QColor(str(fx["fx_shadow_color"])), float(fx["fx_shadow"]))
        out.append((shadow, float(fx["fx_shadow_dx"]) * scale, float(fx["fx_shadow_dy"]) * scale))
    if float(fx["fx_glow"]) > 0 and float(fx["fx_glow_strength"]) > 0:
        blurred = gaussian_blur(alpha[..., None], float(fx["fx_glow"]) * scale / 2.0)[..., 0]
        out.append(
            (tinted_alpha(blurred, QColor(str(fx["fx_glow_color"])), float(fx["fx_glow_strength"])), 0.0, 0.0)
        )
    body = layer
    if (
        abs(float(fx["fx_brightness"])) > 1e-6
        or abs(float(fx["fx_contrast"]) - 1.0) > 1e-6
        or abs(float(fx["fx_saturation"]) - 1.0) > 1e-6
    ):
        body = adjust_colors(
            body, float(fx["fx_brightness"]), float(fx["fx_contrast"]), float(fx["fx_saturation"])
        )
    if float(fx["fx_blur"]) > 0:
        body = gaussian_blur(body, float(fx["fx_blur"]) * scale / 2.0)
    out.append((body, 0.0, 0.0))
    return out


def paint_with_effects(painter: QPainter, local_rect: QRectF, style: dict[str, Any], draw: Any) -> bool:
    """Dessine l'objet (``draw(painter)``, repère de l'objet) dans un calque, applique ses effets et
    compose le résultat sur ``painter``. Retourne False si le calque serait trop grand (dessin direct)."""
    fx = effect_values(style)
    t = painter.worldTransform()
    scale = device_scale(t)
    m = effect_margin(fx)
    device = t.mapRect(local_rect.adjusted(-m, -m, m, m))
    window = QRectF(painter.viewport()) if painter.device() is not None else device
    window = window.adjusted(-m * scale, -m * scale, m * scale, m * scale)
    device = device.intersected(window)
    if device.isEmpty():
        return True
    x0, y0 = math.floor(device.left()), math.floor(device.top())
    w, h = math.ceil(device.right()) - x0, math.ceil(device.bottom()) - y0
    if w < 1 or h < 1 or w * h > MAX_EFFECT_PIXELS:
        return False
    layer_img = QImage(w, h, QImage.Format.Format_RGBA8888_Premultiplied)
    layer_img.fill(0)
    lp = QPainter(layer_img)
    try:
        lp.setRenderHints(painter.renderHints())
        lp.setWorldTransform(t * QTransform.fromTranslate(-x0, -y0))
        draw(lp)
    finally:
        lp.end()
    layers = apply_object_effects(image_to_array(layer_img), style, scale, (x0, y0))
    painter.save()
    painter.resetTransform()
    for arr, dx, dy in layers:
        painter.drawImage(QPointF(x0 + dx, y0 + dy), array_to_image(arr))
    painter.restore()
    return True


# --- filtres de scène -----------------------------------------------------------------------------------
@lru_cache(maxsize=8)
def _vignette_map(w: int, h: int, strength: float) -> Float:
    """Assombrissement radial : 1 au centre, 1 − ``strength`` aux coins (courbe douce)."""
    xx = (np.arange(w, dtype=np.float32) - (w - 1) / 2.0) / (w / 2.0)
    yy = (np.arange(h, dtype=np.float32) - (h - 1) / 2.0) / (h / 2.0)
    d = np.sqrt(xx[None, :] ** 2 + yy[:, None] ** 2) / math.sqrt(2.0)  # 0 au centre, 1 aux coins
    shade = 1.0 - strength * np.clip((d - 0.35) / 0.65, 0.0, 1.0) ** 1.6
    shade.setflags(write=False)
    return shade.astype(np.float32)


GRAIN_FIELDS = 8  # champs de bruit précalculés par taille d'image, choisis selon l'image (reproductible)


@lru_cache(maxsize=4)
def _grain_fields(w: int, h: int) -> tuple[Float, ...]:
    rng = np.random.default_rng(20261022)
    fields = tuple(rng.standard_normal(size=(h, w), dtype=np.float32) for _ in range(GRAIN_FIELDS))
    for f in fields:
        f.setflags(write=False)
    return fields


def apply_scene_post(img: QImage, post: dict[str, Any], seed_key: str, frame: int) -> QImage:
    """Étalonnage, vignettage et grain sur l'image entière (calcul canal par canal, sur des plans
    contigus) ; le grain dépend de la scène et du numéro d'image : deux exports sont identiques."""
    v = post_values(post)
    src = img.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
    w, h = src.width(), src.height()
    buf = np.frombuffer(src.constBits(), dtype=np.uint8, count=src.bytesPerLine() * h)
    u8 = buf.reshape(h, src.bytesPerLine())[:, : w * 4].reshape(h, w, 4)
    planes = u8.transpose(2, 0, 1).astype(np.float32, order="C")  # (4, h, w) vraiment contigu
    planes *= 1.0 / 255.0
    alpha = planes[3]
    opaque = bool(np.min(alpha) >= 1.0)
    if not opaque:
        np.divide(planes[:3], alpha, out=planes[:3], where=alpha > 1e-6)
    m, b = color_matrix(v["brightness"], v["contrast"], v["saturation"], v["temperature"], v["sepia"])
    if not (np.allclose(m, np.eye(3)) and not b.any()):
        r, g, bl = planes[0].copy(), planes[1].copy(), planes[2].copy()
        for c in range(3):
            out = planes[c]
            np.multiply(r, m[0, c], out=out)
            out += g * m[1, c]
            out += bl * m[2, c]
            out += b[c]
    if v["vignette"] > 0:
        planes[:3] *= _vignette_map(w, h, round(v["vignette"], 4))
    if v["grain"] > 0:
        fields = _grain_fields(w, h)
        noise = fields[zlib.crc32(f"{seed_key}:{frame}".encode()) % GRAIN_FIELDS]
        planes[:3] += noise * (0.08 * v["grain"])
    rgb = planes[:3]
    np.maximum(rgb, 0.0, out=rgb)  # np.clip est sensiblement plus lent
    np.minimum(rgb, 1.0, out=rgb)
    if not opaque:
        planes[:3] *= alpha
    planes *= 255.0
    planes += 0.5
    data = np.ascontiguousarray(planes.astype(np.uint8).transpose(1, 2, 0))
    return QImage(data.data, w, h, w * 4, QImage.Format.Format_RGBA8888_Premultiplied).copy()

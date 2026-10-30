"""Lumière et ondes : couleur d'un corps noir, couleur d'une longueur d'onde, effet Doppler (ADR-0009).

Références :
- fonctions colorimétriques CIE 1931 (observateur 2°), ajustement analytique de Wyman, Sloan et
  Shirley, « Simple Analytic Approximations to the CIE XYZ Color Matching Functions », JCGT 2(2), 2013 ;
- loi de Planck ; matrice XYZ → sRGB linéaire (IEC 61966-2-1, blanc D65) ;
- longueur d'onde → couleur : approximation par morceaux de Dan Bruton (1996), usuelle en visualisation ;
- B−V → température effective : Ballesteros, EPL 97 (2012) 34008 ;
- effet Doppler classique (source mobile, milieu immobile) et relativiste longitudinal.
"""

from __future__ import annotations

import math
from functools import lru_cache

H = 6.62607015e-34  # J·s (SI exact)
C = 299_792_458.0  # m/s (SI exact)
KB = 1.380649e-23  # J/K (SI exact)

VISIBLE_NM = (380.0, 780.0)


def _g(x: float, mu: float, s1: float, s2: float) -> float:
    s = s1 if x < mu else s2
    return math.exp(-0.5 * ((x - mu) / s) ** 2)


def cie_xyz(wavelength_nm: float) -> tuple[float, float, float]:
    """x̄, ȳ, z̄ (CIE 1931) — ajustement multi-lobes de Wyman et al. (2013)."""
    w = wavelength_nm
    x = 1.056 * _g(w, 599.8, 37.9, 31.0) + 0.362 * _g(w, 442.0, 16.0, 26.7) - 0.065 * _g(w, 501.1, 20.4, 26.2)
    y = 0.821 * _g(w, 568.8, 46.9, 40.5) + 0.286 * _g(w, 530.9, 16.3, 31.1)
    z = 1.217 * _g(w, 437.0, 11.8, 36.0) + 0.681 * _g(w, 459.0, 26.0, 13.8)
    return x, y, z


def _xyz_to_linear_srgb(x: float, y: float, z: float) -> tuple[float, float, float]:
    r = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    g = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    b = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z
    return r, g, b


def _encode(v: float) -> float:
    v = max(0.0, min(1.0, v))
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(_encode(c) * 255):02X}" for c in rgb)


def planck(wavelength_nm: float, temperature_k: float) -> float:
    """Luminance spectrale B_λ(T) en W·sr⁻¹·m⁻³."""
    lam = wavelength_nm * 1e-9
    a = H * C / (lam * KB * temperature_k)
    if a > 700:  # exp déborde : rayonnement négligeable
        return 0.0
    return 2 * H * C**2 / lam**5 / math.expm1(a)


@lru_cache(maxsize=512)
def blackbody_rgb(temperature_k: float) -> tuple[float, float, float]:
    """Couleur (sRGB linéaire, composante maximale ramenée à 1) d'un corps noir à ``temperature_k``."""
    t = max(500.0, min(100_000.0, float(temperature_k)))
    x = y = z = 0.0
    for w in range(380, 781, 5):
        p = planck(w, t)
        cx, cy, cz = cie_xyz(w)
        x, y, z = x + p * cx, y + p * cy, z + p * cz
    r, g, b = _xyz_to_linear_srgb(x, y, z)
    lo = min(r, g, b)
    if lo < 0:  # hors gamut (très chaud ou très froid) : désaturer vers le blanc
        r, g, b = r - lo, g - lo, b - lo
    m = max(r, g, b) or 1.0
    return r / m, g / m, b / m


def blackbody_hex(temperature_k: float) -> str:
    return _hex(blackbody_rgb(round(float(temperature_k), -1)))


def wavelength_rgb(wavelength_nm: float) -> tuple[float, float, float]:
    """Couleur affichable (sRGB encodé, 0..1) d'une lumière monochromatique — Bruton (1996) ;
    hors du visible : noir."""
    w = float(wavelength_nm)
    lo, hi = VISIBLE_NM
    if not lo <= w <= hi:
        return 0.0, 0.0, 0.0
    if w < 440:
        r, g, b = (440 - w) / 60, 0.0, 1.0
    elif w < 490:
        r, g, b = 0.0, (w - 440) / 50, 1.0
    elif w < 510:
        r, g, b = 0.0, 1.0, (510 - w) / 20
    elif w < 580:
        r, g, b = (w - 510) / 70, 1.0, 0.0
    elif w < 645:
        r, g, b = 1.0, (645 - w) / 65, 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    # sensibilité de l'œil : les extrémités du spectre s'assombrissent
    k = 0.3 + 0.7 * (w - 380) / 40 if w < 420 else (0.3 + 0.7 * (780 - w) / 80 if w > 700 else 1.0)
    return tuple((c * k) ** 0.8 if c > 0 else 0.0 for c in (r, g, b))  # type: ignore[return-value]


def wavelength_hex(wavelength_nm: float) -> str:
    return "#" + "".join(f"{round(c * 255):02X}" for c in wavelength_rgb(wavelength_nm))


def bv_to_temperature(b_v: float) -> float:
    """Indice de couleur B−V → température effective (K), formule de Ballesteros (2012)."""
    return 4600.0 * (1.0 / (0.92 * b_v + 1.7) + 1.0 / (0.92 * b_v + 0.62))


def doppler_classical(
    f_source: float, wave_speed: float, source_speed: float, angle_deg: float = 0.0
) -> float:
    """Fréquence perçue par un observateur immobile ; la source s'approche à ``source_speed`` sous l'angle
    ``angle_deg`` (0 = droit vers l'observateur). ``ValueError`` si la source va au moins aussi vite que
    l'onde vers l'observateur (onde de choc)."""
    approach = source_speed * math.cos(math.radians(angle_deg))
    if approach >= wave_speed:
        raise ValueError("la source rattrape ses propres fronts d'onde : onde de choc, pas de fréquence")
    return f_source * wave_speed / (wave_speed - approach)


def doppler_relativistic(f_source: float, beta: float) -> float:
    """Doppler longitudinal relativiste ; ``beta`` = v/c > 0 quand la source s'éloigne."""
    if not -1.0 < beta < 1.0:
        raise ValueError("|v| < c requis")
    return f_source * math.sqrt((1 - beta) / (1 + beta))


def mach_angle_deg(wave_speed: float, source_speed: float) -> float | None:
    """Demi-angle du cône de Mach, ``None`` en régime subsonique."""
    if source_speed <= wave_speed:
        return None
    return math.degrees(math.asin(wave_speed / source_speed))

"""Fonctions d'interpolation sur u ∈ [0, 1] (ADR-0002 §4)."""

from __future__ import annotations

from collections.abc import Callable


def step(u: float) -> float:
    return 0.0 if u < 1.0 else 1.0


def linear(u: float) -> float:
    return u


def ease_in(u: float) -> float:
    return u * u * u


def ease_out(u: float) -> float:
    v = 1.0 - u
    return 1.0 - v * v * v


def ease_in_out(u: float) -> float:
    if u < 0.5:
        return 4.0 * u * u * u
    v = -2.0 * u + 2.0
    return 1.0 - (v * v * v) / 2.0


def cubic_bezier(x1: float, y1: float, x2: float, y2: float, u: float) -> float:
    """Courbe de Bézier cubique (0,0)-(x1,y1)-(x2,y2)-(1,1), comme ``cubic-bezier()`` en CSS.

    ``u`` est le temps normalisé (abscisse) : on résout x(t) = u par Newton puis dichotomie, et on
    retourne y(t). x1 et x2 sont bornés à [0, 1] pour que x(t) reste monotone (une valeur par instant) ;
    y1 et y2 sont libres (dépassement, effet de rebond).
    """
    x1 = min(1.0, max(0.0, x1))
    x2 = min(1.0, max(0.0, x2))
    if u <= 0.0:
        return 0.0
    if u >= 1.0:
        return 1.0

    def bx(t: float) -> float:
        return ((1 - 3 * x2 + 3 * x1) * t + (3 * x2 - 6 * x1)) * t * t + 3 * x1 * t

    def by(t: float) -> float:
        return ((1 - 3 * y2 + 3 * y1) * t + (3 * y2 - 6 * y1)) * t * t + 3 * y1 * t

    t = u
    for _ in range(8):
        err = bx(t) - u
        if abs(err) < 1e-7:
            return by(t)
        d = (3 * (1 - 3 * x2 + 3 * x1) * t + 2 * (3 * x2 - 6 * x1)) * t + 3 * x1
        if abs(d) < 1e-6:
            break
        t -= err / d
    lo, hi = 0.0, 1.0
    t = u
    for _ in range(60):
        x = bx(t)
        if abs(x - u) < 1e-7:
            break
        if x < u:
            lo = t
        else:
            hi = t
        t = (lo + hi) / 2
    return by(t)


EASING_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "step": step,
    "linear": linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
}


# Libellés français (inspecteur, menus de la timeline, aide) — même ordre que ``model.EASINGS``.
EASING_LABELS: dict[str, str] = {
    "step": "Palier (saut net)",
    "linear": "Linéaire",
    "ease_in": "Accélération",
    "ease_out": "Décélération",
    "ease_in_out": "Douce (accélère puis ralentit)",
    "bezier": "Courbe personnalisée…",
}


def apply_easing(name: str, u: float, bezier: list[float] | None = None) -> float:
    u = 0.0 if u < 0.0 else 1.0 if u > 1.0 else u
    if name == "bezier":
        from antares_studio.domain.model import DEFAULT_BEZIER

        x1, y1, x2, y2 = bezier if bezier is not None and len(bezier) == 4 else DEFAULT_BEZIER
        return cubic_bezier(x1, y1, x2, y2, u)
    try:
        return EASING_FUNCTIONS[name](u)
    except KeyError:
        raise ValueError(f"interpolation inconnue : {name!r}") from None

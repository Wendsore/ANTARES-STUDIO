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


EASING_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "step": step,
    "linear": linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
}


def apply_easing(name: str, u: float) -> float:
    u = 0.0 if u < 0.0 else 1.0 if u > 1.0 else u
    try:
        return EASING_FUNCTIONS[name](u)
    except KeyError:
        raise ValueError(f"interpolation inconnue : {name!r}") from None

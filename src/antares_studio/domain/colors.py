"""Couleurs sRGB sous forme ``#RRGGBB`` ou ``#RRGGBBAA`` et conversion RGBA."""

from __future__ import annotations

import re

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

RGBA = tuple[float, float, float, float]


def is_color(value: object) -> bool:
    return isinstance(value, str) and bool(_HEX_RE.match(value))


def parse_color(value: str) -> RGBA:
    """``#RRGGBB[AA]`` -> composantes dans [0, 1]."""
    if not is_color(value):
        raise ValueError(f"couleur invalide : {value!r} (attendu #RRGGBB ou #RRGGBBAA)")
    h = value[1:]
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    a = int(h[6:8], 16) if len(h) == 8 else 255
    return (r / 255.0, g / 255.0, b / 255.0, a / 255.0)


def format_color(rgba: RGBA) -> str:
    """Composantes [0, 1] -> ``#RRGGBB`` (alpha omis si opaque)."""
    r, g, b, a = (max(0.0, min(1.0, c)) for c in rgba)
    out = f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"
    if round(a * 255) != 255:
        out += f"{round(a * 255):02X}"
    return out


def mix_color(c0: str, c1: str, u: float) -> str:
    a, b = parse_color(c0), parse_color(c1)
    return format_color(tuple(x + (y - x) * u for x, y in zip(a, b, strict=True)))  # type: ignore[arg-type]

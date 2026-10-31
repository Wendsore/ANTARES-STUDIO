"""Personnage en style réaliste : illustration vectorielle sans contour, proportions d'adulte (ADR-0010).

Même catalogue que les chibis (émotions, poses, tenues, coiffures…) et même repère 400 × 560, mais un
dessin d'illustration : volumes rendus par des dégradés et des tons d'ombre et de lumière (lumière
venant d'en haut à gauche), visage anatomique (yeux en amande, nez large, lèvres pleines), pas de
signes de bande dessinée. Les émotions passent par les sourcils, les paupières et la bouche ; seules
les larmes et la sueur, qui existent réellement, sont dessinées.

La tête est dessinée dans un repère local de 200 × 250 puis réduite par ``HEAD_TF``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from antares_studio.domain.characters import EMOTION_BY_ID, EMOTIONS, Emotion
from antares_studio.rendering.chibi import H, Look, W, _d, _el, _f, _look, _mix

HEAD_TF = "translate(164,10) scale(0.36)"  # tête locale 200 × 250 → du sommet (y 8) au menton (y 96)
EYE_L, EYE_R, EYE_Y = 66.0, 134.0, 122.0
MOUTH_Y = 200.0
LIP_DARK = "#3B1A14"
SCLERA = "#ECE4D8"
IRIS = "#2A140B"

_GAZE = {
    "face": (0.0, 0.0),
    "gauche": (-4.5, 0.0),
    "droite": (4.5, 0.0),
    "haut": (0.0, -3.5),
    "bas": (0.0, 3.0),
}


# --- outils ----------------------------------------------------------------------------------------
def _g(transform: str, content: str) -> str:
    return f'<g transform="{transform}">{content}</g>'


def _fill(d: str, color: str, opacity: float = 1.0) -> str:
    return _el("path", d=d, fill=color, opacity=opacity)


def _line(d: str, color: str, width: float, opacity: float = 1.0) -> str:
    return _el(
        "path",
        d=d,
        fill="none",
        stroke=color,
        stroke_width=width,
        stroke_linecap="round",
        stroke_linejoin="round",
        opacity=opacity,
    )


def _tones(base: str) -> tuple[str, str, str]:
    """Ombre profonde, ombre, lumière d'une couleur de base."""
    return _mix(base, "#000000", 0.38), _mix(base, "#000000", 0.2), _mix(base, "#FFFFFF", 0.14)


def _defs(look: Look) -> str:
    deep, shade, light = _tones(look.skin)
    return (
        "<defs>"
        f'<radialGradient id="peau" gradientUnits="userSpaceOnUse" cx="76" cy="96" r="170">'
        f'<stop offset="0" stop-color="{light}"/><stop offset="0.55" stop-color="{look.skin}"/>'
        f'<stop offset="1" stop-color="{shade}"/></radialGradient>'
        f'<linearGradient id="cou" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{deep}"/><stop offset="0.6" stop-color="{shade}"/></linearGradient>'
        '<linearGradient id="volume" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0.12"/>'
        '<stop offset="0.42" stop-color="#FFFFFF" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000000" stop-opacity="0.32"/></linearGradient>'
        '<linearGradient id="chute" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#000000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000000" stop-opacity="0.25"/></linearGradient>'
        "</defs>"
    )


# --- tête ------------------------------------------------------------------------------------------
FACE = (
    "M100,10 C146,10 176,40 178,92 C180,112 178,128 174,146 C168,178 150,212 126,232 "
    "C114,242 86,242 74,232 C50,212 32,178 26,146 C22,128 20,112 22,92 C24,40 54,10 100,10 Z"
)


def _ears(look: Look) -> str:
    deep, shade, _light = _tones(look.skin)
    out = []
    for sx in (1, -1):
        x = 100 + sx * 76
        d = _d(
            "M",
            x - sx * 2,
            116,
            "C",
            x + sx * 10,
            106,
            x + sx * 16,
            124,
            x + sx * 12,
            146,
            "C",
            x + sx * 9,
            160,
            x + sx * 1,
            162,
            x - sx * 3,
            156,
            "Z",
        )
        out.append(_fill(d, shade))
        out.append(
            _line(
                _d("M", x + sx * 2, 122, "C", x + sx * 10, 120, x + sx * 10, 140, x + sx * 4, 148),
                deep,
                2.4,
                0.6,
            )
        )
    return "".join(out)


def _skull_base(look: Look) -> str:
    return _ears(look) + _fill(FACE, "url(#peau)")


def _skull_shading(look: Look) -> str:
    deep, shade, light = _tones(look.skin)
    return "".join(
        [
            # ombre de la mâchoire et des joues, côté opposé à la lumière
            _fill("M174,146 C168,178 150,212 126,232 C140,206 152,180 158,150 Z", shade, 0.7),
            _fill("M28,150 C34,180 50,210 72,230 C62,206 52,184 46,158 Z", shade, 0.35),
            # orbites et cernes, sous le front
            _fill(
                _d("M", 40, 112, "C", 52, 100, 82, 100, 92, 114, "C", 80, 108, 54, 108, 40, 116, "Z"),
                deep,
                0.35,
            ),
            _fill(
                _d("M", 160, 112, "C", 148, 100, 118, 100, 108, 114, "C", 120, 108, 146, 108, 160, 116, "Z"),
                deep,
                0.35,
            ),
            # pommettes éclairées
            _fill("M44,150 C52,140 72,140 80,150 C70,156 54,158 44,150 Z", light, 0.35),
            _fill("M120,150 C128,140 148,140 156,150 C146,156 130,158 120,150 Z", light, 0.22),
        ]
    )


def _nose(look: Look) -> str:
    deep, shade, light = _tones(look.skin)
    return "".join(
        [
            # arête : lumière à gauche, ombre à droite
            _fill("M96,122 C94,140 90,152 86,162 C94,158 98,150 100,124 Z", light, 0.45),
            _fill("M104,122 C108,142 114,154 116,164 C108,160 104,148 102,124 Z", shade, 0.6),
            # ailes larges et narines
            _fill(
                "M74,170 C70,160 80,150 90,156 C96,166 104,166 110,156 C120,150 130,160 126,170 "
                "C122,180 110,182 100,180 C90,182 78,180 74,170 Z",
                shade,
                0.85,
            ),
            _fill("M80,168 C80,162 88,160 92,166 C90,172 84,174 80,168 Z", deep),
            _fill("M120,168 C120,162 112,160 108,166 C110,172 116,174 120,168 Z", deep),
            _fill("M92,152 C96,146 104,146 108,152 C104,158 96,158 92,152 Z", light, 0.5),
        ]
    )


def _eye(cx: float, open_: float, emo: Emotion, side: int, gaze: tuple[float, float], look: Look) -> str:
    """Œil en amande ; ``open_`` de 0 (fermé) à 1.2 (écarquillé) ; ``side`` -1 gauche, 1 droite."""
    deep, shade, _light = _tones(look.skin)
    hw, cy = 17.0, EYE_Y
    inner, outer = cx - side * hw, cx + side * hw
    if open_ <= 0.05:  # paupière fermée : un trait courbe et les cils
        smile = emo.eyes in ("happy", "closed")
        bend = -5 if smile else 3
        return _line(_d("M", inner, cy, "Q", cx, cy + bend, outer, cy - 1), IRIS, 3.4)
    top = cy - 10 * open_
    bottom = cy + 6 + (2 if open_ > 1 else 0)
    if emo.eyes == "happy":  # joues qui remontent : bas de l'œil relevé
        bottom = cy + 2
    almond = _d(
        "M",
        inner,
        cy + 1,
        "C",
        inner + side * 6,
        top,
        outer - side * 8,
        top - 1,
        outer,
        cy - 1,
        "C",
        outer - side * 6,
        bottom,
        inner + side * 6,
        bottom,
        inner,
        cy + 1,
        "Z",
    )
    gx, gy = gaze
    if emo.eyes == "look_up":
        gy -= 4
    elif emo.eyes == "look_side":
        gx -= 5
    ix, iy = cx + gx, cy + 1 + gy
    box = _d("M", cx - 26, cy - 20, "L", cx + 26, cy - 20, "L", cx + 26, cy + 14, "L", cx - 26, cy + 14, "Z")
    out = [
        _fill(almond, SCLERA),
        _el("circle", cx=ix, cy=iy, r=8.2, fill=IRIS),
        _el("circle", cx=ix, cy=iy, r=8.2, fill="none", stroke="#140904", stroke_width=1.2),
        _el("circle", cx=ix, cy=iy, r=3.6, fill="#0B0503"),
        _el("circle", cx=ix - 2.6, cy=iy - 3, r=2.0, fill="#FFFFFF", opacity=0.9),
        # paupières : la peau recouvre tout ce qui dépasse de l'amande
        _el("path", d=box + " " + almond, fill="url(#peau)", fill_rule="evenodd"),
        # ombre portée de la paupière supérieure sur le globe
        _fill(
            _d(
                "M",
                inner,
                cy + 1,
                "C",
                inner + side * 6,
                top,
                outer - side * 8,
                top - 1,
                outer,
                cy - 1,
                "C",
                outer - side * 8,
                top + 4,
                inner + side * 6,
                top + 5,
                inner,
                cy + 1,
                "Z",
            ),
            deep,
            0.4,
        ),
        # cils et ligne de paupière supérieure
        _line(
            _d(
                "M",
                inner,
                cy + 1,
                "C",
                inner + side * 6,
                top,
                outer - side * 8,
                top - 1,
                outer + side * 2,
                cy - 2,
            ),
            "#120904",
            3.2,
        ),
        # pli de la paupière
        _line(
            _d(
                "M",
                inner + side * 3,
                top - 4,
                "C",
                cx - side * 2,
                top - 9,
                outer - side * 4,
                top - 8,
                outer + side * 1,
                cy - 6,
            ),
            deep,
            2,
            0.7,
        ),
        _line(
            _d("M", inner + side * 4, bottom - 1, "Q", cx, bottom + 2, outer - side * 3, cy + 2),
            shade,
            1.6,
            0.8,
        ),
    ]
    return "".join(out)


def _eyes(emo: Emotion, gaze: str, look: Look) -> str:
    g = _GAZE.get(gaze, (0.0, 0.0))
    base = {
        "wide": 1.18,
        "star": 1.08,
        "happy": 0.62,
        "angry": 0.72,
        "sad": 0.78,
        "doubt": 0.85,
        "closed": 0.0,
    }.get(emo.eyes, 1.0)
    base *= 1 - 0.55 * emo.lid
    left, right = base, base
    if emo.eyes == "wink":
        right = 0.0
    elif emo.eyes == "doubt":
        left = base * 0.6
    return _eye(EYE_L, left, emo, -1, g, look) + _eye(EYE_R, right, emo, 1, g, look)


def _brow(side: int, h: float, tilt: float, look: Look) -> str:
    """Sourcil épais, plus large à l'intérieur ; ``h`` > 0 levé, ``tilt`` > 0 intérieur abaissé."""
    hair = _mix(look.hair, "#000000", 0.2)
    cx = EYE_L if side < 0 else EYE_R
    y = EYE_Y - 24 - h * 1.4
    inner_x, outer_x = cx - side * 22, cx + side * 22
    yi, yo = y + tilt * 1.3, y - tilt * 0.4
    d = _d(
        "M",
        inner_x,
        yi + 4,
        "C",
        inner_x + side * 10,
        yi - 3,
        outer_x - side * 14,
        yo - 7,
        outer_x,
        yo + 2,
        "C",
        outer_x - side * 14,
        yo - 2,
        inner_x + side * 10,
        yi + 3,
        inner_x,
        yi + 9,
        "Z",
    )
    return _fill(d, hair)


def _brows(emo: Emotion, look: Look) -> str:
    h, t = emo.brows
    hr, tr = emo.brow_right or emo.brows
    return _brow(-1, h, t, look) + _brow(1, hr, tr, look)


# bouche : (coin gauche dy, coin droit dy, demi-largeur, ouverture, dents haut, dents bas, langue)
_MOUTHS: dict[str, tuple[float, float, float, float, bool, bool, bool]] = {
    "soft": (-1, -1, 27, 0, False, False, False),
    "talk": (0, 0, 26, 9, True, False, False),
    "smile": (-7, -7, 29, 0, False, False, False),
    "big_smile": (-10, -10, 31, 13, True, False, False),
    "laugh": (-11, -11, 32, 26, True, False, True),
    "smirk": (1, -9, 27, 0, False, False, False),
    "o": (2, 2, 15, 18, False, False, False),
    "wavy_open": (4, 4, 30, 11, False, True, False),
    "doubt": (3, -3, 24, 0, False, False, False),
    "pout": (3, 3, 21, 0, False, False, False),
    "wavy": (3, 1, 25, 0, False, False, False),
    "flat": (2, 2, 27, 0, False, False, False),
    "grit": (5, 5, 31, 11, True, True, False),
    "shout": (6, 6, 28, 30, True, True, True),
    "frown": (8, 8, 27, 0, False, False, False),
    "frown_small": (5, 5, 26, 0, False, False, False),
    "disgust": (4, -3, 26, 6, True, False, False),
}


def _mouth(kind: str, look: Look) -> str:
    dl, dr, hw, op, up_teeth, low_teeth, tongue = _MOUTHS.get(kind, _MOUTHS["soft"])
    hw, op = hw * 1.08, op * 1.45
    y = MOUTH_Y
    lx, rx, ly, ry = 100 - hw, 100 + hw, y + dl, y + dr
    cy = y + (dl + dr) * -0.12  # milieu de la commissure : plus bas quand les coins montent
    upper_lip = _mix(look.skin, LIP_DARK, 0.55)
    lower_lip = _mix(look.skin, LIP_DARK, 0.35)
    deep, shade, light = _tones(look.skin)
    out = [
        # ombre sous la lèvre inférieure (menton)
        _fill(
            _d(
                "M",
                lx + 10,
                y + 16 + op,
                "Q",
                100,
                y + 28 + op,
                rx - 10,
                y + 16 + op,
                "Q",
                100,
                y + 22 + op,
                lx + 10,
                y + 16 + op,
                "Z",
            ),
            deep,
            0.35,
        ),
    ]
    top_in = cy - op * 0.15
    bot_in = cy + op * 0.85
    # lèvre supérieure : arc de Cupidon
    upper = _d(
        "M",
        lx,
        ly,
        "C",
        lx + 10,
        cy - 8,
        86,
        cy - 11,
        93,
        cy - 10,
        "Q",
        100,
        cy - 6,
        107,
        cy - 10,
        "C",
        114,
        cy - 11,
        rx - 10,
        cy - 8,
        rx,
        ry,
        "Q",
        100,
        top_in - 2 if op else top_in + 2,
        lx,
        ly,
        "Z",
    )
    lip_bottom = bot_in + 4 if op else bot_in - 1
    lower = _d(
        "M", lx, ly, "Q", 100, lip_bottom, rx, ry, "C", rx - 8, bot_in + 14, lx + 8, bot_in + 14, lx, ly, "Z"
    )
    if op > 0:
        opening = _d("M", lx + 2, ly, "Q", 100, top_in - 2, rx - 2, ry, "Q", 100, bot_in + 4, lx + 2, ly, "Z")
        out.append(_fill(opening, "#2A0C0A"))
        a, b = top_in - 2, bot_in + 4  # points de contrôle haut et bas de l'ouverture
        if tongue:
            out.append(
                _fill(
                    _d(
                        "M",
                        lx + 8,
                        ly + 2,
                        "Q",
                        100,
                        b - op * 0.7,
                        rx - 8,
                        ry + 2,
                        "Q",
                        100,
                        b,
                        lx + 8,
                        ly + 2,
                        "Z",
                    ),
                    "#A8463F",
                )
            )
        if up_teeth:
            t = min(13.0, (b - a) * 0.5)
            out.append(
                _fill(
                    _d("M", lx + 4, ly, "Q", 100, a, rx - 4, ry, "Q", 100, a + t, lx + 4, ly, "Z"), "#EFEAE2"
                )
            )
        if low_teeth:
            t = min(11.0, (b - a) * 0.4)
            out.append(
                _fill(
                    _d("M", lx + 5, ly, "Q", 100, b, rx - 5, ry, "Q", 100, b - t, lx + 5, ly, "Z"), "#DDD6CB"
                )
            )
    out += [
        _fill(lower, lower_lip),
        _fill(
            _d(
                "M",
                88,
                bot_in + 4,
                "Q",
                100,
                bot_in + 8,
                112,
                bot_in + 4,
                "Q",
                100,
                bot_in + 2,
                88,
                bot_in + 4,
                "Z",
            ),
            light,
            0.55,
        ),
        _fill(upper, upper_lip),
        "" if op else _line(_d("M", lx, ly, "Q", 100, top_in + 2, rx, ry), "#22100C", 1.8, 0.9),
        # commissures
        _line(_d("M", lx - 2, ly - 1, "q", -3, 1, -4, 4), shade, 1.6, 0.8),
        _line(_d("M", rx + 2, ry - 1, "q", 3, 1, 4, 4), shade, 1.6, 0.8),
    ]
    if dl < -5:  # sillons nasogéniens creusés par le sourire
        out.append(_line(_d("M", 70, 168, "Q", 60, 186, lx - 2, ly + 8), shade, 2.4, 0.7))
        out.append(_line(_d("M", 130, 168, "Q", 140, 186, rx + 2, ry + 8), shade, 2.4, 0.7))
    return "".join(out)


def _face_extras(emo: Emotion, look: Look) -> str:
    out = []
    if "tears" in emo.extras or "laugh_tears" in emo.extras:
        for x in (EYE_L + 4, EYE_R - 4):
            out.append(
                _fill(
                    _d(
                        "M",
                        x,
                        132,
                        "C",
                        x - 3,
                        146,
                        x - 2,
                        160,
                        x,
                        164,
                        "C",
                        x + 3,
                        160,
                        x + 3,
                        146,
                        x,
                        132,
                        "Z",
                    ),
                    "#BFD8E8",
                    0.75,
                )
            )
    if "sweat" in emo.extras:
        out.append(_fill("M168,70 C162,82 160,90 166,94 C172,96 176,90 172,80 Z", "#D6E6F0", 0.7))
    if "red" in emo.extras:  # afflux de sang, discret sur peau foncée
        out.append(_fill(FACE, "#8A1E14", 0.14))
    if any(e in emo.extras for e in ("blush", "blush_strong")):
        a = 0.22 if "blush_strong" in emo.extras else 0.14
        for x in (56, 144):
            out.append(_el("ellipse", cx=x, cy=158, rx=18, ry=9, fill="#A33A2A", opacity=a))
    return "".join(out)


# --- cheveux, barbe, lunettes, couvre-chefs (repère de la tête) -------------------------------------
HAIR_CAP = (
    "M20,112 C12,52 50,-6 100,-6 C150,-6 188,52 180,112 L172,110 C170,84 162,62 146,52 "
    "C128,44 112,44 100,46 C88,44 72,44 54,52 C38,62 30,84 28,110 Z"
)


def _in_cap(x: float, y: float) -> bool:
    if ((x - 100) / 74) ** 2 + ((y - 58) / 58) ** 2 > 1:
        return False
    return y < 40 + ((x - 100) / 70) ** 2 * 56


def _coils(
    color: str,
    seed: int,
    region: Any = _in_cap,
    box: tuple[float, float, float, float] = (20, -8, 180, 112),
    step: float = 7.0,
    opacity: float = 0.3,
) -> str:
    """Texture de cheveux crépus : petites boucles réparties sans régularité visible."""
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    parts = []
    y = y0
    while y < y1:
        x = x0 + rng.random() * step
        while x < x1:
            px, py = x + rng.uniform(-2, 2), y + rng.uniform(-2, 2)
            if region(px, py):
                r = rng.uniform(1.2, 2.2)
                parts.append(_d("M", px - r, py, "a", r, r, 0, 1, 1, r * 2, 0))
            x += step
        y += step * 0.8
    return _line(" ".join(parts), color, 1.1, opacity) if parts else ""


def _hair_back(look: Look, hair: str) -> str:
    c = look.hair
    hi = _mix(c, "#FFFFFF", 0.12)
    if hair == "afro":
        mass = (
            "M100,-28 C172,-28 210,24 208,92 C206,136 192,160 176,168 "
            "L24,168 C8,160 -6,136 -8,92 C-10,24 28,-28 100,-28 Z"
        )
        return _fill(mass, c) + _coils(
            hi,
            3,
            lambda x, y: ((x - 100) / 106) ** 2 + ((y - 70) / 96) ** 2 < 1,
            (-10, -28, 210, 168),
            8,
            0.45,
        )
    if hair in ("locks", "nattes"):
        rng = random.Random(7 if hair == "locks" else 9)
        out = []
        n = 11 if hair == "locks" else 15
        for i in range(n):
            t = i / (n - 1)
            x = 26 + 148 * t
            length = 300 if hair == "nattes" else 230
            end = 120 + length * (0.75 + 0.25 * math.sin(t * math.pi))
            sway = rng.uniform(-8, 8)
            w = 14 if hair == "locks" else 9
            out.append(
                _line(
                    _d(
                        "M",
                        x,
                        60,
                        "C",
                        x - 6 + sway,
                        120,
                        x + (x - 100) * 0.3,
                        end * 0.8,
                        x + (x - 100) * 0.35 + sway,
                        end,
                    ),
                    c,
                    w,
                )
            )
            if hair == "nattes":  # mailles des tresses
                for k in range(8):
                    yy = 140 + k * (end - 150) / 8
                    xx = x + (x - 100) * 0.3 * (yy - 60) / (end - 60)
                    out.append(_line(_d("M", xx - 4, yy, "l", 8, 6), hi, 1.4, 0.7))
            else:
                out.append(_line(_d("M", x + 2, 140, "L", x + (x - 100) * 0.3 + 2, end - 20), hi, 2, 0.35))
        return "".join(out)
    return ""


def _hair_front(look: Look, hair: str) -> str:
    c = look.hair
    hi = _mix(c, "#FFFFFF", 0.14)
    if hair == "rase":  # repousse : une ombre qui suit le crâne, sous la lisière
        stubble = (
            "M24,100 C24,40 58,10 100,10 C142,10 176,40 176,100 C170,74 150,52 100,48 C50,52 30,74 24,100 Z"
        )
        return _fill(stubble, c, 0.4)
    out = [_fill(HAIR_CAP, c), _coils(hi, 1)]
    if hair == "tresses":  # tresses collées : sillons de l'avant vers l'arrière
        out = [_fill(HAIR_CAP, c)]
        for i in range(7):  # sillons de la lisière vers le sommet du crâne
            x = 40 + i * 20
            y = 48 + ((x - 100) / 60) ** 2 * 18
            top_x = 100 + (x - 100) * 0.55
            out.append(_line(_d("M", x, y, "Q", x + (x - 100) * 0.08, 22, top_x, 2), hi, 5, 0.45))
            out.append(
                _line(
                    _d("M", x + 10, y, "Q", x + 10 + (x - 90) * 0.08, 22, top_x + 5, 2),
                    _mix(c, "#000000", 0.45),
                    2,
                    0.8,
                )
            )
    elif hair == "macarons":
        for cx in (36, 164):
            out.append(_el("circle", cx=cx, cy=10, r=34, fill=c))
            out.append(
                _coils(
                    hi,
                    cx,
                    lambda x, y, cx=cx: (x - cx) ** 2 + (y - 10) ** 2 < 32**2,
                    (cx - 34, -24, cx + 34, 44),
                    7,
                    0.4,
                )
            )
    elif hair == "afro":
        out = [_fill(HAIR_CAP, c)]
    # lisière : légère ombre portée sur le front
    out.append(
        _line(
            "M30,104 C34,74 52,56 74,50 C88,46 112,46 126,50 C148,56 166,74 170,104",
            _mix(c, "#000000", 0.3),
            4,
            0.35,
        )
    )
    return "".join(out)


def _beard(look: Look, beard: str) -> str:
    if beard == "aucune":
        return ""
    c = _mix(look.hair, "#FFFFFF", 0.04)
    hi = _mix(look.hair, "#FFFFFF", 0.16)
    moustache = (
        "M66,194 C70,180 90,176 100,182 C110,176 130,180 134,194 "
        "C124,188 112,188 100,190 C88,188 76,188 66,194 Z"
    )
    out = []
    if beard == "courte":
        full = (
            "M26,116 L34,116 C36,148 48,168 64,178 C66,196 72,216 100,218 C128,216 134,196 136,178 "
            "C152,168 164,148 166,116 L174,116 C176,150 166,190 140,222 C128,240 112,246 100,246 "
            "C88,246 72,240 60,222 C34,190 24,150 26,116 Z"
        )
        out.append(_fill(full, c, 0.92))
        out.append(
            _coils(
                hi,
                11,
                lambda x, y: (
                    ((x - 100) / 66) ** 2 + ((y - 140) / 96) ** 2 < 1
                    and y > 160
                    and (x < 66 or x > 134 or y > 222)
                ),
                (28, 120, 172, 244),
                6,
                0.25,
            )
        )
    elif beard == "bouc":
        out.append(
            _fill("M78,214 C80,232 90,244 100,244 C110,244 120,232 122,214 C112,222 88,222 78,214 Z", c)
        )
    out.append(_fill(moustache, c))
    return "".join(out)


def _glasses(glasses: str) -> str:
    if glasses == "aucune":
        return ""
    out = []
    if glasses == "protection":
        shield = (
            "M26,98 C60,90 140,90 174,98 C178,118 172,140 150,144 C130,146 116,138 100,138 "
            "C84,138 70,146 50,144 C28,140 22,118 26,98 Z"
        )
        out += [
            _fill(shield, "#BFD6E6", 0.3),
            _el("path", d=shield, fill="none", stroke="#E9EEF2", stroke_width=3, opacity=0.9),
            _line("M34,104 C70,98 130,98 166,104", "#FFFFFF", 2, 0.6),
        ]
        return "".join(out)
    color, width = {"rondes": ("#2B2421", 4.5), "rectangles": ("#1E1A18", 6.0), "fines": ("#A9ADB4", 2.6)}[
        glasses
    ]
    for cx in (EYE_L, EYE_R):
        if glasses == "rondes":
            out.append(
                _el(
                    "circle",
                    cx=cx,
                    cy=EYE_Y + 2,
                    r=25,
                    fill="#DCEBF5",
                    fill_opacity=0.12,
                    stroke=color,
                    stroke_width=width,
                )
            )
        else:
            h = 32 if glasses == "rectangles" else 30
            out.append(
                _el(
                    "rect",
                    x=cx - 28,
                    y=EYE_Y - 14,
                    width=56,
                    height=h,
                    rx=9 if glasses == "fines" else 6,
                    fill="#DCEBF5",
                    fill_opacity=0.12,
                    stroke=color,
                    stroke_width=width,
                )
            )
        out.append(_line(_d("M", cx - 16, EYE_Y - 8, "l", 8, -3), "#FFFFFF", 2, 0.35))  # reflet
    out.append(
        _line(_d("M", EYE_L + 26, EYE_Y - 4, "Q", 100, EYE_Y - 12, EYE_R - 26, EYE_Y - 4), color, width * 0.8)
    )
    out.append(_line(_d("M", EYE_L - 28, EYE_Y - 6, "L", 22, EYE_Y - 10), color, width * 0.8))
    out.append(_line(_d("M", EYE_R + 28, EYE_Y - 6, "L", 178, EYE_Y - 10), color, width * 0.8))
    return "".join(out)


def _hat(look: Look, hat: str) -> str:
    c = look.hat
    deep, shade, light = _tones(c)
    if hat == "casquette":
        return "".join(
            [
                _fill("M18,72 C16,10 60,-14 100,-14 C140,-14 184,10 182,72 C150,60 50,60 18,72 Z", c),
                _fill(
                    "M18,72 C16,10 60,-14 100,-14 C140,-14 184,10 182,72 C150,60 50,60 18,72 Z",
                    "url(#volume)",
                ),
                _fill("M24,70 C60,56 140,56 176,70 C170,84 130,82 100,80 C70,82 30,84 24,70 Z", shade),
                _el("circle", cx=100, cy=-12, r=5, fill=deep),
            ]
        )
    if hat == "kufi":
        return "".join(
            [
                _fill("M24,60 C24,10 60,-8 100,-8 C140,-8 176,10 176,60 C140,54 60,54 24,60 Z", c),
                _fill(
                    "M24,60 C24,10 60,-8 100,-8 C140,-8 176,10 176,60 C140,54 60,54 24,60 Z", "url(#volume)"
                ),
                _line("M30,40 C70,30 130,30 170,40", look.accent, 4, 0.8),
                _line("M34,24 C70,14 130,14 166,24", look.accent, 3, 0.6),
            ]
        )
    if hat == "casque":
        dome = "M14,78 C10,10 56,-26 100,-26 C144,-26 190,10 186,78 Z"
        return "".join(
            [
                _fill(dome, c),
                _fill(dome, "url(#volume)"),
                _fill("M92,-25 C96,10 96,50 94,78 L106,78 C104,50 104,10 108,-25 Z", light, 0.8),
                _fill(
                    "M0,76 C40,66 160,66 200,76 C204,86 196,92 186,90 C140,84 60,84 14,90 C4,92 -4,86 0,76 Z",
                    shade,
                ),
            ]
        )
    return ""


# --- corps (repère global 400 × 560) ---------------------------------------------------------------
@dataclass(frozen=True)
class Limb:
    points: tuple[tuple[float, float], ...]  # épaule, coude, poignet
    hand: str = "relax"  # relax | open | fist | point
    wave: bool = False


def _mirror(limb: Limb) -> Limb:
    return Limb(tuple((W - x, y) for x, y in limb.points), limb.hand, limb.wave)


_REST = Limb(((148, 140), (140, 222), (138, 298)))
_HIPS = Limb(((148, 140), (104, 206), (156, 264)), "fist")
_SHRUG = Limb(((146, 134), (114, 212), (82, 184)), "open")
_RAISED = Limb(((148, 138), (110, 84), (98, 32)), "fist")
POSES: dict[str, tuple[Limb, Limb]] = {
    "repos": (_REST, _mirror(_REST)),
    "explique": (_REST, Limb(((252, 140), (272, 222), (318, 186)), "open")),
    "montre": (_REST, Limb(((252, 140), (310, 178), (370, 160)), "point")),
    "index": (_REST, Limb(((252, 140), (284, 216), (292, 142)), "point")),
    "salut": (_REST, Limb(((252, 140), (312, 172), (330, 98)), "open", wave=True)),
    "menton": (
        Limb(((148, 140), (150, 224), (240, 214)), "fist"),
        Limb(((252, 140), (252, 210), (212, 120)), "fist"),
    ),
    "bras_croises": (
        Limb(((148, 140), (142, 230), (244, 218)), "fist"),
        Limb(((252, 140), (260, 210), (158, 200)), "fist"),
    ),
    "hanches": (_HIPS, _mirror(_HIPS)),
    "haussement": (_SHRUG, _mirror(_SHRUG)),
    "victoire": (_RAISED, _mirror(_RAISED)),
}


def _capsule(p0: tuple[float, float], p1: tuple[float, float], w0: float, w1: float) -> str:
    """Segment de membre effilé aux bouts arrondis : les articulations restent rondes à tout angle."""
    (x0, y0), (x1, y1) = p0, p1
    ln = math.hypot(x1 - x0, y1 - y0) or 1.0
    nx, ny = -(y1 - y0) / ln, (x1 - x0) / ln
    r0, r1 = w0 / 2, w1 / 2
    return _d(
        "M",
        x0 + nx * r0,
        y0 + ny * r0,
        "L",
        x1 + nx * r1,
        y1 + ny * r1,
        "A",
        r1,
        r1,
        0,
        0,
        0,
        x1 - nx * r1,
        y1 - ny * r1,
        "L",
        x0 - nx * r0,
        y0 - ny * r0,
        "A",
        r0,
        r0,
        0,
        0,
        0,
        x0 + nx * r0,
        y0 + ny * r0,
        "Z",
    )


def _part(points: tuple[tuple[float, float], ...], widths: tuple[float, ...], color: str) -> str:
    out = []
    for i in range(len(points) - 1):
        d = _capsule(points[i], points[i + 1], widths[i], widths[i + 1])
        out += [_fill(d, color), _fill(d, "url(#volume)")]
    return "".join(out)


def _hand(limb: Limb, look: Look) -> str:
    (x1, y1), (x2, y2) = limb.points[1], limb.points[2]
    angle = math.degrees(math.atan2(-(x2 - x1), y2 - y1))
    side = 1 if limb.points[0][0] < W / 2 else -1  # pouce du côté du corps
    deep, shade, light = _tones(look.skin)
    parts: list[str] = []
    thumb = _capsule((side * 7, 5), (side * 12, 16), 7.6, 6.2)
    if limb.hand in ("open", "relax"):
        tip = 39 if limb.hand == "open" else 33  # main détendue : doigts légèrement repliés
        hand = _d(
            "M",
            -9,
            0,
            "C",
            -10,
            8,
            -10.5,
            16,
            -10,
            22,
            "L",
            -9.5,
            tip - 5,
            "C",
            -9,
            tip - 1,
            -5,
            tip + 1,
            -2,
            tip + 0.5,
            "C",
            1,
            tip + 1.5,
            5,
            tip + 1,
            8,
            tip - 2,
            "L",
            10,
            22,
            "C",
            10.5,
            14,
            10,
            6,
            9,
            0,
            "Z",
        )
        parts += [_fill(thumb, look.skin), _fill(hand, look.skin), _fill(hand, "url(#volume)")]
        parts += [_line(_d("M", fx, 24, "L", fx * 1.05, tip - 1), shade, 1.1, 0.75) for fx in (-4.8, 0, 4.8)]
        parts.append(_line("M-8,21 C-3,23 3,23 8,21", shade, 1, 0.5))
        if limb.hand == "relax":
            parts.append(_line(_d("M", -9, tip - 6, "C", -3, tip - 3, 3, tip - 3, 9, tip - 7), deep, 1, 0.5))
    elif limb.hand == "point":  # poing fermé, index tendu
        fist = "M-10,0 C-12,10 -11,24 -2,27 C8,29 12,22 11,8 C11,3 9,0 8,0 Z"
        finger = _capsule((-3.5 * side, 20), (-3.5 * side, 42), 5.6, 5)
        parts += [
            _fill(finger, look.skin),
            _fill(fist, look.skin),
            _fill(fist, "url(#volume)"),
            _line("M-7,16 C-2,19 4,19 9,16", shade, 1.2, 0.7),
            _line("M-6,22 C-1,25 4,25 8,22", shade, 1.1, 0.6),
            _fill(thumb, look.skin),
            _line(_d("M", side * 9, 9, "L", side * 12, 17), shade, 1, 0.5),
        ]
    else:  # poing
        fist = "M-11,0 C-13,10 -12,24 -2,27 C8,29 13,22 12,8 C12,3 10,0 8,0 Z"
        parts += [
            _fill(fist, look.skin),
            _fill(fist, "url(#volume)"),
            _line("M-8,14 C-2,17 4,17 10,14", shade, 1.4, 0.7),
            _line("M-9,20 C-2,23 4,23 10,20", shade, 1.2, 0.6),
            _line(_d("M", side * 10, 6, "Q", side * 2, 12, -side * 4, 12), shade, 2.4, 0.8),
        ]
    return f'<g transform="translate({_f(x2)},{_f(y2)}) rotate({_f(angle)}) scale(1.25)">{"".join(parts)}</g>'


def _arm(limb: Limb, look: Look) -> str:
    (x0, y0), (x1, y1), (x2, y2) = limb.points
    skin = _part(limb.points, (24, 20, 16), look.skin)
    if look.sleeve_len == "short":
        mx, my = x0 + (x1 - x0) * 0.5, y0 + (y1 - y0) * 0.5
        sleeve = _part(((x0, y0), (mx, my)), (36, 32), look.sleeve)
    else:
        cx, cy = x1 + (x2 - x1) * 0.85, y1 + (y2 - y1) * 0.85
        sleeve = _part(((x0, y0), (x1, y1), (cx, cy)), (34, 30, 24), look.sleeve)
    out = [skin, sleeve, _hand(limb, look)]
    if limb.wave:  # main qui s'agite : léger flou de mouvement
        out.append(_line(_d("M", x2 + 26, y2 - 36, "q", 10, 12, 4, 26), "#FFFFFF", 2, 0.35))
    return "".join(out)


TORSO = (
    "M184,108 C168,116 152,120 140,126 C128,132 122,148 124,172 L134,238 C140,268 148,288 150,300 "
    "L250,300 C252,288 260,268 266,238 L276,172 C278,148 272,132 260,126 C248,120 232,116 216,108 Z"
)


def _legs(look: Look) -> str:
    c = look.pants
    deep, shade, _light = _tones(c)
    out = [_fill("M152,272 L248,272 L250,318 C230,330 170,330 150,318 Z", c)]
    for sx in (-1, 1):
        x = 200 + sx * 25
        pts = ((x, 300), (x + sx * 2, 420), (x + sx * 2, 528))
        out.append(_part(pts, (50, 34, 28), c))
        out.append(_line(_d("M", x + sx * 2, 330, "L", x + sx * 3, 520), deep, 1.4, 0.5))  # pli du pantalon
    out.append(_line("M200,300 L200,330", deep, 2, 0.6))
    for sx in (-1, 1):  # chaussures vues de face
        x = 200 + sx * 27
        shoe = _d(
            "M",
            x - 16,
            534,
            "C",
            x - 18,
            524,
            x + 18,
            524,
            x + 16,
            534,
            "C",
            x + 20,
            542,
            x + 18 + sx * 4,
            548,
            x + sx * 6,
            549,
            "C",
            x - 10,
            550,
            x - 22,
            546,
            x - 16,
            534,
            "Z",
        )
        out += [
            _fill(shoe, look.shoes),
            _fill(shoe, "url(#volume)"),
            _line(_d("M", x - 18, 546, "L", x + 18, 546), _mix(look.shoes, "#000000", 0.4), 2.4, 0.8),
        ]
    return "".join(out)


def _neck(look: Look) -> str:
    deep, shade, _light = _tones(look.skin)
    return _fill("M186,76 L214,76 L216,124 C206,132 194,132 184,124 Z", "url(#cou)") + _fill(
        "M184,96 C194,104 206,104 216,96 L216,108 C206,114 194,114 184,108 Z", deep, 0.5
    )


def _torso(look: Look, outfit: str) -> str:
    f, a = look.fill, look.accent
    fd, fs, fl = _tones(f)
    ad, as_, al = _tones(a)
    base = f
    if outfit in ("doudoune", "gilet_hv"):
        base = a  # le haut porté dessous
    if outfit == "veste_jean":
        base = f
    out = [_fill(TORSO, base), _fill(TORSO, "url(#volume)")]
    if outfit == "tshirt":
        out.append(_fill("M184,110 C192,122 208,122 216,110 C210,116 190,116 184,110 Z", fs))
    elif outfit == "polo":
        out += [
            _fill("M178,106 L200,128 L222,106 L230,120 L200,136 L170,120 Z", fl),
            _fill("M196,128 L204,128 L204,168 L196,168 Z", fs),
            _el("circle", cx=200, cy=144, r=2.2, fill="#EDEDED"),
            _el("circle", cx=200, cy=158, r=2.2, fill="#EDEDED"),
        ]
    elif outfit == "chemise":
        out += [
            _fill("M176,104 L200,132 L190,148 L168,118 Z", fl),
            _fill("M224,104 L200,132 L210,148 L232,118 Z", fl),
            _line("M200,132 L200,300", fs, 2.4),
        ]
        out += [_el("circle", cx=200, cy=y, r=2.4, fill=fl) for y in (160, 196, 232, 268)]
        out.append(_fill("M226,170 L250,170 L250,196 L226,196 Z", fs, 0.4))
    elif outfit == "blouse":
        coat = (
            "M184,108 C164,118 146,122 136,128 C124,136 120,150 122,174 L128,250 C130,300 132,340 134,372 "
            "L266,372 C268,340 270,300 272,250 L278,174 C280,150 276,136 264,128 C254,122 236,118 216,108 Z"
        )
        out = [
            _fill(TORSO, a),
            _fill(coat, f),
            _fill(coat, "url(#volume)"),
            _fill("M184,108 L200,170 L216,108 L208,104 L200,124 L192,104 Z", a),
            _fill("M176,106 L200,176 L184,200 L162,126 Z", fs),
            _fill("M224,106 L200,176 L216,200 L238,126 Z", fs),
            _line("M200,176 L200,372", fd, 2),
            _fill("M146,300 L180,300 L180,330 L146,330 Z", fs, 0.6),
            _fill("M220,300 L254,300 L254,330 L220,330 Z", fs, 0.6),
            _line("M226,170 L248,170", a, 3),
        ]
    elif outfit == "sweat":
        out += [
            _fill("M166,120 C172,96 228,96 234,120 C222,112 178,112 166,120 Z", fs),
            _line("M192,124 L190,176", al, 2.4),
            _line("M208,124 L210,176", al, 2.4),
            _fill("M162,236 L238,236 L246,282 L154,282 Z", fs, 0.7),
        ]
    elif outfit == "dashiki":
        out += [_fill("M178,108 L200,160 L222,108 L232,114 L200,176 L168,114 Z", a)]
        for k in range(6):
            yy = 116 + k * 9
            out.append(
                _line(_d("M", 176 + k * 3.6, yy, "L", 200, yy + 18, "L", 224 - k * 3.6, yy), ad, 1.6, 0.8)
            )
        out.append(_line("M134,288 L266,288", a, 6))
    elif outfit == "costume":
        out += [
            _fill("M184,108 L200,200 L216,108 Z", "#F1F1EE"),
            _fill("M196,118 L204,118 L208,132 L204,196 L200,206 L196,196 L192,132 Z", a),
            _fill("M180,106 L200,206 L178,236 L160,132 Z", fs),
            _fill("M220,106 L200,206 L222,236 L240,132 Z", fs),
            _line("M200,206 L200,300", fd, 2),
        ]
        out += [_el("circle", cx=206, cy=y, r=2.6, fill=fd) for y in (232, 262)]
    elif outfit == "maillot":
        out += [
            _fill("M180,108 L200,140 L220,108 L228,112 L200,150 L172,112 Z", a),
            _line("M134,170 L134,290", a, 5, 0.9),
            _line("M266,170 L266,290", a, 5, 0.9),
        ]
    elif outfit == "doudoune":
        vest = (
            "M174,112 C160,118 154,124 152,134 L156,240 C158,270 160,290 160,304 "
            "L240,304 C240,290 242,270 244,240 "
            "L248,134 C246,124 240,118 226,112 C216,122 184,122 174,112 Z"
        )
        out += [_fill(vest, f), _fill(vest, "url(#volume)")]
        for k in range(7):
            yy = 146 + k * 23
            out.append(
                _line(
                    _d("M", 156, yy, "Q", 178, yy + 4, 198, yy, "M", 202, yy, "Q", 222, yy + 4, 244, yy),
                    _mix(f, "#FFFFFF", 0.14),
                    1.6,
                    0.8,
                )
            )
        out += [
            _fill("M172,100 C184,108 216,108 228,100 L230,118 C216,126 184,126 170,118 Z", f),
            _line("M200,118 L200,304", "#8A8E95", 2),
            _line("M212,150 L206,176", _mix(f, "#FFFFFF", 0.2), 1.6),
        ]
    elif outfit == "gilet_hv":
        vest = (
            "M170,112 C158,118 150,126 150,138 L154,240 C156,272 158,292 158,306 "
            "L242,306 C242,292 244,272 246,240 "
            "L250,138 C250,126 242,118 230,112 L212,170 L188,170 Z"
        )
        band = "#E9EEF2"
        out += [
            _fill(vest, f),
            _fill(vest, "url(#volume)"),
            _line("M176,116 L178,306", band, 9),
            _line("M224,116 L222,306", band, 9),
            _line("M154,236 L246,236", band, 9),
            _line("M156,270 L244,270", band, 9),
            _line("M176,116 L178,306", "#9EA4AA", 1, 0.6),
            _line("M200,170 L200,306", fd, 2),
        ]
    elif outfit == "veste_jean":
        under = "M178,112 L222,112 L226,304 L174,304 Z"
        out += [
            _fill(under, a),
            _fill(under, "url(#volume)"),
            _fill("M168,110 C176,96 224,96 232,110 C220,104 180,104 168,110 Z", _mix(a, "#000000", 0.2)),
            _fill("M174,108 L156,128 L178,176 L186,118 Z", "#E8DFCF"),
            _fill("M226,108 L244,128 L222,176 L214,118 Z", "#E8DFCF"),
            _line("M180,176 L178,304", fd, 2.4),
            _line("M220,176 L222,304", fd, 2.4),
            _fill("M144,176 L172,176 L172,204 L146,204 Z", fs),
            _fill("M228,176 L256,176 L254,204 L228,204 Z", fs),
            _line("M136,262 L178,262", fd, 2, 0.8),
            _line("M222,262 L264,262", fd, 2, 0.8),
        ]
    out.append(_fill(TORSO, "url(#chute)"))
    return "".join(out)


def head_svg(params: dict[str, Any], look: Look, emo: Emotion) -> str:
    """Tête complète en repère local 200 × 250."""
    hair = str(params.get("hair", "court"))
    hat = str(params.get("hat", "aucun"))
    out = [
        _skull_base(look),
        _eyes(emo, str(params.get("gaze", "face")), look),
        _skull_shading(look),
        _nose(look),
        _beard(look, str(params.get("beard", "aucune"))),
        _mouth(emo.mouth, look),
        _brows(emo, look),
        _face_extras(emo, look),
    ]
    if hat != "casque" or hair in ("afro", "macarons"):
        out.append(_hair_front(look, hair))
    out += [_glasses(str(params.get("glasses", "aucune"))), _hat(look, hat)]
    return "".join(out)


def realiste_svg(params: dict[str, Any], style: dict[str, Any]) -> str:
    """SVG complet d'un personnage réaliste, identique pour des paramètres identiques."""
    look = _look(params, style)
    emo = EMOTION_BY_ID.get(str(params.get("emotion", "neutre")), EMOTIONS[0])
    outfit, hair = str(params.get("outfit", "tshirt")), str(params.get("hair", "court"))
    arms = POSES.get(str(params.get("pose", "repos")), POSES["repos"])
    inner = "".join(
        [
            _defs(look),
            _el("ellipse", cx=200, cy=548, rx=86, ry=8, fill="#000000", opacity=0.22),
            _g(HEAD_TF, _hair_back(look, hair)),
            _legs(look),
            _neck(look),
            _torso(look, outfit),
            _g(HEAD_TF, head_svg(params, look, emo)),
            *(_arm(limb, look) for limb in arms),
        ]
    )
    if bool(params.get("mirror", False)):
        inner = f'<g transform="translate({_f(W)},0) scale(-1,1)">{inner}</g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_f(W)} {_f(H)}" width="{_f(W)}" '
        f'height="{_f(H)}">{inner}</svg>'
    )

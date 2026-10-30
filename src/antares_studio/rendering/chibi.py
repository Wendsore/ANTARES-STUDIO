"""Personnages chibis en 2D : un dessin vectoriel composé par le code (ADR-0010).

Chaque image est un SVG assemblé à partir de pièces : silhouette, tenue, coiffure, barbe, accessoires,
yeux, sourcils et bouche de l'émotion, bras de la pose. Rien n'est téléchargé : les dessins sont
originaux et font partie du logiciel. L'émotion, la pose, la tenue et le regard sont des listes
de choix animables en palier : une image clé suffit pour changer le personnage pendant la présentation.

Le rendu passe par ``QSvgRenderer`` (vectoriel, donc net à toutes les tailles, en 4K comme dans
l'éditeur). Les moteurs de rendu sont gardés en cache par thread, car l'export tourne dans un thread
secondaire.
"""

from __future__ import annotations

import math
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgRenderer

from antares_studio.domain.characters import EMOTION_BY_ID, EMOTIONS, SKIN_HEX, Emotion
from antares_studio.domain.colors import parse_color

W, H = 400.0, 560.0  # repère du dessin
OUT = "#2A1A12"  # trait de contour
LW = 5.0


_GAZE = {
    "face": (0.0, 0.0),
    "gauche": (-6.0, 0.0),
    "droite": (6.0, 0.0),
    "haut": (0.0, -6.0),
    "bas": (0.0, 5.0),
}


# --- outils SVG ------------------------------------------------------------------------------------
def _rgb(color: str) -> tuple[int, int, int]:
    r, g, b, _a = parse_color(color)
    return round(r * 255), round(g * 255), round(b * 255)


def _mix(a: str, b: str, t: float) -> str:
    ca, cb = _rgb(a), _rgb(b)
    r, g, bl = (round(x + (y - x) * t) for x, y in zip(ca, cb, strict=True))
    return f"#{r:02X}{g:02X}{bl:02X}"


def _hex6(color: str) -> str:
    r, g, b = _rgb(color)
    return f"#{r:02X}{g:02X}{b:02X}"


def _f(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _d(*items: str | float) -> str:
    """Tracé SVG : les lettres de commande restent telles quelles, les nombres sont arrondis."""
    return " ".join(i if isinstance(i, str) else _f(i) for i in items)


def _el(tag: str, **attrs: str | float) -> str:
    """Élément SVG ; ``stroke_width`` devient ``stroke-width``."""
    body = " ".join(f'{k.replace("_", "-")}="{v if isinstance(v, str) else _f(v)}"' for k, v in attrs.items())
    return f"<{tag} {body}/>"


def _stroke(d: str, color: str, width: float, opacity: float = 1.0, cap: str = "round") -> str:
    return _el(
        "path",
        d=d,
        fill="none",
        stroke=color,
        stroke_width=width,
        stroke_linecap=cap,
        stroke_linejoin="round",
        opacity=opacity,
    )


def _shape(d: str, fill: str, width: float = LW) -> str:
    return _el("path", d=d, fill=fill, stroke=OUT, stroke_width=width, stroke_linejoin="round")


def _circle(cx: float, cy: float, r: float, fill: str, width: float = 4.5) -> str:
    return _el("circle", cx=cx, cy=cy, r=r, fill=fill, stroke=OUT, stroke_width=width)


def _blob(cx: float, cy: float, r: float, bumps: int, depth: float, squash: float = 1.0) -> str:
    """Contour bosselé (afro, macarons) : rayon modulé, assez de points pour paraître lisse."""
    pts = []
    n = bumps * 10
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r + depth * abs(math.cos(bumps * a / 2))
        pts.append(f"{_f(cx + rr * math.cos(a))},{_f(cy + rr * math.sin(a) * squash)}")
    return "M" + " L".join(pts) + " Z"


def _sparkle(x: float, y: float, r: float) -> str:
    """Étoile à quatre branches courbes (éclat, reflet d'émerveillement)."""
    k = r * 0.15
    return _d(
        "M", x, y - r, "Q", x + k, y - k, x + r, y, "Q", x + k, y + k, x, y + r,
        "Q", x - k, y + k, x - r, y, "Q", x - k, y - k, x, y - r, "Z",
    )  # fmt: skip


# --- silhouette et pose ----------------------------------------------------------------------------
HEAD = "M70,190 C70,95 135,52 200,52 C265,52 330,95 330,190 C330,262 280,305 200,305 C120,305 70,262 70,190 Z"
JAW_SHADE = (
    "M86,232 C100,282 150,300 200,300 C250,300 300,282 314,232 "
    "C296,270 250,288 200,288 C150,288 104,270 86,232 Z"
)
HAIR_CAP = (
    "M76,178 C70,88 136,40 200,40 C264,40 330,88 324,178 C312,140 296,118 268,110 "
    "C240,104 160,104 132,110 C104,118 88,140 76,178 Z"
)
VEST_HEM = " L262,452 C262,460 256,464 248,464 L152,464 C144,464 138,460 138,452 Z"  # bas des gilets
TORSO = (
    "M138,342 C138,322 162,314 200,314 C238,314 262,322 262,342 L268,452 "
    "C268,460 262,464 254,464 L146,464 C138,464 132,460 132,452 Z"
)


@dataclass(frozen=True)
class Arm:
    points: tuple[tuple[float, float], ...]  # épaule, coude, poignet
    hand: str = "fist"  # fist | open | point
    finger_deg: float = 0.0
    front: bool = True  # devant la tête (sinon derrière)
    wave: bool = False


def _mirror_arm(arm: Arm) -> Arm:
    return Arm(
        tuple((W - x, y) for x, y in arm.points), arm.hand, 180.0 - arm.finger_deg, arm.front, arm.wave
    )


_REST_L = Arm(((150, 340), (130, 396), (138, 446)))
_HIPS_L = Arm(((150, 340), (106, 392), (146, 440)))
_SHRUG_L = Arm(((148, 336), (100, 366), (74, 330)), "open", front=False)
_RAISED_L = Arm(((150, 338), (92, 312), (40, 236)), front=False)
_POSES: dict[str, tuple[Arm, Arm]] = {
    "repos": (_REST_L, _mirror_arm(_REST_L)),
    "explique": (_REST_L, Arm(((250, 340), (302, 376), (322, 318)), "open", front=False)),
    "montre": (_REST_L, Arm(((250, 340), (306, 352), (356, 334)), "point", -10, front=False)),
    "index": (_REST_L, Arm(((250, 340), (298, 356), (306, 286)), "point", -90, front=False)),
    "salut": (_REST_L, Arm(((250, 340), (308, 316), (332, 252)), "open", front=False, wave=True)),
    "menton": (Arm(((150, 340), (146, 400), (252, 404))), Arm(((250, 340), (284, 404), (236, 308)))),
    "bras_croises": (Arm(((150, 340), (138, 394), (234, 400))), Arm(((250, 340), (264, 388), (168, 392)))),
    "hanches": (_HIPS_L, _mirror_arm(_HIPS_L)),
    "haussement": (_SHRUG_L, _mirror_arm(_SHRUG_L)),
    "victoire": (_RAISED_L, _mirror_arm(_RAISED_L)),
}


@dataclass(frozen=True)
class Look:
    skin: str
    shade: str
    fill: str
    accent: str
    hair: str
    hat: str
    sleeve: str  # couleur des manches (le sweat sous une doudoune, par exemple)
    sleeve_len: str  # short | long
    pants: str
    shoes: str


def _look(params: dict[str, Any], style: dict[str, Any]) -> Look:
    skin = SKIN_HEX.get(str(params.get("skin", "fonce")), SKIN_HEX["fonce"])
    fill = _hex6(str(style.get("fill", "#E07A2E")))
    accent = _hex6(str(style.get("accent", "#2E5E8C")))
    hair = _hex6(str(style.get("hair_color", "#1B120C")))
    hat = _hex6(str(style.get("hat_color", "#F4F4F2")))
    outfit = str(params.get("outfit", "tshirt"))
    sleeve, sleeve_len, pants, shoes = fill, "long", "#34405A", "#2B2B2E"
    if outfit == "tshirt":
        sleeve_len, pants, shoes = "short", "#3A5A8F", "#F1F1EE"
    elif outfit == "chemise":
        pants, shoes = "#3D3A4B", "#5A3A22"
    elif outfit == "blouse":
        pants, shoes = "#2F3542", "#3A2A20"
    elif outfit == "sweat":
        pants, shoes = "#4A4F5A", "#F1F1EE"
    elif outfit == "dashiki":
        sleeve_len, pants, shoes = "short", _mix(fill, "#000000", 0.25), "#7A4A26"
    elif outfit == "costume":
        pants, shoes = fill, "#151515"
    elif outfit == "maillot":
        sleeve_len, pants, shoes = "short", accent, "#1E1E1E"
    elif outfit == "doudoune":  # gilet sans manches : les manches sont celles du sweat dessous
        sleeve, pants, shoes = accent, "#25324A", "#1C1C1E"
    elif outfit == "gilet_hv":
        sleeve, pants, shoes = accent, "#1E1E22", "#2A2A2A"
    elif outfit == "veste_jean":
        pants, shoes = "#C8A66B", "#3A2A20"
    elif outfit == "polo":
        sleeve_len, pants, shoes = "short", "#2A2A30", "#1C1C1E"
    shade = _mix(skin, "#000000", 0.22)
    return Look(skin, shade, fill, accent, hair, hat, sleeve, sleeve_len, pants, shoes)


def _arm_svg(arm: Arm, look: Look, k: float = 1.0) -> str:
    """Bras en deux segments ; ``k`` règle l'épaisseur (adulte : bras plus fins que le chibi)."""
    (x0, y0), (x1, y1), (x2, y2) = arm.points
    d = _d("M", x0, y0, "L", x1, y1, "L", x2, y2)
    out = [_stroke(d, OUT, 38 * k), _stroke(d, look.skin, 28 * k)]
    if look.sleeve_len == "long":  # la manche s'arrête un peu avant le poignet
        cx, cy = x1 + (x2 - x1) * 0.78, y1 + (y2 - y1) * 0.78
        out.append(_stroke(_d("M", x0, y0, "L", x1, y1, "L", cx, cy), look.sleeve, 28 * k))
    else:
        mx, my = x0 + (x1 - x0) * 0.55, y0 + (y1 - y0) * 0.55
        out.append(_stroke(_d("M", x0, y0, "L", mx, my), look.sleeve, 34 * k, cap="butt"))
    out.append(_hand(arm, look, k))
    if arm.wave:
        for k, rr in enumerate((30.0, 42.0)):
            dw = _d("M", x2 + rr * 0.6, y2 - rr * 0.8, "Q", x2 + rr, y2, x2 + rr * 0.6, y2 + rr * 0.6)
            out.append(_stroke(dw, OUT, 4 - k))
    return "".join(out)


def _hand(arm: Arm, look: Look, k: float = 1.0) -> str:
    x, y = arm.points[2]
    r = 16.5 * k
    if arm.hand == "point":  # index tendu : contour, paume, puis doigt fondu dans la paume
        a = math.radians(arm.finger_deg)
        tx, ty = x + 34 * k * math.cos(a), y + 34 * k * math.sin(a)
        bx, by = x + 8 * k * math.cos(a), y + 8 * k * math.sin(a)
        return (
            _stroke(_d("M", x, y, "L", tx, ty), OUT, 20 * k)
            + _circle(x, y, r, look.skin)
            + _stroke(_d("M", bx, by, "L", tx, ty), look.skin, 10.5 * k)
        )
    if arm.hand == "open":  # paume ouverte, doigts suggérés
        out = [
            _el("ellipse", cx=x, cy=y, rx=r * 1.09, ry=r * 1.18, fill=look.skin, stroke=OUT, stroke_width=4.5)
        ]
        for i in (-1, 0, 1):
            out.append(
                _stroke(_d("M", x + i * 7 * k, y - 14 * k, "L", x + i * 7 * k, y - 7 * k), look.shade, 2.6)
            )
        return "".join(out)
    return _circle(x, y, r, look.skin) + _stroke(
        _d("M", x - 7 * k, y - 2 * k, "Q", x, y + 3 * k, x + 7 * k, y - 2 * k), look.shade, 2.6
    )


# --- tenue -----------------------------------------------------------------------------------------
@dataclass(frozen=True)
class LegFrame:
    xs: tuple[float, float]  # bord gauche de chaque jambe
    top: float
    width: float
    height: float
    shoe_y: float
    shoe_w: float


CHIBI_LEGS = LegFrame((152.0, 206.0), 446.0, 42.0, 64.0, 518.0, 30.0)
ADULT_LEGS = LegFrame((142.0, 204.0), 396.0, 54.0, 138.0, 548.0, 33.0)


def _legs(look: Look, outfit: str, f: LegFrame = CHIBI_LEGS) -> str:
    if f is not CHIBI_LEGS:
        return _adult_legs(look, outfit, f)
    out = []
    for x in (152.0, 206.0):
        if outfit == "maillot":  # short, jambes nues, chaussettes
            out.append(
                _el(
                    "rect",
                    x=x,
                    y=448,
                    width=42,
                    height=62,
                    rx=12,
                    fill=look.skin,
                    stroke=OUT,
                    stroke_width=LW,
                )
            )
            out.append(
                _el(
                    "rect",
                    x=x,
                    y=482,
                    width=42,
                    height=26,
                    rx=6,
                    fill=look.fill,
                    stroke=OUT,
                    stroke_width=3.5,
                )
            )
            out.append(
                _el(
                    "rect",
                    x=x - 4,
                    y=446,
                    width=50,
                    height=22,
                    rx=6,
                    fill=look.pants,
                    stroke=OUT,
                    stroke_width=LW,
                )
            )
        else:
            out.append(
                _el(
                    "rect",
                    x=x,
                    y=446,
                    width=42,
                    height=64,
                    rx=12,
                    fill=look.pants,
                    stroke=OUT,
                    stroke_width=LW,
                )
            )
    for cx in (170.0, 230.0):
        out.append(
            _shape(_d("M", cx - 30, 518, "C", cx - 30, 498, cx + 30, 498, cx + 30, 518, "Z"), look.shoes)
        )
        out.append(_stroke(_d("M", cx - 28, 516, "L", cx + 28, 516), _mix(look.shoes, "#000000", 0.3), 3))
    return "".join(out)


def _adult_legs(look: Look, outfit: str, f: LegFrame) -> str:
    out = []
    shorts = outfit == "maillot"
    for x in f.xs:
        leg = look.skin if shorts else look.pants
        out.append(
            _el(
                "rect",
                x=x,
                y=f.top,
                width=f.width,
                height=f.height,
                rx=14,
                fill=leg,
                stroke=OUT,
                stroke_width=LW,
            )
        )
        if shorts:
            out.append(
                _el(
                    "rect",
                    x=x - 3,
                    y=f.top,
                    width=f.width + 6,
                    height=46,
                    rx=8,
                    fill=look.pants,
                    stroke=OUT,
                    stroke_width=LW,
                )
            )
            out.append(
                _el(
                    "rect",
                    x=x,
                    y=f.top + f.height - 48,
                    width=f.width,
                    height=40,
                    rx=6,
                    fill=look.fill,
                    stroke=OUT,
                    stroke_width=3.5,
                )
            )
        else:  # couture et pli du genou
            out.append(
                _stroke(
                    _d("M", x + f.width / 2, f.top + 10, "L", x + f.width / 2, f.top + f.height - 12),
                    _mix(look.pants, "#FFFFFF", 0.12),
                    2,
                )
            )
    for x in f.xs:
        cx, y = x + f.width / 2, f.shoe_y
        w = f.shoe_w
        out.append(
            _shape(_d("M", cx - w, y, "C", cx - w, y - 24, cx + w, y - 24, cx + w, y, "Z"), look.shoes)
        )
        out.append(
            _stroke(_d("M", cx - w + 2, y - 3, "L", cx + w - 2, y - 3), _mix(look.shoes, "#FFFFFF", 0.25), 3)
        )
    return "".join(out)


def _torso(look: Look, outfit: str) -> str:
    dark = _mix(look.fill, "#000000", 0.28)
    light = _mix(look.fill, "#FFFFFF", 0.35)
    out = [_shape(TORSO, look.fill)]
    if outfit == "tshirt":
        out.append(_stroke("M176,318 Q200,340 224,318", dark, 5))
    elif outfit == "chemise":
        out.append(_shape("M172,316 L200,346 L186,358 L166,326 Z", light, 4))
        out.append(_shape("M228,316 L200,346 L214,358 L234,326 Z", light, 4))
        out.append(_stroke("M200,348 L200,458", dark, 3))
        for y in (372.0, 400.0, 428.0):
            out.append(_el("circle", cx=200, cy=y, r=3.2, fill=dark))
        out.append(_shape("M146,372 L176,372 L176,398 L146,398 Z", "none", 3))
    elif outfit == "blouse":  # blouse ouverte sur un t-shirt de la couleur d'accent, stylos en poche
        out.append(_shape("M180,316 L200,392 L220,316 Z", look.accent, 4))
        out.append(_stroke("M180,318 L196,400 L190,460", "#B9C2CC", 4))
        out.append(_stroke("M220,318 L204,400 L210,460", "#B9C2CC", 4))
        out.append(_shape("M150,388 L180,388 L180,414 L150,414 Z", look.fill, 3.5))
        for k, col in enumerate(("#3D7DD8", "#D64545", "#2E9E5B")):
            out.append(_stroke(_d("M", 156 + k * 9, 388, "L", 156 + k * 9, 372), col, 5))
    elif outfit == "sweat":  # capuche rabattue, cordons, poche ventrale
        out.append(_shape("M138,330 C150,300 250,300 262,330 C240,346 160,346 138,330 Z", dark, 4.5))
        for x in (190.0, 210.0):
            out.append(_stroke(_d("M", x, 336, "L", x - 2, 380), "#F2F2F2", 3.5))
            out.append(_circle(x - 2, 382, 3.5, "#F2F2F2", 1.5))
        out.append(_shape("M164,410 L236,410 L248,452 L152,452 Z", look.fill, 4))
        out.append(_stroke("M134,450 L266,450", dark, 6))
    elif outfit == "dashiki":  # encolure en V brodée, bande en zigzag au bas
        out.append(_shape("M170,316 L200,370 L230,316 L218,316 L200,350 L182,316 Z", look.accent, 3.5))
        out.append(_stroke("M178,330 L186,344 L194,330 M206,330 L214,344 L222,330", look.accent, 2.5))
        hem = "M133,434 L267,434 L268,452 C268,460 262,464 254,464 L146,464 C138,464 132,460 132,452 Z"
        out.append(_shape(hem, look.accent, 4))
        zig = " ".join(f"L{_f(140 + i * 10)},{_f(449 if i % 2 else 441)}" for i in range(13))
        out.append(_stroke(f"M136,445 {zig}", look.fill, 3))
        for cx, cy in ((168.0, 392.0), (232.0, 392.0), (200.0, 410.0)):
            out.append(_el("circle", cx=cx, cy=cy, r=6, fill="none", stroke=look.accent, stroke_width=3))
    elif outfit == "costume":
        out.append(_shape("M178,316 L200,402 L222,316 Z", "#F5F5F2", 4))
        out.append(_shape("M193,322 L207,322 L210,334 L200,338 L190,334 Z", look.accent, 3))
        out.append(_shape("M196,336 L204,336 L210,388 L200,400 L190,388 Z", look.accent, 3))
        out.append(_stroke("M178,318 L166,352 L190,372", dark, 4))
        out.append(_stroke("M222,318 L234,352 L210,372", dark, 4))
        out.append(_el("circle", cx=203, cy=424, r=4, fill=dark))
        out.append(_stroke("M226,372 L248,372", dark, 3))
    elif outfit == "maillot":
        for x in (172.0, 200.0, 228.0):
            out.append(_el("rect", x=x - 6, y=330, width=12, height=128, fill=look.accent, opacity=0.9))
        out.append(_shape("M176,316 L200,342 L224,316 Z", look.accent, 4))
        out.append(
            '<text x="200" y="406" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" '
            f'font-size="40" fill="{look.fill}" stroke="{OUT}" stroke-width="2">10</text>'
        )
    elif outfit == "doudoune":  # gilet matelassé noir sur sweat à capuche
        out[0] = _shape(TORSO, look.accent)
        out.append(
            _shape(
                "M156,322 C168,298 232,298 244,322 C226,334 174,334 156,322 Z",
                _mix(look.accent, "#000000", 0.2),
                4,
            )
        )
        vest = "M146,332 L178,316 L200,334 L222,316 L254,332" + VEST_HEM
        out.append(_shape(vest, look.fill))
        quilt = _mix(look.fill, "#FFFFFF", 0.16)
        for y in (362.0, 386.0, 410.0, 434.0):
            out.append(_stroke(_d("M", 142, y, "L", 258, y), quilt, 2))
        out.append(_shape("M178,316 L180,300 L200,314 L220,300 L222,316 L200,334 Z", look.fill, 4))
        out.append(_stroke("M200,334 L200,462", "#4A4C52", 3))
        out.append(_stroke("M160,370 L170,404", "#4A4C52", 3))
    elif outfit == "gilet_hv":  # gilet orange à bandes réfléchissantes, sur maillot sombre
        out[0] = _shape(TORSO, look.accent)
        out.append(
            _shape(
                "M182,316 L200,330 L218,316 L214,312 L200,322 L186,312 Z",
                _mix(look.accent, "#FFFFFF", 0.1),
                3,
            )
        )
        vest = "M146,330 L180,318 L200,384 L220,318 L254,330" + VEST_HEM
        out.append(_shape(vest, look.fill))
        silver = "#DCE1E5"
        for y in (404.0, 432.0):
            out.append(
                _el("rect", x=139, y=y, width=122, height=11, fill=silver, stroke="#9AA3AB", stroke_width=1.5)
            )
        for x0, x1 in ((166.0, 186.0), (234.0, 214.0)):
            out.append(_stroke(_d("M", x0, 324, "L", x1, 400), silver, 10))
        out.append(_stroke("M200,386 L200,462", _mix(look.fill, "#000000", 0.3), 2.5))
    elif outfit == "veste_jean":  # veste en jean ouverte, doublure sherpa, sweat dessous
        out[0] = _shape(TORSO, look.accent)
        out.append(
            _shape(
                "M160,322 C170,300 230,300 240,322 C224,332 176,332 160,322 Z",
                _mix(look.accent, "#000000", 0.2),
                4,
            )
        )
        for x in (192.0, 208.0):
            out.append(_stroke(_d("M", x, 330, "L", x - 1, 372), _mix(look.accent, "#FFFFFF", 0.3), 3))
        out.append(_shape("M170,410 L230,410 L238,448 L162,448 Z", look.accent, 3.5))
        sherpa = "#EFE8DA"
        for side in (-1, 1):

            def X(x: float, side: int = side) -> float:
                return 200 + side * (x - 200)

            panel = _d(
                "M", X(138), 342, "C", X(138), 322, X(160), 316, X(176), 316,
                "L", X(184), 464, "L", X(146), 464, "C", X(138), 464, X(132), 460, X(132), 452, "Z",
            )  # fmt: skip
            out.append(_shape(panel, look.fill))
            out.append(_stroke(_d("M", X(178), 320, "L", X(185), 462), sherpa, 9))
            out.append(_shape(_d("M", X(150), 322, "L", X(178), 314, "L", X(186), 356, "Z"), sherpa, 3))
            out.append(
                _shape(
                    _d("M", X(146), 372, "L", X(170), 372, "L", X(170), 392, "L", X(146), 392, "Z"),
                    "none",
                    2.5,
                )
            )
            out.append(_el("circle", cx=X(158), cy=382, r=2.8, fill="#C9CED4"))
    elif outfit == "polo":
        out.append(_shape("M176,316 L200,334 L188,344 L170,322 Z", dark, 3.5))
        out.append(_shape("M224,316 L200,334 L212,344 L230,322 Z", dark, 3.5))
        out.append(_stroke("M200,334 L200,370", dark, 3))
        for y in (346.0, 360.0):
            out.append(_el("circle", cx=200, cy=y, r=2.8, fill=light))
    return "".join(out)


# --- coiffures, barbe, accessoires -----------------------------------------------------------------
def _hair_back(look: Look, hair: str) -> str:
    h = look.hair
    if hair == "afro":
        return _shape(_blob(200, 150, 168, 18, 9, 0.93), h)
    if hair == "macarons":
        return _shape(_blob(92, 74, 64, 12, 6), h) + _shape(_blob(308, 74, 64, 12, 6), h)
    out = []
    if hair == "locks":
        for x, y1 in ((66, 330), (88, 352), (312, 352), (334, 330), (52, 290), (348, 290)):
            d = _d("M", 200 + (x - 200) * 0.75, 120, "Q", x, 200, x, y1)
            out.append(_stroke(d, OUT, 30) + _stroke(d, h, 21))
    if hair == "nattes":  # perles dorées au bout des tresses
        for x, y1 in ((60, 400), (80, 420), (100, 410), (300, 410), (320, 420), (340, 400)):
            d = _d("M", 200 + (x - 200) * 0.6, 110, "Q", x, 210, x, y1)
            out.append(_stroke(d, OUT, 22) + _stroke(d, h, 14))
            out.append(_circle(x, y1 + 4, 7, "#E2B33C", 3))
    return "".join(out)


def _hair_front(look: Look, hair: str) -> str:
    h = look.hair
    light = _mix(h, "#FFFFFF", 0.16)
    if hair == "rase":
        return _el("path", d=HAIR_CAP, fill=h, opacity=0.32)
    out = [_shape(HAIR_CAP, h)]
    if hair in ("court", "afro", "macarons"):
        # boucles serrées : petits arcs répartis par le nombre d'or (image reproductible)
        for i in range(60):
            a = math.pi * (0.1 + 0.8 * ((i * 0.618) % 1.0))
            rr = 64 + 56 * ((i * 0.37) % 1.0)
            x, y = 200 - rr * math.cos(a), 168 - rr * math.sin(a)
            if y < 100 or (y < 160 and (x < 98 or x > 302)):
                out.append(_stroke(_d("M", x - 4, y, "Q", x, y - 4, x + 4, y), light, 2.4))
    if hair == "macarons":
        out.append(_stroke("M200,42 L200,104", light, 3))
    if hair == "tresses":
        for k in range(-3, 4):
            d = _d("M", 200 + k * 26, 106, "Q", 200 + k * 27, 74, 200 + k * 14, 54)
            out.append(_stroke(d, light, 3))
    if hair in ("locks", "nattes"):
        w = 26 if hair == "locks" else 18
        for x, y1 in ((122, 160), (150, 128), (250, 128), (278, 160)):
            d = _d("M", x + (200 - x) * 0.3, 56, "Q", x, 84, x, y1)
            out.append(_stroke(d, OUT, w + 8) + _stroke(d, h, w))
            if hair == "locks":
                out.append(_stroke(_d("M", x - 7, y1 - 10, "L", x + 7, y1 - 14), light, 2.5))
    return "".join(out)


def _beard(look: Look, beard: str) -> str:
    h = look.hair
    out = []
    if beard == "courte":
        d = (
            "M80,214 C88,292 142,314 200,314 C258,314 312,292 320,214 "
            "C304,256 270,292 200,294 C130,292 96,256 80,214 Z"
        )
        out.append(_shape(d, h, 4))
    if beard == "bouc":
        out.append(_shape("M178,284 C182,304 218,304 222,284 C210,290 190,290 178,284 Z", h, 4))
    if beard in ("courte", "bouc", "moustache"):
        d = "M176,253 C186,240 196,244 200,247 C204,244 214,240 224,253 C212,250 188,250 176,253 Z"
        out.append(_shape(d, h, 3))
    return "".join(out)


EYE_L, EYE_R = (148.0, 212.0), (252.0, 212.0)


def _accessories(look: Look, glasses: str, hat: str) -> str:
    out = []
    frame = "#26262A"
    glass: dict[str, str | float] = {
        "fill": "#BFE3FF",
        "fill_opacity": 0.16,
        "stroke": frame,
        "stroke_width": 5.0,
    }
    if glasses == "rondes":
        for cx, cy in (EYE_L, EYE_R):
            out.append(_el("circle", cx=cx, cy=cy, r=35, **glass))
        out.append(_stroke("M183,206 Q200,196 217,206", frame, 5))
        out.append(_stroke("M113,204 L76,196 M287,204 L324,196", frame, 5))
    elif glasses == "rectangles":
        for cx, cy in (EYE_L, EYE_R):
            out.append(_el("rect", x=cx - 36, y=cy - 26, width=72, height=54, rx=10, **glass))
        out.append(_stroke("M184,206 Q200,198 216,206", frame, 5))
        out.append(_stroke("M112,200 L76,194 M288,200 L324,194", frame, 5))
    elif glasses == "fines":  # monture métallique fine aux angles arrondis
        metal = "#9A9EA6"
        for cx, cy in (EYE_L, EYE_R):
            out.append(
                _el(
                    "rect",
                    x=cx - 36,
                    y=cy - 28,
                    width=72,
                    height=58,
                    rx=22,
                    fill="#BFE3FF",
                    fill_opacity=0.12,
                    stroke=metal,
                    stroke_width=3,
                )
            )
        out.append(_stroke("M184,204 Q200,196 216,204", metal, 3))
        out.append(_stroke("M112,200 L76,194 M288,200 L324,194", metal, 3))
    elif glasses == "protection":
        _goggles(out, 200, 212, 1.0)
    dark = _mix(look.hat, "#000000", 0.25)
    if hat == "casquette":
        out.append(_shape("M74,138 C74,58 140,30 200,30 C260,30 326,58 326,138 Z", look.hat))
        out.append(_shape("M66,138 Q200,112 334,138 Q338,152 326,156 Q200,138 74,156 Q62,152 66,138 Z", dark))
        out.append(_stroke("M200,32 L200,128", dark, 3))
        out.append(_circle(200, 32, 7, look.hat, 3.5))
    elif hat == "casque":  # casque de chantier : dôme, nervure, visière tout autour
        out.append(_shape("M76,140 C76,52 140,20 200,20 C260,20 324,52 324,140 Z", look.hat))
        rib = _mix(look.hat, "#000000", 0.12)
        out.append(_shape("M184,22 C186,60 188,100 188,138 L212,138 C212,100 214,60 216,22 Z", rib, 3))
        out.append(
            _shape("M58,140 Q200,116 342,140 Q346,154 334,158 Q200,140 66,158 Q54,154 58,140 Z", look.hat)
        )
    elif hat == "kufi":  # calot brodé de losanges
        out.append(_shape("M104,100 C112,58 288,58 296,100 C270,84 130,84 104,100 Z", look.hat))
        out.append(_shape("M104,100 C130,84 270,84 296,100 L300,116 C270,102 130,102 100,116 Z", look.hat))
        for k in range(7):
            x = 128 + k * 24
            out.append(
                _el(
                    "path",
                    d=_d("M", x, 96, "L", x + 8, 104, "L", x, 112, "L", x - 8, 104, "Z"),
                    fill=look.fill,
                )
            )
    return "".join(out)


def _goggles(out: list[str], cx: float, cy: float, k: float) -> None:
    """Lunettes de protection enveloppantes, transparentes, avec élastique."""
    d = _d(
        "M", cx - 80 * k, cy - 22 * k, "Q", cx, cy - 36 * k, cx + 80 * k, cy - 22 * k,
        "L", cx + 76 * k, cy + 24 * k, "Q", cx + 40 * k, cy + 38 * k, cx + 8 * k, cy + 22 * k,
        "L", cx - 8 * k, cy + 22 * k, "Q", cx - 40 * k, cy + 38 * k, cx - 76 * k, cy + 24 * k, "Z",
    )  # fmt: skip
    out.append(_el("path", d=d, fill="#D8ECFF", fill_opacity=0.3, stroke="#8E98A3", stroke_width=4 * k))
    out.append(
        _stroke(_d("M", cx - 62 * k, cy - 18 * k, "L", cx - 40 * k, cy - 22 * k), "#FFFFFF", 4 * k, 0.8)
    )
    out.append(_stroke(_d("M", cx - 80 * k, cy - 6 * k, "L", cx - 124 * k, cy - 14 * k), "#3A3F46", 6 * k))
    out.append(_stroke(_d("M", cx + 80 * k, cy - 6 * k, "L", cx + 124 * k, cy - 14 * k), "#3A3F46", 6 * k))


# --- visage ----------------------------------------------------------------------------------------
def _open_eye(cx: float, cy: float, gx: float, gy: float, wide: bool = False, star: bool = False) -> str:
    rw, rh = (26.0, 30.0) if wide else (24.0, 29.0)
    ir, irh, pr = (11.0, 14.0, 5.0) if wide else (17.0, 22.0, 9.0)
    ix, iy = cx + gx, cy + gy
    out = [
        _el("ellipse", cx=cx, cy=cy, rx=rw, ry=rh, fill="#FFFFFF", stroke=OUT, stroke_width=4),
        _el("ellipse", cx=ix, cy=iy + 2, rx=ir, ry=irh, fill="#4A2B17"),
        _el("ellipse", cx=ix, cy=iy + 4, rx=ir * 0.62, ry=irh * 0.6, fill="#7A4A26"),
        _el("ellipse", cx=ix, cy=iy + 2, rx=pr, ry=pr * 1.3, fill="#120A06"),
    ]
    if star:
        out.append(_el("path", d=_sparkle(ix, iy, 14), fill="#FFFFFF"))
    else:
        out.append(_el("circle", cx=ix - 6, cy=iy - 8, r=6.5, fill="#FFFFFF"))
        out.append(_el("circle", cx=ix + 7, cy=iy + 9, r=3, fill="#FFFFFF"))
    out.append(_stroke(_d("M", cx - rw - 2, cy - 6, "Q", cx, cy - rh - 9, cx + rw + 2, cy - 6), OUT, 6.5))
    return "".join(out)


def _lid(cx: float, cy: float, y_out: float, y_in: float, side: int, skin: str) -> str:
    """Paupière supérieure droite ; ``side`` = +1 pour l'œil gauche (intérieur à droite)."""
    xo, xi = cx - 28 * side, cx + 28 * side
    d = _d("M", xo, cy + y_out, "L", xi, cy + y_in, "L", xi, cy - 40, "L", xo, cy - 40, "Z")
    edge = _d("M", xo + 2 * side, cy + y_out, "L", xi - 2 * side, cy + y_in)
    return _el("path", d=d, fill=skin) + _stroke(edge, OUT, 6)


def _eyes(emo: Emotion, gaze: str, look: Look) -> str:
    gx, gy = _GAZE.get(gaze, (0.0, 0.0))
    out = []
    for (cx, cy), side in ((EYE_L, 1), (EYE_R, -1)):
        kind = emo.eyes
        if kind == "happy" or (kind == "wink" and side == -1):
            out.append(_stroke(_d("M", cx - 22, cy + 6, "Q", cx, cy - 22, cx + 22, cy + 6), OUT, 7))
            continue
        if kind == "closed":
            out.append(_stroke(_d("M", cx - 22, cy - 2, "Q", cx, cy + 14, cx + 22, cy - 2), OUT, 6.5))
            continue
        ex, ey = gx, gy
        if kind == "look_up":
            ex, ey = gx - 4 * side, min(gy, 0.0) - 6
        elif kind == "look_side":
            ex, ey = gx - 7, gy + 3
        out.append(_open_eye(cx, cy, ex, ey, wide=kind == "wide", star=kind == "star"))
        if kind == "angry":
            out.append(_lid(cx, cy, -20, -4, side, look.skin))
        elif kind == "sad":
            out.append(_lid(cx, cy, -4, -22, side, look.skin))
        elif kind == "doubt" and side == 1:
            out.append(_lid(cx, cy, -2, 0, side, look.skin))
        elif emo.lid > 0:
            y = -28 + 30 * emo.lid
            out.append(_lid(cx, cy, y, y, side, look.skin))
    return "".join(out)


def _brows(emo: Emotion, look: Look) -> str:
    color = _mix(look.hair, "#000000", 0.2)
    out = []
    for (cx, _cy), side, (raise_, tilt) in ((EYE_L, 1, emo.brows), (EYE_R, -1, emo.brow_right or emo.brows)):
        by = 164 - raise_
        ix, iy = cx + 22 * side, by + tilt
        ox, oy = cx - 22 * side, by - tilt
        out.append(_stroke(_d("M", ox, oy, "Q", (ix + ox) / 2, (iy + oy) / 2 - 5, ix, iy), color, 10))
    return "".join(out)


_TONGUE = "#D9615A"
_MOUTH_IN = "#4A1714"
_LINE_MOUTHS = {
    "soft": ("M184,258 Q200,270 216,258", 5.0),
    "smile": ("M176,254 Q200,278 224,254", 5.5),
    "flat": ("M184,264 L216,264", 5.5),
    "doubt": ("M182,268 Q196,264 204,264 Q212,264 218,258", 5.5),
    "pout": ("M190,266 Q200,258 210,266", 5.5),
    "frown": ("M180,272 Q200,252 220,272", 5.5),
    "frown_small": ("M186,270 Q200,260 214,270", 5.0),
    "wavy": ("M178,264 Q184,256 190,264 Q196,272 202,264 Q208,256 214,264 Q218,270 222,264", 4.5),
}


def _mouth(kind: str) -> str:
    if kind in _LINE_MOUTHS:
        d, w = _LINE_MOUTHS[kind]
        return _stroke(d, OUT, w)
    if kind == "talk":
        return _shape("M184,254 Q200,252 216,254 Q214,276 200,277 Q186,276 184,254 Z", _MOUTH_IN, 4.5) + _el(
            "ellipse", cx=200, cy=270, rx=9, ry=4.5, fill=_TONGUE
        )
    if kind in ("big_smile", "laugh"):
        w, dp = (24.0, 36.0) if kind == "big_smile" else (30.0, 46.0)
        x0, x1 = 200 - w, 200 + w
        mouth = _d(
            "M",
            x0,
            250,
            "Q",
            200,
            248,
            x1,
            250,
            "Q",
            x1 - 2,
            250 + dp,
            200,
            252 + dp,
            "Q",
            x0 + 2,
            250 + dp,
            x0,
            250,
            "Z",
        )
        teeth = _d(
            "M", x0 + 4, 252, "L", x1 - 4, 252, "Q", x1 - 6, 262, 200, 262, "Q", x0 + 6, 262, x0 + 4, 252, "Z"
        )
        return (
            _shape(mouth, _MOUTH_IN)
            + _el("path", d=teeth, fill="#FFFFFF")
            + _el("ellipse", cx=200, cy=240 + dp, rx=w * 0.5, ry=dp * 0.18, fill=_TONGUE)
        )
    if kind == "smirk":
        return _stroke("M180,264 Q202,270 222,252", OUT, 5.5) + _stroke("M219,250 L226,256", OUT, 4)
    if kind == "o":
        return _shape("M200,252 C214,252 214,282 200,282 C186,282 186,252 200,252 Z", _MOUTH_IN, 4.5)
    if kind == "wavy_open":
        return _shape(
            "M180,262 Q190,252 200,260 Q210,252 220,262 Q212,280 200,280 Q188,280 180,262 Z", _MOUTH_IN, 4.5
        )
    if kind == "grit":  # dents serrées
        out = [
            _el("rect", x=176, y=252, width=48, height=22, rx=7, fill="#FFFFFF", stroke=OUT, stroke_width=4.5)
        ]
        out.append(_stroke("M178,263 L222,263", OUT, 2.5))
        for x in (188.0, 200.0, 212.0):
            out.append(_stroke(_d("M", x, 254, "L", x, 272), OUT, 2.5))
        return "".join(out)
    if kind == "shout":
        return (
            _shape("M172,282 Q172,244 200,244 Q228,244 228,282 Q200,290 172,282 Z", _MOUTH_IN)
            + _el("path", d="M178,250 Q200,242 222,250 L220,256 Q200,252 180,256 Z", fill="#FFFFFF")
            + _el("ellipse", cx=200, cy=278, rx=14, ry=5, fill=_TONGUE)
        )
    if kind == "disgust":
        return _stroke("M180,262 Q188,254 196,264 Q206,274 220,258", OUT, 5.5) + _stroke(
            "M207,268 Q210,276 214,268", OUT, 3
        )
    return _stroke(_LINE_MOUTHS["soft"][0], OUT, 5.0)


def _face(emo: Emotion, gaze: str, look: Look) -> str:
    out = []
    blush = 0.6 if "blush_strong" in emo.extras else 0.42 if "blush" in emo.extras else 0.22
    for cx in (118.0, 282.0):
        out.append(_el("ellipse", cx=cx, cy=250, rx=21, ry=11, fill="#E0573E", opacity=blush))
        if "blush_strong" in emo.extras:
            for k in (-1, 0, 1):
                out.append(_stroke(_d("M", cx + k * 9 - 3, 255, "L", cx + k * 9 + 3, 245), "#B8392A", 2.5))
    if "red" in emo.extras:  # le haut du visage rougit, en fondu vers les joues
        out.append(_red_flush())
    out.append(_eyes(emo, gaze, look))
    out.append(_brows(emo, look))
    out.append(_stroke("M190,238 Q200,246 210,238", look.shade, 4.5))
    out.append(_mouth(emo.mouth))
    return "".join(out)


def _sign(text: str, x: float, y: float, size: float, color: str) -> str:
    return (
        f'<text x="{_f(x)}" y="{_f(y)}" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" '
        f'font-size="{_f(size)}" fill="{color}" stroke="{OUT}" stroke-width="3">{text}</text>'
    )


def _extras(emo: Emotion, mirror: bool) -> str:
    """Signes de bande dessinée, dessinés hors du groupe retourné pour que « ? » reste lisible."""

    def mx(x: float) -> float:
        return W - x if mirror else x

    out = []
    ex = emo.extras
    if "sweat" in ex:
        x, y = mx(326), 128.0
        d = _d("M", x, y - 22, "Q", x + 15, y, x, y + 8, "Q", x - 15, y, x, y - 22, "Z")
        out.append(_shape(d, "#9AD8FF", 3))
    if "anger" in ex or "anger_small" in ex:  # veine de colère : quatre crochets rouges
        s = 1.0 if "anger" in ex else 0.7
        x, y = mx(304), 92.0
        for ax, ay in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            x0, y0 = x + ax * 6 * s, y + ay * 6 * s
            out.append(
                _stroke(_d("M", x0, y0 + ay * 14 * s, "Q", x0, y0, x0 + ax * 14 * s, y0), "#E5322D", 7 * s)
            )
    if "tears" in ex:
        for cx in (EYE_L[0], EYE_R[0]):
            out.append(_stroke(_d("M", cx - 6, 238, "Q", cx - 12, 270, cx - 8, 300), "#7CC8FF", 10, 0.9))
    if "laugh_tears" in ex:
        for x in (mx(106), mx(294)):
            out.append(_circle(x, 206, 7, "#9AD8FF", 2.5))
    if "question" in ex or "question2" in ex:
        out.append(_sign("?", mx(334), 112, 72, "#FFC93C"))
        if "question2" in ex:
            out.append(_sign("?", mx(70), 96, 52, "#FFC93C"))
    if "exclaim" in ex:
        out.append(_sign("!", mx(336), 104, 74, "#FF5A4A"))
    if "sparkles" in ex or "sparkles_small" in ex:
        pts = [(mx(70), 96.0, 18.0), (mx(338), 76.0, 22.0), (mx(352), 160.0, 13.0)]
        for x, y, r in pts[1:] if "sparkles_small" in ex else pts:
            out.append(_shape(_sparkle(x, y, r), "#FFE066", 2.5))
    if "gloom" in ex:  # traits d'abattement sur le front
        for k in range(5):
            x = 160 + k * 20
            out.append(_stroke(_d("M", x, 60 + (k % 2) * 8, "L", x, 118 + (k % 2) * 6), "#3A4A7A", 4, 0.55))
    if "steam" in ex:
        for x0 in (mx(64), mx(336)):
            for dx, dy, r in ((0, 0, 14), (12, -16, 11), (-6, -30, 9)):
                out.append(_circle(x0 + dx, 90 + dy, r, "#F4F4F4", 3))
    if "thinking" in ex:
        for x, y, r in ((300, 128, 6), (318, 100, 9), (342, 66, 13)):
            out.append(_circle(mx(x), y, r, "#FFFFFF", 3))
    if "sigh" in ex:
        x, s = mx(246), -1.0 if mirror else 1.0
        out.append(_stroke(_d("M", x, 282, "Q", x + 14 * s, 292, x + 30 * s, 284), "#DDE6EE", 6))
    return "".join(out)


# --- proportions adultes ---------------------------------------------------------------------------
# La tête, la coiffure, la barbe, les couvre-chefs et les signes du chibi sont réutilisés, réduits ;
# le corps, les bras et les traits du visage (yeux en amande, nez large, lèvres) sont propres à l'adulte.
HEAD_TF = "translate(200,121) scale(0.6) translate(-200,-180)"
TORSO_TF = "translate(200,222) scale(1.294,1.213) translate(-200,-314)"
A_EYE_L, A_EYE_R = (172.0, 128.0), (228.0, 128.0)
_A_REST_L = Arm(((128, 254), (112, 330), (118, 404)))
_A_HIPS_L = Arm(((128, 254), (82, 312), (124, 376)))
_A_SHRUG_L = Arm(((126, 252), (76, 292), (58, 248)), "open", front=False)
_A_RAISED_L = Arm(((128, 252), (78, 204), (54, 128)), front=False)
_ADULT_POSES: dict[str, tuple[Arm, Arm]] = {
    "repos": (_A_REST_L, _mirror_arm(_A_REST_L)),
    "explique": (_A_REST_L, Arm(((272, 254), (318, 318), (342, 256)), "open", front=False)),
    "montre": (_A_REST_L, Arm(((272, 254), (330, 286), (360, 262)), "point", -12, front=False)),
    "index": (_A_REST_L, Arm(((272, 254), (316, 300), (314, 226)), "point", -90, front=False)),
    "salut": (_A_REST_L, Arm(((272, 254), (328, 236), (344, 172)), "open", front=False, wave=True)),
    "menton": (Arm(((128, 254), (128, 322), (250, 322))), Arm(((272, 254), (270, 322), (226, 194)))),
    "bras_croises": (Arm(((128, 254), (116, 318), (252, 322))), Arm(((272, 254), (286, 312), (150, 316)))),
    "hanches": (_A_HIPS_L, _mirror_arm(_A_HIPS_L)),
    "haussement": (_A_SHRUG_L, _mirror_arm(_A_SHRUG_L)),
    "victoire": (_A_RAISED_L, _mirror_arm(_A_RAISED_L)),
}


def _g(transform: str, content: str) -> str:
    return f'<g transform="{transform}">{content}</g>' if content else ""


def _adult_lid(cx: float, cy: float, y_out: float, y_in: float, side: int, skin: str) -> str:
    xo, xi = cx - 18 * side, cx + 18 * side
    d = _d("M", xo, cy + y_out, "L", xi, cy + y_in, "L", xi, cy - 16, "L", xo, cy - 16, "Z")
    return _el("path", d=d, fill=skin) + _stroke(_d("M", xo, cy + y_out, "L", xi, cy + y_in), OUT, 3)


def _adult_eyes(emo: Emotion, gaze: str, look: Look) -> str:
    gx, gy = _GAZE.get(gaze, (0.0, 0.0))
    out = []
    for (cx, cy), side in ((A_EYE_L, 1), (A_EYE_R, -1)):
        kind = emo.eyes
        if kind == "happy" or (kind == "wink" and side == -1):
            out.append(_stroke(_d("M", cx - 14, cy + 2, "Q", cx, cy - 8, cx + 14, cy + 2), OUT, 3.4))
            out.append(_stroke(_d("M", cx - 10, cy + 8, "Q", cx, cy + 11, cx + 10, cy + 8), look.shade, 1.8))
            continue
        if kind == "closed":
            out.append(_stroke(_d("M", cx - 14, cy - 1, "Q", cx, cy + 5, cx + 14, cy - 1), OUT, 3.2))
            continue
        ex, ey = gx * 0.5, gy * 0.4
        if kind == "look_up":
            ex, ey = -2.0 * side, -2.5
        elif kind == "look_side":
            ex, ey = -4.0, 1.0
        top = 13.0 if kind == "wide" else 11.0
        almond = _d("M", cx - 16, cy, "Q", cx, cy - top, cx + 16, cy, "Q", cx, cy + 8, cx - 16, cy, "Z")
        iris = 4.8 if kind == "wide" else 6.0
        out += [
            _el("path", d=almond, fill="#F2ECE4"),
            _el("ellipse", cx=cx + ex, cy=cy + ey - 0.5, rx=iris, ry=iris * 0.85, fill="#3B2416"),
            _el("circle", cx=cx + ex, cy=cy + ey - 0.5, r=iris * 0.45, fill="#0E0805"),
        ]
        if kind == "star":
            out.append(_el("path", d=_sparkle(cx + ex, cy + ey - 0.5, 4.5), fill="#FFFFFF"))
        else:
            out.append(_el("circle", cx=cx + ex - 2, cy=cy + ey - 2.5, r=1.6, fill="#FFFFFF"))
        out.append(_stroke(_d("M", cx - 17, cy + 1, "Q", cx, cy - top - 1.5, cx + 17, cy - 0.5), OUT, 3.2))
        out.append(_stroke(_d("M", cx - 12, cy + 3.5, "Q", cx, cy + 7.5, cx + 12, cy + 3.5), look.shade, 1.6))
        if kind == "angry":
            out.append(_adult_lid(cx, cy, -6, -0.5, side, look.skin))
        elif kind == "sad":
            out.append(_adult_lid(cx, cy, -1, -6, side, look.skin))
        elif kind == "doubt" and side == 1:
            out.append(_adult_lid(cx, cy, -1.5, -1, side, look.skin))
        elif emo.lid > 0:
            y = -6.5 + 7 * emo.lid
            out.append(_adult_lid(cx, cy, y, y, side, look.skin))
    return "".join(out)


def _adult_brows(emo: Emotion, look: Look) -> str:
    color = _mix(look.hair, "#000000", 0.2)
    out = []
    for (cx, _cy), side, (raise_, tilt) in (
        (A_EYE_L, 1, emo.brows),
        (A_EYE_R, -1, emo.brow_right or emo.brows),
    ):
        by = 111 - raise_ * 0.55
        ix, iy = cx + 15 * side, by + tilt * 0.55
        ox, oy = cx - 17 * side, by - tilt * 0.55
        out.append(_stroke(_d("M", ox, oy, "Q", (ix + ox) / 2, (iy + oy) / 2 - 3, ix, iy), color, 6))
    return "".join(out)


def _adult_face(emo: Emotion, gaze: str, look: Look) -> str:
    out = []
    if "blush" in emo.extras or "blush_strong" in emo.extras:
        op = 0.45 if "blush_strong" in emo.extras else 0.3
        for cx in (160.0, 240.0):
            out.append(_el("ellipse", cx=cx, cy=150, rx=12, ry=6, fill="#C8503E", opacity=op))
    out.append(_adult_eyes(emo, gaze, look))
    out.append(_adult_brows(emo, look))
    # nez large : ailes du nez, arête suggérée, reflet
    out.append(_stroke("M197,124 Q195,136 192,144", look.shade, 1.6, 0.6))
    out.append(
        _stroke(
            "M184,144 Q179,154 189,156 Q195,160 200,157 Q205,160 211,156 Q221,154 216,144", look.shade, 3.2
        )
    )
    out.append(_el("ellipse", cx=201, cy=145, rx=3.5, ry=2.2, fill="#FFFFFF", opacity=0.12))
    if emo.mouth in _LINE_MOUTHS:  # lèvres pleines sous les bouches fermées
        lip = _mix(look.skin, "#9C4A44", 0.35)
        out.append(_el("ellipse", cx=200, cy=171, rx=18, ry=6.5, fill=lip))
    out.append(_g("translate(200,170) scale(0.72) translate(-200,-262)", _mouth(emo.mouth)))
    return "".join(out)


def _adult_glasses(glasses: str) -> str:
    out: list[str] = []
    dark, metal = "#26262A", "#9A9EA6"
    tint: dict[str, str | float] = {"fill": "#BFE3FF", "fill_opacity": 0.12}
    if glasses == "rondes":
        for cx, cy in (A_EYE_L, A_EYE_R):
            out.append(_el("circle", cx=cx, cy=cy, r=19, stroke=dark, stroke_width=3, **tint))
    elif glasses == "rectangles":
        for cx, cy in (A_EYE_L, A_EYE_R):
            out.append(
                _el(
                    "rect",
                    x=cx - 21,
                    y=cy - 12,
                    width=42,
                    height=25,
                    rx=5,
                    stroke=dark,
                    stroke_width=3,
                    **tint,
                )
            )
    elif glasses == "fines":
        for cx, cy in (A_EYE_L, A_EYE_R):
            out.append(
                _el(
                    "rect",
                    x=cx - 20,
                    y=cy - 15,
                    width=40,
                    height=30,
                    rx=12,
                    stroke=metal,
                    stroke_width=2.2,
                    **tint,
                )
            )
    elif glasses == "protection":
        _goggles(out, 200, 128, 0.42)
        return "".join(out)
    if out:
        color = metal if glasses == "fines" else dark
        out.append(_stroke("M190,126 Q200,121 210,126", color, 2.5))
        out.append(_stroke("M152,125 L127,121 M248,125 L273,121", color, 2.5))
    return "".join(out)


def _red_flush() -> str:
    return (
        '<defs><linearGradient id="rouge" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#D9302A" stop-opacity="0.38"/>'
        '<stop offset="1" stop-color="#D9302A" stop-opacity="0"/></linearGradient></defs>'
        + _el(
            "path",
            d="M80,170 C84,128 110,108 200,108 C290,108 316,128 320,170 L320,236 L80,236 Z",
            fill="url(#rouge)",
        )
    )


def _head(look: Look, beard: str, hair: str) -> str:
    """Oreilles, visage, ombre de la mâchoire, barbe et coiffure (repère du chibi)."""
    out = []
    for x in (72.0, 328.0):
        out.append(_el("ellipse", cx=x, cy=208, rx=17, ry=23, fill=look.skin, stroke=OUT, stroke_width=LW))
        out.append(_stroke(_d("M", x, 198, "Q", x + (6 if x < 200 else -6), 208, x, 218), look.shade, 3.5))
    out += [
        _shape(HEAD, look.skin),
        _el("path", d=JAW_SHADE, fill=look.shade, opacity=0.35),
        _beard(look, beard),
        _hair_front(look, hair),
    ]
    return "".join(out)


def _chibi_body(params: dict[str, Any], look: Look, emo: Emotion) -> str:
    outfit, hair = str(params.get("outfit", "tshirt")), str(params.get("hair", "court"))
    arms = _POSES.get(str(params.get("pose", "repos")), _POSES["repos"])
    body = [
        _el("ellipse", cx=200, cy=526, rx=104, ry=13, fill="#000000", opacity=0.2),
        _hair_back(look, hair),
        _legs(look, outfit),
        _el("rect", x=182, y=288, width=36, height=42, fill=look.shade, stroke=OUT, stroke_width=LW),
        _torso(look, outfit),
    ]
    body += [_arm_svg(arm, look) for arm in arms if not arm.front]
    body += [
        _head(look, str(params.get("beard", "aucune")), hair),
        _face(emo, str(params.get("gaze", "face")), look),
        _accessories(look, str(params.get("glasses", "aucune")), str(params.get("hat", "aucun"))),
    ]
    body += [_arm_svg(arm, look) for arm in arms if arm.front]
    return "".join(body)


def _adult_body(params: dict[str, Any], look: Look, emo: Emotion) -> str:
    outfit, hair = str(params.get("outfit", "tshirt")), str(params.get("hair", "court"))
    arms = _ADULT_POSES.get(str(params.get("pose", "repos")), _ADULT_POSES["repos"])
    k = 0.82
    body = [
        _el("ellipse", cx=200, cy=550, rx=100, ry=9, fill="#000000", opacity=0.2),
        _g(HEAD_TF, _hair_back(look, hair)),
        _legs(look, outfit, ADULT_LEGS),
        _el("rect", x=176, y=180, width=48, height=54, fill=look.shade, stroke=OUT, stroke_width=LW),
        _g(TORSO_TF, _torso(look, outfit)),
    ]
    body += [_arm_svg(arm, look, k) for arm in arms if not arm.front]
    body.append(_g(HEAD_TF, _head(look, str(params.get("beard", "aucune")), hair)))
    if "red" in emo.extras:
        body.append(_g(HEAD_TF, _red_flush()))
    body += [
        _adult_face(emo, str(params.get("gaze", "face")), look),
        _adult_glasses(str(params.get("glasses", "aucune"))),
        _g(HEAD_TF, _accessories(look, "aucune", str(params.get("hat", "aucun")))),
    ]
    body += [_arm_svg(arm, look, k) for arm in arms if arm.front]
    return "".join(body)


def chibi_svg(params: dict[str, Any], style: dict[str, Any]) -> str:
    """SVG complet d'un personnage, identique pour des paramètres identiques."""
    look = _look(params, style)
    emo = EMOTION_BY_ID.get(str(params.get("emotion", "neutre")), EMOTIONS[0])
    mirror = bool(params.get("mirror", False))
    adult = params.get("proportions") == "adulte"
    inner = _adult_body(params, look, emo) if adult else _chibi_body(params, look, emo)
    if mirror:
        inner = f'<g transform="translate({_f(W)},0) scale(-1,1)">{inner}</g>'
    signs = _g(HEAD_TF, _extras(emo, mirror)) if adult else _extras(emo, mirror)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_f(W)} {_f(H)}" width="{_f(W)}" '
        f'height="{_f(H)}">{inner}{signs}</svg>'
    )


# --- rendu Qt --------------------------------------------------------------------------------------
_local = threading.local()


def _renderer(svg: str) -> QSvgRenderer:
    cache: OrderedDict[str, QSvgRenderer] | None = getattr(_local, "cache", None)
    if cache is None:
        cache = OrderedDict()
        _local.cache = cache
    r = cache.get(svg)
    if r is None:
        r = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        cache[svg] = r
        while len(cache) > 96:
            cache.popitem(last=False)
    else:
        cache.move_to_end(svg)
    return r


def chibi_bounds(params: dict[str, Any]) -> QRectF:
    h = max(1.0, float(params.get("height", 420.0)))
    w = h * W / H
    return QRectF(-w / 2, -h / 2, w, h)


def paint_chibi(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    _renderer(chibi_svg(params, style)).render(painter, chibi_bounds(params))

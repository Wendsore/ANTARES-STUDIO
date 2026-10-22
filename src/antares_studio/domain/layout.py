"""Géométrie de mise en page sans Qt : aligner, répartir, guides d'aimantation entre objets.

Les rectangles sont des boîtes englobantes en pixels du canevas : ``(gauche, haut, droite, bas)``.
"""

from __future__ import annotations

from dataclasses import dataclass

Rect = tuple[float, float, float, float]

ALIGN_MODES: dict[str, str] = {
    "left": "Aligner à gauche",
    "hcenter": "Centrer horizontalement",
    "right": "Aligner à droite",
    "top": "Aligner en haut",
    "vcenter": "Centrer verticalement",
    "bottom": "Aligner en bas",
}


def _cx(r: Rect) -> float:
    return (r[0] + r[2]) / 2


def _cy(r: Rect) -> float:
    return (r[1] + r[3]) / 2


def union(rects: list[Rect]) -> Rect:
    return (
        min(r[0] for r in rects),
        min(r[1] for r in rects),
        max(r[2] for r in rects),
        max(r[3] for r in rects),
    )


def align_deltas(rects: list[Rect], mode: str, reference: Rect | None = None) -> list[tuple[float, float]]:
    """Déplacements qui alignent chaque boîte sur la boîte englobante de la sélection (ou ``reference``,
    par exemple le canevas quand un seul objet est sélectionné)."""
    if mode not in ALIGN_MODES:
        raise ValueError(f"alignement inconnu : {mode!r}")
    if not rects:
        return []
    ref = reference or union(rects)
    out: list[tuple[float, float]] = []
    for r in rects:
        dx = dy = 0.0
        if mode == "left":
            dx = ref[0] - r[0]
        elif mode == "right":
            dx = ref[2] - r[2]
        elif mode == "hcenter":
            dx = _cx(ref) - _cx(r)
        elif mode == "top":
            dy = ref[1] - r[1]
        elif mode == "bottom":
            dy = ref[3] - r[3]
        else:
            dy = _cy(ref) - _cy(r)
        out.append((dx, dy))
    return out


def distribute_deltas(rects: list[Rect], axis: str) -> list[tuple[float, float]]:
    """Espacement égal entre boîtes successives (les deux extrêmes ne bougent pas) ; 3 objets minimum."""
    if axis not in ("x", "y"):
        raise ValueError("axe x ou y attendu")
    out = [(0.0, 0.0)] * len(rects)
    if len(rects) < 3:
        return out
    lo, hi = (0, 2) if axis == "x" else (1, 3)
    order = sorted(range(len(rects)), key=lambda i: (rects[i][lo] + rects[i][hi]) / 2)
    first, last = rects[order[0]], rects[order[-1]]
    span = last[hi] - first[lo]
    sizes = sum(rects[i][hi] - rects[i][lo] for i in order)
    gap = (span - sizes) / (len(rects) - 1)
    pos = first[hi] + gap
    for i in order[1:-1]:
        shift = pos - rects[i][lo]
        out[i] = (shift, 0.0) if axis == "x" else (0.0, shift)
        pos += rects[i][hi] - rects[i][lo] + gap
    return out


@dataclass(frozen=True)
class Guide:
    axis: str  # "x" : ligne verticale à la coordonnée ``value`` ; "y" : ligne horizontale
    value: float
    start: float  # étendue de la ligne sur l'autre axe
    end: float


def snap_rect(moving: Rect, targets: list[Rect], threshold: float) -> tuple[float, float, list[Guide]]:
    """Corrige un déplacement pour aligner bords et centres de ``moving`` sur ceux des ``targets``.

    Retourne (dx, dy, guides) : la plus petite correction sous le seuil sur chaque axe et les lignes de
    repère à afficher (une par coïncidence). Le canevas peut être passé comme cible (bords et centre).
    """
    best: dict[str, tuple[float, float] | None] = {"x": None, "y": None}  # (|écart|, correction)
    for axis, (a, b) in (("x", (0, 2)), ("y", (1, 3))):
        ours = (moving[a], (moving[a] + moving[b]) / 2, moving[b])
        for t in targets:
            for theirs in (t[a], (t[a] + t[b]) / 2, t[b]):
                for v in ours:
                    d = theirs - v
                    if abs(d) <= threshold and (best[axis] is None or abs(d) < best[axis][0]):  # type: ignore[index]
                        best[axis] = (abs(d), d)
    dx = best["x"][1] if best["x"] else 0.0
    dy = best["y"][1] if best["y"] else 0.0
    m = (moving[0] + dx, moving[1] + dy, moving[2] + dx, moving[3] + dy)
    guides: list[Guide] = []
    eps = 0.5
    for axis, (a, b), (oa, ob) in (("x", (0, 2), (1, 3)), ("y", (1, 3), (0, 2))):
        if best[axis] is None:
            continue
        ours = (m[a], (m[a] + m[b]) / 2, m[b])
        for t in targets:
            for theirs in (t[a], (t[a] + t[b]) / 2, t[b]):
                if any(abs(theirs - v) <= eps for v in ours):
                    g = Guide(axis, theirs, min(m[oa], t[oa]), max(m[ob], t[ob]))
                    if g not in guides:
                        guides.append(g)
    return dx, dy, guides

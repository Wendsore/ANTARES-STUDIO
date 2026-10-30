"""Solides 3D de la bibliothèque (cube, sphère, cylindre, polyèdres, tore…) générés par le logiciel.

Chaque forme est un maillage de triangles orientés vers l'extérieur et une liste d'arêtes à montrer
(les arêtes vives d'un polyèdre, les parallèles et méridiens d'une sphère). Le rendu reprend la
projection et l'éclairage des modèles glTF (``rendering.gltf``) : faces triées du fond vers l'avant,
faces cachées éliminées, arêtes cachées en pointillé en mode fil de fer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from antares_studio.rendering.gltf import LIGHT

Array = np.ndarray[Any, np.dtype[Any]]


@dataclass(frozen=True)
class Solid:
    vertices: Array  # (N, 3), rayon maximal 1, y vers le haut, z vers l'observateur
    triangles: Array  # (M, 3), sens direct vu de l'extérieur
    edges: Array  # (E, 2) arêtes à dessiner
    edge_faces: tuple[tuple[int, ...], ...]  # faces adjacentes à chaque arête


def _normalize(v: Array) -> Array:
    out: Array = v / float(np.max(np.linalg.norm(v, axis=1)) or 1.0)
    return out


def _quad_grid(rows: int, cols: int, wrap_cols: bool, offset: int = 0) -> list[tuple[int, int, int]]:
    """Triangles d'une grille de sommets ``rows × cols`` (indice = offset + r * cols + c)."""
    tris = []
    last = cols if wrap_cols else cols - 1
    for r in range(rows - 1):
        for c in range(last):
            a = offset + r * cols + c
            b = offset + r * cols + (c + 1) % cols
            d = offset + (r + 1) * cols + c
            e = offset + (r + 1) * cols + (c + 1) % cols
            tris += [(a, d, b), (b, d, e)]
    return tris


def _box(sx: float, sy: float, sz: float) -> tuple[Array, list[tuple[int, int, int]], list[tuple[int, int]]]:
    v = np.array([[x * sx, y * sy, z * sz] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=float)
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    tris = [t for a, b, c, d in quads for t in ((a, b, c), (a, c, d))]
    edges = [(a, b) for a in range(8) for b in range(a + 1, 8) if bin(a ^ b).count("1") == 1]
    return v, tris, edges


def _sphere(
    rings: int = 14, segs: int = 24
) -> tuple[Array, list[tuple[int, int, int]], list[tuple[int, int]]]:
    verts = []
    for r in range(rings + 1):
        phi = math.pi * r / rings
        for c in range(segs):
            th = 2 * math.pi * c / segs
            verts.append((math.sin(phi) * math.cos(th), math.cos(phi), math.sin(phi) * math.sin(th)))
    tris = _quad_grid(rings + 1, segs, True)  # triangles dégénérés aux pôles retirés par ``solid_mesh``
    edges = [(r * segs + c, r * segs + (c + 1) % segs) for r in range(1, rings) for c in range(segs)]
    edges += [(r * segs + c, (r + 1) * segs + c) for r in range(rings) for c in range(0, segs, 2)]
    return np.array(verts), tris, edges


def _lathe(
    profile: list[tuple[float, float]], segs: int, cap_bottom: bool, cap_top: bool
) -> tuple[Array, list[tuple[int, int, int]], list[tuple[int, int]]]:
    """Solide de révolution autour de y : ``profile`` = (rayon, hauteur) de bas en haut."""
    verts = []
    for rad, y in profile:
        for c in range(segs):
            th = 2 * math.pi * c / segs
            verts.append((rad * math.cos(th), y, rad * math.sin(th)))
    tris = _quad_grid(len(profile), segs, True)
    edges: list[tuple[int, int]] = []
    rows = len(profile)
    if cap_bottom:
        center = len(verts)
        verts.append((0.0, profile[0][1], 0.0))
        tris += [(center, c, (c + 1) % segs) for c in range(segs)]
    if cap_top:
        center = len(verts)
        verts.append((0.0, profile[-1][1], 0.0))
        top = (rows - 1) * segs
        tris += [(center, top + (c + 1) % segs, top + c) for c in range(segs)]
    for r in range(rows):
        if profile[r][0] > 1e-9:
            edges += [(r * segs + c, r * segs + (c + 1) % segs) for c in range(segs)]
    edges += [(r * segs + c, (r + 1) * segs + c) for r in range(rows - 1) for c in range(0, segs, segs // 8)]
    return np.array(verts), tris, edges


def _polyhedron(name: str) -> tuple[Array, list[tuple[int, int, int]], list[tuple[int, int]]]:
    if name == "tetrahedron":
        v = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=float)
        tris = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
    elif name == "octahedron":
        v = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], dtype=float)
        tris = [(a, b, c) for a in (0, 1) for b in (2, 3) for c in (4, 5)]
    elif name == "icosahedron":
        g = (1 + math.sqrt(5)) / 2
        v = np.array(
            [[-1, g, 0], [1, g, 0], [-1, -g, 0], [1, -g, 0], [0, -1, g], [0, 1, g]]
            + [[0, -1, -g], [0, 1, -g], [g, 0, -1], [g, 0, 1], [-g, 0, -1], [-g, 0, 1]],
            dtype=float,
        )
        n = len(v)
        d = np.linalg.norm(v[:, None] - v[None, :], axis=2)
        tris = [
            (a, b, c)
            for a in range(n)
            for b in range(a + 1, n)
            for c in range(b + 1, n)
            if abs(d[a, b] - 2) < 1e-6 and abs(d[b, c] - 2) < 1e-6 and abs(d[a, c] - 2) < 1e-6
        ]
    else:  # pyramide à base carrée
        v = np.array([[-1, -0.7, -1], [1, -0.7, -1], [1, -0.7, 1], [-1, -0.7, 1], [0, 1.0, 0]], dtype=float)
        tris = [(0, 1, 2), (0, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)]
        return v, tris, edges
    edges = sorted({tuple(sorted((t[i], t[(i + 1) % 3]))) for t in tris for i in range(3)})  # type: ignore[misc]
    return v, tris, edges


def _torus(
    major: int = 32, minor: int = 14
) -> tuple[Array, list[tuple[int, int, int]], list[tuple[int, int]]]:
    big, small = 1.0, 0.42
    verts = []
    for i in range(major):
        u = 2 * math.pi * i / major
        for j in range(minor):
            w = 2 * math.pi * j / minor
            rad = big + small * math.cos(w)
            verts.append((rad * math.cos(u), small * math.sin(w), rad * math.sin(u)))
    tris = []
    for i in range(major):
        for j in range(minor):
            a = i * minor + j
            b = i * minor + (j + 1) % minor
            c = ((i + 1) % major) * minor + j
            d = ((i + 1) % major) * minor + (j + 1) % minor
            tris += [(a, b, c), (b, d, c)]
    edges = [(i * minor + j, i * minor + (j + 1) % minor) for i in range(0, major, 2) for j in range(minor)]
    edges += [
        (i * minor + j, ((i + 1) % major) * minor + j) for i in range(major) for j in range(0, minor, 2)
    ]
    return np.array(verts), tris, edges


def _orient(v: Array, tris: list[tuple[int, int, int]], shape: str) -> Array:
    """Oriente chaque triangle vers l'extérieur (normale opposée au centre de la forme ou du tube)."""
    t = np.array(tris, dtype=np.int64)
    p = v[t]
    n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    c = p.mean(axis=1)
    if shape == "torus":
        ring = c.copy()
        ring[:, 1] = 0.0
        ring /= np.maximum(np.linalg.norm(ring, axis=1), 1e-9)[:, None]
        center = ring * 1.0
    else:
        center = np.zeros_like(c)
    flip = np.einsum("ij,ij->i", n, c - center) < 0
    t[flip] = t[flip][:, [0, 2, 1]]
    return t


@lru_cache(maxsize=32)
def solid_mesh(shape: str, sx: float = 1.6, sy: float = 1.0, sz: float = 0.8) -> Solid:
    if shape in ("cube", "box"):
        v, tris, edges = _box(*((1.0, 1.0, 1.0) if shape == "cube" else (sx, sy, sz)))
    elif shape == "sphere":
        v, tris, edges = _sphere()
    elif shape == "cylinder":
        v, tris, edges = _lathe([(1.0, -1.0), (1.0, 1.0)], 40, True, True)
    elif shape == "cone":
        v, tris, edges = _lathe([(1.0, -0.8), (0.0, 1.2)], 40, True, False)
        tris = [t for t in tris if len(set(t)) == 3]
    elif shape == "torus":
        v, tris, edges = _torus()
    else:
        v, tris, edges = _polyhedron(
            shape if shape in ("tetrahedron", "octahedron", "icosahedron") else "pyramid"
        )
    tris = [t for t in tris if len(set(t)) == 3]
    # triangles dégénérés (pôles de la sphère) : retirés
    vv = np.asarray(v, dtype=float)
    areas = [np.linalg.norm(np.cross(vv[b] - vv[a], vv[c] - vv[a])) for a, b, c in tris]
    tris = [t for t, area in zip(tris, areas, strict=True) if area > 1e-9]
    vv = _normalize(vv - (vv.min(axis=0) + vv.max(axis=0)) / 2)
    t = _orient(vv, tris, shape)
    adjacency: dict[tuple[int, int], list[int]] = {}
    for f, (a, b, c) in enumerate(t.tolist()):
        for e in ((a, b), (b, c), (c, a)):
            adjacency.setdefault((min(e), max(e)), []).append(f)
    e_arr = np.array([(min(a, b), max(a, b)) for a, b in edges], dtype=np.int64).reshape(-1, 2)
    faces = tuple(tuple(adjacency.get((int(a), int(b)), ())) for a, b in e_arr)
    return Solid(vv, t, e_arr, faces)


def rotation3(yaw_deg: float, pitch_deg: float, roll_deg: float) -> Array:
    a, b, r = (math.radians(x) for x in (yaw_deg, pitch_deg, roll_deg))
    ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    out: Array = rz @ rx @ ry
    return out


@dataclass(frozen=True)
class Projected:
    screen: Array  # (N, 2) px, y vers le bas
    visible: Array  # (M,) bool : face tournée vers l'observateur
    order: Array  # faces du fond vers l'avant
    light: Array  # (M,) éclairement 0..1


def project_solid(
    solid: Solid,
    yaw: float,
    pitch: float,
    roll: float,
    size: float,
    persp: float,
    light: Array | None = None,
    ambient: float = 0.3,
) -> Projected:
    v = solid.vertices @ rotation3(yaw, pitch, roll).T * (size / 2)
    tri = v[solid.triangles]
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1), 1e-12)[:, None]
    centers = tri.mean(axis=1)
    if persp > 0:
        dist = size * (1.2 + 6.0 * (1.0 - persp))  # distance de l'œil au centre
        eye = np.array([0.0, 0.0, dist])
        visible = np.einsum("ij,ij->i", normals, eye - centers) > 0
        s = dist / np.maximum(dist - v[:, 2], size * 0.05)
        screen = np.stack([v[:, 0] * s, -v[:, 1] * s], axis=1)
    else:
        visible = normals[:, 2] > 0
        screen = np.stack([v[:, 0], -v[:, 1]], axis=1)
    lv = LIGHT if light is None else light
    shade = ambient + (1.0 - ambient) * np.clip(normals @ lv, 0.0, 1.0)
    order = np.argsort(centers[:, 2], kind="stable")
    return Projected(screen, visible, order, shade)


def _light(params: dict[str, Any]) -> Array | None:
    """Direction de la lumière des paramètres ; ``None`` (lumière fixe d'origine) s'ils sont absents."""
    if "light_az_deg" not in params and "light_el_deg" not in params:
        return None
    a = math.radians(float(params.get("light_az_deg", -29.74488129694223)))
    e = math.radians(float(params.get("light_el_deg", 36.65693295448205)))
    out: Array = np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)])
    return out


def _poly(screen: Array, idx: Any) -> QPolygonF:
    return QPolygonF([QPointF(float(screen[i][0]), float(screen[i][1])) for i in idx])


def paint_solid(painter: QPainter, params: dict[str, Any], style: dict[str, Any], qcolor: Any) -> None:
    solid = solid_mesh(
        str(params.get("shape", "cube")),
        round(float(params.get("size_x", 1.6)), 3),
        round(float(params.get("size_y", 1.0)), 3),
        round(float(params.get("size_z", 0.8)), 3),
    )
    proj = project_solid(
        solid,
        float(params.get("yaw_deg", 35.0)),
        float(params.get("pitch_deg", 25.0)),
        float(params.get("roll_deg", 0.0)),
        max(1.0, float(params.get("size", 300.0))),
        max(0.0, min(1.0, float(params.get("perspective", 0.0)))),
        _light(params),
        max(0.0, min(1.0, float(params.get("ambient", 0.3)))),
    )
    mode = str(params.get("render_mode", "shaded_edges"))
    fill = qcolor(style.get("fill", "#2677B8"))
    edge_color = qcolor(style.get("stroke", "#FFFFFF"))
    edge_w = max(0.0, float(style.get("stroke_width", 2.5) or 0.0))
    edge_visible = [any(bool(proj.visible[f]) for f in faces) for faces in solid.edge_faces]
    s = proj.screen

    def edge_pen(hidden: bool) -> QPen:
        c = QColor(edge_color)
        if hidden:
            c.setAlphaF(c.alphaF() * 0.45)
        pen = QPen(c, edge_w * (0.7 if hidden else 1.0), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        if hidden:
            pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    def face_color(f: int, alpha: float) -> QColor:
        c = QColor(fill)
        k = float(proj.light[f])
        c.setRgbF(
            min(1.0, c.redF() * k), min(1.0, c.greenF() * k), min(1.0, c.blueF() * k), c.alphaF() * alpha
        )
        return c

    painter.save()
    if mode == "wireframe" or mode == "transparent":
        if mode == "transparent":
            for f in proj.order:
                c = face_color(int(f), 0.18 if not proj.visible[f] else 0.38)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(c)
                painter.drawPolygon(_poly(s, solid.triangles[f]))
        if edge_w > 0:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for hidden in (True, False):  # arêtes cachées d'abord, en pointillé
                painter.setPen(edge_pen(hidden))
                for k, (a, b) in enumerate(solid.edges):
                    if edge_visible[k] != hidden:
                        painter.drawLine(QPointF(*map(float, s[a])), QPointF(*map(float, s[b])))
        painter.restore()
        return
    # faces ombrées (et arêtes) : du fond vers l'avant, faces cachées omises
    face_edges: dict[int, list[int]] = {}
    if mode == "shaded_edges" and edge_w > 0:
        rank = {int(f): i for i, f in enumerate(proj.order)}
        for k, faces in enumerate(solid.edge_faces):
            front = [f for f in faces if proj.visible[f]]
            if front:  # l'arête est dessinée avec la plus proche de ses faces visibles
                face_edges.setdefault(max(front, key=lambda f: rank[f]), []).append(k)
    for f in proj.order:
        fi = int(f)
        if not proj.visible[fi]:
            continue
        c = face_color(fi, 1.0)
        painter.setBrush(c)
        painter.setPen(QPen(c, 0.8))  # trait de même couleur : pas de fente entre triangles
        painter.drawPolygon(_poly(s, solid.triangles[fi]))
        for k in face_edges.get(fi, ()):
            a, b = solid.edges[k]
            painter.setPen(edge_pen(False))
            painter.drawLine(QPointF(*map(float, s[a])), QPointF(*map(float, s[b])))
    painter.restore()

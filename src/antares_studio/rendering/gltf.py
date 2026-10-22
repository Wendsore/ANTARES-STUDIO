"""Lecture de modèles 3D glTF 2.0 (.glb, ou .gltf aux données intégrées) en triangles colorés.

Lecteur volontairement restreint, sans dépendance ni exécution de code : géométrie (POSITION, indices,
primitives en triangles), transformations des nœuds (matrice ou translation/rotation/échelle) et
couleur de base des matériaux (``baseColorFactor``). Les textures, animations, morph targets et
squelettes sont ignorés et signalés dans ``Mesh.notes``.

Spécification : Khronos glTF 2.0, https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
"""

from __future__ import annotations

import base64
import json
import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

GLB_MAGIC = 0x46546C67  # « glTF »
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942
MAX_TRIANGLES = 100_000
MAX_BYTES = 64 * 1024 * 1024
_COMPONENTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_TYPE_SIZE = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
DEFAULT_COLOR = (0.8, 0.8, 0.8, 1.0)


class GltfError(ValueError):
    """Fichier illisible, non conforme ou hors des limites prises en charge."""


@dataclass
class Mesh:
    vertices: np.ndarray  # (N, 3) float64, repère glTF (y vers le haut)
    triangles: np.ndarray  # (M, 3) int64
    colors: np.ndarray  # (M, 4) float64, RGBA 0–1 par triangle
    notes: list[str] = field(default_factory=list)

    @property
    def triangle_count(self) -> int:
        return int(self.triangles.shape[0])


def _read_document(path: Path) -> tuple[dict[str, Any], bytes | None]:
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise GltfError(f"fichier trop volumineux (> {MAX_BYTES // 2**20} Mo)")
    if raw[:4] == b"glTF":
        if len(raw) < 20:
            raise GltfError("en-tête GLB tronqué")
        magic, version, length = struct.unpack_from("<III", raw, 0)
        if magic != GLB_MAGIC or version != 2:
            raise GltfError(f"GLB version {version} non prise en charge (2 attendue)")
        if length > len(raw):
            raise GltfError("fichier GLB tronqué")
        offset, doc, binary = 12, None, None
        while offset + 8 <= length:
            size, kind = struct.unpack_from("<II", raw, offset)
            chunk = raw[offset + 8 : offset + 8 + size]
            if len(chunk) != size:
                raise GltfError("bloc GLB tronqué")
            if kind == CHUNK_JSON and doc is None:
                doc = json.loads(chunk.decode("utf-8"))
            elif kind == CHUNK_BIN and binary is None:
                binary = chunk
            offset += 8 + size + (-size % 4)
        if not isinstance(doc, dict):
            raise GltfError("bloc JSON absent du GLB")
        return doc, binary
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GltfError(f"ni GLB ni glTF JSON valide : {exc}") from None
    if not isinstance(doc, dict):
        raise GltfError("document glTF invalide")
    return doc, None


def _buffers(doc: dict[str, Any], binary: bytes | None) -> list[bytes]:
    out = []
    for i, buf in enumerate(doc.get("buffers", [])):
        uri = buf.get("uri")
        if uri is None:
            if binary is None:
                raise GltfError(f"buffer {i} sans données")
            out.append(binary)
        elif isinstance(uri, str) and uri.startswith("data:") and ";base64," in uri:
            out.append(base64.b64decode(uri.split(",", 1)[1]))
        else:
            # pas de lecture de fichiers voisins : la ressource copiée dans le projet doit être autonome
            raise GltfError(
                f"le buffer {i} référence un fichier externe ({str(uri)[:60]}) : exportez le modèle en .glb "
                "(fichier unique) depuis Blender ou votre logiciel 3D"
            )
    return out


def _accessor(doc: dict[str, Any], buffers: list[bytes], index: int) -> np.ndarray:
    try:
        acc = doc["accessors"][index]
        view = doc["bufferViews"][acc["bufferView"]]
        fmt, size = _COMPONENTS[acc["componentType"]]
        width = _TYPE_SIZE[acc["type"]]
        count = int(acc["count"])
        data = buffers[view["buffer"]]
    except (KeyError, IndexError, TypeError) as exc:
        raise GltfError(f"accesseur {index} invalide ({exc})") from None
    if acc.get("sparse"):
        raise GltfError("accesseurs « sparse » non pris en charge")
    start = int(view.get("byteOffset", 0)) + int(acc.get("byteOffset", 0))
    stride = int(view.get("byteStride", 0)) or size * width
    end = start + stride * (count - 1) + size * width if count else start
    if end > len(data) or end > int(view.get("byteOffset", 0)) + int(view["byteLength"]):
        raise GltfError(f"accesseur {index} hors de son buffer")
    dtype = np.dtype("<" + fmt)
    if stride == size * width:
        arr = np.frombuffer(data, dtype=dtype, count=count * width, offset=start).reshape(count, width)
    else:
        rows = [
            np.frombuffer(data, dtype=dtype, count=width, offset=start + i * stride) for i in range(count)
        ]
        arr = np.array(rows).reshape(count, width)
    out = arr.astype(np.float64)
    if acc.get("normalized") and fmt != "f":
        out /= float(np.iinfo(dtype).max)
    return out


def _node_matrix(node: dict[str, Any]) -> np.ndarray:
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T  # glTF : colonne majeure
    t = np.array(node.get("translation", [0, 0, 0]), dtype=np.float64)
    x, y, z, w = (float(v) for v in node.get("rotation", [0, 0, 0, 1]))
    s = np.array(node.get("scale", [1, 1, 1]), dtype=np.float64)
    r = np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )
    m = np.eye(4)
    m[:3, :3] = r * s
    m[:3, 3] = t
    return m


def load_mesh(path: Path) -> Mesh:
    """Triangles de la scène par défaut, transformations appliquées ; ``GltfError`` si non lisible."""
    doc, binary = _read_document(Path(path))
    version = str(doc.get("asset", {}).get("version", ""))
    if not version.startswith("2."):
        raise GltfError(f"glTF version {version or 'inconnue'} non prise en charge (2.x attendue)")
    buffers = _buffers(doc, binary)
    notes: set[str] = set()
    if doc.get("textures"):
        notes.add("textures ignorées (couleur de base du matériau seulement)")
    if doc.get("animations"):
        notes.add("animations du fichier ignorées")
    if doc.get("skins"):
        notes.add("squelettes ignorés")
    materials = doc.get("materials", [])
    nodes = doc.get("nodes", [])
    scenes = doc.get("scenes", [])
    roots = scenes[int(doc.get("scene", 0))]["nodes"] if scenes else list(range(len(nodes)))
    all_v: list[np.ndarray] = []
    all_t: list[np.ndarray] = []
    all_c: list[np.ndarray] = []
    base = 0
    stack = [(int(i), np.eye(4), 0) for i in roots]
    while stack:
        idx, parent, depth = stack.pop()
        if depth > 64 or not 0 <= idx < len(nodes):
            raise GltfError("hiérarchie de nœuds invalide (cycle ou index hors limites)")
        node = nodes[idx]
        world = parent @ _node_matrix(node)
        stack += [(int(c), world, depth + 1) for c in node.get("children", [])]
        if "mesh" not in node:
            continue
        for prim in doc["meshes"][node["mesh"]].get("primitives", []):
            if int(prim.get("mode", 4)) != 4:
                notes.add("primitives non triangulaires ignorées (points, lignes, bandes)")
                continue
            if prim.get("targets"):
                notes.add("morph targets ignorées")
            if "POSITION" not in prim.get("attributes", {}):
                continue
            pos = _accessor(doc, buffers, prim["attributes"]["POSITION"])[:, :3]
            if "indices" in prim:
                tri = _accessor(doc, buffers, prim["indices"]).astype(np.int64).reshape(-1)
            else:
                tri = np.arange(pos.shape[0], dtype=np.int64)
            if tri.size % 3 or (tri.size and (int(np.min(tri)) < 0 or int(np.max(tri)) >= pos.shape[0])):
                raise GltfError("indices de triangles invalides")
            homo = np.hstack([pos, np.ones((pos.shape[0], 1))]) @ world.T
            all_v.append(homo[:, :3])
            tris = tri.reshape(-1, 3) + base
            all_t.append(tris)
            color = DEFAULT_COLOR
            if "material" in prim and 0 <= int(prim["material"]) < len(materials):
                pbr = materials[int(prim["material"])].get("pbrMetallicRoughness", {})
                color = tuple(float(c) for c in pbr.get("baseColorFactor", DEFAULT_COLOR))  # type: ignore[assignment]
            all_c.append(np.tile(np.array(color, dtype=np.float64), (tris.shape[0], 1)))
            base += pos.shape[0]
            if sum(t.shape[0] for t in all_t) > MAX_TRIANGLES:
                raise GltfError(
                    f"modèle trop détaillé (> {MAX_TRIANGLES} triangles) : simplifiez-le (Blender : Décimer)"
                )
    if not all_t:
        raise GltfError("aucun triangle dans la scène du fichier")
    vertices = np.vstack(all_v)
    if not np.all(np.isfinite(vertices)):
        raise GltfError("coordonnées non finies")
    return Mesh(vertices, np.vstack(all_t), np.vstack(all_c), sorted(notes))


def rotation(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    """Rotation autour de l'axe vertical (lacet) puis de l'axe horizontal (tangage)."""
    a, b = math.radians(yaw_deg), math.radians(pitch_deg)
    ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    out: np.ndarray = rx @ ry
    return out


LIGHT = np.array([-0.4, 0.6, 0.7]) / np.linalg.norm([-0.4, 0.6, 0.7])  # haut-gauche, vers l'avant


def project(
    mesh: Mesh, yaw_deg: float, pitch_deg: float, size: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Projection orthographique centrée : (polygones écran (M, 3, 2), couleurs ombrées (M, 4), ordre de
    dessin du plus lointain au plus proche). ``size`` = plus grande dimension du modèle à l'écran."""
    v = mesh.vertices - (mesh.vertices.min(axis=0) + mesh.vertices.max(axis=0)) / 2
    extent = float(np.max(np.linalg.norm(v, axis=1))) or 1.0
    v = v @ rotation(yaw_deg, pitch_deg).T * (size / 2 / extent)
    tri = v[mesh.triangles]  # (M, 3, 3)
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    lengths[lengths == 0] = 1.0
    normals /= lengths[:, None]
    normals[normals[:, 2] < 0] *= -1  # face visible : éclairage de la face tournée vers l'observateur
    light = 0.35 + 0.65 * np.clip(normals @ LIGHT, 0.0, 1.0)
    colors = mesh.colors.copy()
    colors[:, :3] *= light[:, None]
    screen = np.stack([tri[:, :, 0], -tri[:, :, 1]], axis=2)  # y écran vers le bas
    order = np.argsort(tri[:, :, 2].mean(axis=1), kind="stable")  # z croissant : du fond vers l'avant
    return screen, colors, order

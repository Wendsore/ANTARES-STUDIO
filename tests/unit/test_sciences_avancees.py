"""Histogrammes et barres, simulation à N corps, constantes et unités, morphing de formules, modèles glTF."""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np
import pytest

from antares_studio.domain.model import Asset, Canvas, Node, Project, Scene
from antares_studio.domain.validation import validate_project
from antares_studio.resources.templates import create_project
from antares_studio.science.data import histogram
from antares_studio.science.kepler import SimulationError
from antares_studio.science.nbody import (
    FIGURE_EIGHT_PERIOD,
    Body,
    binary_star,
    figure_eight,
    simulate_nbody,
)
from antares_studio.science.units import (
    CONSTANTS,
    SOURCES,
    UnitError,
    convert,
    format_number,
    format_quantity,
)
from antares_studio.timeline.evaluator import evaluate
from antares_studio.timeline.presets import apply_preset

CUBE_V = [
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
]  # fmt: skip
CUBE_I = [
    0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4,
    2, 3, 7, 2, 7, 6, 1, 2, 6, 1, 6, 5, 0, 4, 7, 0, 7, 3,
]  # fmt: skip


def gltf_cube(
    color=(0.2, 0.6, 1.0, 1.0), translation=(0.0, 0.0, 0.0), version: str = "2.0"
) -> tuple[dict, bytes]:  # type: ignore[no-untyped-def]
    """Document glTF minimal d'un cube (12 triangles) et son buffer binaire."""
    pos = b"".join(struct.pack("<3f", *v) for v in CUBE_V)
    idx = b"".join(struct.pack("<H", i) for i in CUBE_I)
    binary = pos + idx
    doc = {
        "asset": {"version": version},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "translation": list(translation)}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}],
        "materials": [{"pbrMetallicRoughness": {"baseColorFactor": list(color)}}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos)},
            {"buffer": 0, "byteOffset": len(pos), "byteLength": len(idx)},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 8,
                "type": "VEC3",
                "min": [-1, -1, -1],
                "max": [1, 1, 1],
            },
            {"bufferView": 1, "componentType": 5123, "count": 36, "type": "SCALAR"},
        ],
    }
    return doc, binary


def write_glb(path: Path, doc: dict, binary: bytes) -> Path:  # type: ignore[type-arg]
    js = json.dumps(doc).encode()
    js += b" " * (-len(js) % 4)
    binary += b"\0" * (-len(binary) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binary), 0x004E4942) + binary
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
    return path


# --- histogrammes -----------------------------------------------------------------------------------
def test_histogram_bins_cover_the_data_and_close_the_last_class() -> None:
    bins = histogram([0.0, 1.0, 2.0, 2.5, 10.0, math.nan], 5)
    assert [b.count for b in bins] == [2, 2, 0, 0, 1]  # 10 tombe dans la dernière classe (fermée)
    assert bins[0].left == 0.0 and bins[-1].right == 10.0
    assert sum(b.count for b in bins) == 5  # NaN ignoré
    assert histogram([3.0, 3.0], 4) == [histogram([3.0], 1)[0].__class__(2.5, 3.5, 2)]
    assert histogram([], 3) == []


def _chart_image(qapp, tmp_path: Path, chart_type: str):  # type: ignore[no-untyped-def]
    from antares_studio.rendering.qt_painter import render_state_to_image

    csv = tmp_path / "mesures.csv"
    csv.write_text("x (s);y (m)\n1;2\n2;4\n3;6\n4;8\n", encoding="utf-8")
    project = Project.create("G", Canvas(800, 600, 30, 1))
    scene = Scene.create("S", duration_frames=10)
    node = Node.create("chart", "C", position=[400.0, 300.0])
    from antares_studio.domain.kinds import spec_for

    node.params = spec_for("chart").default_params() | {
        "data_asset_id": "asset-00000000csv0",
        "x_column": "x",
        "y_column": "y",
        "chart_type": chart_type,
        "bins": 4,
    }
    node.style = spec_for("chart").default_style() | {"stroke": "#FF0000", "fill": "#000000"}
    scene.nodes.append(node)
    project.scenes.append(scene)
    project.assets.append(Asset(id="asset-00000000csv0", path="mesures.csv", kind="data"))
    assert validate_project(project) == []
    return render_state_to_image(
        evaluate(project, scene.id, 0), project.canvas, 800, 600, assets=lambda _i: csv
    )


def _red_pixels(img) -> int:  # type: ignore[no-untyped-def]
    count = 0
    for x in range(0, img.width(), 4):
        for y in range(0, img.height(), 4):
            c = img.pixelColor(x, y)
            count += c.red() > 200 and c.green() < 60 and c.blue() < 60
    return count


def test_bars_and_histogram_fill_areas_where_the_line_only_draws_a_stroke(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    line = _red_pixels(_chart_image(qapp, tmp_path, "line"))
    bars = _red_pixels(_chart_image(qapp, tmp_path, "bars"))
    hist = _red_pixels(_chart_image(qapp, tmp_path, "histogram"))
    assert bars > 5 * line and hist > 5 * line


def test_chart_type_is_validated() -> None:
    from antares_studio.domain.kinds import check_param_value, spec_for

    spec = next(p for p in spec_for("chart").params if p.name == "chart_type")
    assert check_param_value(spec, "bars") is None
    assert check_param_value(spec, "camembert") is not None


# --- N corps ------------------------------------------------------------------------------------
def test_figure_eight_returns_to_its_start_and_conserves_invariants() -> None:
    bodies = figure_eight()
    coarse = simulate_nbody(bodies, FIGURE_EIGHT_PERIOD / 2000, 2000)
    fine = simulate_nbody(bodies, FIGURE_EIGHT_PERIOD / 8000, 8000)
    gap = max(math.dist(a, b) for a, b in zip(fine.positions[0], fine.positions[-1], strict=True))
    assert gap < 1e-4  # orbite périodique : retour au point de départ après une période
    assert fine.energy_drift < 1e-6
    assert max(abs(c) for m in fine.momenta for c in m) < 1e-12
    # Verlet est d'ordre 2 : pas divisé par 4 → écart d'énergie divisé par ≈ 16
    assert 10 < coarse.energy_drift / fine.energy_drift < 25


def test_binary_star_follows_the_circular_solution() -> None:
    bodies, period = binary_star(0.5, 1.0)
    result = simulate_nbody(bodies, period / 4000, 2000)  # une demi-période
    (x1, y1), (x2, y2) = result.positions[-1]
    assert (x1, y1) == pytest.approx((-bodies[0].position[0], 0.0), abs=1e-5)
    assert (x2, y2) == pytest.approx((-bodies[1].position[0], 0.0), abs=1e-5)
    m1, m2 = bodies[0].mass, bodies[1].mass
    assert m1 * x1 + m2 * x2 == pytest.approx(0.0, abs=1e-12)  # centre de masse immobile


@pytest.mark.parametrize(
    ("bodies", "dt", "steps"),
    [
        ([Body("A", 1.0, (0.0, 0.0), (0.0, 0.0))], 0.1, 10),  # un seul corps
        ([Body("A", -1.0, (0.0, 0.0), (0.0, 0.0)), Body("B", 1.0, (1.0, 0.0), (0.0, 0.0))], 0.1, 10),
        ([Body("A", 1.0, (0.0, 0.0), (0.0, 0.0)), Body("B", 1.0, (0.0, 0.0), (0.0, 0.0))], 0.1, 10),
        ([Body("A", 1.0, (0.0, 0.0), (0.0, 0.0)), Body("B", 1.0, (1.0, 0.0), (0.0, 0.0))], 0.0, 10),
        ([Body("A", 1.0, (math.inf, 0.0), (0.0, 0.0)), Body("B", 1.0, (1.0, 0.0), (0.0, 0.0))], 0.1, 10),
    ],
)
def test_invalid_simulations_are_refused(bodies: list[Body], dt: float, steps: int) -> None:
    with pytest.raises((SimulationError, UnitError)):
        simulate_nbody(bodies, dt, steps)


@pytest.mark.parametrize("template", ["three_body", "binary_star"])
def test_simulation_templates_are_valid_and_documented(template: str) -> None:
    project = create_project("Sim", Canvas(), template, 10)
    assert validate_project(project) == []
    meta = project.scientific_metadata
    assert meta["representation"] == "simulation" and meta["parameters"]["method"] == "verlet"
    assert meta["parameters"]["energy_drift"] < 1e-4 and meta["sources"]
    scene = project.scenes[0]
    bodies = [n for n in scene.nodes if n.kind == "circle" and n.name != "Centre de masse"]
    first = evaluate(project, scene.id, 0).node(bodies[0].id).world
    later = evaluate(project, scene.id, 100).node(bodies[0].id).world
    assert first != later  # les corps bougent


# --- constantes et unités ---------------------------------------------------------------------------
def test_constants_are_sourced_and_numbers_are_written_the_french_way() -> None:
    assert all(c.source in SOURCES for c in CONSTANTS)
    assert format_number(149_597_870_700) == "1,496 × 10¹¹"
    assert format_number(0.000123, 3) == "1,23 × 10⁻⁴"
    assert format_number(1.5) == "1,5" and format_number(0) == "0" and format_number(-42.5) == "-42,5"
    assert format_number(9.99996e9) == "1 × 10¹⁰"  # arrondi qui change la puissance
    assert format_quantity(convert(1, "al", "km"), "km") == "9,461 × 10¹² km"
    with pytest.raises(UnitError):
        format_number(math.nan)


# --- morphing de formules ---------------------------------------------------------------------------
def test_morph_keeps_common_symbols_and_interpolates_the_box(qapp) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.rendering.formula_layout import formula_rect, layout_glyphs, morph_pairs

    params = {"text": "F = m a", "morph_to": r"F = G \frac{m M}{r^{2}}", "font_size": 40.0, "morph": 0.0}
    src, _ = layout_glyphs(params, params["text"])
    dst, dst_strokes = layout_glyphs(params, params["morph_to"])
    pairs, gone, new = morph_pairs(src, dst)
    assert [a.text for a, _b in pairs] == ["F", "=", "m"]
    assert [g.text for g in gone] == ["a"] and {g.text for g in new} == {"G", "M", "r", "2"}
    assert len(dst_strokes) == 1  # barre de fraction
    r0, r1 = formula_rect(params), formula_rect(params | {"morph": 1.0})
    mid = formula_rect(params | {"morph": 0.5})
    assert mid.width() == pytest.approx((r0.width() + r1.width()) / 2)
    assert formula_rect(params | {"morph_to": "", "morph": 0.5}) == r0  # sans cible : pas de morphing


def _formula_image(params: dict) -> bytes:  # type: ignore[type-arg]
    from PySide6.QtGui import QColor, QImage, QPainter, QPen

    from antares_studio.rendering.formula_layout import paint_formula

    img = QImage(600, 300, QImage.Format.Format_ARGB32)
    img.fill(QColor("#000000"))
    p = QPainter(img)
    p.translate(300, 150)
    paint_formula(p, params, QPen(QColor("#FFFFFF")), None)
    p.end()
    return bytes(img.constBits())


def test_morph_ends_match_the_plain_formulas(qapp) -> None:  # type: ignore[no-untyped-def]
    base = {"text": "E = m c^{2}", "font_size": 40.0}
    target = {"text": r"E = \frac{1}{2} m v^{2}", "font_size": 40.0}
    morph = base | {"morph_to": target["text"]}
    assert _formula_image(morph | {"morph": 0.0}) == _formula_image(base)
    assert _formula_image(morph | {"morph": 1.0}) == _formula_image(target)
    middle = _formula_image(morph | {"morph": 0.5})
    assert middle not in (_formula_image(base), _formula_image(target))


def test_morph_preset_animates_from_zero_to_one() -> None:
    node = Node.create("formula", "F")
    (track,) = apply_preset("morph", node, {"start_frame": 10, "duration_frames": 30})
    assert track.property == "params.morph"
    assert [(k.frame, k.value) for k in track.keyframes] == [(10, 0.0), (40, 1.0)]


# --- glTF ------------------------------------------------------------------------------------------
def test_glb_cube_is_read_with_transform_and_material(tmp_path: Path) -> None:
    from antares_studio.rendering.gltf import load_mesh

    doc, binary = gltf_cube(translation=(5.0, 0.0, 0.0))
    mesh = load_mesh(write_glb(tmp_path / "cube.glb", doc, binary))
    assert mesh.triangle_count == 12 and mesh.notes == []
    assert mesh.vertices[:, 0].min() == pytest.approx(4.0) and mesh.vertices[:, 0].max() == pytest.approx(6.0)
    assert np.allclose(mesh.colors[0], [0.2, 0.6, 1.0, 1.0])


def test_embedded_gltf_is_read_and_external_or_broken_files_are_refused(tmp_path: Path) -> None:
    import base64

    from antares_studio.rendering.gltf import GltfError, load_mesh

    doc, binary = gltf_cube()
    doc["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(binary).decode()
    (tmp_path / "cube.gltf").write_text(json.dumps(doc), encoding="utf-8")
    assert load_mesh(tmp_path / "cube.gltf").triangle_count == 12
    doc["buffers"][0]["uri"] = "cube.bin"
    (tmp_path / "ext.gltf").write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(GltfError, match=r"\.glb"):
        load_mesh(tmp_path / "ext.gltf")
    doc1, bin1 = gltf_cube(version="1.0")
    with pytest.raises(GltfError, match="version"):
        load_mesh(write_glb(tmp_path / "v1.glb", doc1, bin1))
    good = write_glb(tmp_path / "ok.glb", *gltf_cube())
    (tmp_path / "cut.glb").write_bytes(good.read_bytes()[:60])
    with pytest.raises(GltfError):
        load_mesh(tmp_path / "cut.glb")
    doc2, bin2 = gltf_cube()
    doc2["accessors"][1]["count"] = 400  # indices au-delà du buffer
    with pytest.raises(GltfError):
        load_mesh(write_glb(tmp_path / "bad.glb", doc2, bin2))
    (tmp_path / "texte.glb").write_text("pas un modèle", encoding="utf-8")
    with pytest.raises(GltfError):
        load_mesh(tmp_path / "texte.glb")


def test_model3d_node_draws_the_shaded_model_and_turns(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.domain.kinds import spec_for
    from antares_studio.rendering.qt_painter import render_state_to_image

    glb = write_glb(tmp_path / "cube.glb", *gltf_cube(color=(1.0, 0.0, 0.0, 1.0)))
    project = Project.create("M", Canvas(400, 400, 30, 1))
    scene = Scene.create("S", duration_frames=10)
    node = Node.create(
        "model3d", "Cube", position=[200.0, 200.0], params=spec_for("model3d").default_params()
    )
    node.params["model_asset_id"] = "asset-00000000glb0"
    node.params["size"] = 300.0
    scene.nodes.append(node)
    project.scenes.append(scene)
    project.assets.append(Asset(id="asset-00000000glb0", path="cube.glb", kind="model"))
    assert validate_project(project) == []

    def render(yaw: float) -> object:
        node.params["yaw_deg"] = yaw
        return render_state_to_image(
            evaluate(project, scene.id, 0), project.canvas, 400, 400, assets=lambda _i: glb
        )

    img = render(30.0)
    center = img.pixelColor(200, 200)  # type: ignore[attr-defined]
    assert center.red() > 80 and center.green() < 30 and center.blue() < 30  # rouge ombré
    corner = img.pixelColor(5, 5)  # type: ignore[attr-defined]
    assert corner.red() < 40  # fond hors du modèle
    assert bytes(render(30.0).constBits()) != bytes(render(60.0).constBits())  # type: ignore[attr-defined]
    missing = render_state_to_image(
        evaluate(project, scene.id, 0), project.canvas, 400, 400, assets=lambda _i: None
    )
    assert missing.pixelColor(200 - 150, 200).red() > 200  # cadre rouge « absent »

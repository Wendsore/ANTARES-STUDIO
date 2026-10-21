"""Phase 8 — CSV avec unités (diagnostics, sans exécution), graphique rendu, tracé progressif."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from antares_studio.domain.model import Canvas, Project, Scene
from antares_studio.persistence.schema import project_from_dict, project_to_dict
from antares_studio.rendering.qt_painter import ImageCache, chart_frame, render_state_to_image
from antares_studio.science.data import DataError, load_csv, nice_ticks, parse_csv, parse_header
from antares_studio.timeline.evaluator import evaluate
from antares_studio.timeline.presets import apply_preset
from tests.unit.helpers import make_node

CSV = "t (s);position [km];commentaire\n0;0,0;départ\n1;1,5;\n2;6,0;\n3;13,5;mesure\n4;24,0;\n"


def test_parse_header_units_and_separators() -> None:
    assert parse_header("t (s)") == ("t", "s")
    assert parse_header("position [km]") == ("position", "km")
    assert parse_header("  vitesse ") == ("vitesse", "")
    assert parse_header("") == ("colonne", "")
    t = parse_csv(CSV)
    assert [c.label for c in t.columns] == ["t (s)", "position (km)", "commentaire"]
    assert t.row_count == 5 and t.xy("t", "position")[2] == (2.0, 6.0)
    assert any("commentaire" in d for d in t.diagnostics)  # colonne texte signalée, pas refusée
    t2 = parse_csv("x,y\n1,2\n3,4\n")
    assert t2.xy("x", "y") == [(1.0, 2.0), (3.0, 4.0)]
    t3 = parse_csv("x\ty\n1\t2\n")
    assert t3.xy("x", "y") == [(1.0, 2.0)]


def test_csv_diagnostics_and_refusals(tmp_path: Path) -> None:
    t = parse_csv("x;y\n1;2\n3;abc\n4\n")
    assert math.isnan(t.column("y").values[1])  # type: ignore[union-attr]
    assert any("ligne 4" in d for d in t.diagnostics) and any("non numérique" in d for d in t.diagnostics)
    with pytest.raises(DataError, match="aucune colonne numérique"):
        parse_csv("a;b\nx;y\n")
    with pytest.raises(DataError, match="en-tête"):
        parse_csv("seulement une ligne\n")
    p = tmp_path / "latin.csv"
    p.write_bytes("température (°C);t (s)\n21,5;0\n".encode("cp1252"))
    assert load_csv(p).columns[0].label == "température (°C)"
    # contenu « exécutable » : simple texte, jamais interprété
    t4 = parse_csv("x;y\n1;2\n=cmd|' /C calc'!A0;3\n")
    assert t4.xy("x", "y") == [(1.0, 2.0)]


def test_nice_ticks_cover_range() -> None:
    assert nice_ticks(0, 10) == [0, 2, 4, 6, 8, 10]
    assert nice_ticks(0.13, 0.87)[0] >= 0.13 and nice_ticks(0.13, 0.87)[-1] <= 0.87
    assert nice_ticks(float("nan"), 1) == []


def _chart_project(tmp_path: Path) -> tuple[Project, Scene, object, Path]:
    from antares_studio.domain.model import Asset

    data = tmp_path / "mesures.csv"
    data.write_text(CSV, encoding="utf-8")
    project = Project.create("Graphique", Canvas(1920, 1080, 30, 1))
    scene = Scene.create("S", duration_frames=60)
    project.scenes.append(scene)
    project.assets.append(Asset(id="asset-000000000abc", path="assets/mesures.csv", kind="data"))
    chart = make_node("chart", "Courbe", position=[960.0, 540.0])
    chart.params.update({"data_asset_id": "asset-000000000abc", "x_column": "t", "y_column": "position"})
    scene.nodes.append(chart)
    return project, scene, chart, data


def test_chart_renders_axes_units_and_progressive_curve(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    project, scene, chart, data = _chart_project(tmp_path)
    scene.tracks += apply_preset("trace", chart, {"duration_frames": 60})  # type: ignore[arg-type]
    assert project_from_dict(project_to_dict(project)).scenes[0].nodes[0].kind == "chart"
    cache = ImageCache()

    def resolve(asset_id: str) -> Path | None:
        return data if asset_id == "asset-000000000abc" else None

    def curve_pixels(frame: int) -> int:
        st = evaluate(project, scene.id, frame)
        img = render_state_to_image(st, project.canvas, 1920, 1080, resolve, cache)
        f = chart_frame(chart.params)  # type: ignore[attr-defined]
        count = 0
        for x in range(int(960 + f.left()), int(960 + f.right()), 2):
            for y in range(int(540 + f.top()), int(540 + f.bottom()), 2):
                c = img.pixelColor(x, y)
                if c.blue() > 200 and c.red() < 140:  # couleur de la courbe #4FC3F7
                    count += 1
        return count

    none, half, full = curve_pixels(0), curve_pixels(30), curve_pixels(60)
    assert none == 0 and 0 < half < full
    # données absentes : cadre explicite, pas d'exception
    st = evaluate(project, scene.id, 60)
    img = render_state_to_image(st, project.canvas, 1920, 1080, lambda _a: None, cache)
    assert img.width() == 1920
    # colonnes inconnues : idem
    chart.params["y_column"] = "inconnue"  # type: ignore[attr-defined]
    project.scenes[0].nodes[0] = chart  # type: ignore[index]
    img2 = render_state_to_image(evaluate(project, scene.id, 60), project.canvas, 1920, 1080, resolve, cache)
    assert img2.width() == 1920

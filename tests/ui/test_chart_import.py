"""Phase 8 (interface) — import CSV en graphique, colonnes proposées par l'inspecteur, export."""

from __future__ import annotations

from pathlib import Path

import pytest

from antares_studio.app.main_window import MainWindow
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.exporter import export_video
from antares_studio.rendering.plan import build_render_plan

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot, tmp_path: Path):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    w.document.save(tmp_path / "Graphe.antares")
    return w


def test_import_csv_creates_chart_with_columns_and_inspector_choices(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    src = tmp_path / "chute.csv"
    src.write_text("t (s);h (m)\n0;0\n1;4,9\n2;19,6\n3;44,1\n", encoding="utf-8")
    node = window.add_chart_from_csv(src)
    assert node is not None and node.kind == "chart"
    assert node.params["x_column"] == "t" and node.params["y_column"] == "h"
    assert (window.document.root / "assets" / "chute.csv").is_file()
    qtbot.wait(30)
    combo = window.inspector._editors["params.y_column"]
    assert [combo.itemText(i) for i in range(combo.count())] == ["t", "h"]
    assert window.library.assets.topLevelItemCount() == 1
    # import refusé : fichier sans colonne numérique, message explicite, pas de nœud
    bad = tmp_path / "texte.csv"
    bad.write_text("a;b\nx;y\n", encoding="utf-8")
    from PySide6.QtWidgets import QMessageBox

    seen: list[str] = []
    orig = QMessageBox.critical
    QMessageBox.critical = staticmethod(lambda *a, **k: seen.append(str(a[2])))  # type: ignore[method-assign,assignment]
    try:
        assert window.add_chart_from_csv(bad) is None
    finally:
        QMessageBox.critical = orig  # type: ignore[method-assign]
    assert seen and "numérique" in seen[0]


@pytest.mark.render
@pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg absent")
def test_chart_export_uses_project_asset(window, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    src = tmp_path / "serie.csv"
    src.write_text("x;y\n0;1\n1;3\n2;2\n", encoding="utf-8")
    window.add_chart_from_csv(src)
    scene = window.document.scene
    scene.duration_frames = 5
    window.document.version += 1
    out = tmp_path / "graphe.mp4"
    plan = build_render_plan(window.document.project, scene.id, "draft_720p", str(out))
    result = export_video(window.document.project, plan, assets=window.document.resolve_asset)
    assert result.probe.nb_frames == 5 and out.is_file()

"""Interface des outils scientifiques : constantes et unités, modèle 3D, représentation des graphiques."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QComboBox, QMessageBox

from antares_studio.app.library_dock import CATEGORIES
from antares_studio.app.main_window import MainWindow
from antares_studio.app.units_dialog import UnitsDialog, parse_value
from antares_studio.science.units import UnitError
from tests.unit.test_sciences_avancees import gltf_cube, write_glb

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot, tmp_path: Path):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    w.document.save(tmp_path / "Sciences.antares")
    return w


def test_units_dialog_converts_refuses_and_inserts_one_undoable_text(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    dlg = UnitsDialog(window)
    qtbot.addWidget(dlg)
    assert dlg.table.rowCount() >= 8
    dlg.value.setText("1")
    dlg.from_unit.setCurrentIndex(dlg.from_unit.findData("au"))
    dlg.to_unit.setCurrentIndex(dlg.to_unit.findData("km"))
    assert dlg.result_label.text() == "1,496 × 10⁸ km"
    # seules les unités de même grandeur sont proposées : pas de conversion longueur → durée
    assert dlg.to_unit.findData("s") == -1
    dlg.value.setText("douze")
    assert (
        dlg.result_label.text() == "—" and not dlg.insert_btn.isEnabled() and "illisible" in dlg.error.text()
    )
    dlg.value.setText("1,5")
    dlg.from_unit.setCurrentIndex(dlg.from_unit.findData("ly"))
    dlg.to_unit.setCurrentIndex(dlg.to_unit.findData("pc"))
    dlg.insert_btn.click()
    assert dlg.inserted_text == "1,5 ly = 0,4599 pc"
    nodes_before = len(window.document.scene.nodes)
    node = window.insert_physical_value(dlg)
    assert node is not None and node.params["text"] == "1,5 ly = 0,4599 pc"
    window.document.undo.undo()  # une seule étape : l'objet disparaît
    assert len(window.document.scene.nodes) == nodes_before
    assert parse_value("3 000,5") == 3000.5 and parse_value("1.5e8") == 1.5e8
    with pytest.raises(UnitError):
        parse_value("")
    dlg.table.selectRow(1)  # G : valeur sourcée insérée telle quelle
    assert dlg.text_to_insert().startswith("G = 6,674 × 10⁻¹¹")


def test_import_glb_adds_a_model_with_inspector_choice(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    glb = write_glb(tmp_path / "cube.glb", *gltf_cube())
    node = window.add_model_from_file(glb)
    assert node is not None and node.kind == "model3d" and node.name == "Modèle cube"
    assert (window.document.root / "assets" / "cube.glb").is_file()
    asset = window.document.project.asset(node.params["model_asset_id"])
    assert asset is not None and asset.kind == "model"
    assert "12 triangles" in window.statusBar().currentMessage()
    qtbot.wait(30)
    combo = window.inspector._editors["params.model_asset_id"]
    assert isinstance(combo, QComboBox) and combo.currentData() == asset.id
    window.document.undo.undo()  # création et choix du modèle : une seule étape
    assert window.document.scene.find_node(node.id) is None
    ext = tmp_path / "externe.gltf"
    doc, _bin = gltf_cube()
    doc["buffers"][0]["uri"] = "cube.bin"
    import json

    ext.write_text(json.dumps(doc), encoding="utf-8")
    seen: list[str] = []
    orig = QMessageBox.critical
    QMessageBox.critical = staticmethod(lambda *a, **k: seen.append(str(a[2])))  # type: ignore[method-assign,assignment]
    try:
        assert window.add_model_from_file(ext) is None
    finally:
        QMessageBox.critical = orig  # type: ignore[method-assign]
    assert seen and ".glb" in seen[0]
    assert "model3d" in CATEGORIES["3D"]


def test_chart_representation_is_a_choice_in_the_inspector(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    node = window.add_node_of_kind("chart")
    qtbot.wait(30)
    combo = window.inspector._editors["params.chart_type"]
    assert isinstance(combo, QComboBox)
    assert [combo.itemData(i) for i in range(combo.count())] == ["line", "bars", "histogram"]
    combo.setCurrentIndex(2)
    assert window.document.scene.find_node(node.id).params["chart_type"] == "histogram"


def test_simulation_templates_are_offered(window) -> None:  # type: ignore[no-untyped-def]
    window.add_template_scene("three_body")
    scene = window.document.scene
    assert any(n.name == "Centre de masse" for n in scene.nodes)
    assert window.document.project.scientific_metadata["representation"] == "simulation"
    labels = [window.library.templates.item(i).text() for i in range(window.library.templates.count())]
    assert any("Trois corps" in t for t in labels) and any("Étoile double" in t for t in labels)


def test_presets_skip_objects_they_do_not_apply_to(window) -> None:  # type: ignore[no-untyped-def]
    formula = window.add_node_of_kind("formula")
    circle = window.add_node_of_kind("circle")
    window.document.set_selection([formula.id, circle.id])
    skipped = window.apply_preset_values("morph", {"start_frame": 0, "duration_frames": 30})
    assert skipped == [circle.name]
    scene = window.document.scene
    assert [t.property for t in scene.tracks_for(formula.id)] == ["params.morph"]
    assert scene.tracks_for(circle.id) == []
    assert "ne s'applique pas" in window.statusBar().currentMessage()
    from antares_studio.domain.validation import validate_project

    assert validate_project(window.document.project) == []

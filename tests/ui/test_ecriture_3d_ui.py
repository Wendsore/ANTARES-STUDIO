"""Phase 12 dans l'éditeur : solides et grilles de la Bibliothèque, styles d'écriture, polices, décor."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QComboBox, QScrollArea

from antares_studio.app.library_dock import CATEGORIES, ID_ROLE
from antares_studio.app.main_window import MainWindow
from antares_studio.domain.kinds import SOLID_SHAPES
from antares_studio.domain.text_styles import TEXT_STYLES
from antares_studio.resources.fonts import BUNDLED_FONTS

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    return w


def _item(lst, ident: str):  # type: ignore[no-untyped-def]
    return next(lst.item(i) for i in range(lst.count()) if lst.item(i).data(ID_ROLE) == ident)


def test_library_lists_each_solid_and_grid(window) -> None:  # type: ignore[no-untyped-def]
    assert CATEGORIES["Solides 3D"] == tuple(f"solid3d:{s}" for s, _l in SOLID_SHAPES)
    lib = window.library
    for shape, label in SOLID_SHAPES:
        item = _item(lib.objects, f"solid3d:{shape}")
        assert item.text() == label and not item.icon().isNull()
    lib.objects.itemDoubleClicked.emit(_item(lib.objects, "solid3d:sphere"))
    node = window.document.selected_nodes[0]
    assert node.kind == "solid3d" and node.params["shape"] == "sphere" and node.name == "Sphère 1"
    lib.objects.itemDoubleClicked.emit(_item(lib.objects, "grid:spacetime"))
    grid = window.document.selected_nodes[0]
    assert grid.kind == "grid" and grid.params["perspective"] is True and grid.params["warp"] == "gravity"
    lib.search.setText("cube")
    visible = [
        lib.objects.item(i).text() for i in range(lib.objects.count()) if not lib.objects.item(i).isHidden()
    ]
    assert "Cube" in visible and "Sphère" not in visible


def test_text_style_from_library_is_one_undo_step(window) -> None:  # type: ignore[no-untyped-def]
    text = window.add_node_of_kind("text")
    formula = window.add_node_of_kind("formula")
    circle = window.add_node_of_kind("circle")
    window.document.set_selection([text.id, formula.id, circle.id])
    for key in TEXT_STYLES:
        assert _item(window.library.effects, f"écriture:{key}") is not None
    window.library.effects.itemDoubleClicked.emit(_item(window.library.effects, "écriture:chalk"))
    assert text.params["font_family"] == "Kalam" and text.params["write_style"] == "chalk"
    assert formula.style["fx_chalk"] == 0.6 and "fx_chalk" not in circle.style  # le cercle n'est pas un texte
    window.document.undo.undo()
    assert text.params["font_family"] == "DejaVu Sans" and text.style.get("fx_chalk", 0.0) == 0.0


def test_write_preset_on_text_and_skip_on_circle(window) -> None:  # type: ignore[no-untyped-def]
    text = window.add_node_of_kind("text")
    circle = window.add_node_of_kind("circle")
    window.document.set_selection([text.id, circle.id])
    skipped = window.apply_preset_values("write", {"start_frame": 0, "duration_frames": 30})
    assert skipped == [circle.name]
    assert window.document.scene.track_for(text.id, "params.write") is not None


def test_inspector_font_list_starts_with_bundled_fonts(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    text = window.add_node_of_kind("text")
    window.document.set_selection([text.id])
    window.inspector.rebuild()
    combo = window.inspector.findChild(QComboBox, "font_family")
    assert combo is not None and combo.isEditable()
    assert [combo.itemData(i) for i in range(len(BUNDLED_FONTS))] == [f.family for f in BUNDLED_FONTS]
    combo.setCurrentIndex(combo.findData("Caveat"))
    combo.textActivated.emit(combo.currentText())
    assert text.params["font_family"] == "Caveat"
    area = window.inspector.findChild(QScrollArea)
    qtbot.wait(50)
    assert area is not None and area.horizontalScrollBar().maximum() == 0  # libellés longs élidés


def test_scene_backdrop_from_inspector(window) -> None:  # type: ignore[no-untyped-def]
    window.document.set_selection([])
    window.inspector.rebuild()
    combo = window.inspector.findChild(QComboBox, "scene_backdrop")
    assert combo is not None
    combo.setCurrentIndex(combo.findData("chalkboard_black"))
    assert window.document.scene.backdrop == "chalkboard_black"
    window.document.undo.undo()
    assert window.document.scene.backdrop == ""


def test_new_templates_in_library(window) -> None:  # type: ignore[no-untyped-def]
    for tid in ("chalkboard", "linear_map", "curved_spacetime", "solids"):
        assert _item(window.library.templates, tid) is not None
    window.add_template_scene("chalkboard")
    assert window.document.scene.backdrop == "chalkboard_black"

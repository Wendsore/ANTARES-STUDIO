"""Interpolation dans la Timeline, éditeur de courbe, édition multiple et annulation groupée."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from antares_studio.app.curve_editor import CURVE_PRESETS, CurveEditorDialog
from antares_studio.app.main_window import MainWindow
from antares_studio.domain.commands import SetKeyframe
from antares_studio.timeline.evaluator import evaluate

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    return w


def _animated_circle(window):  # type: ignore[no-untyped-def]
    node = window.add_node_of_kind("circle")
    scene = window.document.scene
    window.document.push(SetKeyframe(scene.id, node.id, "position.x", 0, 100.0))
    window.document.push(SetKeyframe(scene.id, node.id, "position.x", 30, 400.0))
    return node, scene


def test_easing_combo_follows_selected_key_and_changes_motion(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    node, scene = _animated_circle(window)
    tl = window.timeline
    assert not tl.easing_combo.isEnabled()  # aucune clé sélectionnée
    linear_mid = evaluate(window.document.project, scene.id, 15).node(node.id).position[0]
    tl.view._select_key((node.id, "position.x", 0))
    assert tl.easing_combo.isEnabled() and tl.easing_combo.currentData() == "linear"
    tl.easing_combo.setCurrentIndex(tl.easing_combo.findData("ease_in"))
    tl.easing_combo.activated.emit(tl.easing_combo.currentIndex())
    kf = scene.track_for(node.id, "position.x").keyframes[0]
    assert kf.easing == "ease_in"
    eased_mid = evaluate(window.document.project, scene.id, 15).node(node.id).position[0]
    assert linear_mid == pytest.approx(250.0) and eased_mid < 200.0  # accélération : en retard à mi-course
    assert window.document.undo.undo_label == "Modifier l'interpolation"
    window.document.undo.undo()
    assert kf.easing == "linear" and tl.easing_combo.currentData() == "linear"


def test_bezier_choice_opens_curve_editor_and_stores_points(window, qtbot, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    node, scene = _animated_circle(window)
    tl = window.timeline
    tl.view._select_key((node.id, "position.x", 0))
    monkeypatch.setattr(CurveEditorDialog, "exec", lambda self: CurveEditorDialog.DialogCode.Accepted)
    monkeypatch.setattr(CurveEditorDialog, "bezier", lambda self: [0.34, 1.56, 0.64, 1.0])
    assert tl.view.set_selected_easing("bezier")
    kf = scene.track_for(node.id, "position.x").keyframes[0]
    assert (kf.easing, kf.bezier) == ("bezier", [0.34, 1.56, 0.64, 1.0])
    # « élan » : l'objet dépasse sa cible avant la fin du segment
    xs = [evaluate(window.document.project, scene.id, f).node(node.id).position[0] for f in range(31)]
    assert max(xs) > 400.0
    monkeypatch.setattr(CurveEditorDialog, "exec", lambda self: CurveEditorDialog.DialogCode.Rejected)
    tl.view._select_key((node.id, "position.x", 0))
    assert not tl.view.set_selected_easing("bezier")  # annulé : rien ne change
    assert kf.bezier == [0.34, 1.56, 0.64, 1.0]


def test_curve_editor_handles_presets_and_spins(qtbot) -> None:  # type: ignore[no-untyped-def]
    dlg = CurveEditorDialog([0.1, 0.2, 0.3, 0.4])
    qtbot.addWidget(dlg)
    dlg.show()
    assert dlg.bezier() == [0.1, 0.2, 0.3, 0.4]
    dlg.set_points(list(CURVE_PRESETS["Accélération"]))
    assert dlg.bezier() == [0.42, 0.0, 1.0, 1.0] and dlg.spins[0].value() == pytest.approx(0.42)
    dlg.spins[3].setValue(0.5)
    assert dlg.bezier()[3] == 0.5
    # glisser la première poignée en haut à gauche du graphe
    view = dlg.view
    start = view.to_px(0.42, 0.0).toPoint()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view, view.to_px(0.2, 0.9).toPoint())
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=view.to_px(0.2, 0.9).toPoint())
    x1, y1 = dlg.bezier()[:2]
    assert x1 == pytest.approx(0.2, abs=0.02) and y1 == pytest.approx(0.9, abs=0.03)
    assert dlg.spins[1].value() == pytest.approx(y1)
    dlg._start_preview()
    qtbot.wait(80)
    assert view.preview_u is not None


def test_multi_selection_edits_common_properties_in_one_step(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    a = window.add_node_of_kind("circle")
    b = window.add_node_of_kind("rect")
    t = window.add_node_of_kind("text")
    window.document.set_selection([a.id, b.id])
    editors = window.inspector._editors
    assert {"opacity", "rotation_deg", "style.fill", "style.stroke_width"} <= set(editors)
    assert "params.radius" not in editors and "position.x" not in editors  # propres à un seul type
    editors["style.fill"].set_value("#FF0000")
    for cb in editors["style.fill"].changed:
        cb("#FF0000")
    assert a.style["fill"] == b.style["fill"] == "#FF0000"
    editors["opacity"].setValue(0.4)
    assert a.opacity == b.opacity == pytest.approx(0.4)
    assert window.document.undo.undo_label == "Modifier 2 objets"
    window.document.undo.undo()
    assert a.opacity == b.opacity == 1.0 and a.style["fill"] == "#FF0000"
    # cercle + texte : « Remplissage » et « Couleur » ont le même nom interne (fill) et le même type
    window.document.set_selection([a.id, t.id])
    assert "style.fill" in window.inspector._editors
    window.document.set_node_property(b.id, "rotation_deg", 30.0)
    window.document.set_selection([a.id, b.id])
    assert window.inspector._mixed_labels["rotation_deg"].text() == "≠"


def test_group_and_ungroup_are_single_undo_steps(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    a = window.add_node_of_kind("circle")
    b = window.add_node_of_kind("star")
    scene = window.document.scene
    before = len(scene.nodes)
    window.document.set_selection([a.id, b.id])
    window.group_selection()
    assert len(scene.nodes) == before + 1 and a.parent_id is not None
    window.document.undo.undo()  # un seul Ctrl+Z défait tout le regroupement
    assert len(scene.nodes) == before and a.parent_id is None and b.parent_id is None
    window.document.set_selection([a.id, b.id])
    window.duplicate_selection()
    assert len(scene.nodes) == before + 2
    window.document.undo.undo()
    assert len(scene.nodes) == before
    window.document.set_selection([a.id, b.id])
    window.delete_selection()
    assert len(scene.nodes) == before - 2
    window.document.undo.undo()
    assert len(scene.nodes) == before


def test_timeline_key_menu_lists_every_interpolation(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    node, scene = _animated_circle(window)
    tl = window.timeline
    tl.view.rebuild_rows()
    row = next(i for i, r in enumerate(tl.view.rows) if r.track is not None)
    key = tl.view._key_at(QPointF(tl.view.frame_to_x(30), 26 + row * 22 + 11))
    assert key == (node.id, "position.x", 30)  # le losange est bien trouvé sous la souris
    menu = tl.view.keyframe_menu(key)
    texts = [a.text() for a in menu.actions()]
    assert "Linéaire" in texts and "Courbe personnalisée…" in texts and "Supprimer l'image clé" in texts
    assert tl.view.selected_key == key
    step = next(a for a in menu.actions() if a.text().startswith("Palier"))
    step.trigger()
    assert scene.track_for(node.id, "position.x").keyframes[1].easing == "step"
    next(a for a in menu.actions() if a.text() == "Supprimer l'image clé").trigger()
    assert len(scene.track_for(node.id, "position.x").keyframes) == 1

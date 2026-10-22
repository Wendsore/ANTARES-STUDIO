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


# --- presse-papiers, aligner, guides -------------------------------------------------------------
def _png(path, color=(200, 40, 40)) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtGui import QColor, QImage

    img = QImage(16, 16, QImage.Format.Format_RGB32)
    img.fill(QColor(*color))
    assert img.save(str(path))


def test_copy_paste_in_scene_and_cut_is_one_step(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    a = window.add_node_of_kind("circle")
    scene = window.document.scene
    window.document.push(SetKeyframe(scene.id, a.id, "opacity", 0, 0.0))
    window.document.set_selection([a.id])
    assert window.act_copy.isEnabled() and window.copy_selection()
    before = len(scene.nodes)
    roots = window.paste()
    assert len(roots) == 1 and len(scene.nodes) == before + 1
    pasted = scene.node(roots[0])
    assert pasted.id != a.id and pasted.position == [a.position[0] + 20, a.position[1] + 20]
    assert scene.track_for(pasted.id, "opacity") is not None
    assert window.document.selection == roots and window.document.undo.undo_label == "Coller"
    second = window.paste()  # deuxième collage : décalé une fois de plus
    assert scene.node(second[0]).position == [a.position[0] + 40, a.position[1] + 40]
    window.document.set_selection([a.id])
    window.cut_selection()
    assert scene.find_node(a.id) is None
    window.document.undo.undo()  # un seul Ctrl+Z restaure l'objet coupé
    assert scene.find_node(a.id) is not None


def test_paste_rejects_foreign_clipboard(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtWidgets import QApplication

    QApplication.clipboard().setText("du texte ordinaire")
    assert window.paste() == []
    assert "ne contient pas" in window.statusBar().currentMessage()


def test_paste_into_another_project_copies_image_file(window, qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.app.document import ProjectDocument
    from antares_studio.domain.model import Canvas
    from antares_studio.resources.assets import import_asset
    from antares_studio.resources.templates import create_project

    window.document.save(tmp_path / "Source.antares")
    _png(tmp_path / "terre.png")
    asset = import_asset(window.document, tmp_path / "terre.png", kind="image")
    from antares_studio.domain.commands import SetAssetLicense
    from antares_studio.domain.model import AssetLicense

    window.document.push(SetAssetLicense(asset.id, AssetLicense(author="Moi", license="CC-BY-4.0")))
    img = window.add_node_of_kind("image")
    window.document.set_node_property(img.id, "params.asset_id", asset.id)
    window.document.set_selection([img.id])
    assert window.copy_selection()
    window.document.undo.mark_clean()
    target = ProjectDocument(create_project("Cible", Canvas(), "", 10))
    target.save(tmp_path / "Cible.antares")
    window._set_document(target)
    roots = window.paste()
    node = target.scene.node(roots[0])
    new_asset = target.project.asset(node.params["asset_id"])
    assert new_asset is not None and new_asset.id != "" and new_asset.sha256 == asset.sha256
    assert (tmp_path / "Cible.antares" / new_asset.path).is_file()  # fichier recopié dans le projet cible
    assert new_asset.license.author == "Moi" and new_asset.license.license == "CC-BY-4.0"


def test_align_and_distribute_from_menu(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    a, b, c = (window.add_node_of_kind("rect") for _ in range(3))
    for n, (x, y) in zip((a, b, c), ((300.0, 200.0), (900.0, 500.0), (1500.0, 260.0)), strict=True):
        window.document.set_node_properties(n.id, {"position.x": x, "position.y": y})
    window.document.set_selection([a.id, b.id, c.id])
    assert window.act_distribute_h.isEnabled()
    window.align_actions["top"].trigger()
    assert a.position[1] == b.position[1] == c.position[1] == pytest.approx(200.0)
    assert window.document.undo.undo_label == "Aligner en haut"
    window.document.set_node_properties(b.id, {"position.x": 500.0})
    window.distribute_selection("x")
    assert b.position[0] == pytest.approx(900.0)  # milieu exact entre 300 et 1500 (largeurs égales)
    window.document.set_selection([a.id])
    window.align_selection("hcenter")  # objet seul : centré sur le canevas
    assert a.position[0] == pytest.approx(960.0)


def test_drag_snaps_to_canvas_center_with_guides_and_ctrl_disables(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    canvas = window.canvas
    window.resize(1400, 860)
    canvas.fit_to_view()
    node = window.add_node_of_kind("circle")  # rayon 80 : boîte de 160 px
    window.document.set_node_properties(node.id, {"position.x": 600.0, "position.y": 300.0})
    qtbot.wait(20)
    start = canvas.canvas_to_widget(QPointF(600, 300)).toPoint()
    # 357 px canevas vers la droite : le centre arrive à 957, à 3 px du centre du canevas (960)
    end = canvas.canvas_to_widget(QPointF(957, 300)).toPoint()
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(canvas, start + (end - start) / 2)
    QTest.mouseMove(canvas, end)
    assert canvas.guides and any(g.axis == "x" and g.value == pytest.approx(960.0) for g in canvas.guides)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
    assert node.position[0] == pytest.approx(960.0) and not canvas.guides
    # Ctrl maintenu : aucune aimantation, l'objet reste où on le lâche
    window.document.set_node_properties(node.id, {"position.x": 600.0})
    qtbot.wait(20)
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, start)
    QTest.mouseMove(canvas, start + (end - start) / 2)
    canvas._apply_drag(QPointF(957, 300), Qt.KeyboardModifier.ControlModifier)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, end)
    assert node.position[0] == pytest.approx(957.0, abs=1.5) and node.position[0] != pytest.approx(960.0)
    window.act_guides.trigger()  # désactivés depuis le menu Affichage
    assert canvas.smart_guides is False

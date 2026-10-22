"""Repères de Timeline, calage d'une animation, transitions de scène et caméra dans l'interface."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from antares_studio.app.main_window import MainWindow
from antares_studio.app.preset_dialog import PresetDialog, sync_targets
from antares_studio.domain.commands import AddSubtitle
from antares_studio.domain.model import Subtitle

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    return w


def test_markers_add_jump_rename_move_and_delete(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    doc = window.document
    scene = doc.scene
    doc.set_frame(30)
    first = window.add_marker()
    doc.set_frame(90)
    QTest.keyClick(window, Qt.Key.Key_M)  # raccourci clavier
    assert [m.frame for m in scene.sorted_markers()] == [30, 90]
    assert window.add_marker() is scene.sorted_markers()[1]  # pas de doublon à la même image
    doc.set_frame(0)
    assert window.jump_marker(1) and doc.frame == 30
    QTest.keyClick(window, Qt.Key.Key_BracketRight)
    assert doc.frame == 90
    assert not window.jump_marker(1)  # pas de repère après le dernier
    assert window.jump_marker(-1) and doc.frame == 30
    view = window.timeline.view
    view.rename_marker(first, "Éclipse totale")
    assert first.label == "Éclipse totale"
    assert view.marker_at(QPointF(view.frame_to_x(30) + 3, 12)) is first
    assert view.marker_at(QPointF(view.frame_to_x(30) + 3, 60)) is None  # hors de la règle
    start = QPointF(view.frame_to_x(30) + 2, 18).toPoint()
    end = QPointF(view.frame_to_x(45) + 2, 18).toPoint()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view, end)
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=end)
    assert first.frame == 45 and doc.frame == 45 and doc.undo.undo_label == "Déplacer un repère"
    menu = view.marker_menu(first)
    next(a for a in menu.actions() if a.text() == "Supprimer le repère").trigger()
    assert [m.frame for m in scene.markers] == [90]
    doc.undo.undo()
    assert len(scene.markers) == 2


def test_preset_can_be_synced_on_marker_subtitle_and_audio(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    doc = window.document
    scene = doc.scene
    node = window.add_node_of_kind("circle")
    doc.set_frame(60)
    window.add_marker("Arrivée")
    doc.set_frame(150)
    window.add_marker("Départ")
    doc.push(AddSubtitle(scene.id, Subtitle.create(200, 260, "La Lune passe devant le Soleil")))
    labels = [label for label, _span in sync_targets(doc)]
    assert labels[0].startswith("Repère « Arrivée »") and labels[2].startswith("Sous-titre « La Lune")
    dlg = PresetDialog("appear", doc, node, window)
    qtbot.addWidget(dlg)
    dlg.sync.setCurrentIndex(1)  # repère Arrivée : jusqu'au repère suivant
    assert (dlg.values()["start_frame"], dlg.values()["duration_frames"]) == (60, 90)
    dlg.sync.setCurrentIndex(3)  # sous-titre : sa plage exacte
    assert (dlg.values()["start_frame"], dlg.values()["duration_frames"]) == (200, 60)
    dlg.sync.setCurrentIndex(2)  # dernier repère : la durée saisie reste
    assert (dlg.values()["start_frame"], dlg.values()["duration_frames"]) == (150, 60)


def test_scene_transition_is_set_from_inspector_and_previewed(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtWidgets import QComboBox, QSpinBox

    doc = window.document
    window.add_template_scene("intro")
    second = doc.scene
    doc.set_selection([])
    combo = window.inspector.findChild(QComboBox, "scene_transition")
    spin = window.inspector.findChild(QSpinBox, "scene_transition_duration")
    assert combo is not None and spin is not None and not spin.isEnabled()
    combo.setCurrentIndex(combo.findData("slide_left"))
    assert second.transition.kind == "slide_left" and second.transition.duration_frames == 15
    window.inspector.rebuild()
    spin = window.inspector.findChild(QSpinBox, "scene_transition_duration")
    spin.setValue(24)
    spin.editingFinished.emit()
    assert second.transition.duration_frames == 24
    doc.set_frame(5)
    window.canvas.repaint()  # la transition passe par le même moteur que l'export (sans erreur)
    assert window.canvas._frames is not None
    doc.undo.undo()
    assert second.transition.duration_frames == 15


def test_camera_object_frames_view_and_editing_follows_it(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    doc = window.document
    circle = window.add_node_of_kind("circle")
    doc.set_node_properties(circle.id, {"position.x": 1200.0, "position.y": 400.0})
    cam = window.add_node_of_kind("camera")
    c = doc.project.canvas
    assert cam is not None and cam.position == [c.width / 2, c.height / 2]
    doc.set_node_property(cam.id, "params.zoom", 2.0)
    doc.set_node_properties(cam.id, {"position.x": 1200.0, "position.y": 400.0})
    st = doc.state()
    assert st.camera_id == cam.id and st.node(circle.id).world[4] == pytest.approx(960.0)
    # glisser l'objet de 100 px à l'écran (canevas) : avec un zoom 2, il bouge de 50 px dans la scène
    doc.set_selection([circle.id])
    window.canvas.fit_to_view()
    canvas = window.canvas
    start = canvas.canvas_to_widget(QPointF(960, 540)).toPoint()
    end = canvas.canvas_to_widget(QPointF(1060, 540)).toPoint()
    window.act_guides.setChecked(False)
    window.toggle_guides(False)
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(canvas, canvas.canvas_to_widget(QPointF(1010, 540)).toPoint())
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=end)
    assert circle.position[0] == pytest.approx(1250.0, abs=2.0)
    # vue de toute la scène : la caméra ne s'applique plus dans l'éditeur, le cadre est dessiné
    window.act_camera_view.trigger()
    assert doc.preview_camera is False and doc.state().camera_id is None
    canvas.repaint()
    added = window.add_node_of_kind("star")
    assert added is not None
    window.act_camera_view.trigger()
    # vue caméra : un nouvel objet apparaît au centre de ce que montre l'image, donc près du point visé
    doc.set_selection([])
    star = window.add_node_of_kind("star")
    center = canvas.visible_center_canvas()
    assert star.position == pytest.approx([center.x(), center.y()])
    assert abs(center.x() - 1200.0) < 400 and abs(center.y() - 400.0) < 300

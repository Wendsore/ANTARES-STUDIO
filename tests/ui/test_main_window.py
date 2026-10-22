"""UI-01 … UI-13 (sous-ensemble headless) — fenêtre principale, persistance, édition, timeline, export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from antares_studio.app.canvas_widget import Handle
from antares_studio.app.main_window import MainWindow
from antares_studio.domain.model import Canvas
from antares_studio.persistence.schema import project_to_dict
from antares_studio.rendering import ffmpeg as ff
from antares_studio.resources.templates import create_project
from antares_studio.timeline.evaluator import evaluate

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot):  # type: ignore[no-untyped-def]
    w = MainWindow()
    # mark_clean avant fermeture : évite la boîte modale « enregistrer ? » (bloquante hors écran)
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    w.canvas.fit_to_view()
    return w


def _wait(qtbot, ms: int = 20) -> None:  # type: ignore[no-untyped-def]
    qtbot.wait(ms)


def test_ui07_startup_has_french_menus_and_docks(window) -> None:  # type: ignore[no-untyped-def]
    titles = [a.text().replace("&", "") for a in window.menuBar().actions()]
    assert titles == ["Fichier", "Édition", "Objet", "Animation", "Narration", "Affichage", "Aide"]
    for dock in (window.library_dock, window.layers_dock, window.inspector_dock, window.timeline_dock):
        assert dock.isVisible()
    assert window.narration_dock.widget() is window.narration and window.narration.tabs.count() == 2
    assert window.document.scene is not None
    assert "ANTARES Studio" in window.windowTitle()


def test_ui02_add_object_selects_and_fills_inspector(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    node = window.add_node_of_kind("circle")
    _wait(qtbot)
    assert node is not None and window.document.selection == [node.id]
    assert "position.x" in window.inspector._editors
    assert window.inspector._editors["params.radius"].value() == 80.0
    assert window.windowTitle().startswith("Sans titre*")


def test_ui03_inspector_edit_updates_model_and_canvas(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    node = window.add_node_of_kind("rect")
    _wait(qtbot)
    editor = window.inspector._editors["position.x"]
    editor.setValue(123.0)
    _wait(qtbot)
    assert node.position[0] == 123.0
    state = window.document.state()
    assert state.node(node.id).position[0] == 123.0
    window.inspector._editors["style.fill"].set_value("#FF0000")
    for cb in window.inspector._editors["style.fill"].changed:
        cb("#FF0000")
    assert node.style["fill"] == "#FF0000"


def test_ui03_canvas_drag_moves_object_with_single_undo_step(  # type: ignore[no-untyped-def]
    window, qtbot
) -> None:
    # selon la taille de la vue, le centre calculé tombe à 960,0000000000001 (vu sur la CI Windows) :
    # l'objet est posé au centième près, et Ctrl+Z après le glisser le ramène exactement à 960
    node = window.add_node_of_kind("circle", at=QPointF(960.0000000000001, 539.9999999999999))
    assert node.position == [960.0, 540.0]
    _wait(qtbot)
    canvas = window.canvas
    start = canvas.canvas_to_widget(QPointF(node.position[0], node.position[1])).toPoint()
    before = len(window.document.undo._undo)
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    for i in range(1, 6):
        QTest.mouseMove(canvas, start + QPoint(10 * i, 4 * i))
        _wait(qtbot, 5)
    QTest.mouseRelease(
        canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + QPoint(50, 20)
    )
    _wait(qtbot)
    dx = 50 / canvas.zoom
    assert node.position[0] == pytest.approx(960 + dx, abs=1.5)
    assert len(window.document.undo._undo) == before + 1  # un seul pas d'annulation pour tout le glisser
    window.document.undo.undo()
    assert node.position[0] == 960.0


def test_ui03_scale_handle_changes_scale(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    node = window.add_node_of_kind("rect")
    _wait(qtbot)
    canvas = window.canvas
    state = window.document.state()
    handles = canvas._handles(state.node(node.id))
    br = handles[Handle.BR].toPoint()
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, br)
    QTest.mouseMove(canvas, br + QPoint(40, 30))
    _wait(qtbot, 5)
    QTest.mouseMove(canvas, br + QPoint(60, 40))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, br + QPoint(60, 40))
    _wait(qtbot)
    assert node.scale[0] > 1.0 and node.scale[1] > 1.0


def test_ui04_rubber_band_multi_selection_and_group(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    a = window.add_node_of_kind("circle")
    b = window.add_node_of_kind("rect")
    b.position = [700.0, 300.0]
    window.document.version += 1
    _wait(qtbot)
    canvas = window.canvas
    p0 = canvas.canvas_to_widget(QPointF(400, 100)).toPoint()
    p1 = canvas.canvas_to_widget(QPointF(1300, 800)).toPoint()
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p0)
    QTest.mouseMove(canvas, p1)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)
    _wait(qtbot)
    assert set(window.document.selection) == {a.id, b.id}
    window.group_selection()
    scene = window.document.scene
    group = scene.node(window.document.selection[0])
    assert group.kind == "group" and a.parent_id == group.id and b.parent_id == group.id
    world_a = evaluate(window.document.project, scene.id, 0).node(a.id).world
    assert (world_a[4], world_a[5]) == pytest.approx((960.0, 540.0))
    window.ungroup_selection()
    assert a.parent_id is None and a.position == pytest.approx([960.0, 540.0])


def test_ui05_keyboard_shortcuts_undo_redo_delete_duplicate(  # type: ignore[no-untyped-def]
    window, qtbot
) -> None:
    node = window.add_node_of_kind("text")
    _wait(qtbot)
    scene = window.document.scene
    assert len(scene.nodes) == 1
    window.act_duplicate.trigger()
    assert len(scene.nodes) == 2 and scene.nodes[1].name.endswith("(copie)")
    window.act_undo.trigger()
    assert len(scene.nodes) == 1
    window.act_redo.trigger()
    assert len(scene.nodes) == 2
    window.document.set_selection([node.id])
    window.act_delete.trigger()
    assert all(n.id != node.id for n in scene.nodes)
    assert window.act_undo.shortcut().toString() in ("Ctrl+Z", "Z")
    assert window.act_save.shortcut().toString() == "Ctrl+S"


def test_ui01_gate1_save_reopen_preserves_everything(  # type: ignore[no-untyped-def]
    window, qtbot, tmp_path: Path, monkeypatch
) -> None:
    window.add_template_scene("moon_phases")
    circle = window.add_node_of_kind("circle")
    window.document.set_node_property(circle.id, "params.radius", 33.0)
    _wait(qtbot)
    snapshot = project_to_dict(window.document.project)
    root = tmp_path / "Lune.antares"
    window.document.save(root)
    assert (root / "project.json").is_file() and not window.document.is_dirty
    assert "*" not in window.windowTitle().split(" — ")[0]
    # réouverture dans une nouvelle fenêtre
    w2 = MainWindow()
    qtbot.addWidget(w2, before_close_func=lambda win: win.document.undo.mark_clean())
    assert w2.open_project_path(root)
    assert project_to_dict(w2.document.project) == snapshot
    assert w2.document.root == root
    for f in (0, 150, 299):
        assert evaluate(w2.document.project, snapshot["scenes"][1]["id"], f) == evaluate(
            window.document.project, snapshot["scenes"][1]["id"], f
        )
    w2.close()


def test_gate1_corrupt_project_offers_recovery_without_loss(  # type: ignore[no-untyped-def]
    window, qtbot, tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "C.antares"
    window.add_node_of_kind("star")
    window.document.save(root)
    window.add_node_of_kind("circle")
    window.document.autosave()  # autosave plus récent, valide
    original = (root / "project.json").read_bytes()
    (root / "project.json").write_text("{corrompu", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    w2 = MainWindow()
    qtbot.addWidget(w2, before_close_func=lambda win: win.document.undo.mark_clean())
    assert w2.open_project_path(root)
    assert len(w2.document.scene.nodes) == 2  # récupéré depuis l'autosave
    assert w2.document.is_dirty
    backups = list((root / "autosaves").glob("corrompu-*.json"))
    assert backups and backups[0].read_text(encoding="utf-8") == "{corrompu"
    assert (root / "project.json").read_text(
        encoding="utf-8"
    ) == "{corrompu"  # jamais écrasé sans Enregistrer
    w2.document.undo.mark_clean()
    w2.close()
    assert original  # l'original lisible était bien là avant corruption


def test_gate1_unreadable_without_autosave_reports_error(  # type: ignore[no-untyped-def]
    window, qtbot, tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "D.antares"
    window.document.save(root)
    (root / "project.json").write_text('{"schema_version": 1}', encoding="utf-8")
    seen: list[str] = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: seen.append(a[2])))
    assert not window.open_project_path(root)
    assert seen and "project_id" in seen[0]


def test_ui08_close_with_unsaved_changes_asks(  # type: ignore[no-untyped-def]
    window, qtbot, monkeypatch
) -> None:
    window.add_node_of_kind("circle")
    asked: list[str] = []

    def fake_question(*args, **kwargs):  # type: ignore[no-untyped-def]
        asked.append(args[1])
        return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))
    window.close()
    assert asked and "non enregistrées" in asked[0]
    assert window.isVisible()
    window.document.undo.mark_clean()


def test_ui06_timeline_scrub_and_keyframes(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    node = window.add_node_of_kind("circle")
    window.inspector._toggle_key("opacity")  # clé à la frame 0 (opacité 1)
    window.document.set_frame(60)
    window.document.set_node_property(node.id, "opacity", 0.0)  # propriété animée -> clé auto
    scene = window.document.scene
    track = scene.track_for(node.id, "opacity")
    assert track is not None and [k.frame for k in track.keyframes] == [0, 60]
    window.document.set_frame(30)
    assert window.document.state().node(node.id).opacity == pytest.approx(0.5)
    assert window.timeline.frame_spin.value() == 30
    view = window.timeline.view
    assert any(r.track is not None and r.track.property == "opacity" for r in view.rows)
    x = int(view.frame_to_x(45))
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x, 10))
    assert window.document.frame == 45
    # lecture : la frame avance sans bloquer l'interface
    window.timeline.play()
    qtbot.wait(250)
    assert window.timeline.playing and window.document.frame > 45
    window.timeline.pause()


def test_preset_from_library_applies_orbit(  # type: ignore[no-untyped-def]
    window, qtbot, monkeypatch
) -> None:
    from antares_studio.app import preset_dialog as pd

    node = window.add_node_of_kind("circle")
    node.position = [1260.0, 540.0]
    monkeypatch.setattr(pd.PresetDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.apply_preset_to_selection("orbit")
    scene = window.document.scene
    assert {t.property for t in scene.tracks_for(node.id)} == {"position.x", "position.y"}
    st = evaluate(window.document.project, scene.id, 0).node(node.id)
    assert st.position == pytest.approx((1260.0, 540.0), abs=1e-6)


def test_new_project_dialog_defaults_and_templates(qtbot) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.app.dialogs import NewProjectDialog
    from antares_studio.resources.templates import template_labels

    dlg = NewProjectDialog(template_labels())
    qtbot.addWidget(dlg)
    dlg.ratio.setCurrentIndex(1)  # 9:16
    dlg.resolution.setCurrentIndex(1)  # 720p
    ch = dlg.choice()
    assert (ch.canvas.width, ch.canvas.height) == (720, 1280)
    assert ch.canvas.fps_num == 30
    project = create_project("Test", Canvas(), "scale_comparison", 15)
    assert project.scenes[0].duration_frames == 450 and len(project.scenes[0].nodes) == 6


@pytest.mark.render
@pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg absent")
def test_ui13_export_dialog_runs_in_background_and_verifies(  # type: ignore[no-untyped-def]
    window, qtbot, tmp_path: Path
) -> None:
    from antares_studio.app.export_dialog import ExportDialog

    window.add_template_scene("moon_phases")
    window.document.scene.duration_frames = 20
    window.document.version += 1
    dlg = ExportDialog(window.document, window.settings, window)
    qtbot.addWidget(dlg)
    dlg.profile.setCurrentIndex(dlg.profile.findData("draft_720p"))
    out = tmp_path / "export test.mp4"
    dlg.path_edit.setText(str(out))
    assert dlg.open_folder_btn.isHidden()
    dlg.start()
    qtbot.waitUntil(lambda: dlg._worker is None, timeout=60000)
    assert dlg.render_result is not None, dlg.status.text()
    assert out.is_file()
    assert not dlg.open_folder_btn.isHidden()  # « Ouvrir le dossier » proposé après un export réussi
    assert dlg.render_result.probe.nb_frames == 20
    manifest = json.loads(dlg.render_result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["plan"]["width"] == 1280


@pytest.mark.render
@pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg absent")
def test_ui13_export_cancel_leaves_no_file(  # type: ignore[no-untyped-def]
    window, qtbot, tmp_path: Path
) -> None:
    from antares_studio.app.export_dialog import ExportDialog

    window.add_template_scene("moon_phases")
    dlg = ExportDialog(window.document, window.settings, window)
    qtbot.addWidget(dlg)
    dlg.profile.setCurrentIndex(dlg.profile.findData("final_1080p"))
    out = tmp_path / "annule.mp4"
    dlg.path_edit.setText(str(out))
    dlg.start()
    qtbot.waitUntil(lambda: dlg.progress.value() > 0, timeout=30000)
    dlg._cancel_or_close()
    qtbot.waitUntil(lambda: dlg._worker is None, timeout=30000)
    assert not out.exists() and not list(tmp_path.glob(".*.part"))
    assert "annulé" in dlg.status.text()


def test_store_recent_and_settings_isolated(window) -> None:  # type: ignore[no-untyped-def]
    import os

    folder = Path(os.environ["ANTARES_SETTINGS_DIR"]).resolve()
    stored = Path(window.settings._s.fileName()).resolve()
    assert folder in stored.parents, f"préférences réelles touchées : {stored}"
    window.settings.add_recent(Path("/tmp/a.antares"))
    assert window.settings.recent_projects()[0] == Path("/tmp/a.antares")


def test_layers_dock_toggles_visibility_and_lock(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    node = window.add_node_of_kind("circle")
    _wait(qtbot)
    tree = window.layers.tree
    item = tree.topLevelItem(0)
    assert item.data(0, Qt.ItemDataRole.UserRole + 1) == node.id
    item.setCheckState(1, Qt.CheckState.Unchecked)
    assert node.visible is False
    _wait(qtbot)  # l'arbre est reconstruit de façon différée après chaque commande
    item = tree.topLevelItem(0)
    item.setCheckState(2, Qt.CheckState.Checked)
    assert node.locked is True
    _wait(qtbot)
    # un objet verrouillé n'est pas sélectionnable au clic sur le canevas
    window.document.set_selection([])
    canvas = window.canvas
    pt = canvas.canvas_to_widget(QPointF(960, 540)).toPoint()
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pt)
    assert window.document.selection == []


def test_image_import_copies_asset_and_renders_placeholder_when_missing(  # type: ignore[no-untyped-def]
    window, qtbot, tmp_path: Path
) -> None:
    from PySide6.QtGui import QColor, QImage

    from antares_studio.resources.assets import import_asset

    src = tmp_path / "terre.png"
    img = QImage(64, 32, QImage.Format.Format_RGBA8888)
    img.fill(QColor("#00FF00"))
    img.save(str(src))
    window.document.save(tmp_path / "I.antares")
    asset = import_asset(window.document, src, kind="image")
    assert (tmp_path / "I.antares" / "assets" / "terre.png").is_file() and asset.path == "assets/terre.png"
    node = window.add_node_of_kind("image")
    window.document.set_node_property(node.id, "params.asset_id", asset.id)
    from antares_studio.rendering.qt_painter import render_state_to_image

    st = window.document.state()
    out = render_state_to_image(st, window.document.project.canvas, 1920, 1080, window.document.resolve_asset)
    assert out.pixelColor(960, 540).green() == 255
    (tmp_path / "I.antares" / "assets" / "terre.png").unlink()
    window.document.version += 1
    from antares_studio.rendering.qt_painter import ImageCache

    out2 = render_state_to_image(
        st, window.document.project.canvas, 1920, 1080, window.document.resolve_asset, ImageCache()
    )
    assert out2.pixelColor(960, 540).green() != 255  # placeholder, pas de crash (MOD-07)
    QApplication.processEvents()

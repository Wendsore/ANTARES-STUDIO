"""Post-production dans l'éditeur : onglets « Effets » et « Sons », Inspecteur « Effets » et « Filtres »."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QDoubleSpinBox, QMessageBox

from antares_studio.app.library_dock import sound_cache_dir
from antares_studio.app.main_window import MainWindow
from antares_studio.audio import sfx
from antares_studio.domain.effects import EFFECTS, OBJECT_LOOKS, SCENE_LOOKS
from antares_studio.rendering import ffmpeg as ff

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
    from antares_studio.app.library_dock import ID_ROLE

    return next(lst.item(i) for i in range(lst.count()) if lst.item(i).data(ID_ROLE) == ident)


def test_library_lists_every_effect_look_and_sound(window) -> None:  # type: ignore[no-untyped-def]
    lib = window.library
    names = [lib.tabs.tabText(i) for i in range(lib.tabs.count())]
    assert names[:5] == ["Objets", "Animations", "Effets", "Sons", "Modèles"]
    for key in OBJECT_LOOKS:
        assert _item(lib.effects, f"objet:{key}") is not None
    for key in SCENE_LOOKS:
        assert _item(lib.effects, f"scène:{key}") is not None
    for sid in sfx.SOUNDS:
        assert _item(lib.sounds, sid).text() == sfx.SOUNDS[sid].label
    lib.search.setText("gong")
    visible = [
        lib.sounds.item(i).text() for i in range(lib.sounds.count()) if not lib.sounds.item(i).isHidden()
    ]
    assert "Gong" in visible and "Laser" not in visible


def test_object_look_from_library_is_one_undo_step(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    a = window.add_node_of_kind("circle")
    b = window.add_node_of_kind("rect")
    window.document.set_selection([a.id, b.id])
    window.library.effects.itemDoubleClicked.emit(_item(window.library.effects, "objet:glow_star"))
    for node in (a, b):
        assert node.style["fx_glow"] == 40.0 and node.style["fx_blur"] == 0.0
    window.apply_object_look("black_white")  # remplace le préréglage précédent
    assert a.style["fx_saturation"] == 0.0 and a.style["fx_glow"] == 0.0
    window.document.undo.undo()
    assert a.style["fx_glow"] == 40.0 and b.style["fx_glow"] == 40.0
    window.document.undo.undo()
    assert a.style.get("fx_glow", 0.0) == 0.0 and b.style.get("fx_glow", 0.0) == 0.0


def test_object_look_needs_a_selection(window, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: shown.append(a[2]))
    window.document.set_selection([])
    assert window.apply_object_look("glow_star") == 0
    assert shown and "Sélectionnez" in shown[0]


def test_inspector_effects_section_edits_and_keys_effects(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    node = window.add_node_of_kind("circle")
    qtbot.wait(20)
    editors = window.inspector._editors
    for p in EFFECTS:
        assert f"style.{p.name}" in editors
    blur = editors["style.fx_blur"]
    assert isinstance(blur, QDoubleSpinBox) and blur.value() == 0.0  # valeur par défaut, clé absente
    assert "fx_blur" not in node.style
    blur.setValue(6.0)
    assert node.style["fx_blur"] == 6.0
    assert "style.fx_blur" in window.inspector._key_buttons  # animable : bouton image clé
    window.inspector._toggle_key("style.fx_glow")
    assert window.document.scene.track_for(node.id, "style.fx_glow") is not None


def test_groups_and_cameras_have_no_effects_section(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    window.add_node_of_kind("camera")
    qtbot.wait(20)
    assert "style.fx_blur" not in window.inspector._editors


def test_scene_filters_from_inspector_and_library(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    scene = window.document.scene
    window.document.set_selection([])
    qtbot.wait(20)
    insp = window.inspector
    look = insp._post_look
    assert look is not None and look.currentData() == "none"
    look.setCurrentIndex(look.findData("cinema"))
    assert scene.post == SCENE_LOOKS["cinema"][2]
    assert insp._post_editors["vignette"].value() == pytest.approx(0.35)
    insp._post_editors["grain"].setValue(0.5)
    assert scene.post["grain"] == 0.5 and look.currentData() == ""  # réglage fin : « Personnalisé »
    window.library.effects.itemDoubleClicked.emit(_item(window.library.effects, "scène:none"))
    assert scene.post == {} and look.currentData() == "none"
    window.document.undo.undo()
    qtbot.wait(20)
    assert scene.post["grain"] == 0.5 and insp._post_editors["grain"].value() == 0.5


def test_effect_animation_presets_are_reachable_from_effects_tab(window, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    asked: list[str] = []
    monkeypatch.setattr(window, "apply_preset_to_selection", lambda pid: asked.append(pid))
    window.library.presetRequested.disconnect()
    window.library.presetRequested.connect(window.apply_preset_to_selection)
    window.library.effects.itemDoubleClicked.emit(_item(window.library.effects, "animation:glow_pulse"))
    assert asked == ["glow_pulse"]


def test_insert_sound_requires_a_saved_project(window, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: shown.append(a[2]))
    assert window.insert_sound("ding") is None
    assert shown and "Enregistrez" in shown[0]
    assert not window.document.scene.audio


@pytest.mark.skipif(ff.find_ffmpeg() is None, reason="FFmpeg absent")
def test_insert_sound_adds_an_effect_clip_with_cc0_provenance(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    window.document.save(tmp_path / "Sons.antares")
    window.document.set_frame(12)
    clip = window.insert_sound("ding")
    assert clip is not None
    assert clip.role == "effect" and clip.offset_frames == 12 and clip.name == "Cloche (bonne réponse)"
    assert clip.duration_seconds == pytest.approx(sfx.sound_duration("ding"), abs=0.02)
    asset = window.document.project.asset(clip.asset_id)
    assert asset is not None and asset.path.startswith("audio/")
    resolved = window.document.resolve_asset(asset.id)
    assert resolved is not None and resolved.is_file()
    assert asset.license.license == "CC0-1.0" and asset.license.redistribution_allowed
    assert "ANTARES Studio" in asset.license.author
    window.document.undo.undo()  # une seule étape : clip, rôle et fiche
    assert not window.document.scene.audio


def test_sound_preview_writes_the_cache_once(window) -> None:  # type: ignore[no-untyped-def]
    lib = window.library
    lib.sounds.setCurrentItem(_item(lib.sounds, "pop"))
    path = lib.preview_selected_sound()
    assert path is not None and path.parent == sound_cache_dir() and path.is_file()
    stamp = path.stat().st_mtime_ns
    assert lib.preview_selected_sound() == path and path.stat().st_mtime_ns == stamp

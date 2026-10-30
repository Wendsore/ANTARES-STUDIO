"""Phase 14 dans l'éditeur : personnages de la Bibliothèque, émotion changée en cours de scène (ADR-0010)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QComboBox

from antares_studio.app.library_dock import CATEGORIES, ID_ROLE
from antares_studio.app.main_window import MainWindow
from antares_studio.domain.characters import PERSONALITIES

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


def test_library_lists_every_personality_with_a_rendered_thumbnail(window) -> None:  # type: ignore[no-untyped-def]
    assert len(CATEGORIES["Personnages"]) == len(PERSONALITIES)
    for p in PERSONALITIES:
        assert not _item(window.library.objects, f"character:{p.id}").icon().isNull(), p.id


def test_emotion_changes_during_the_scene_from_the_inspector(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = window.library
    lib.objects.itemDoubleClicked.emit(_item(lib.objects, "character:ironique"))
    node = window.document.selected_nodes[0]
    assert node.kind == "character" and node.params["emotion"] == "ironie"
    assert node.style["fill"] == "#4C6B3C" and not any(k.startswith("style_") for k in node.params)
    qtbot.wait(20)
    combo = window.inspector._editors["params.emotion"]
    assert isinstance(combo, QComboBox) and combo.currentData() == "ironie"
    assert "params.emotion" in window.inspector._key_buttons  # animable : bouton image clé
    window.inspector._toggle_key("params.emotion")  # clé à la frame 0 : « ironie »
    window.document.set_frame(45)
    qtbot.wait(20)
    combo = window.inspector._editors["params.emotion"]
    combo.setCurrentIndex(combo.findData("fureur"))  # propriété animée : nouvelle clé à 45
    track = window.document.scene.track_for(node.id, "params.emotion")
    assert track is not None and [(k.frame, k.value) for k in track.keyframes] == [
        (0, "ironie"),
        (45, "fureur"),
    ]
    window.document.set_frame(44)
    assert window.document.state().node(node.id).params["emotion"] == "ironie"
    window.document.set_frame(46)
    assert window.document.state().node(node.id).params["emotion"] == "fureur"

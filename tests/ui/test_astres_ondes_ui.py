"""Phase 13 dans l'éditeur : astres, étoiles, cartes, ondes et optique de la Bibliothèque (ADR-0009)."""

from __future__ import annotations

import pytest

from antares_studio.app.library_dock import CATEGORIES, ID_ROLE
from antares_studio.app.main_window import MainWindow
from antares_studio.resources.astro import BODIES, FAMOUS_STARS

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


def test_library_lists_every_body_and_famous_star(window) -> None:  # type: ignore[no-untyped-def]
    for cat in ("Astres", "Étoiles connues", "Cartes et ciel", "Ondes", "Lumière et optique"):
        assert CATEGORIES[cat], cat
    assert CATEGORIES["Phénomènes cosmiques"]
    lib = window.library
    for body in BODIES:
        item = _item(lib.objects, f"celestial:{body}")
        assert not item.icon().isNull(), body
    for star in FAMOUS_STARS:  # le Soleil est rangé parmi les Astres, avec sa vraie texture
        assert _item(lib.objects, "celestial:sun" if star == "sun" else f"celestial:star_{star}") is not None


def test_adding_saturn_then_a_star_from_the_library(window) -> None:  # type: ignore[no-untyped-def]
    lib = window.library
    lib.objects.itemDoubleClicked.emit(_item(lib.objects, "celestial:saturn"))
    saturn = window.document.selected_nodes[0]
    assert saturn.kind == "celestial" and saturn.params["body"] == "saturn"
    assert saturn.params["tilt_deg"] == pytest.approx(BODIES["saturn"].obliquity_deg)
    lib.objects.itemDoubleClicked.emit(_item(lib.objects, "celestial:star_betelgeuse"))
    star = window.document.selected_nodes[0]
    assert star.params["body"] == "star"
    assert star.params["temperature_k"] == FAMOUS_STARS["betelgeuse"].temperature_k
    window.document.undo.undo()
    assert star not in window.document.scene.nodes and saturn in window.document.scene.nodes


def test_variant_style_keys_go_to_the_node_style(window) -> None:  # type: ignore[no-untyped-def]
    lib = window.library
    for ident in CATEGORIES["Ondes"] + CATEGORIES["Lumière et optique"] + CATEGORIES["Cartes et ciel"]:
        lib.objects.itemDoubleClicked.emit(_item(lib.objects, ident))
        node = window.document.selected_nodes[0]
        assert not any(k.startswith("style_") for k in node.params), ident
    window.inspector.rebuild()  # l'Inspecteur accepte chacun des nouveaux types

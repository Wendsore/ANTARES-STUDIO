"""Astuces de première utilisation : une fois par panneau, jamais pendant un tutoriel, désactivables."""

from __future__ import annotations

from antares_studio.app.first_tips import TIPS
from antares_studio.app.main_window import MainWindow


def _window(qtbot) -> MainWindow:  # type: ignore[no-untyped-def]
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def test_every_tip_targets_a_real_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _window(qtbot)
    for key in TIPS:
        assert window.findChild(object, key) is not None or key == "canvas", key
    assert window.canvas.objectName() == "canvas"


def test_focus_shows_tip_once_then_never_again(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _window(qtbot)
    tips = window.tips
    assert window.settings.tips_seen() == set()
    window.layers_dock.widget().setFocus()
    window.activateWindow()
    assert tips.maybe_show("dock_layers", window.layers_dock) or tips.bubble.key == "dock_layers"
    assert tips.bubble.isVisible() and "Scènes et objets" in tips.bubble.title.text()
    assert "dock_layers" in window.settings.tips_seen()
    tips.bubble.ok.click()
    assert not tips.bubble.isVisible()
    assert not tips.maybe_show("dock_layers", window.layers_dock)  # déjà vue
    # le focus réel déclenche aussi la bulle d'un autre panneau
    tips._focus_changed(None, window.canvas)  # focus initial (ouverture de la fenêtre) : rien
    assert not tips.bubble.isVisible()
    tips._focus_changed(window.layers_dock.widget(), window.canvas)
    assert tips.bubble.isVisible() and tips.bubble.key == "canvas"
    assert "Alt" in tips.bubble.text.text()  # le geste réellement disponible, pas la barre d'espace


def test_tips_can_be_turned_off_and_reset(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _window(qtbot)
    tips = window.tips
    assert tips.maybe_show("dock_inspector", window.inspector_dock)
    tips.bubble.never.setChecked(True)
    tips.bubble.ok.click()
    assert not window.settings.show_tips()
    assert not tips.maybe_show("dock_timeline", window.timeline_dock)
    window.act_reset_tips.trigger()
    assert window.settings.show_tips() and window.settings.tips_seen() == set()
    assert tips.maybe_show("dock_timeline", window.timeline_dock)


def test_no_tip_during_a_tutorial(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = _window(qtbot)
    assert window.start_tutorial("interface")
    assert not window.tips.maybe_show("dock_library", window.library_dock)
    assert "dock_library" not in window.settings.tips_seen()  # elle reste à montrer plus tard

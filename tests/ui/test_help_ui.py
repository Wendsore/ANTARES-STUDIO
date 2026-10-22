"""Aide, tutoriels, palette de commandes, accueil et apparence : comportements réels de la fenêtre."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from antares_studio.app import icons, theme, thumbnails, tutorial_panel
from antares_studio.app.command_palette import CommandPalette, menu_actions
from antares_studio.app.main_window import ACTION_ICONS, CONTEXT_TOPICS, MainWindow
from antares_studio.app.welcome import WelcomeDialog
from antares_studio.help import topics
from antares_studio.help.tutorials import TUTORIALS, TUTORIALS_BY_ID

pytestmark = pytest.mark.ui
TOP_MENUS = "Fichier|Édition|Objet|Animation|Narration|Affichage|Aide"
MENU_PATH = re.compile(rf"\*\*((?:{TOP_MENUS})(?: > [^*\n]+)+)\*\*")


@pytest.fixture
def window(qtbot):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    return w


def _clean(text: str) -> str:
    return text.replace("&", "").split("\t")[0].strip()


def _menu_texts(window: MainWindow) -> set[str]:
    out: set[str] = set()

    def walk(menu: QMenu, path: list[str]) -> None:
        for act in menu.actions():
            if act.isSeparator():
                continue
            here = [*path, _clean(act.text())]
            out.add(" > ".join(here))
            if act.menu() is not None:
                walk(act.menu(), here)  # type: ignore[arg-type]

    for act in window.menuBar().actions():
        top = act.menu()
        if top is not None:
            out.add(_clean(act.text()))
            walk(top, [_clean(act.text())])  # type: ignore[arg-type]
    return out


def test_menu_paths_quoted_in_help_exist(window) -> None:  # type: ignore[no-untyped-def]
    """Chaque chemin « **Menu > Article** » cité dans l'aide existe dans la vraie barre de menus."""
    known = _menu_texts(window)
    quoted: dict[str, str] = {}
    for t in topics.TOPICS:
        for path in MENU_PATH.findall(topics.raw_markdown(t.id)):
            quoted.setdefault(path.strip(), t.id)
    assert len(quoted) > 20
    missing = {p: tid for p, tid in quoted.items() if p not in known}
    assert not missing, f"chemins de menu introuvables : {missing}"


def test_shortcuts_are_unique_and_platform_safe(window) -> None:  # type: ignore[no-untyped-def]
    seen: dict[str, str] = {}
    for path, act in menu_actions(window.menuBar()):
        for key in act.shortcuts():
            text = key.toString(QKeySequence.SequenceFormat.PortableText)
            assert text not in seen, f"{text} : {seen.get(text)} et {path}"
            seen[text] = path
    assert [k.toString() for k in window.act_delete.shortcuts()] == ["Del"]  # pas Ctrl+D (Dupliquer)
    assert {k.toString() for k in window.act_redo.shortcuts()} == {"Ctrl+Y", "Ctrl+Shift+Z"}
    assert window.act_save_as.shortcut().toString() == "Ctrl+Shift+S"
    assert window.act_help.shortcut().toString() == "F1"
    assert window.act_palette.shortcut().toString() == "Ctrl+K"


def test_f1_opens_the_topic_of_the_focused_panel(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    assert set(CONTEXT_TOPICS.values()) <= set(topics.TOPICS_BY_ID)
    window.inspector_dock.show()
    window.inspector.setFocus()
    qtbot.waitUntil(lambda: QApplication.focusWidget() is not None)
    window.show_context_help()
    center = window.help_center
    assert center is not None and center.current_topic == "inspecteur"
    assert "Inspecteur" in center.browser.toPlainText()
    window.canvas.setFocus()
    window.show_context_help()
    assert center.current_topic == "canevas" and window.ui_counters["help_opened"] == 2
    center.close()


def test_help_center_navigation_search_and_links(window) -> None:  # type: ignore[no-untyped-def]
    center = window.show_help("bienvenue")
    center.show_topic("animations")
    center.back()
    assert center.current_topic == "bienvenue"
    center.forward()
    assert center.current_topic == "animations"
    center.search.setText("sous titres")
    assert center.tree.topLevelItemCount() >= 1 and center.results_label.isVisible()
    center.search.setText("")
    assert center.tree.topLevelItemCount() == len(topics.sections())
    from PySide6.QtCore import QUrl

    center._on_link(QUrl("export-video.md"))
    assert center.current_topic == "export-video"
    raccourcis = window.show_help("raccourcis").browser.toPlainText()
    assert "Ctrl+K" in raccourcis and "section indisponible" not in raccourcis
    center.close()


def test_help_images_load_and_traversal_is_refused(window) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtGui import QImage, QTextDocument

    center = window.show_help("interface")
    img_type = int(QTextDocument.ResourceType.ImageResource.value)
    img = center.browser.loadResource(img_type, "images/interface.png")
    assert isinstance(img, QImage) and not img.isNull()
    assert center.browser.loadResource(img_type, "../../../pyproject.toml") is None
    center.close()


def test_command_palette_filters_and_triggers(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    pal = CommandPalette(window.menuBar(), window)
    qtbot.addWidget(pal)
    total = pal.list.count()
    assert total == len(menu_actions(window.menuBar())) > 40
    pal.edit.setText("grille")  # recherche sans accent ni casse
    visible = [pal.list.item(i) for i in range(pal.list.count()) if not pal.list.item(i).isHidden()]
    assert visible and all("grille" in topics.fold(it.text()) for it in visible)
    before = window.act_grid.isChecked()
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    QTest.keyClick(pal.edit, Qt.Key.Key_Return)
    assert pal.triggered is window.act_grid
    pal.triggered.trigger()
    assert window.act_grid.isChecked() is not before


def test_welcome_template_choice_creates_the_project(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    dlg = WelcomeDialog([Path("/tmp/x/Lune.antares")], {"interface"}, False, True, window)
    qtbot.addWidget(dlg)
    assert dlg.tutorials.count() == len(TUTORIALS)
    assert "terminé" in dlg.tutorials.item(0).text() and "terminé" not in dlg.tutorials.item(1).text()
    assert dlg.findChild(QWidget, "welcome_ffmpeg").property("role") == "warning"
    card = dlg.findChild(QWidget, "welcome_template_moon_phases")
    assert card is not None
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    QTest.mouseClick(card, Qt.MouseButton.LeftButton, pos=QPoint(20, 20))
    assert dlg.choice == ("template", "moon_phases")
    assert window.new_project_from_template("moon_phases")
    assert window.document.project.title == "Phases de la Lune"
    assert not window.new_project_from_template("inexistant")


def test_welcome_page_shown_at_startup_only_when_enabled(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    seen: list[WelcomeDialog] = []

    def close_it() -> None:
        dlg = QApplication.activeModalWidget()
        if isinstance(dlg, WelcomeDialog):
            seen.append(dlg)
            dlg.show_at_startup.setChecked(False)
            dlg.choose("tutorial", "premiere-scene")

    QTimer.singleShot(50, close_it)
    window.show_welcome()
    assert seen and window.settings.show_welcome() is False
    assert window.tutorial.run is not None and window.tutorial.run.tutorial.id == "premiere-scene"


def test_theme_and_text_size_apply_and_persist(window, qapp) -> None:  # type: ignore[no-untyped-def]
    try:
        window.set_theme("clair")
        assert theme.active().name == "clair" and window.settings.theme() == "clair"
        assert window.theme_actions["clair"].isChecked()
        window.set_font_scale(130)
        assert window.settings.font_scale() == 130 and window.scale_actions[130].isChecked()
        window.set_theme("inconnu")  # ignoré
        assert theme.active().name == "clair"
    finally:
        theme.apply_theme(qapp, "sombre", 100)


def test_tutorial_dock_is_readable_and_show_me_highlights(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    assert window.start_tutorial("interface")
    qtbot.waitUntil(lambda: window.tutorial_dock.isVisible())
    column = window.tutorial_dock.height() + window.inspector_dock.height()
    assert window.tutorial_dock.height() >= 0.45 * column, (window.tutorial_dock.height(), column)
    for tut in TUTORIALS:
        for step in tut.steps:
            if step.target:
                assert window.findChild(QWidget, step.target) is not None, f"{tut.id} : {step.target}"
    window.library_dock.hide()
    hl = window.highlight_widget("library_search")
    assert hl is not None and window.library_dock.isVisible()
    assert window.highlight_widget("inexistant") is None
    window.tutorial.stop()
    assert not window.tutorial_dock.isVisible()


def test_tutorial_premiere_scene_walkthrough(window, qtbot, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Parcours complet : chaque étape se valide seule quand l'action réelle est faite, jamais avant."""
    monkeypatch.setattr(tutorial_panel, "ADVANCE_DELAY_MS", 1)
    assert window.start_tutorial("premiere-scene")
    panel, doc = window.tutorial, window.document
    assert doc.scene is not None and not doc.scene.nodes  # projet vide
    state: dict[str, str] = {}

    def add_circle() -> None:
        node = window.add_node_of_kind("circle")
        assert node is not None
        state["circle"] = node.id

    def add_text() -> None:
        node = window.add_node_of_kind("text")
        assert node is not None
        state["text"] = node.id

    actions = [
        add_circle,
        lambda: doc.set_node_property(state["circle"], "position.x", 300.0),
        lambda: doc.set_node_property(state["circle"], "params.radius", 90.0),
        lambda: doc.set_node_property(state["circle"], "style.fill", "#FFB300FF"),
        add_text,
        lambda: doc.set_node_property(state["text"], "params.text", "Le Soleil"),
        lambda: window.add_node_of_kind("ellipse"),
        lambda: doc.set_node_property(state["circle"], "name", "Soleil"),
        lambda: doc.set_node_property(state["text"], "locked", True),
        lambda: doc.save(tmp_path / "Premiere.antares"),
    ]
    steps = TUTORIALS_BY_ID["premiere-scene"].steps
    assert len(actions) == len(steps)
    finished: list[str] = []
    panel.tutorialFinished.connect(finished.append)
    for i, act in enumerate(actions):
        assert panel.run is not None and panel.run.index == i
        panel.refresh()
        assert i not in panel.run.completed, f"étape {i + 1} validée sans action"
        act()
        panel.refresh()
        assert i in panel.run.completed, f"étape {i + 1} « {steps[i].title} » non validée"
        if i + 1 < len(actions):
            qtbot.waitUntil(lambda i=i: panel.run is not None and panel.run.index == i + 1, timeout=3000)
    assert finished == ["premiere-scene"] and "premiere-scene" in window.settings.tutorials_done()


def test_tutorial_menu_marks_finished_tutorials(window) -> None:  # type: ignore[no-untyped-def]
    window.settings.mark_tutorial_done("exporter")
    window._fill_tutorials_menu()
    texts = [a.text() for a in window.menu_tutorials.actions() if not a.isSeparator()]
    assert len([t for t in texts if t[:1].isdigit() or "✓" in t]) >= len(TUTORIALS)
    assert any("✓" in t and "Exporter" in t for t in texts)


def test_import_example_data_records_provenance(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.app.provenance_dialog import ProvenanceDialog

    window.document.save(tmp_path / "Donnees.antares")

    def close_dialog() -> None:
        dlg = QApplication.activeModalWidget()
        if isinstance(dlg, ProvenanceDialog):
            dlg.reject()

    QTimer.singleShot(100, close_dialog)
    node = window.import_example_data()
    assert node is not None and node.kind == "chart"
    stored = window.document.scene.find_node(node.id)
    asset = window.document.project.asset(str(stored.params["data_asset_id"]))
    assert asset is not None and asset.license is not None
    assert "NASA" in asset.license.author and asset.license.license == "public-domain"
    assert asset.license.source_url.startswith("https://nssdc.gsfc.nasa.gov/")
    assert (tmp_path / "Donnees.antares" / asset.path).is_file()


def test_colour_button_shows_alpha_and_transparent(qtbot) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.app.inspector_dock import ColorButton

    btn = ColorButton()
    qtbot.addWidget(btn)
    btn.set_value("#FFFFFF00")
    assert btn.text() == "Transparent" and "rgba(255, 255, 255, 0)" in btn.styleSheet()
    btn.set_value("#D9D9D9")
    assert btn.text() == "#D9D9D9" and "rgba(217, 217, 217, 255)" in btn.styleSheet()


def test_empty_canvas_shows_first_steps_hint(window, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[int] = []
    original = window.canvas._paint_empty_hint
    monkeypatch.setattr(window.canvas, "_paint_empty_hint", lambda *a: (calls.append(1), original(*a)))
    window.canvas.repaint()
    assert calls, "une scène vide affiche le rappel des premiers gestes"
    window.add_node_of_kind("circle")
    calls.clear()
    window.canvas.repaint()
    assert not calls


def test_all_interface_icons_exist(qapp) -> None:  # type: ignore[no-untyped-def]
    names = set(icons.icon_names())
    used = {*ACTION_ICONS.values(), *thumbnails.KIND_ICONS.values(), *thumbnails.PRESET_ICONS.values()}
    used |= {"chevron-up", "chevron-down", "chevron-left", "chevron-right", "house", "search", icons.LOGO}
    assert used <= names, f"icônes manquantes : {sorted(used - names)}"
    assert not icons.icon("play").isNull() and not icons.app_icon().isNull()
    files = icons.arrow_files("#123456")
    assert all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in files.values())
    assert (icons.ICON_DIR / "LICENSE-lucide.txt").is_file()

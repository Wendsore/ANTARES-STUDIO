"""Rejeu des tutoriels 1 et 3 à 7 : chaque étape est faite avec les vraies commandes de la fenêtre, puis
doit se valider seule — jamais avant l'action (le tutoriel 2 est rejoué dans ``test_help_ui``)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QFileDialog

from antares_studio.app import tutorial_panel
from antares_studio.app.export_queue import ExportJob
from antares_studio.app.main_window import MainWindow
from antares_studio.domain.commands import (
    MoveKeyframe,
    RemoveKeyframe,
    SetAssetLicense,
    SetProjectMetadata,
    SetSubtitleAttr,
)
from antares_studio.domain.model import AssetLicense
from antares_studio.help.tutorials import TUTORIALS_BY_ID
from antares_studio.rendering import ffmpeg as ff
from antares_studio.rendering.plan import build_render_plan
from antares_studio.timeline.presets import PRESETS
from tests.integration.test_audio import make_wav

pytestmark = pytest.mark.ui
needs_ffmpeg = pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg/ffprobe absents")
Action = Callable[[], object] | None  # None : étape sans vérification, on passe avec « Suivant »


@pytest.fixture
def window(qtbot, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(tutorial_panel, "ADVANCE_DELAY_MS", 1)
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    return w


@contextmanager
def closing_dialogs() -> Iterator[None]:
    """Ferme les dialogues modaux ouverts par les commandes (inventaire, provenance, recherche)."""

    def close() -> None:
        dlg = QApplication.activeModalWidget()
        if dlg is not None:
            dlg.close()

    timer = QTimer()
    timer.timeout.connect(close)
    timer.start(30)
    try:
        yield
    finally:
        timer.stop()


def replay(window: MainWindow, qtbot, tutorial_id: str, actions: list[Action]) -> None:  # type: ignore[no-untyped-def]
    tut = TUTORIALS_BY_ID[tutorial_id]
    assert len(actions) == len(tut.steps), "une action par étape"
    assert window.start_tutorial(tutorial_id)
    panel = window.tutorial
    finished: list[str] = []
    panel.tutorialFinished.connect(finished.append)
    for i, act in enumerate(actions):
        assert panel.run is not None and panel.run.index == i, f"{tutorial_id} : étape {i + 1} attendue"
        if act is None:
            assert tut.steps[i].check is None
            panel.next()
            continue
        panel.refresh()
        assert i not in panel.run.completed, f"{tutorial_id} : étape {i + 1} validée sans action"
        act()
        panel.refresh()
        assert i in panel.run.completed, f"{tutorial_id} : étape {i + 1} « {tut.steps[i].title} » non validée"
        if i + 1 < len(actions):
            qtbot.waitUntil(lambda i=i: panel.run is not None and panel.run.index == i + 1, timeout=3000)
    if tut.steps[-1].check is None:
        qtbot.waitUntil(lambda: bool(finished) or panel.run is None, timeout=3000)
    assert finished == [tutorial_id], f"{tutorial_id} non terminé"


class LiveDocument:
    """Document courant de la fenêtre : un tutoriel qui prépare un projet remplace le document."""

    def __init__(self, window: MainWindow):
        self._window = window

    def __getattr__(self, name: str) -> Any:
        return getattr(self._window.document, name)


def _select_first(window: MainWindow, kind: str) -> str:
    node = next(n for n in window.document.scene.nodes if n.kind == kind)  # type: ignore[union-attr]
    window.document.set_selection([node.id])
    return node.id


def test_tutorial_1_interface(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    def play() -> None:
        window.timeline.play()
        qtbot.wait(50)

    with closing_dialogs():
        replay(
            window,
            qtbot,
            "interface",
            [
                None,
                lambda: window.library.search.setText("cercle"),
                window.act_zoom_in.trigger,
                lambda: _select_first(window, "circle"),
                lambda: window.document.set_frame(45),
                play,
                window.show_command_palette,
                lambda: window.show_help("interface"),
            ],
        )
    window.timeline.pause()
    assert window.help_center is not None
    window.help_center.close()


def test_tutorial_3_animer(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    doc = LiveDocument(window)
    state: dict[str, str] = {}

    def add_circle() -> None:
        node = window.add_node_of_kind("circle")
        assert node is not None
        state["id"] = node.id
        doc.set_selection([node.id])

    def preset(pid: str) -> Callable[[], object]:
        return lambda: window.apply_preset_values(pid, PRESETS[pid].defaults())

    def manual_key() -> None:
        window.timeline.pause()  # la lecture de l'étape précédente ferait bouger l'image courante
        doc.set_frame(100)
        window.inspector._toggle_key("rotation_deg")

    def move_key() -> None:
        doc.push(MoveKeyframe(doc.scene_id, state["id"], "rotation_deg", 100, 120))

    def remove_key() -> None:
        doc.push(RemoveKeyframe(doc.scene_id, state["id"], "rotation_deg", 120))

    def play() -> None:
        window.timeline.play()
        qtbot.wait(50)

    replay(
        window,
        qtbot,
        "animer",
        [add_circle, preset("appear"), preset("orbit"), play, manual_key, move_key, remove_key],
    )
    window.timeline.pause()


@needs_ffmpeg
def test_tutorial_4_narration(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    doc = LiveDocument(window)
    wav = tmp_path / "voix.wav"
    make_wav(wav, 2.0)

    def adjust() -> None:
        clip = doc.scene.audio[0]  # type: ignore[union-attr]
        window.narration.audio._set(clip.id, "gain", 0.6)

    def edit_subtitle() -> None:
        sub = doc.scene.subtitles[0]  # type: ignore[union-attr]
        doc.push(SetSubtitleAttr(doc.scene_id, sub.id, "text", "La Lune réfléchit la lumière du Soleil."))

    replay(
        window,
        qtbot,
        "narration",
        [
            lambda: doc.save(tmp_path / "Narration.antares"),
            lambda: window.narration.audio.add_audio_file(wav),
            adjust,
            window.narration.subtitles.add_at_current_frame,
            edit_subtitle,
            window.act_safe.trigger,
        ],
    )


def test_tutorial_5_science(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    doc = LiveDocument(window)

    def formula() -> None:
        node = window.add_node_of_kind("formula")
        assert node is not None
        doc.set_node_property(node.id, "params.text", r"T^{2} = \frac{4 \pi^{2}}{G M} a^{3}")

    def trace() -> None:
        _select_first(window, "chart")
        window.apply_preset_values("trace", PRESETS["trace"].defaults())

    def add_source() -> None:
        sources = list(doc.project.scientific_metadata.get("sources", []))
        sources.append(
            {"label": "NASA Planetary Fact Sheet", "url": "https://nssdc.gsfc.nasa.gov/planetary/factsheet/"}
        )
        doc.push(SetProjectMetadata("sources", sources))

    with closing_dialogs():
        replay(
            window,
            qtbot,
            "science",
            [
                lambda: window.add_template_scene("kepler_orbit"),
                formula,
                lambda: doc.save(tmp_path / "Science.antares"),
                lambda: window._tutorial_action("import_example_csv"),
                trace,
                lambda: doc.push(SetProjectMetadata("representation", "data")),
                add_source,
                window.add_scale_warning,
            ],
        )


def test_tutorial_6_ressources(window, qtbot, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    doc = LiveDocument(window)
    doc.save(tmp_path / "Ressources.antares")
    image = tmp_path / "schema.png"
    img = QImage(64, 64, QImage.Format.Format_RGB32)
    img.fill(QColor("#336699"))
    img.save(str(image))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(image), "")))

    def document_provenance() -> None:
        asset = next(a for a in doc.project.assets if a.kind == "image")
        complete = AssetLicense(
            author="Moi",
            source_url="https://example.org/schema",
            license="own-work",
            redistribution_allowed=True,
            verified_on="2026-10-22",
        )
        doc.push(SetAssetLicense(asset.id, complete))

    with closing_dialogs():
        replay(
            window,
            qtbot,
            "ressources",
            [
                window.import_image,
                document_provenance,
                window.show_inventory,
                lambda: window.add_template_scene("credits"),
            ],
        )


@needs_ffmpeg
def test_tutorial_7_exporter(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    doc = LiveDocument(window)
    window.add_template_scene("intro")
    doc.scene.duration_frames = 6  # type: ignore[union-attr]
    for scene in doc.project.scenes:
        scene.duration_frames = 6
    doc.version += 1

    def run(job: ExportJob) -> None:
        window.export_queue.submit(job)
        qtbot.waitUntil(lambda: job.status in ("done", "failed"), timeout=60000)
        assert job.status == "done", job.message

    def draft() -> None:
        out = tmp_path / "brouillon.mp4"
        plan = build_render_plan(doc.project, doc.scene_id, "draft_720p", str(out))
        run(ExportJob.from_document(window.document, out.name, out, plan))

    def full() -> None:
        out = tmp_path / "complete.mp4"
        run(ExportJob.from_document(window.document, out.name, out, whole_project_profile="draft_720p"))

    replay(window, qtbot, "exporter", [draft, full, None])
    assert (tmp_path / "complete.mp4").is_file() and (tmp_path / "complete.credits.txt").is_file()

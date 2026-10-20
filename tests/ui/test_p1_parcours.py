"""Gate 5 — parcours P1 « Pourquoi la Lune change-t-elle de forme ? » exécuté par l'interface, sans code.

Création 16:9 depuis le modèle, avertissement d'échelle, voix off, sous-titres, crédits, export 1080p/30,
fermeture et réouverture sans perte, provenance scientifique et crédits exportés.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from antares_studio.app.export_dialog import ExportDialog
from antares_studio.app.main_window import MainWindow
from antares_studio.domain.model import AssetLicense, Canvas
from antares_studio.persistence.schema import project_to_dict
from antares_studio.rendering import ffmpeg as ff
from antares_studio.resources.templates import create_project
from antares_studio.timeline.evaluator import evaluate
from tests.integration.test_audio import make_wav

pytestmark = [pytest.mark.ui, pytest.mark.render, pytest.mark.slow]
needs_ffmpeg = pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg absent")


@pytest.fixture
def window(qtbot):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    return w


@needs_ffmpeg
def test_gate5_p1_moon_phases_end_to_end(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    # 1. nouveau projet 16:9 depuis le modèle (ce que fait l'assistant « Nouveau projet »)
    from antares_studio.app.document import ProjectDocument

    project = create_project(
        "Pourquoi la Lune change-t-elle de forme ?", Canvas(1920, 1080, 30, 1), "moon_phases", 3
    )
    window._set_document(ProjectDocument(project))
    scene = window.document.scene
    assert scene is not None and scene.duration_frames == 90
    names = {n.name for n in scene.nodes}
    assert {"Soleil", "Terre", "Lune", "Avertissement d'échelle"} <= names
    # la Lune tourne : positions différentes à 0 et à mi-parcours
    moon = next(n for n in scene.nodes if n.name == "Lune")
    p0 = next(s for s in evaluate(project, scene.id, 0).nodes if s.id == moon.id).position
    p1 = next(s for s in evaluate(project, scene.id, 45).nodes if s.id == moon.id).position
    assert p0 != p1
    # 2. modification par l'inspecteur (sans code) et avertissement d'échelle ajouté par le menu puis annulé
    window.document.set_selection([moon.id])
    qtbot.wait(20)
    window.inspector._editors["params.radius"].setValue(30.0)
    window.inspector._editors["params.radius"].editingFinished.emit()
    assert moon.params["radius"] == 30.0
    extra = window.add_scale_warning()
    assert extra is not None and extra.kind == "callout"
    window.act_undo.trigger()  # on garde l'avertissement du modèle seulement
    assert all(n.id != extra.id for n in scene.nodes)
    # 3. enregistrer, importer la voix off, la placer à 0,5 s, renseigner sa provenance
    root = tmp_path / "Lune.antares"
    window.document.save(root)
    voice = tmp_path / "voix.wav"
    make_wav(voice, 2.0, lead_silence=0.0)
    window.document.set_frame(15)
    clip = window.narration.audio.add_audio_file(voice)
    assert clip is not None and clip.offset_frames == 15
    from antares_studio.domain.commands import SetAssetLicense

    window.document.push(
        SetAssetLicense(
            clip.asset_id,
            AssetLicense(author="Voix : l'enseignant·e", license="own-work", redistribution_allowed=True),
        )
    )
    # 4. sous-titres : deux blocs saisis dans l'onglet
    window.document.set_frame(0)
    window.narration.subtitles.add_at_current_frame()
    window.document.set_frame(45)
    window.narration.subtitles.add_at_current_frame()
    subs = scene.subtitles
    assert len(subs) == 2
    subs[0].text = "La Lune tourne autour de la Terre."
    subs[0].end_frame = 45  # fin ajustée dans le tableau : pas de chevauchement
    subs[1].text = "Nous voyons la partie éclairée par le Soleil."
    window.document.version += 1
    # 5. scène de crédits depuis la bibliothèque, puis retour à la scène principale
    window.add_template_scene("credits")
    credits_scene = project.scenes[-1]
    assert credits_scene.name == "Crédits"
    window.document.set_scene(scene.id)
    # 6. inventaire : la voix est documentée, aucun avertissement de provenance
    window.library.tabs.setCurrentIndex(3)
    qtbot.wait(20)
    assert window.library.assets.topLevelItemCount() == 1
    assert window.library.assets.topLevelItem(0).text(1) == "complète"
    # 7. export final 1080p / 30 fps
    window.document.save()
    dlg = ExportDialog(window.document, window.settings, window)
    qtbot.addWidget(dlg)
    dlg.profile.setCurrentIndex(dlg.profile.findData("final_1080p"))
    out = tmp_path / "lune.mp4"
    dlg.path_edit.setText(str(out))
    dlg.start()
    qtbot.waitUntil(lambda: dlg._worker is None, timeout=180000)
    assert dlg.render_result is not None, dlg.status.text()
    probe = dlg.render_result.probe
    assert (probe.width, probe.height, probe.nb_frames, probe.has_audio) == (1920, 1080, 90, True)
    assert probe.fps.numerator == 30 and probe.fps.denominator == 1
    assert dlg.render_result.plan.warnings == ()
    srt = (tmp_path / "lune.srt").read_text(encoding="utf-8")
    assert "La Lune tourne autour de la Terre." in srt and "00:00:01,500 -->" in srt
    credits = (tmp_path / "lune.credits.txt").read_text(encoding="utf-8")
    assert "NASA Science — Moon phases" in credits and "voix.wav — Voix : l'enseignant·e" in credits
    manifest = json.loads(dlg.render_result.manifest_path.read_text(encoding="utf-8"))
    assert (
        manifest["scientific_metadata"]["to_scale"] is False and manifest["credits"] == credits.splitlines()
    )
    # 8. fermer et rouvrir : rien n'est perdu (objets, animations, audio, sous-titres, licence, métadonnées)
    snapshot = project_to_dict(project)
    assert not window.document.is_dirty
    w2 = MainWindow()
    qtbot.addWidget(w2, before_close_func=lambda win: win.document.undo.mark_clean())
    assert w2.open_project_path(root)
    assert project_to_dict(w2.document.project) == snapshot
    for f in (0, 45, 89):
        assert evaluate(w2.document.project, scene.id, f) == evaluate(project, scene.id, f)
    sub = w2.document.project.scene(scene.id).subtitle_at(50)
    assert sub is not None and sub.text == "Nous voyons la partie éclairée par le Soleil."
    w2.close()
    assert out.stat().st_size > 10_000

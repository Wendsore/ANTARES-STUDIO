"""Projets d'exemple : complets, lisibles (sous-titres valides) et sans ressource externe."""

from __future__ import annotations

from fractions import Fraction

import pytest

from antares_studio.audio.subtitles import check_subtitles
from antares_studio.domain.model import TRANSITIONS, Canvas
from antares_studio.persistence.schema import project_from_dict, project_to_dict
from antares_studio.resources.examples import EXAMPLES, build_example
from antares_studio.timeline.evaluator import evaluate


@pytest.mark.parametrize("example_id", list(EXAMPLES))
def test_example_is_a_finished_multi_scene_video(example_id: str) -> None:
    project = build_example(example_id)
    fps = Fraction(project.canvas.fps)
    assert len(project.scenes) >= 3 and not project.assets  # aucun fichier externe
    assert project.scenes[0].nodes[0].params["text"] == EXAMPLES[example_id].title
    assert project.scenes[-1].name.startswith("Crédits")
    assert all(s.transition.kind in TRANSITIONS for s in project.scenes)
    assert any(s.markers for s in project.scenes)
    assert all(not s.audio for s in project.scenes)  # pas de voix : annoncé honnêtement à l'accueil
    for scene in project.scenes:
        assert check_subtitles(scene.subtitles, scene.duration_frames, fps) == [], scene.name
        for frame in (0, scene.duration_frames // 2, scene.duration_frames - 1):
            evaluate(project, scene.id, frame)
    credits = " ".join(str(n.params.get("text", "")) for n in project.scenes[-1].nodes)
    assert all(src["label"] in credits for src in project.scientific_metadata.get("sources", []))
    again = project_from_dict(project_to_dict(project))
    assert [len(s.subtitles) for s in again.scenes] == [len(s.subtitles) for s in project.scenes]


def test_examples_do_not_mix_representations() -> None:
    """La représentation (schéma, modèle, simulation) est déclarée pour tout le projet : un seul type."""
    from antares_studio.resources.templates import TEMPLATES, create_project

    for ex in EXAMPLES.values():
        kinds = {
            create_project("x", Canvas(), s.template).scientific_metadata.get("representation")
            for s in ex.scenes
            if s.template not in ("intro", "credits")
        }
        assert len(kinds) == 1, ex.title
        assert all(s.template in TEMPLATES for s in ex.scenes)

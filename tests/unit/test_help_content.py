"""Aide intégrée : rubriques présentes, liens et images valides, sections générées, recherche, tutoriels."""

from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest

from antares_studio.domain.model import Canvas, Node
from antares_studio.help import topics
from antares_studio.help.tutorials import TUTORIALS, TUTORIALS_BY_ID, UI_KEYS, TutorialContext, TutorialRun
from antares_studio.resources.templates import TEMPLATES, create_project

IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
RUNTIME_KEYS = {"raccourcis"}  # fournie par la fenêtre principale (raccourcis réellement liés)


def test_every_topic_has_its_file_and_every_file_is_a_topic() -> None:
    files = {p.stem for p in topics.HELP_DIR.glob("*.md")}
    ids = [t.id for t in topics.TOPICS]
    assert len(ids) == len(set(ids)), "identifiant de rubrique en double"
    assert files == set(ids)
    assert topics.DEFAULT_TOPIC in topics.TOPICS_BY_ID


@pytest.mark.parametrize("topic", topics.TOPICS, ids=lambda t: t.id)
def test_topic_starts_with_title_and_links_resolve(topic: topics.Topic) -> None:
    raw = topics.raw_markdown(topic.id)
    assert raw.startswith("# "), "une rubrique commence par son titre"
    for target in topics.internal_links(raw):
        assert target.removesuffix(".md") in topics.TOPICS_BY_ID, f"lien cassé : {target}"
    for image in IMAGE.findall(raw):
        path = (topics.HELP_DIR / image).resolve()
        assert path.is_file() and topics.HELP_DIR in path.parents, f"image absente : {image}"
    for key in topics.AUTO.findall(raw):
        assert key in topics.GENERATED or key in RUNTIME_KEYS, f"section automatique inconnue : {key}"


def test_generated_sections_list_the_real_catalogues() -> None:
    from antares_studio.domain.kinds import KINDS
    from antares_studio.timeline.presets import PRESETS

    objects = topics.topic_markdown("objets")
    assert all(f"**{spec.label}**" in objects for spec in KINDS.values())
    animations = topics.topic_markdown("animations")
    assert all(f"### {spec.label}" in animations for spec in PRESETS.values())
    templates = topics.topic_markdown("modeles")
    assert all(f"**{label}**" in templates for label, _b in TEMPLATES.values())
    assert all(t.title in topics.topic_markdown("tutoriels") for t in TUTORIALS)
    assert "<!--" not in "".join(topics.topic_markdown(t.id, {"raccourcis": "x"}) for t in topics.TOPICS)


def test_runtime_section_is_injected_and_missing_ones_are_marked() -> None:
    assert "| Ctrl+S |" in topics.topic_markdown("raccourcis", {"raccourcis": "| Ctrl+S | Enregistrer |"})
    assert "section indisponible" in topics.topic_markdown("raccourcis")
    with pytest.raises(KeyError):
        topics.topic_markdown("inexistante")


def test_search_ignores_accents_and_case_and_ranks_titles_first() -> None:
    with_accents = [t.id for t, _ in topics.search("Équation")]
    without = [t.id for t, _ in topics.search("equation")]
    assert with_accents == without and with_accents[0] == "equations"
    assert topics.search("sous-titres")[0][0].id == "sous-titres"
    assert topics.search("x") == [] and topics.search("zzzzqqq") == []
    assert "orbite" in topics.fold(topics.snippet("kepler", "orbite"))


def test_example_csv_is_documented_and_parseable() -> None:
    from antares_studio.science.data import load_csv

    path = topics.EXAMPLES_DIR / "planetes-periode-distance.csv"
    table = load_csv(path)
    assert table.row_count == 8 and not table.diagnostics
    assert path.name in topics.topic_markdown("graphiques")


# --- tutoriels --------------------------------------------------------------------------------------
def _start_context(tutorial_id: str) -> TutorialContext:
    tut = TUTORIALS_BY_ID[tutorial_id]
    project = create_project("Tutoriel", Canvas(), tut.setup_template or "", 20)
    return TutorialContext(project=project, scene_id=project.scenes[0].id, ui=dict.fromkeys(UI_KEYS, 0))


@pytest.mark.parametrize("tutorial", TUTORIALS, ids=lambda t: t.id)
def test_tutorial_structure(tutorial) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.help.tutorials import ACTIONS

    assert tutorial.title.startswith(f"{TUTORIALS.index(tutorial) + 1}. ")
    assert tutorial.steps and tutorial.minutes > 0 and tutorial.summary
    assert tutorial.help_topic in topics.TOPICS_BY_ID
    assert tutorial.setup_template in (None, "") or tutorial.setup_template in TEMPLATES
    for step in tutorial.steps:
        assert step.title and step.body
        assert step.action in ("", *ACTIONS)


@pytest.mark.parametrize("tutorial", TUTORIALS, ids=lambda t: t.id)
def test_no_step_validates_without_an_action(tutorial) -> None:  # type: ignore[no-untyped-def]
    """Au départ, rien n'a bougé : aucune vérification ne doit être vraie (pas de validation gratuite)."""
    ctx = _start_context(tutorial.id)
    for step in tutorial.steps:
        if step.check is not None:
            assert not step.check(ctx, ctx), f"{tutorial.id} : « {step.title} » validée sans action"


def test_checks_detect_the_real_changes() -> None:
    tut = TUTORIALS_BY_ID["premiere-scene"]
    base = _start_context("premiere-scene")
    run = TutorialRun(tut, base)
    project = copy.deepcopy(base.project)  # le contexte de départ reste intact
    project.scenes[0].nodes.append(Node.create("circle", "Cercle 1"))
    after = TutorialContext(project, base.scene_id, ui=base.ui)
    assert run.update(after) and 0 in run.completed
    run.next(after)
    moved = copy.deepcopy(after.project)
    moved.scenes[0].nodes[0].position = [10.0, 20.0]
    assert run.update(TutorialContext(moved, base.scene_id, ui=base.ui))


def test_run_navigation_is_bounded() -> None:
    tut = TUTORIALS_BY_ID["interface"]
    ctx = _start_context("interface")
    run = TutorialRun(tut, ctx)
    run.go(-5, ctx)
    assert run.index == 0
    run.go(999, ctx)
    assert run.index == len(tut.steps) - 1
    assert Path(topics.topic_path(tut.help_topic)).is_file()

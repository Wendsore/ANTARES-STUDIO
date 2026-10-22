"""Interpolations (dont courbe de Bézier), repères, transitions de scène, rôle audio, macros d'annulation."""

from __future__ import annotations

import json

import pytest

from antares_studio.domain.commands import (
    AddMarker,
    Batch,
    RemoveMarker,
    SetKeyframe,
    SetKeyframeEasing,
    SetMarkerAttr,
    SetProperty,
    SetSceneProperty,
    UndoStack,
)
from antares_studio.domain.model import AudioClip, Keyframe, Marker, SceneTransition, Track
from antares_studio.domain.validation import validate_project
from antares_studio.persistence.schema import ProjectFormatError, project_from_dict, project_to_dict
from antares_studio.timeline.easing import EASING_LABELS, apply_easing, cubic_bezier
from antares_studio.timeline.evaluator import sample_track
from tests.unit.helpers import earth_moon_project


def test_cubic_bezier_matches_reference_points() -> None:
    # (0,0,1,1) est la droite ; la courbe CSS « ease » est connue : ≈ 0,8024 à mi-temps
    for i in range(11):
        assert cubic_bezier(0.0, 0.0, 1.0, 1.0, i / 10) == pytest.approx(i / 10, abs=1e-6)
    assert cubic_bezier(0.25, 0.1, 0.25, 1.0, 0.5) == pytest.approx(0.8024, abs=1e-3)
    assert cubic_bezier(0.25, 0.1, 0.25, 1.0, 0.0) == 0.0
    assert cubic_bezier(0.25, 0.1, 0.25, 1.0, 1.0) == 1.0
    # dépassement autorisé en y (rebond), monotone en x même si x1, x2 sont hors bornes
    assert max(cubic_bezier(0.3, 1.6, 0.6, 1.4, i / 50) for i in range(51)) > 1.0
    assert cubic_bezier(-3.0, 0.0, 4.0, 1.0, 0.5) == pytest.approx(cubic_bezier(0.0, 0.0, 1.0, 1.0, 0.5))


def test_every_easing_has_a_label_and_bezier_uses_its_points() -> None:
    from antares_studio.domain.model import EASINGS

    assert list(EASING_LABELS) == list(EASINGS)
    assert apply_easing("bezier", 0.5) == pytest.approx(cubic_bezier(0.25, 0.1, 0.25, 1.0, 0.5))
    assert apply_easing("bezier", 0.5, [0.0, 0.0, 1.0, 1.0]) == pytest.approx(0.5)
    track = Track("n", "opacity", [Keyframe(0, 0.0, "bezier", [0.9, 0.0, 1.0, 0.1]), Keyframe(10, 1.0)])
    assert sample_track(track, 5) == pytest.approx(cubic_bezier(0.9, 0.0, 1.0, 0.1, 0.5))
    assert sample_track(track, 5) < 0.1  # départ très lent : la courbe est bien appliquée


def test_set_keyframe_keeps_existing_interpolation() -> None:
    """Corriger la valeur d'une clé ne doit plus remettre son interpolation à « linéaire »."""
    project, scene, earth, _ = earth_moon_project()
    stack = UndoStack(project)
    stack.push(SetKeyframe(scene.id, earth.id, "opacity", 0, 0.0, "ease_out"))
    stack.push(SetKeyframeEasing(scene.id, earth.id, "opacity", 0, "bezier", [0.1, 0.2, 0.3, 0.4]))
    stack.push(SetKeyframe(scene.id, earth.id, "opacity", 0, 0.5))
    kf = scene.track_for(earth.id, "opacity").keyframes[0]  # type: ignore[union-attr]
    assert (kf.value, kf.easing, kf.bezier) == (0.5, "bezier", [0.1, 0.2, 0.3, 0.4])
    stack.undo()
    stack.undo()
    kf = scene.track_for(earth.id, "opacity").keyframes[0]  # type: ignore[union-attr]
    assert (kf.value, kf.easing, kf.bezier) == (0.0, "ease_out", None)
    with pytest.raises(KeyError):
        stack.push(SetKeyframeEasing(scene.id, earth.id, "opacity", 99, "linear"))


def test_markers_transition_and_role_roundtrip_and_old_files_unchanged() -> None:
    project, scene, earth, _ = earth_moon_project()
    before = project_to_dict(project)
    assert "markers" not in before["scenes"][0] and "transition" not in before["scenes"][0]
    stack = UndoStack(project)
    marker = Marker.create(45, "La Lune passe devant")
    stack.push(AddMarker(scene.id, marker))
    stack.push(SetMarkerAttr(scene.id, marker.id, "label", "Éclipse"))
    stack.push(SetSceneProperty(scene.id, "transition", SceneTransition("slide_left", 20)))
    scene.tracks.append(Track(earth.id, "opacity", [Keyframe(0, 0.0, "bezier", [0.2, 0.0, 0.8, 1.0])]))
    scene.audio.append(AudioClip.create("asset-000000000000", "Musique", role="music"))
    data = json.loads(json.dumps(project_to_dict(project)))
    again = project_from_dict(data)
    assert again == project
    assert again.scenes[0].markers[0].label == "Éclipse"
    assert again.scenes[0].transition == SceneTransition("slide_left", 20)
    # le rôle par défaut (voix) n'est pas écrit : un ancien projet relu reste octet pour octet identique
    assert project_to_dict(project_from_dict(before)) == before
    stack.undo()
    assert scene.transition == SceneTransition()
    stack.push(RemoveMarker(scene.id, marker.id))
    assert not scene.markers
    stack.undo()
    assert scene.markers[0].id == marker.id


def test_invalid_new_fields_are_reported() -> None:
    project, scene, earth, _ = earth_moon_project()
    scene.markers.append(Marker("pas-un-id", -3))
    scene.transition = SceneTransition("explosion", 0)
    scene.audio.append(AudioClip.create("asset-000000000000", role="chorale"))
    scene.tracks.append(Track(earth.id, "opacity", [Keyframe(0, 0.0, "bezier", [1.5, 0.0, 0.5, 1.0])]))
    messages = " | ".join(str(i) for i in validate_project(project))
    for needle in (
        "repère",
        "image entière",
        "transition inconnue",
        "durée entière",
        "rôle inconnu",
        "bezier",
    ):
        assert needle in messages
    data = project_to_dict(project)
    data["scenes"][0]["tracks"][-1]["keyframes"][0]["bezier"] = [0.1, 0.2]
    with pytest.raises(ProjectFormatError, match="quatre nombres"):
        project_from_dict(data)


def test_macro_is_a_single_undo_step_and_aborts_cleanly() -> None:
    project, scene, earth, moon = earth_moon_project()
    stack = UndoStack(project)
    notified: list[int] = []
    stack.listeners.append(lambda: notified.append(1))
    stack.begin_macro("Aligner")
    stack.push(SetProperty(scene.id, earth.id, "position.x", 1.0))
    stack.begin_macro("imbriquée")
    stack.push(SetProperty(scene.id, moon.id, "position.x", 2.0))
    stack.end_macro()
    assert not notified  # rien n'est publié avant la fin de la macro
    stack.end_macro()
    assert len(notified) == 1 and stack.undo_label == "Aligner"
    assert isinstance(stack._undo[-1], Batch)
    stack.undo()
    assert (earth.position[0], moon.position[0]) == (960.0, 1260.0)
    stack.redo()
    assert (earth.position[0], moon.position[0]) == (1.0, 2.0)
    stack.begin_macro("échoue")
    stack.push(SetProperty(scene.id, earth.id, "position.x", 50.0))
    stack.abort_macro()
    assert earth.position[0] == 1.0 and stack.undo_label == "Aligner"
    stack.begin_macro("vide")
    stack.end_macro()
    assert stack.undo_label == "Aligner"
    with pytest.raises(RuntimeError):
        stack.end_macro()

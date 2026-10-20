"""MOD-01, MOD-10, MOD-12 — modèle, identifiants, validation, cycles."""

from __future__ import annotations

from antares_studio.domain.ids import is_valid_id, new_id
from antares_studio.domain.kinds import KINDS, animatable_properties
from antares_studio.domain.model import Keyframe, Track
from antares_studio.domain.properties import get_property, set_property
from antares_studio.domain.validation import find_parent_cycles, validate_project
from tests.unit.helpers import earth_moon_project, make_node


def test_mod01_100_objects_have_unique_ids_and_valid_structure() -> None:
    project, scene, _, _ = earth_moon_project()
    kinds = list(KINDS)
    for i in range(100):
        scene.nodes.append(make_node(kinds[i % len(kinds)], f"objet {i}"))
    ids = [n.id for n in scene.nodes]
    assert len(set(ids)) == len(ids)
    assert all(is_valid_id(i) for i in ids)
    assert validate_project(project) == []


def test_new_id_format_and_prefix_validation() -> None:
    assert is_valid_id(new_id("node"))
    assert not is_valid_id("node-xyz")
    assert not is_valid_id(42)
    try:
        new_id("Bad Prefix")
    except ValueError:
        pass
    else:
        raise AssertionError("préfixe invalide accepté")


def test_mod12_parent_cycle_detected() -> None:
    project, scene, earth, moon = earth_moon_project()
    earth.parent_id = moon.id
    moon.parent_id = earth.id
    cycles = find_parent_cycles(scene)
    assert cycles and set(cycles[0][:-1]) == {earth.id, moon.id}
    issues = validate_project(project)
    assert any("cycle" in i.message for i in issues)


def test_self_parent_rejected() -> None:
    project, scene, earth, _ = earth_moon_project()
    earth.parent_id = earth.id
    assert any("propre parent" in i.message for i in validate_project(project))


def test_mod10_invalid_values_reported_with_path() -> None:
    project, scene, earth, moon = earth_moon_project()
    earth.params["radius"] = -5
    moon.style["fill"] = "bleu"
    scene.tracks.append(
        Track(target_id="node-000000000000", property="opacity", keyframes=[Keyframe(0, 1.0)])
    )
    scene.tracks.append(Track(target_id=earth.id, property="params.text", keyframes=[Keyframe(0, 1.0)]))
    scene.tracks.append(
        Track(
            target_id=earth.id, property="opacity", keyframes=[Keyframe(0, 1.0, "bounce"), Keyframe(-1, 2.0)]
        )
    )
    msgs = {i.path: i.message for i in validate_project(project)}
    assert any("params.radius" in p for p in msgs)
    assert any("style.fill" in p for p in msgs)
    assert any("target_id" in p and "cible inconnue" in m for p, m in msgs.items())
    assert any("non animable" in m for m in msgs.values())
    assert any("interpolation inconnue" in m for m in msgs.values())
    assert any("frame entière" in m for m in msgs.values())
    assert any("entre 0 et 1" in m for m in msgs.values())


def test_property_access_and_type_checks() -> None:
    node = make_node("circle", "c")
    set_property(node, "position.x", 12.5)
    set_property(node, "params.radius", 42.0)
    set_property(node, "style.fill", "#FF000080")
    assert get_property(node, "position.x") == 12.5
    assert get_property(node, "params.radius") == 42.0
    for path, bad in (
        ("opacity", 1.5),
        ("params.radius", "x"),
        ("style.fill", "red"),
        ("visible", 1),
        ("position.y", float("nan")),
    ):
        try:
            set_property(node, path, bad)
        except ValueError:
            continue
        raise AssertionError(f"{path}={bad!r} accepté")


def test_animatable_properties_per_kind() -> None:
    assert "params.radius" in animatable_properties("circle")
    assert "params.text" not in animatable_properties("text")
    assert "style.fill" in animatable_properties("text")
    assert "opacity" in animatable_properties("group")

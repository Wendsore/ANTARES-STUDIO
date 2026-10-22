"""TIM-01 … TIM-12 — évaluateur pur, interpolation, keyframes, presets."""

from __future__ import annotations

import math

import pytest

from antares_studio.domain.colors import format_color, mix_color, parse_color
from antares_studio.domain.model import Canvas, Keyframe, Track
from antares_studio.timeline.easing import apply_easing
from antares_studio.timeline.evaluator import evaluate, interpolate_value, sample_track
from antares_studio.timeline.presets import PRESETS, apply_preset
from tests.unit.helpers import earth_moon_project, make_node


def test_tim01_linear_midpoint() -> None:
    t = Track("n", "opacity", [Keyframe(0, 0.0), Keyframe(100, 10.0)])
    assert sample_track(t, 50) == pytest.approx(5.0)
    assert sample_track(t, 0) == 0.0
    assert sample_track(t, 100) == 10.0


def test_tim02_frame_rate_rational_conversions() -> None:
    c = Canvas(fps_num=30, fps_den=1)
    assert c.seconds_to_frame(10.0) == 300
    assert c.frame_to_seconds(300) == 10.0
    ntsc = Canvas(fps_num=30000, fps_den=1001)
    assert ntsc.frame_to_seconds(30000) == pytest.approx(1001.0)
    assert ntsc.seconds_to_frame(1.0) == 30


def test_tim03_same_frame_collision_last_wins() -> None:
    t = Track("n", "opacity", [Keyframe(10, 1.0), Keyframe(10, 0.25)])
    assert sample_track(t, 10) == 0.25
    assert len(t.sorted_keyframes()) == 1
    t.set_keyframe(10, 0.5)
    assert len(t.keyframes) == 2  # la liste brute garde les deux ; set_keyframe met à jour la première
    assert sample_track(t, 10) == 0.25 or sample_track(t, 10) == 0.5


def test_tim05_easings_monotone_and_bounded() -> None:
    for name in ("linear", "ease_in", "ease_out", "ease_in_out"):
        prev = -1.0
        for i in range(101):
            v = apply_easing(name, i / 100)
            assert 0.0 <= v <= 1.0
            assert v >= prev - 1e-12
            prev = v
        assert apply_easing(name, 0.0) == 0.0
        assert apply_easing(name, 1.0) == 1.0
    assert apply_easing("step", 0.99) == 0.0 and apply_easing("step", 1.0) == 1.0
    assert apply_easing("ease_in_out", 0.5) == pytest.approx(0.5)


def test_tim06_angles_interpolated_as_declared_full_turn() -> None:
    t = Track("n", "rotation_deg", [Keyframe(0, 350.0), Keyframe(100, 370.0)])
    assert sample_track(t, 50) == pytest.approx(360.0)
    t2 = Track("n", "rotation_deg", [Keyframe(0, 0.0), Keyframe(300, 360.0)])
    assert sample_track(t2, 150) == pytest.approx(180.0)


def test_tim07_orbit_preset_cardinal_points() -> None:
    project, scene, earth, moon = earth_moon_project(duration_frames=300)
    tracks = apply_preset(
        "orbit",
        moon,
        {"center_x": 960, "center_y": 540, "radius": 300, "duration_frames": 300, "samples_per_turn": 360},
    )
    scene.tracks += tracks
    s0 = evaluate(project, scene.id, 0).node(moon.id)
    s75 = evaluate(project, scene.id, 75).node(moon.id)
    s150 = evaluate(project, scene.id, 150).node(moon.id)
    s225 = evaluate(project, scene.id, 225).node(moon.id)
    s299 = evaluate(project, scene.id, 299).node(moon.id)
    assert s0.position == pytest.approx((1260.0, 540.0))
    assert s75.position == pytest.approx((960.0, 240.0), abs=1e-6)  # sens trigonométrique écran : y décroît
    assert s150.position == pytest.approx((660.0, 540.0), abs=1e-6)
    assert s225.position == pytest.approx((960.0, 840.0), abs=1e-6)
    # dernière frame proche du point de départ, boucle sans saut
    assert math.dist(s299.position, (1260.0, 540.0)) < 300 * 2 * math.pi / 300 + 1e-6


def test_tim08_scrub_is_pure() -> None:
    project, scene, earth, moon = earth_moon_project()
    scene.tracks += apply_preset("translate", moon, {"dx": 100, "dy": 50, "duration_frames": 100})
    a = evaluate(project, scene.id, 42)
    evaluate(project, scene.id, 99)
    evaluate(project, scene.id, 0)
    b = evaluate(project, scene.id, 42)
    assert a == b


def test_tim09_keyframe_order_invariant() -> None:
    kfs = [Keyframe(0, 0.0), Keyframe(100, 10.0), Keyframe(50, 2.0)]
    t1 = Track("n", "opacity", list(kfs))
    t2 = Track("n", "opacity", list(reversed(kfs)))
    for f in (0, 25, 50, 75, 100):
        assert sample_track(t1, f) == sample_track(t2, f)


def test_tim10_invalid_preset_params_rejected() -> None:
    node = make_node("circle", "c")
    with pytest.raises(ValueError):
        apply_preset("orbit", node, {"duration_frames": 0})
    with pytest.raises(ValueError):
        apply_preset("nope", node)


def test_tim11_parent_transform_and_opacity_cascade() -> None:
    project, scene, earth, moon = earth_moon_project()
    group = make_node("group", "G", position=[100.0, 100.0], rotation_deg=90.0, opacity=0.5)
    scene.nodes.insert(0, group)
    moon.parent_id = group.id
    moon.position = [10.0, 0.0]
    moon.opacity = 0.5
    st = evaluate(project, scene.id, 0)
    ms = st.node(moon.id)
    x, y = ms.world[4], ms.world[5]
    assert (x, y) == pytest.approx((100.0, 110.0), abs=1e-9)  # rotation 90° : (10,0) -> (0,10)
    assert ms.world_opacity == pytest.approx(0.25)
    group.visible = False
    assert evaluate(project, scene.id, 0).node(moon.id).visible is False


def test_tim_cycle_in_evaluation_raises() -> None:
    project, scene, earth, moon = earth_moon_project()
    earth.parent_id = moon.id
    moon.parent_id = earth.id
    with pytest.raises(ValueError, match="cycle"):
        evaluate(project, scene.id, 0)


def test_interpolate_value_types() -> None:
    assert interpolate_value(0.0, 10.0, 0.25) == 2.5
    assert interpolate_value([0.0, 0.0], [10.0, 20.0], 0.5) == [5.0, 10.0]
    assert interpolate_value("#000000", "#FFFFFF", 0.5) == "#808080"
    assert interpolate_value("a", "b", 0.5) == "a" and interpolate_value("a", "b", 1.0) == "b"
    assert interpolate_value(True, False, 0.5) is True


def test_color_helpers() -> None:
    assert parse_color("#FF8000") == pytest.approx((1.0, 0.5019607843, 0.0, 1.0))
    assert format_color((1.0, 0.0, 0.0, 0.5)) == "#FF000080"
    assert mix_color("#000000FF", "#FFFFFF00", 0.5) == "#80808080"


def test_all_mvp_presets_generate_valid_tracks() -> None:
    project, scene, earth, moon = earth_moon_project()
    from antares_studio.domain.validation import validate_project

    chart = make_node("chart", "Courbe")
    formula = make_node("formula", "Équation")
    scene.nodes += [chart, formula]
    targets = {"trace": chart, "morph": formula}  # « tracer » vise un graphique, « transformer » une formule
    for pid in PRESETS:
        tracks = apply_preset(pid, targets.get(pid, moon))
        assert tracks, pid
        scene.tracks = tracks
        assert validate_project(project) == [], pid
        evaluate(project, scene.id, 30)


def test_rotation_preset_full_turn_loops_without_jump() -> None:
    project, scene, earth, moon = earth_moon_project(duration_frames=300)
    scene.tracks = apply_preset("rotate", earth, {"duration_frames": 300, "turns": 1})
    r0 = evaluate(project, scene.id, 0).node(earth.id).rotation_deg
    r150 = evaluate(project, scene.id, 150).node(earth.id).rotation_deg
    r299 = evaluate(project, scene.id, 299).node(earth.id).rotation_deg
    assert r0 == 0.0 and r150 == pytest.approx(180.0)
    assert 360.0 - r299 == pytest.approx(360.0 / 300)


def test_evaluate_frame_clamped_to_scene_duration() -> None:
    project, scene, earth, moon = earth_moon_project(duration_frames=10)
    assert evaluate(project, scene.id, 500).frame == 9
    assert evaluate(project, scene.id, -5).frame == 0

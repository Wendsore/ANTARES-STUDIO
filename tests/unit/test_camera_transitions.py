"""Caméra 2D (cadrage animé) et transitions d'entrée de scène : mêmes images à l'export et dans l'éditeur."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor

from antares_studio.domain.model import Canvas, Keyframe, Scene, SceneTransition, Track
from antares_studio.domain.validation import validate_project
from antares_studio.rendering.transitions import FrameRenderer, transition_at
from antares_studio.timeline.evaluator import apply_affine, evaluate, evaluate_scene
from tests.unit.helpers import earth_moon_project, make_node


def _camera(scene: Scene, x: float, y: float, zoom: float = 1.0, rotation: float = 0.0):  # type: ignore[no-untyped-def]
    cam = make_node("camera", "Caméra", position=[x, y], rotation_deg=rotation)
    cam.params["zoom"] = zoom
    scene.nodes.append(cam)
    return cam


def test_camera_zoom_brings_target_to_center_and_scales() -> None:
    project, scene, earth, moon = earth_moon_project()
    _camera(scene, 1260.0, 540.0, zoom=2.0)  # vise la Lune, zoom ×2
    st = evaluate(project, scene.id, 0)
    m = st.node(moon.id).world
    assert (m[4], m[5]) == pytest.approx((960.0, 540.0))  # la Lune arrive au centre de l'image
    assert (m[0], m[3]) == pytest.approx((2.0, 2.0))
    e = st.node(earth.id).world
    assert (e[4], e[5]) == pytest.approx((960.0 - 2 * 300.0, 540.0))
    assert st.camera_id is not None and apply_affine(st.camera, 1260.0, 540.0) == pytest.approx(
        (960.0, 540.0)
    )
    # vue de travail (sans caméra) et ancien appel sans canevas : rien ne bouge
    assert evaluate(project, scene.id, 0, use_camera=False).node(moon.id).world[4] == pytest.approx(1260.0)
    assert evaluate_scene(scene, 0).node(moon.id).world[4] == pytest.approx(1260.0)


def test_camera_rotation_scale_animation_and_visibility() -> None:
    project, scene, earth, moon = earth_moon_project()
    cam = _camera(scene, 960.0, 540.0, rotation=90.0)
    st = evaluate(project, scene.id, 0)
    # caméra inclinée de 90° : la scène tourne de -90° ; la Lune (à droite de la Terre) passe au-dessus
    m = st.node(moon.id).world
    assert (m[4], m[5]) == pytest.approx((960.0, 540.0 - 300.0))
    cam.rotation_deg = 0.0
    cam.scale = [2.0, 2.0]  # cadre agrandi aux poignées : la caméra recule (zoom 0,5)
    assert evaluate(project, scene.id, 0).node(moon.id).world[4] == pytest.approx(960.0 + 150.0)
    cam.scale = [1.0, 1.0]
    scene.tracks.append(Track(cam.id, "params.zoom", [Keyframe(0, 1.0), Keyframe(10, 3.0)]))
    assert evaluate(project, scene.id, 5).node(moon.id).world[0] == pytest.approx(2.0)
    cam.visible = False
    assert evaluate(project, scene.id, 5).camera_id is None
    assert validate_project(project) == []


def _two_scenes(kind: str, duration: int = 9):  # type: ignore[no-untyped-def]
    project, s1, _e, _m = earth_moon_project(duration_frames=10)
    project.canvas = Canvas(320, 180, 30, 1)
    s1.nodes.clear()
    s1.background = "#FF0000"
    s2 = Scene.create("Bleu", duration_frames=20, background="#0000FF")
    s2.transition = SceneTransition(kind, duration)
    project.scenes.append(s2)
    return project, s1, s2


def _pixel(img, x: int, y: int) -> tuple[int, int, int]:  # type: ignore[no-untyped-def]
    c = QColor(img.pixel(x, y))
    return c.red(), c.green(), c.blue()


def test_transition_window_and_progress() -> None:
    project, s1, s2 = _two_scenes("fade")
    assert transition_at(project, s1.id, 0) is None
    kind, u, prev = transition_at(project, s2.id, 0)  # type: ignore[misc]
    assert (kind, prev) == ("fade", s1.id) and u == pytest.approx(0.1)
    assert transition_at(project, s2.id, 8)[1] == pytest.approx(0.9)  # type: ignore[index]
    assert transition_at(project, s2.id, 9) is None
    s1.transition = SceneTransition("fade_black", 4)
    assert transition_at(project, s1.id, 0)[2] is None  # type: ignore[index]  # première scène : depuis le noir


@pytest.mark.parametrize(
    ("kind", "frame", "check"),
    [
        ("fade", 4, lambda left, right: left == right and 100 < left[0] < 155 and 100 < left[2] < 155),
        ("fade_black", 2, lambda left, right: left == right and left[2] == 0 and 0 < left[0] < 255),
        ("slide_left", 4, lambda left, right: left == (255, 0, 0) and right == (0, 0, 255)),
        ("wipe", 4, lambda left, right: left == (0, 0, 255) and right == (255, 0, 0)),
    ],
)
def test_frame_renderer_composes_previous_last_image(qapp, kind, frame, check) -> None:  # type: ignore[no-untyped-def]
    project, _s1, s2 = _two_scenes(kind)
    img = FrameRenderer(project).render(s2.id, frame, 320, 180)
    assert check(_pixel(img, 5, 90), _pixel(img, 314, 90)), (_pixel(img, 5, 90), _pixel(img, 314, 90))
    after = FrameRenderer(project).render(s2.id, 15, 320, 180)
    assert _pixel(after, 5, 90) == _pixel(after, 314, 90) == (0, 0, 255)

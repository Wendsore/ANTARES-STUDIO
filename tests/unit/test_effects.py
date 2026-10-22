"""Effets d'objet, filtres de scène, animations d'effet : modèle, fichier, validation et pixels rendus."""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtGui import QColor, QImage

from antares_studio.domain.commands import SetSceneProperty
from antares_studio.domain.effects import (
    EFFECTS,
    OBJECT_LOOKS,
    SCENE_LOOKS,
    SCENE_POST_BY_NAME,
    has_effects,
    post_is_neutral,
)
from antares_studio.domain.kinds import animatable_properties
from antares_studio.domain.model import Canvas
from antares_studio.domain.properties import get_property
from antares_studio.domain.validation import validate_project
from antares_studio.persistence.schema import project_from_dict, project_to_dict
from antares_studio.rendering.effects import apply_scene_post, box_radii, color_matrix, gaussian_blur
from antares_studio.rendering.transitions import FrameRenderer
from antares_studio.resources.templates import create_project, new_node
from antares_studio.timeline.evaluator import evaluate
from antares_studio.timeline.presets import apply_preset

W, H = 320, 180


def _project(*styles: dict, kind: str = "circle"):  # type: ignore[no-untyped-def]
    p = create_project("Effets", Canvas(width=W, height=H), "", 2)
    p.scenes[0].background = "#000000"
    for i, style in enumerate(styles):
        n = new_node(kind, f"Disque {i + 1}", W / 2, H / 2, radius=30.0)
        n.style.update({"fill": "#FF0000", "stroke_width": 0.0, **style})
        p.scenes[0].nodes.append(n)
    return p


def _render(p, frame: int = 0) -> np.ndarray:  # type: ignore[no-untyped-def]
    img = FrameRenderer(p).render(p.scenes[0].id, frame, W, H).convertToFormat(QImage.Format.Format_RGB888)
    arr = np.frombuffer(img.constBits(), np.uint8, count=img.bytesPerLine() * H).reshape(
        H, img.bytesPerLine()
    )
    return arr[:, : W * 3].reshape(H, W, 3).astype(int)


# --- modèle -------------------------------------------------------------------------------------------
def test_effects_are_absent_by_default_and_read_as_defaults() -> None:
    p = _project({})
    node = p.scenes[0].nodes[0]
    assert not any(k.startswith("fx_") for k in node.style)
    for spec in EFFECTS:
        assert get_property(node, f"style.{spec.name}") == spec.default
    assert not has_effects(node.style)
    assert {f"style.{s.name}" for s in EFFECTS} <= set(animatable_properties("circle"))
    assert not any(p.startswith("style.fx_") for p in animatable_properties("camera"))


def test_every_look_uses_known_effects_and_filters() -> None:
    names = {s.name for s in EFFECTS}
    for _label, _desc, values in OBJECT_LOOKS.values():
        assert set(values) <= names
    for _label, _desc, values in SCENE_LOOKS.values():
        assert set(values) <= set(SCENE_POST_BY_NAME)
    assert post_is_neutral(SCENE_LOOKS["none"][2]) and not post_is_neutral(SCENE_LOOKS["cinema"][2])


def test_file_round_trip_keeps_effects_and_omits_empty_filters() -> None:
    p = _project({"fx_glow": 12.0, "fx_glow_color": "#4FC3F7"})
    data = project_to_dict(p)
    assert "post" not in data["scenes"][0]  # fichiers des versions précédentes inchangés
    p.scenes[0].post = {"vignette": 0.4, "grain": 0.1}
    back = project_from_dict(project_to_dict(p))
    assert back.scenes[0].post == {"vignette": 0.4, "grain": 0.1}
    assert back.scenes[0].nodes[0].style["fx_glow_color"] == "#4FC3F7"


def test_validation_rejects_bad_effects_and_unknown_filters() -> None:
    p = _project({"fx_blur": -3.0})
    p.scenes[0].post = {"bloom": 1.0}
    messages = " ".join(i.message for i in validate_project(p))
    assert "fx_blur" in messages or "Flou" in messages
    assert "filtre inconnu" in messages
    assert not validate_project(_project({"fx_blur": 4.0, "fx_shadow": 0.5}))


def test_set_scene_property_post_is_undoable() -> None:
    p = _project({})
    cmd = SetSceneProperty(p.scenes[0].id, "post", {"sepia": 1.0})
    cmd.do(p)
    assert p.scenes[0].post == {"sepia": 1.0}
    cmd.undo(p)
    assert p.scenes[0].post == {}
    with pytest.raises(TypeError):
        SetSceneProperty(p.scenes[0].id, "post", [1]).do(p)


# --- traitement d'image -----------------------------------------------------------------------------
def test_gaussian_blur_preserves_energy_and_spreads() -> None:
    a = np.zeros((41, 41, 4), dtype=np.float32)  # (h, w, canaux)
    a[20, 20, :] = 1.0
    out = gaussian_blur(a, 4.0)
    assert out.sum() == pytest.approx(a.sum(), rel=1e-3)
    assert out[20, 20, 0] < 0.1 and out[20, 26, 0] > 0 and out[26, 20, 0] > 0
    assert sum(box_radii(4.0)) > 0 and box_radii(0.0) == [0, 0, 0]


def test_color_matrix_neutral_and_grayscale() -> None:
    m, b = color_matrix(0.0, 1.0, 1.0, 0.0, 0.0)
    assert np.allclose(m, np.eye(3)) and not b.any()
    m, b = color_matrix(0.0, 1.0, 0.0, 0.0, 0.0)
    rgb = np.array([1.0, 0.0, 0.0]) @ m + b
    assert rgb[0] == pytest.approx(rgb[1]) == pytest.approx(rgb[2])


def test_scene_post_neutral_is_identity_and_grain_is_reproducible(qapp) -> None:  # type: ignore[no-untyped-def]
    img = QImage(64, 36, QImage.Format.Format_RGBA8888_Premultiplied)
    img.fill(QColor("#336699"))
    assert apply_scene_post(img, {}, "s", 0) == img.convertToFormat(
        QImage.Format.Format_RGBA8888_Premultiplied
    )
    a = apply_scene_post(img, {"grain": 0.8}, "scene-1", 5)
    assert a == apply_scene_post(img, {"grain": 0.8}, "scene-1", 5)  # deux exports identiques
    assert a != img.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
    vignette = apply_scene_post(img, {"vignette": 1.0}, "s", 0)
    assert QColor(vignette.pixel(0, 0)).value() < QColor(vignette.pixel(32, 18)).value()


# --- pixels rendus ----------------------------------------------------------------------------------
def test_glow_lights_pixels_outside_the_disc(qapp) -> None:  # type: ignore[no-untyped-def]
    probe = (H // 2, W // 2 + 40)  # 10 px hors du disque de rayon 30
    plain = _render(_project({}))
    glow = _render(_project({"fx_glow": 20.0, "fx_glow_color": "#00FF00", "fx_glow_strength": 2.0}))
    assert plain[probe].sum() == 0
    assert glow[probe][1] > 30 and glow[H // 2, W // 2][0] > 200  # halo vert, disque toujours rouge


def test_shadow_is_offset_and_blur_softens_the_edge(qapp) -> None:  # type: ignore[no-untyped-def]
    shadow = _render(
        _project({"fx_shadow": 1.0, "fx_shadow_blur": 0.0, "fx_shadow_dx": 0.0, "fx_shadow_dy": 0.0})
    )
    p = _project({"fx_shadow": 1.0, "fx_shadow_blur": 2.0, "fx_shadow_dx": 0.0, "fx_shadow_dy": 40.0})
    p.scenes[0].background = "#FFFFFF"
    offset = _render(p)
    assert offset[H // 2 + 40, W // 2].sum() < 100  # ombre noire sous le disque, sur fond blanc
    assert shadow[H // 2, W // 2][0] > 200
    edge = (H // 2, W // 2 + 30)
    sharp, soft = _render(_project({})), _render(_project({"fx_blur": 6.0}))
    assert soft[edge][0] > 0 and soft[H // 2, W // 2 + 36][0] > sharp[H // 2, W // 2 + 36][0]


def test_saturation_zero_renders_grey(qapp) -> None:  # type: ignore[no-untyped-def]
    px = _render(_project({"fx_saturation": 0.0}))[H // 2, W // 2]
    assert abs(px[0] - px[1]) <= 2 and abs(px[1] - px[2]) <= 2 and px[0] > 20


def test_scene_filter_is_applied_by_the_frame_renderer(qapp) -> None:  # type: ignore[no-untyped-def]
    p = _project({})
    p.scenes[0].post = {"saturation": 0.0}
    px = _render(p)[H // 2, W // 2]
    assert abs(px[0] - px[1]) <= 2


# --- animations d'effet -----------------------------------------------------------------------------
@pytest.mark.parametrize("preset_id", ["shake", "flash", "blink", "focus", "glow_pulse"])
def test_effect_presets_build_valid_tracks(preset_id: str) -> None:
    p = _project({})
    scene = p.scenes[0]
    scene.duration_frames = 120
    node = scene.nodes[0]
    tracks = apply_preset(preset_id, node, {})
    assert tracks and all(t.property in animatable_properties("circle") for t in tracks)
    scene.tracks += tracks
    assert not validate_project(p)
    for frame in range(0, 120, 7):
        evaluate(p, scene.id, frame)


def test_shake_is_reproducible_and_returns_home() -> None:
    p = _project({})
    node = p.scenes[0].nodes[0]
    a, b = apply_preset("shake", node, {}), apply_preset("shake", node, {})
    assert [k.value for k in a[0].keyframes] == [k.value for k in b[0].keyframes]
    assert a[0].keyframes[-1].value == node.position[0] and a[1].keyframes[-1].value == node.position[1]
    assert len({k.value for k in a[0].keyframes}) > 3


def test_flash_peaks_then_vanishes() -> None:
    p = _project({})
    scene, node = p.scenes[0], p.scenes[0].nodes[0]
    scene.duration_frames = 120
    scene.tracks += apply_preset("flash", node, {})
    track = scene.track_for(node.id, "style.fx_glow_strength")
    assert track is not None
    first, last = track.keyframes[0], track.keyframes[-1]
    assert first.value == 0.0 and last.value == 0.0 and max(k.value for k in track.keyframes) == 2.5

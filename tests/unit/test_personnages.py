"""Phase 14 : personnages chibis 2D, émotions, poses, tenues, fiches de jeu, dialogue (ADR-0010)."""

from __future__ import annotations

import random
import threading
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from antares_studio.domain import characters
from antares_studio.domain.kinds import (
    OBJECT_VARIANTS,
    check_param_value,
    resolve_variant,
    spec_for,
    split_style,
)
from antares_studio.domain.model import Canvas, Project, Scene, Track
from antares_studio.persistence.store import ProjectStore
from antares_studio.rendering import chibi
from antares_studio.rendering.qt_painter import local_bounds, render_state_to_image
from antares_studio.resources.templates import TEMPLATES, create_project
from antares_studio.timeline.evaluator import evaluate
from tests.unit.helpers import make_node

CHOICE_LISTS = {
    "emotion": characters.EMOTION_CHOICES,
    "pose": characters.POSES,
    "outfit": characters.OUTFITS,
    "hair": characters.HAIRS,
    "beard": characters.BEARDS,
    "glasses": characters.GLASSES,
    "hat": characters.HATS,
    "gaze": characters.GAZES,
    "skin": characters.SKIN_CHOICES,
    "proportions": characters.PROPORTIONS,
}


def _valid(svg: str) -> bool:
    return QSvgRenderer(QByteArray(svg.encode("utf-8"))).isValid()


def _render(params: dict, style: dict | None = None, w: int = 200, h: int = 280) -> np.ndarray:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(w / 2, h / 2)
    chibi.paint_chibi(p, {"height": float(h), **params}, style or {}, None)
    p.end()
    ptr = img.constBits()
    return np.frombuffer(ptr, np.uint8).reshape(h, img.bytesPerLine() // 4, 4)[:, :w].copy()


def test_catalogue_is_pure_data_without_qt() -> None:
    source = Path(characters.__file__).read_text(encoding="utf-8")
    assert "PySide6" not in source and "Qt" not in source.split('"""', 2)[2]


def test_every_choice_of_every_list_gives_a_valid_svg(qapp) -> None:  # type: ignore[no-untyped-def]
    for name, choices in CHOICE_LISTS.items():
        for value, _label in choices:
            svg = chibi.chibi_svg({name: value}, {})
            assert _valid(svg), (name, value)


def test_random_combinations_and_mirror_give_valid_svgs(qapp) -> None:  # type: ignore[no-untyped-def]
    rng = random.Random(14)
    for _ in range(150):
        params = {name: rng.choice(choices)[0] for name, choices in CHOICE_LISTS.items()}
        params["mirror"] = rng.random() < 0.5
        assert _valid(chibi.chibi_svg(params, {"fill": "#123456", "accent": "#ABCDEF"})), params


def test_each_emotion_pose_and_outfit_changes_the_drawing() -> None:
    for name in ("emotion", "pose", "outfit", "hair", "gaze"):
        svgs = {chibi.chibi_svg({name: v}, {}) for v, _l in CHOICE_LISTS[name]}
        assert len(svgs) == len(CHOICE_LISTS[name]), name


def test_identity_and_catalogue_sizes() -> None:
    assert len(characters.EMOTIONS) >= 20 and len(characters.POSES) >= 10
    assert len({e.id for e in characters.EMOTIONS}) == len(characters.EMOTIONS)
    ids = {p.id for p in characters.PERSONALITIES}
    assert {"ironique", "scientifique", "sceptique", "rouspeteur", "ingenieur"} <= ids
    assert characters.PERSONALITIES[0].id == "ingenieur"  # le personnage du porteur en tête
    # toutes les fiches de jeu ne citent que des valeurs connues
    for p in characters.PERSONALITIES:
        for key, value in p.params.items():
            assert value in {v for v, _l in CHOICE_LISTS[key]}, (p.id, key, value)


def test_the_drawing_is_deterministic_and_opaque_at_the_head(qapp) -> None:  # type: ignore[no-untyped-def]
    a = _render({"emotion": "joie"})
    b = _render({"emotion": "joie"})
    assert np.array_equal(a, b)
    assert a[0, 0, 3] == 0 and a[-1, 0, 3] == 0  # coins transparents
    assert a[90, 100, 3] == 255  # visage opaque


def test_mirror_is_a_horizontal_flip(qapp) -> None:  # type: ignore[no-untyped-def]
    a = _render({"emotion": "neutre", "pose": "montre"}).astype(int)
    b = _render({"emotion": "neutre", "pose": "montre", "mirror": True}).astype(int)
    diff = np.abs(a[:, ::-1] - b)[..., 3]
    assert np.mean(diff > 40) < 0.01  # seuls quelques pixels d'anticrénelage diffèrent


def test_signs_stay_readable_when_mirrored() -> None:
    svg = chibi.chibi_svg({"emotion": "doute", "mirror": True}, {})
    head, _, tail = svg.partition("</g>")
    assert "scale(-1,1)" in head and ">?</text>" in tail  # le « ? » est hors du groupe retourné


def test_8_digit_colours_are_read_as_rrggbbaa() -> None:
    svg = chibi.chibi_svg({"outfit": "tshirt"}, {"fill": "#FF000080"})
    assert 'fill="#FF0000"' in svg and "#80FF00" not in svg


def test_kind_spec_and_variants(qapp) -> None:  # type: ignore[no-untyped-def]
    spec = spec_for("character")
    animated = {p.name for p in spec.params if p.animatable}
    assert {"emotion", "pose", "gaze", "outfit", "glasses", "hat", "mirror"} <= animated
    by_name = {p.name: p for p in spec.params}
    for ident in (v for v in OBJECT_VARIANTS if v.startswith("character:")):
        kind, _label, raw = resolve_variant(ident)
        params, style = split_style(raw)
        assert kind == "character"
        for key, value in params.items():
            assert check_param_value(by_name[key], value) is None, (ident, key)
        assert set(style) <= {p.name for p in spec.style}
    assert check_param_value(by_name["emotion"], "inconnue") is not None
    assert len([v for v in OBJECT_VARIANTS if v.startswith("character:")]) == len(characters.PERSONALITIES)


def test_bounds_follow_the_height() -> None:
    node = make_node("character", "Perso")
    node.params["height"] = 560.0
    r = local_bounds(evaluate_single(node))
    assert r.height() == pytest.approx(560.0) and r.width() == pytest.approx(400.0)


def evaluate_single(node):  # type: ignore[no-untyped-def]
    project = Project.create("t", Canvas(320, 180, 30, 1))
    scene = Scene.create("s", duration_frames=30)
    scene.nodes.append(node)
    project.scenes.append(scene)
    return evaluate(project, scene.id, 0).node(node.id)


def test_emotion_switches_in_steps_and_survives_save_and_reload(tmp_path: Path) -> None:
    project = Project.create("Chibi", Canvas(320, 180, 30, 1))
    scene = Scene.create("s", duration_frames=90)
    node = make_node("character", "Perso")
    scene.nodes.append(node)
    track = Track(node.id, "params.emotion")
    track.set_keyframe(0, "neutre")
    track.set_keyframe(60, "colere")
    scene.tracks.append(track)
    project.scenes.append(scene)
    assert evaluate(project, scene.id, 59).node(node.id).params["emotion"] == "neutre"  # pas de mélange
    assert evaluate(project, scene.id, 60).node(node.id).params["emotion"] == "colere"
    store = ProjectStore()
    store.save_atomic(project, tmp_path / "p")
    again = store.load(tmp_path / "p")
    st = evaluate(again, again.scenes[0].id, 75).node(node.id)
    assert st.kind == "character" and st.params["emotion"] == "colere"


def test_dialogue_template_changes_emotions_and_cites_its_source(qapp) -> None:  # type: ignore[no-untyped-def]
    assert "dialogue" in TEMPLATES
    project = create_project("Dialogue", Canvas(480, 270, 30, 1), "dialogue", 20)
    scene = project.scenes[0]
    chars = [n for n in scene.nodes if n.kind == "character"]
    assert len(chars) == 2 and any(n.params["mirror"] for n in chars)
    sceptic = next(n for n in chars if n.params["mirror"])
    d = scene.duration_frames
    seen = [
        evaluate(project, scene.id, int(f * d)).node(sceptic.id).params["emotion"]
        for f in (0.1, 0.4, 0.6, 0.9)
    ]
    assert seen == ["doute", "ironie", "surprise", "enthousiasme"]
    urls = [s["url"] for s in project.scientific_metadata["sources"]]
    assert "https://science.nasa.gov/moon/facts/" in urls
    img = render_state_to_image(evaluate(project, scene.id, int(0.4 * d)), project.canvas, 480, 270)
    assert not img.isNull()


def test_rendering_from_a_worker_thread(qapp) -> None:  # type: ignore[no-untyped-def]
    out: list[np.ndarray] = []
    t = threading.Thread(target=lambda: out.append(_render({"emotion": "fureur"})))
    t.start()
    t.join()
    assert out and np.array_equal(out[0], _render({"emotion": "fureur"}))


def test_adult_proportions_have_a_smaller_head_and_their_own_face(qapp) -> None:  # type: ignore[no-untyped-def]
    params = {"emotion": "neutre", "outfit": "doudoune", "glasses": "fines"}
    chibi_svg = chibi.chibi_svg(params, {})
    adult_svg = chibi.chibi_svg({**params, "proportions": "adulte"}, {})
    assert 'rx="24" ry="29"' in chibi_svg and 'rx="24" ry="29"' not in adult_svg  # grands yeux ronds du chibi
    assert chibi.HEAD_TF in adult_svg and _valid(adult_svg)

    def head_width(p: dict) -> int:  # largeur opaque maximale dans le tiers supérieur (la tête seule)
        img = _render({**p, "pose": "repos"}, w=200, h=280)
        rows = img[: 280 // 3, :, 3] > 0
        return int(rows.sum(axis=1).max())

    chibi_w, adult_w = head_width(params), head_width({**params, "proportions": "adulte"})
    assert adult_w < 0.7 * chibi_w, (adult_w, chibi_w)


def test_adult_poses_and_emotions_cover_the_whole_catalogue(qapp) -> None:  # type: ignore[no-untyped-def]
    for name in ("emotion", "pose", "outfit", "glasses", "hat"):
        svgs = {chibi.chibi_svg({"proportions": "adulte", name: v}, {}) for v, _l in CHOICE_LISTS[name]}
        assert len(svgs) == len(CHOICE_LISTS[name]), name
        assert all(_valid(s) for s in svgs), name


def test_hat_colour_and_engineer_sheets() -> None:
    svg = chibi.chibi_svg({"hat": "casque"}, {"hat_color": "#FFD400"})
    assert 'fill="#FFD400"' in svg
    terrain = characters.PERSONALITY_BY_ID["ingenieur_terrain"]
    assert terrain.params["outfit"] == "gilet_hv" and terrain.params["hat"] == "casque"
    assert all(
        p.params.get("proportions") == "adulte"
        for p in characters.PERSONALITIES
        if p.id.startswith("ingenieur")
    )

"""Aligner, répartir, guides d'aimantation ; presse-papiers d'objets (copie autonome, collage sûr)."""

from __future__ import annotations

import json

import pytest

from antares_studio.domain.clipboard import FORMAT, ClipboardError, copy_nodes, read_payload, remap_assets
from antares_studio.domain.ids import is_valid_id
from antares_studio.domain.layout import align_deltas, distribute_deltas, snap_rect
from antares_studio.domain.model import Asset, Keyframe, Track
from antares_studio.domain.validation import validate_project
from tests.unit.helpers import earth_moon_project, make_node

A = (0.0, 0.0, 100.0, 50.0)
B = (300.0, 200.0, 340.0, 260.0)
C = (150.0, 80.0, 250.0, 120.0)


def test_align_on_selection_box_and_on_reference() -> None:
    assert align_deltas([A, B], "left") == [(0.0, 0.0), (-300.0, 0.0)]
    assert align_deltas([A, B], "right") == [(240.0, 0.0), (0.0, 0.0)]
    assert align_deltas([A, B], "vcenter") == [(0.0, 105.0), (0.0, -100.0)]
    # un seul objet : aligné sur le canevas fourni comme référence
    assert align_deltas([A], "hcenter", (0.0, 0.0, 1920.0, 1080.0)) == [(910.0, 0.0)]
    assert align_deltas([A], "bottom", (0.0, 0.0, 1920.0, 1080.0)) == [(0.0, 1030.0)]
    assert align_deltas([], "left") == []
    with pytest.raises(ValueError):
        align_deltas([A], "diagonale")


def test_distribute_gives_equal_gaps_and_keeps_extremes() -> None:
    deltas = distribute_deltas([B, A, C], "x")
    moved = [(r[0] + d[0], r[2] + d[0]) for r, d in zip([B, A, C], deltas, strict=True)]
    order = sorted(moved)
    gaps = [order[i + 1][0] - order[i][1] for i in range(2)]
    assert gaps[0] == pytest.approx(gaps[1])
    assert deltas[0] == (0.0, 0.0) and deltas[1] == (0.0, 0.0)  # B et A sont les extrêmes
    assert distribute_deltas([A, B], "y") == [(0.0, 0.0), (0.0, 0.0)]
    with pytest.raises(ValueError):
        distribute_deltas([A, B, C], "z")


def test_snap_rect_corrects_small_offsets_and_reports_guides() -> None:
    canvas = (0.0, 0.0, 1920.0, 1080.0)
    moving = (970.0, 300.0, 1070.0, 400.0)  # bords et centre à plus de 6 px de ceux du canevas
    dx, dy, guides = snap_rect(moving, [canvas], threshold=6.0)
    assert (dx, dy, guides) == (0.0, 0.0, [])
    moving = (908.0, 300.0, 1008.0, 400.0)  # centre 958 : 2 px du centre du canevas
    dx, dy, guides = snap_rect(moving, [canvas], threshold=6.0)
    assert dx == pytest.approx(2.0) and dy == 0.0
    assert any(g.axis == "x" and g.value == 960.0 for g in guides)
    # bord gauche aligné sur le bord droit d'un autre objet, plus petite correction gagnante
    dx, _dy, guides = snap_rect((103.0, 500.0, 153.0, 550.0), [A, canvas], threshold=6.0)
    assert dx == pytest.approx(-3.0) and any(g.value == 100.0 for g in guides)


def test_copy_paste_roundtrip_gives_new_ids_and_keeps_animation() -> None:
    project, scene, earth, moon = earth_moon_project()
    scene.tracks.append(Track(moon.id, "position.x", [Keyframe(0, 1260.0), Keyframe(30, 1300.0, "ease_in")]))
    label = make_node("text", "Légende", parent_id=moon.id, position=[0.0, -40.0])
    scene.nodes.append(label)
    data = json.loads(json.dumps(copy_nodes(project, scene, [moon.id])))
    assert data["format"] == FORMAT and len(data["nodes"]) == 2  # descendant inclus
    payload = read_payload(data, project, offset=(20.0, 20.0))
    ids = {n.id for n in payload.nodes}
    assert ids.isdisjoint({moon.id, label.id}) and all(is_valid_id(i) for i in ids)
    root = next(n for n in payload.nodes if n.parent_id is None)
    child = next(n for n in payload.nodes if n.parent_id is not None)
    assert child.parent_id == root.id and child.position == [0.0, -40.0]  # l'enfant reste relatif
    assert root.position == [1280.0, 560.0]
    track = payload.tracks[0]
    assert track.target_id == root.id
    assert [k.value for k in track.keyframes] == [1280.0, 1320.0] and track.keyframes[1].easing == "ease_in"
    assert payload.same_project
    scene.nodes += payload.nodes
    scene.tracks += payload.tracks
    assert validate_project(project) == []


def test_copy_child_without_its_group_keeps_screen_position() -> None:
    project, scene, earth, moon = earth_moon_project()
    label = make_node("text", "Légende", parent_id=moon.id, position=[0.0, -40.0])
    scene.nodes.append(label)
    scene.tracks.append(Track(label.id, "position.y", [Keyframe(0, -40.0), Keyframe(10, -80.0)]))
    payload = read_payload(copy_nodes(project, scene, [label.id]), project, offset=(0.0, 0.0))
    (node,) = payload.nodes
    assert node.parent_id is None and node.position == [1260.0, 500.0]
    assert [k.value for k in payload.tracks[0].keyframes] == [500.0, 460.0]


def test_paste_refuses_foreign_or_malformed_content() -> None:
    project, scene, earth, _ = earth_moon_project()
    for bad, message in (
        ({"format": "autre"}, "ANTARES"),
        ({"format": FORMAT, "version": 1, "nodes": []}, "aucun objet"),
        (
            {"format": FORMAT, "version": 1, "nodes": [{"id": "x", "kind": "circle", "position": "ici"}]},
            "invalide",
        ),
        ({"format": FORMAT, "version": 1, "nodes": [{"id": "x", "kind": "trou_noir"}]}, "inconnus"),
        ("texte", "invalide"),
    ):
        with pytest.raises(ClipboardError, match=message):
            read_payload(bad, project)


def test_assets_are_listed_and_remapped() -> None:
    project, scene, earth, _ = earth_moon_project()
    project.assets.append(Asset("asset-0123456789ab", "assets/terre.png", "image", "abc"))
    img = make_node("image", "Photo")
    img.params["asset_id"] = "asset-0123456789ab"
    scene.nodes.append(img)
    payload = read_payload(copy_nodes(project, scene, [img.id], "/tmp/projet.antares"), project)
    assert [a.path for a in payload.assets] == [
        "assets/terre.png"
    ] and payload.root_path == "/tmp/projet.antares"
    remap_assets(payload, {"asset-0123456789ab": ""})
    assert payload.nodes[0].params["asset_id"] == ""

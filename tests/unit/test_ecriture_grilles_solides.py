"""Phase 12 : écriture progressive, craie, décors, polices livrées, grilles déformables, solides 3D."""

from __future__ import annotations

import math

import numpy as np
import pytest
from PySide6.QtGui import QFont, QImage

from antares_studio.domain.commands import SetSceneProperty
from antares_studio.domain.effects import has_effects
from antares_studio.domain.kinds import (
    OBJECT_VARIANTS,
    SOLID_SHAPES,
    check_param_value,
    resolve_variant,
    spec_for,
)
from antares_studio.domain.model import BACKDROPS, Canvas, Project, Scene
from antares_studio.domain.properties import get_property
from antares_studio.domain.text_styles import TEXT_STYLES, style_values
from antares_studio.domain.validation import validate_project
from antares_studio.persistence.schema import project_from_dict, project_to_dict
from antares_studio.rendering import grid as grid_math
from antares_studio.rendering.effects import chalk_mask
from antares_studio.rendering.qt_painter import render_state_to_image
from antares_studio.rendering.solids import project_solid, solid_mesh
from antares_studio.rendering.writing import text_units, unit_progress
from antares_studio.resources.fonts import BUNDLED_BY_FAMILY, BUNDLED_FONTS, FONTS_DIR, ensure_fonts
from antares_studio.resources.templates import create_project, new_node
from antares_studio.timeline.evaluator import evaluate_scene
from antares_studio.timeline.presets import apply_preset

W, H = 480, 270
CANVAS = Canvas(W, H, 30, 1)


def _render(*nodes, backdrop: str = "", background: str = "#000000", paint_background: bool = True):  # type: ignore[no-untyped-def]
    scene = Scene.create("test", 10)
    scene.background = background
    scene.backdrop = backdrop
    scene.nodes = list(nodes)
    img = render_state_to_image(
        evaluate_scene(scene, 0, CANVAS), CANVAS, W, H, paint_background=paint_background
    )
    img = img.convertToFormat(QImage.Format.Format_RGBA8888)
    buf = np.frombuffer(img.constBits(), np.uint8, count=img.bytesPerLine() * H)
    return buf.reshape(H, img.bytesPerLine())[:, : W * 4].reshape(H, W, 4).astype(int)


def _ink(arr: np.ndarray) -> int:
    """Quantité d'encre claire sur fond noir (somme du canal vert)."""
    return int(arr[..., 1].sum())


# --- écriture progressive -----------------------------------------------------------------------------
def test_unit_progress_bounds_and_order() -> None:
    for overlap in (0.0, 1.0, 2.5):
        assert all(unit_progress(0.0, i, 10, overlap) == 0.0 for i in range(10))
        assert all(unit_progress(1.0, i, 10, overlap) == 1.0 for i in range(10))
        mid = [unit_progress(0.5, i, 10, overlap) for i in range(10)]
        assert mid == sorted(mid, reverse=True)  # les premières unités sont plus avancées
    # machine à écrire : exactement ⌊amount × n⌋ caractères visibles
    assert sum(unit_progress(0.35, i, 20, 0.0) > 0 for i in range(20)) == 7


def test_text_units_follow_reading_order_and_words(qapp) -> None:  # type: ignore[no-untyped-def]
    font = QFont("DejaVu Sans")
    font.setPointSizeF(30)
    from antares_studio.rendering.qt_painter import text_layout_rect

    params = {"text": "la Terre\ntourne", "font_size": 30.0}
    rect, flags = text_layout_rect(params)
    units = text_units(params["text"], font, rect, flags, 0.0)
    assert len(units) == len("laTerretourne")
    assert [u.word for u in units] == [1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3]
    assert units[2].rect.top() < units[-1].rect.top()  # « tourne » est sur la seconde ligne


@pytest.mark.parametrize("style", ["trace", "chalk", "typewriter", "letters", "words"])
def test_writing_reveals_text_progressively(qapp, style: str) -> None:  # type: ignore[no-untyped-def]
    def text(write: float):  # type: ignore[no-untyped-def]
        return new_node(
            "text", "t", W / 2, H / 2, text="Écrire E = mc²", font_size=34.0, write=write, write_style=style
        )

    empty, half, full = (_ink(_render(text(w))) for w in (0.0, 0.5, 1.0))
    assert empty == 0
    assert 0.1 * full < half < 0.95 * full
    assert np.array_equal(_render(text(0.5)), _render(text(0.5)))  # reproductible


def test_fully_written_text_equals_legacy_text(qapp) -> None:  # type: ignore[no-untyped-def]
    legacy = new_node("text", "t", W / 2, H / 2, text="Ancien projet", font_size=30.0)
    for key in ("write", "write_style"):
        del legacy.params[key]  # projet enregistré avant l'écriture progressive
    written = new_node("text", "t", W / 2, H / 2, text="Ancien projet", font_size=30.0, write=1.0)
    assert np.array_equal(_render(legacy), _render(written))
    assert get_property(legacy, "params.write") == 1.0  # valeur par défaut pour les anciens objets
    assert get_property(legacy, "params.write_style") == "trace"


def test_formula_writes_glyphs_and_strokes(qapp) -> None:  # type: ignore[no-untyped-def]
    def formula(write: float, **kw: object):  # type: ignore[no-untyped-def]
        return new_node(
            "formula", "f", W / 2, H / 2, text=r"\frac{a}{\sqrt{b}}", font_size=40.0, write=write, **kw
        )

    full = _ink(_render(formula(1.0)))
    assert _ink(_render(formula(0.0))) == 0
    assert 0 < _ink(_render(formula(0.5))) < full
    # pendant une transformation de formule, l'écriture ne s'applique pas
    morphing = _ink(_render(formula(0.0, morph_to="x", morph=0.25)))
    assert morphing > 0


def test_write_presets(qapp) -> None:  # type: ignore[no-untyped-def]
    node = new_node("text", "t", 0, 0)
    (track,) = apply_preset("write", node, {"start_frame": 10, "duration_frames": 30})
    assert track.property == "params.write"
    assert [(k.frame, k.value) for k in track.keyframes] == [(10, 0.0), (40, 1.0)]
    (track,) = apply_preset("erase", node, {"start_frame": 0, "duration_frames": 12})
    assert [k.value for k in track.keyframes] == [1.0, 0.0]


# --- craie, polices, styles -----------------------------------------------------------------------------
def test_chalk_texture_is_partial_and_deterministic(qapp) -> None:  # type: ignore[no-untyped-def]
    mask = chalk_mask(64, 96, 10, 20, 0.6)
    assert mask.shape == (64, 96) and mask.min() >= 0.0 and mask.max() <= 1.0
    assert np.array_equal(mask, chalk_mask(64, 96, 10, 20, 0.6))
    assert has_effects({"fx_chalk": 0.6})
    plain = new_node("rect", "r", W / 2, H / 2, width=200.0, height=80.0, style_fill="#FFFFFF")
    chalky = new_node("rect", "r", W / 2, H / 2, width=200.0, height=80.0, style_fill="#FFFFFF")
    chalky.style["fx_chalk"] = 0.6
    a, b = _ink(_render(plain)), _ink(_render(chalky))
    assert 0.3 * a < b < 0.95 * a


def test_bundled_fonts_are_loaded_and_licensed(qapp) -> None:  # type: ignore[no-untyped-def]
    families = ensure_fonts()
    for font in BUNDLED_FONTS:
        assert font.family in families, font.family
        folder = FONTS_DIR / font.folder
        licence = "LICENSE.txt" if font.license == "Apache-2.0" else "OFL.txt"
        assert (folder / licence).is_file(), font.folder
        assert list(folder.glob("*.ttf"))
    readme = (FONTS_DIR / "README.md").read_text(encoding="utf-8")
    for ttf in FONTS_DIR.rglob("*.ttf"):
        assert ttf.relative_to(FONTS_DIR).as_posix() in readme


def test_text_styles_apply_only_known_properties() -> None:
    for sid, (_label, _desc, values) in TEXT_STYLES.items():
        family = values["params.font_family"]
        assert family in BUNDLED_BY_FAMILY or family == "DejaVu Sans", sid
        for kind in ("text", "formula", "callout"):
            spec = spec_for(kind)
            for path, value in style_values(sid, kind).items():
                group, _, name = path.partition(".")
                specs = {p.name: p for p in (spec.params if group == "params" else spec.style)}
                if name in specs:
                    assert check_param_value(specs[name], value) is None, (sid, path)
                else:
                    assert name.startswith("fx_"), (sid, kind, path)
    callout = style_values("chalk", "callout")
    assert callout["style.text_color"] == "#F4F1E8" and "style.fill" not in callout
    assert "params.write_style" not in callout  # un encadré ne s'écrit pas progressivement
    assert style_values("chalk", "circle") == {}
    assert style_values("neon", "text")["style.fx_glow"] == 18.0
    assert style_values("chalk", "text")["style.fx_glow"] == 0.0  # effets précédents remis à zéro


# --- décors de scène ------------------------------------------------------------------------------------
def test_backdrop_is_saved_validated_and_undoable() -> None:
    project = Project.create("Décor", CANVAS)
    scene = Scene.create("S", 10)
    project.scenes.append(scene)
    assert "backdrop" not in project_to_dict(project)["scenes"][0]  # fichiers identiques sans décor
    cmd = SetSceneProperty(scene.id, "backdrop", "chalkboard_green")
    cmd.do(project)
    data = project_to_dict(project)
    assert data["scenes"][0]["backdrop"] == "chalkboard_green"
    assert project_from_dict(data).scenes[0].backdrop == "chalkboard_green"
    cmd.undo(project)
    assert scene.backdrop == ""
    with pytest.raises(ValueError):
        SetSceneProperty(scene.id, "backdrop", "papier-peint").do(project)
    scene.backdrop = "papier-peint"
    assert any(i.path.endswith(".backdrop") for i in validate_project(project))


@pytest.mark.parametrize("backdrop", [k for k in BACKDROPS if k])
def test_backdrops_render_and_stay_out_of_transparent_exports(qapp, backdrop: str) -> None:  # type: ignore[no-untyped-def]
    plain = _render(background="#000000")
    decorated = _render(backdrop=backdrop)
    assert not np.array_equal(plain, decorated)
    assert np.array_equal(decorated, _render(backdrop=backdrop))  # reproductible
    transparent = _render(backdrop=backdrop, paint_background=False)
    assert transparent[..., 3].max() == 0


# --- grilles --------------------------------------------------------------------------------------------
def test_grid_linear_map_follows_basis_vectors() -> None:
    params = {"step": 50.0, "m_a": 1.0, "m_b": 1.0, "m_c": 0.0, "m_d": 1.0}
    q, z = grid_math.transform(params, np.array([[1.0, 0.0], [0.0, 1.0], [2.0, 3.0]]))
    # î reste (1, 0) ; ĵ devient (1, 1) — y écran vers le bas
    assert np.allclose(q, [[50.0, 0.0], [50.0, -50.0], [250.0, -150.0]])
    assert not z.any()
    assert not grid_math.is_deformed({}) and grid_math.is_deformed(params)


def test_grid_warps() -> None:
    pts = np.array([[1.0, 0.0], [3.0, 0.0], [0.0, 6.0]])
    base = {"step": 100.0, "warp_radius": 200.0, "warp_amount": 0.8}
    flat, _ = grid_math.transform({**base, "warp": "none"}, pts)
    pulled, _ = grid_math.transform({**base, "warp": "gravity"}, pts)
    assert np.all(np.linalg.norm(pulled, axis=1) < np.linalg.norm(flat, axis=1))  # attirés vers la masse
    _, dip = grid_math.transform({**base, "warp": "gravity", "perspective": True}, pts)
    assert np.all(dip < 0) and dip[0] < dip[1] < dip[2]  # plus profond près de la masse
    swirled, _ = grid_math.transform({**base, "warp": "swirl"}, pts)
    assert np.allclose(np.linalg.norm(swirled, axis=1), np.linalg.norm(flat, axis=1))  # rotation pure
    assert not np.allclose(swirled, flat)


def test_grid_geometry_is_bounded_and_robust() -> None:
    geo = grid_math.grid_geometry({"width": 800.0, "height": 400.0, "step": 100.0})
    assert len(geo.axes) == 2 and not geo.ghost
    assert all(np.isfinite(line).all() for line in geo.lines)
    tiny = grid_math.grid_geometry({"width": 4000.0, "height": 4000.0, "step": 5.0})
    assert len(tiny.lines) + len(tiny.axes) <= grid_math.MAX_LINES
    singular = grid_math.grid_geometry({"m_a": 1.0, "m_b": 2.0, "m_c": 0.5, "m_d": 1.0, "show_basis": True})
    assert singular.ghost and len(singular.basis) == 2  # déterminant nul : pas d'erreur


def test_grid_renders_progressively_and_transforms(qapp) -> None:  # type: ignore[no-untyped-def]
    def grid(**kw: object):  # type: ignore[no-untyped-def]
        return new_node("grid", "g", W / 2, H / 2, width=float(W), height=float(H), step=40.0, **kw)

    assert _ink(_render(grid(progress=0.0))) == 0
    half, full = _ink(_render(grid(progress=0.5))), _ink(_render(grid()))
    assert 0 < half < full
    assert not np.array_equal(_render(grid()), _render(grid(m_b=1.0)))
    spacetime = _render(grid(perspective=True, warp="gravity", warp_amount=1.0, warp_radius=60.0))
    assert _ink(spacetime) > 0


def test_grid_presets(qapp) -> None:  # type: ignore[no-untyped-def]
    node = new_node("grid", "g", 0, 0)
    tracks = apply_preset("linear_map", node, {"a": 0.0, "b": -1.0, "c": 1.0, "d": 0.0})
    assert {t.property: t.keyframes[-1].value for t in tracks} == {
        "params.m_a": 0.0,
        "params.m_b": -1.0,
        "params.m_c": 1.0,
        "params.m_d": 0.0,
    }
    (warp,) = apply_preset("warp", node, {"amount": 1.2})
    assert warp.property == "params.warp_amount" and warp.keyframes[-1].value == 1.2
    (wave,) = apply_preset("wave_travel", node, {"cycles": 2.0})
    assert wave.keyframes[-1].value == 2.0


# --- solides 3D -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("shape", [s for s, _l in SOLID_SHAPES])
def test_solid_meshes_are_closed_outward_and_edged(shape: str) -> None:
    solid = solid_mesh(shape)
    v, t = solid.vertices, solid.triangles
    assert np.max(np.linalg.norm(v, axis=1)) == pytest.approx(1.0)
    tri = v[t]
    volume = float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()) / 6.0
    assert volume > 0.05  # normales vers l'extérieur : volume orienté positif
    # surface fermée : chaque arête de triangle (par position) est partagée par deux triangles
    keys: dict[tuple[tuple[float, ...], tuple[float, ...]], int] = {}
    for a, b, c in t:
        for p, q in ((a, b), (b, c), (c, a)):
            e = tuple(sorted((tuple(np.round(v[p], 6)), tuple(np.round(v[q], 6)))))
            keys[e] = keys.get(e, 0) + 1  # type: ignore[index]
    assert set(keys.values()) == {2}, shape
    assert len(solid.edges) > 0 and all(solid.edge_faces)


def test_solid_volumes_match_geometry() -> None:
    sphere = solid_mesh("sphere")
    tri = sphere.vertices[sphere.triangles]
    volume = float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()) / 6.0
    assert volume == pytest.approx(4 / 3 * math.pi, rel=0.05)
    cube = solid_mesh("cube")
    assert len(cube.edges) == 12 and len(cube.triangles) == 12


def test_cube_shows_one_to_three_faces() -> None:
    cube = solid_mesh("cube")
    for yaw, pitch in ((0, 0), (35, 25), (120, -40), (200, 70)):
        visible = int(project_solid(cube, yaw, pitch, 0.0, 200.0, 0.0).visible.sum())
        assert visible in (2, 4, 6)  # 1 à 3 faces carrées de deux triangles
        assert int(project_solid(cube, yaw, pitch, 0.0, 200.0, 0.8).visible.sum()) >= 2


def test_solid_render_modes_differ(qapp) -> None:  # type: ignore[no-untyped-def]
    images = []
    for mode in ("shaded_edges", "shaded", "wireframe", "transparent"):
        node = new_node("solid3d", "c", W / 2, H / 2, shape="icosahedron", size=180.0, render_mode=mode)
        arr = _render(node)
        assert _ink(arr) > 0, mode
        images.append(arr)
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            assert not np.array_equal(images[i], images[j])


def test_spin3d_preset() -> None:
    node = new_node("solid3d", "c", 0, 0, yaw_deg=30.0, pitch_deg=10.0)
    yaw, pitch = apply_preset("spin3d", node, {"turns": 2.0, "tilt_deg": 15.0})
    assert yaw.keyframes[-1].value == 30.0 + 720.0 and pitch.keyframes[-1].value == 25.0
    assert len(apply_preset("spin3d", node, {"turns": 1.0})) == 1


# --- bibliothèque et modèles ----------------------------------------------------------------------------
def test_object_variants_are_valid() -> None:
    for ident, (_label, params) in OBJECT_VARIANTS.items():
        kind, label, forced = resolve_variant(ident)
        assert label and forced == params
        specs = {p.name: p for p in spec_for(kind).params}
        for name, value in params.items():
            assert check_param_value(specs[name], value) is None, (ident, name)
    assert resolve_variant("circle") == ("circle", "Cercle", {})


@pytest.mark.parametrize("template_id", ["chalkboard", "linear_map", "curved_spacetime", "solids"])
def test_new_templates_are_valid_and_animated(qapp, template_id: str) -> None:  # type: ignore[no-untyped-def]
    project = create_project("Démo", CANVAS, template_id, 6)
    assert validate_project(project) == []
    scene = project.scenes[0]
    early = render_state_to_image(evaluate_scene(scene, 2, CANVAS), CANVAS, W, H)
    late = render_state_to_image(evaluate_scene(scene, scene.duration_frames - 1, CANVAS), CANVAS, W, H)
    assert early != late


def test_rotated_grid_still_fills_the_frame() -> None:
    """Après un quart de tour, les lignes doivent encore couvrir tout le cadre (largeur ≠ hauteur)."""
    params = {
        "width": 1920.0,
        "height": 1080.0,
        "step": 110.0,
        "m_a": 0.0,
        "m_b": -1.0,
        "m_c": 1.0,
        "m_d": 0.0,
    }
    geo = grid_math.grid_geometry(params)
    xs = np.concatenate([line[:, 0] for line in geo.lines])
    ys = np.concatenate([line[:, 1] for line in geo.lines])
    assert xs.min() <= -960 and xs.max() >= 960 and ys.min() <= -540 and ys.max() >= 540
    horizontal = [line for line in geo.lines if np.ptp(line[:, 1]) < 1e-6]
    assert max(abs(line[0, 1]) for line in horizontal) >= 540 - 110  # lignes horizontales jusqu'aux bords

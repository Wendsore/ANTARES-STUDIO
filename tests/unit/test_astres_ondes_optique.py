"""Phase 13 : astres texturés, cartes, ciel réel, ondes, rayons, optique, phénomènes cosmiques (ADR-0009)."""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest
from PySide6.QtGui import QImage

from antares_studio.domain.kinds import OBJECT_VARIANTS, resolve_variant, spec_for, split_style
from antares_studio.domain.model import Canvas, Project, Scene
from antares_studio.domain.validation import validate_project
from antares_studio.rendering import celestial, cosmic, maps, optics, sky, waves
from antares_studio.rendering.gltf import LIGHT
from antares_studio.rendering.qt_painter import render_state_to_image
from antares_studio.rendering.solids import _light, project_solid, solid_mesh
from antares_studio.resources import astro
from antares_studio.resources.licenses import bundled_datasets_used, credits_lines
from antares_studio.resources.templates import TEMPLATES, create_project
from antares_studio.science import light
from antares_studio.timeline.evaluator import evaluate, evaluate_scene
from antares_studio.timeline.presets import apply_preset
from tests.unit.helpers import make_node

W, H = 480, 270
CANVAS = Canvas(W, H, 30, 1)
PHASE13_TEMPLATES = (
    "lunar_phases_real",
    "doppler",
    "tides",
    "supernova",
    "double_slit",
    "solar_system",
    "world_map",
    "night_sky",
)


def _render(*nodes) -> np.ndarray:  # type: ignore[no-untyped-def]
    scene = Scene.create("test", 10)
    scene.background = "#000000"
    scene.nodes = list(nodes)
    img = render_state_to_image(evaluate_scene(scene, 0, CANVAS), CANVAS, W, H)
    img = img.convertToFormat(QImage.Format.Format_RGBA8888)
    buf = np.frombuffer(img.constBits(), np.uint8, count=img.bytesPerLine() * H)
    return buf.reshape(H, img.bytesPerLine())[:, : W * 4].reshape(H, W, 4).astype(int)


def _body(body: str, **params: object):  # type: ignore[no-untyped-def]
    node = make_node("celestial", body)
    node.position = [W / 2, H / 2]
    node.params.update({"body": body, "size": 200.0, **params})
    return node


def _lit(arr: np.ndarray, threshold: int = 40) -> int:
    return int((arr[..., :3].max(axis=-1) > threshold).sum())


# --- physique de la lumière et des ondes ------------------------------------------------------------
def test_blackbody_colours_follow_temperature() -> None:
    r, g, b = light.blackbody_rgb(6500)
    assert min(r, g, b) > 0.85  # ~ blanc du D65
    cool, hot = light.blackbody_rgb(3000), light.blackbody_rgb(20000)
    assert cool[0] == 1.0 and cool[2] < 0.5  # rouge-orangé
    assert hot[2] == 1.0 and hot[0] < 0.8  # bleuté
    assert light.blackbody_hex(5772).startswith("#") and len(light.blackbody_hex(5772)) == 7


def test_wavelength_colours_and_ballesteros() -> None:
    red, green, blue = light.wavelength_rgb(700), light.wavelength_rgb(530), light.wavelength_rgb(450)
    assert red[0] > 0.5 and red[1] == 0 and red[2] == 0
    assert green[1] == max(green)
    assert blue[2] == max(blue)
    assert light.wavelength_rgb(300) == (0.0, 0.0, 0.0)
    # B−V du Soleil ≈ 0,65 → ~ 5 800 K (Ballesteros 2012)
    assert 5600 < light.bv_to_temperature(0.65) < 6000


def test_doppler_and_mach() -> None:
    assert light.doppler_classical(100, 340, 170) == pytest.approx(200)  # v = c/2, en approche
    assert light.doppler_classical(100, 340, 170, 180) == pytest.approx(100 * 340 / 510)
    with pytest.raises(ValueError):
        light.doppler_classical(100, 340, 340)
    assert light.doppler_relativistic(100, 0.6) == pytest.approx(50)  # √(0,4/1,6) = 1/2
    assert light.mach_angle_deg(340, 300) is None
    assert light.mach_angle_deg(340, 680) == pytest.approx(30)


def test_wave_fronts_are_closer_ahead_of_a_moving_source() -> None:
    params = {"time_s": 3.0, "wave_speed": 200.0, "frequency": 2.0, "source_speed": 100.0, "max_radius": 2000}
    fronts = waves.front_circles(params)
    sx, _ = waves.source_position(params)
    ahead = sorted(cx + r - sx for cx, _cy, r, _a in fronts)
    behind = sorted(sx - (cx - r) for cx, _cy, r, _a in fronts)
    gap_ahead, gap_behind = ahead[1] - ahead[0], behind[1] - behind[0]
    # λ' = (c − v)/f devant, (c + v)/f derrière
    assert gap_ahead == pytest.approx(50.0) and gap_behind == pytest.approx(150.0)


def test_supersonic_fronts_have_a_mach_envelope() -> None:
    params = {"time_s": 4.0, "wave_speed": 100.0, "frequency": 4.0, "source_speed": 200.0, "max_radius": 5000}
    sx, _ = waves.source_position(params)
    # chaque front est tangent au cône : r / distance au sommet = sin θ = c/v
    for cx, _cy, r, _a in waves.front_circles(params)[:-1]:
        assert r / (sx - cx) == pytest.approx(0.5, rel=1e-6)


def test_string_standing_wave_has_fixed_nodes() -> None:
    p = {"width": 400.0, "wavelength": 200.0, "amplitude": 50.0, "standing": True}
    for t in (0.0, 0.3, 1.1):
        pts = waves.string_points({**p, "time_s": t}, samples=400)
        assert abs(pts[100][1]) < 1e-9 and abs(pts[200][1]) < 1e-9  # nœuds tous les λ/2


# --- astres --------------------------------------------------------------------------------------------
def test_bundled_textures_and_bodies(qapp) -> None:  # type: ignore[no-untyped-def]
    for body in astro.BODIES.values():
        assert astro.texture_path(body.texture).is_file(), body.id
        assert body.diameter_km > 0
    assert astro.BODIES["earth"].obliquity_deg == pytest.approx(23.4)
    assert astro.BODIES["saturn"].rings
    for star in astro.FAMOUS_STARS.values():
        assert 2000 < star.temperature_k < 30000, star.id
        assert star.qid.startswith("Q")


def test_phase_fraction() -> None:
    assert celestial.phase_fraction(0) == pytest.approx(1.0)  # pleine lune : lumière derrière l'observateur
    assert celestial.phase_fraction(180) == pytest.approx(0.0)
    assert celestial.phase_fraction(90) == pytest.approx(0.5)


def test_full_moon_is_brighter_than_quarter_and_new_moon(qapp) -> None:  # type: ignore[no-untyped-def]
    """Disque de 100 px de rayon : ~31 400 px éclairés en pleine lune, la moitié au quartier."""
    full = _lit(_render(_body("moon", light_az_deg=0.0, light_el_deg=0.0)))
    quarter = _lit(_render(_body("moon", light_az_deg=90.0, light_el_deg=0.0)))
    new = _lit(_render(_body("moon", light_az_deg=180.0, light_el_deg=0.0)))
    assert 25000 < full < 33000  # le disque seul : pas de halo autour d'une planète
    assert 0.35 < quarter / full < 0.65
    assert new < full * 0.05


def test_transparent_tint_leaves_colours_unchanged(qapp) -> None:  # type: ignore[no-untyped-def]
    """Régression : « #FFFFFF00 » (blanc transparent, #RRGGBBAA) ne doit pas teinter l'astre en jaune
    (QColor lit les 8 chiffres en #AARRGGBB)."""
    plain = _body("moon", light_az_deg=0.0)
    plain.style.pop("tint", None)
    tinted = _body("moon", light_az_deg=0.0)
    tinted.style["tint"] = "#FFFFFF00"
    a, b = _render(plain), _render(tinted)
    assert np.array_equal(a, b)
    disc = a[a[..., :3].max(axis=-1) > 60]
    assert abs(float(disc[:, 0].mean()) - float(disc[:, 2].mean())) < 12  # Lune grise, pas jaune
    red = _body("moon", light_az_deg=0.0)
    red.style["tint"] = "#FF000080"
    c = _render(red)
    assert c[..., 0].sum() > c[..., 2].sum() * 1.3


def test_saturn_rings_widen_the_image(qapp) -> None:  # type: ignore[no-untyped-def]
    with_rings = _lit(_render(_body("saturn", size=120.0, pitch_deg=20.0)), 25)
    without = _lit(_render(_body("saturn", size=120.0, pitch_deg=20.0, rings=False)), 25)
    assert with_rings > without * 1.3
    assert celestial.extent({"body": "saturn"}) > 2.3 and celestial.extent({"body": "earth"}) < 1.5


def test_star_colour_comes_from_its_temperature(qapp) -> None:  # type: ignore[no-untyped-def]
    red = _render(_body("star", temperature_k=3200.0, corona=0.0))
    blue = _render(_body("star", temperature_k=12000.0, corona=0.0))
    disc_r, disc_b = red[H // 2, W // 2], blue[H // 2, W // 2]
    assert disc_r[0] > disc_r[2] + 60
    assert disc_b[2] >= disc_b[0]


def test_tide_outline_bulges_toward_the_moon() -> None:
    poly = celestial.tide_outline(100.0, 0.3, 0.0)
    rs = [math.hypot(poly.at(i).x(), poly.at(i).y()) for i in range(poly.count())]
    along, across = max(rs), min(rs)
    assert along == pytest.approx(130.0, rel=1e-3) and across == pytest.approx(85.0, rel=1e-3)
    tip = max(range(poly.count()), key=lambda i: rs[i])
    assert abs(poly.at(tip).y()) < 5  # bourrelets sur l'axe φ = 0


# --- cartes et ciel ------------------------------------------------------------------------------------
@pytest.mark.parametrize("projection", ["equal_earth", "equirectangular", "mercator"])
def test_map_projection_round_trip(projection: str) -> None:
    lon = np.array([-170.0, -60.0, 0.0, 2.35, 139.7])
    lat = np.array([-60.0, -33.9, 0.0, 48.85, 35.7])
    x, y = maps.project(projection, lon, lat)
    lon2, lat2, ok = maps.unproject(projection, x, y)
    assert ok.all()
    assert np.allclose(lon2, lon, atol=1e-6) and np.allclose(lat2, lat, atol=1e-6)


def test_world_map_data_and_render(qapp) -> None:  # type: ignore[no-untyped-def]
    names = {c["name"] for c in astro.countries("110m")}
    assert {"France", "Brésil", "Japon"} <= names
    assert {c["continent"] for c in astro.countries("110m")} >= set(astro.CONTINENTS_FR)
    assert maps.aspect("equirectangular") == pytest.approx(2.0)
    node = make_node("world_map", "Carte")
    node.position = [W / 2, H / 2]
    node.params["width"] = 440.0
    assert _lit(_render(node), 30) > 20000


def test_sky_catalogue_and_render(qapp) -> None:  # type: ignore[no-untyped-def]
    rows, _names = astro.stars()
    assert len(rows) > 5000 and len(astro.constellations()) >= 88
    assert sky.constellation_center("Ori") is not None
    node = make_node("sky", "Ciel")
    node.position = [W / 2, H / 2]
    node.params.update(width=480.0, height=270.0, center_ra_deg=84.0, center_dec_deg=0.0, fov_deg=60.0)
    assert _lit(_render(node), 60) > 200
    # projection stéréographique : centre au milieu, est à gauche
    x, y, _ = sky.stereographic(np.radians([84.0, 94.0]), np.radians([0.0, 0.0]), math.radians(84), 0.0)
    assert abs(x[0]) < 1e-12 and x[1] < 0


# --- optique -------------------------------------------------------------------------------------------
def test_impacts_are_reproducible_and_build_fringes() -> None:
    a = optics.impact_points("two_slits", 5.0, 0.8, 7, 4000)
    b = optics.impact_points("two_slits", 5.0, 0.8, 7, 4000)
    assert np.array_equal(a, b)
    hist, edges = np.histogram(a[:, 0], bins=50, range=(-1, 1))
    centres = (edges[:-1] + edges[1:]) / 2
    expected = optics.intensity("two_slits", centres, 5.0, 0.8)
    assert np.corrcoef(hist, expected)[0, 1] > 0.9
    # sans franges quand on sait par quelle fente passe le photon
    w = optics.impact_points("which_path", 5.0, 0.8, 7, 4000)
    hw, _ = np.histogram(w[:, 0], bins=50, range=(-1, 1))
    assert np.corrcoef(hw, expected)[0, 1] < np.corrcoef(hist, expected)[0, 1] - 0.2


def test_ray_path_length_and_points() -> None:
    pts = [(0.0, 0.0), (300.0, 0.0), (300.0, 400.0)]
    assert optics.path_length(pts) == pytest.approx(700.0)
    x, y, dx, dy = optics.point_at(pts, 500.0)
    assert (x, y) == pytest.approx((300.0, 200.0)) and (dx, dy) == pytest.approx((0.0, 1.0))


def test_ray_colour_from_wavelength(qapp) -> None:  # type: ignore[no-untyped-def]
    from antares_studio.rendering.qt_painter import qcolor

    c = optics.ray_color({"wavelength_nm": 650.0}, {"stroke": "#FFFFFF"}, qcolor)
    assert c.red() > 200 and c.blue() < 30


# --- phénomènes cosmiques ----------------------------------------------------------------------------
def test_particles_are_deterministic_and_expand() -> None:
    p = {"mode": "explosion", "count": 300, "seed": 3, "speed": 300.0}
    a0, *_ = cosmic.particle_state({**p, "time_s": 0.5})
    a1, *_ = cosmic.particle_state({**p, "time_s": 0.5})
    b, *_ = cosmic.particle_state({**p, "time_s": 2.0})
    assert np.array_equal(a0, a1)
    assert np.linalg.norm(b, axis=1).mean() > np.linalg.norm(a0, axis=1).mean() * 1.5


def test_accretion_inner_particles_orbit_faster() -> None:
    p = {"mode": "accretion", "count": 400, "seed": 1, "radius": 400.0, "inflow": 0.0}
    pos0, *_ = cosmic.particle_state({**p, "time_s": 0.0})
    pos1, *_ = cosmic.particle_state({**p, "time_s": 0.05})
    r = np.linalg.norm(pos0, axis=1)
    ang = np.abs(np.angle((pos1[:, 0] + 1j * pos1[:, 1]) / (pos0[:, 0] + 1j * pos0[:, 1])))
    inner, outer = ang[r < np.percentile(r, 30)], ang[r > np.percentile(r, 70)]
    assert inner.mean() > outer.mean() * 1.5  # ω ∝ r^-3/2


def test_black_hole_has_a_dark_horizon(qapp) -> None:  # type: ignore[no-untyped-def]
    node = make_node("black_hole", "Trou noir")
    node.position = [W / 2, H / 2]
    arr = _render(node)
    assert arr[H // 2, W // 2, :3].max() < 20  # horizon noir
    assert _lit(arr, 80) > 1000  # disque et anneau de photons


# --- lumière des solides : rendu d'origine inchangé -----------------------------------------------------
def test_solid_default_light_reproduces_legacy_light() -> None:
    lv = _light(spec_for("solid3d").default_params())
    assert lv is not None and np.allclose(lv, LIGHT, atol=1e-12)
    assert _light({}) is None
    mesh = solid_mesh("cube")
    legacy = project_solid(mesh, 30, 20, 0, 100, 0)
    new = project_solid(mesh, 30, 20, 0, 100, 0, lv, 0.3)
    assert np.allclose(legacy.light, new.light)


# --- presets ---------------------------------------------------------------------------------------------
def test_moon_phases_preset_goes_round_once() -> None:
    node = make_node("celestial", "Lune")
    (track,) = apply_preset("moon_phases", node, {"start_frame": 0, "duration_frames": 90})
    kfs = track.sorted_keyframes()
    assert track.property == "params.light_az_deg"
    assert (kfs[0].value, kfs[-1].value) == (180.0, 540.0)


def test_tide_follow_matches_the_orbit_preset() -> None:
    """Les bourrelets restent alignés sur un corps animé par le preset « orbit » (y vers le bas)."""
    moon = make_node("circle", "Lune")
    earth = make_node("celestial", "Terre")
    orbit = {"start_frame": 0, "duration_frames": 60, "turns": 1.0, "start_angle_deg": 30.0}
    orbit_tracks = apply_preset("orbit", moon, {**orbit, "cx": 0.0, "cy": 0.0, "radius": 100.0})
    (tide,) = apply_preset("tide_follow", earth, orbit)
    project = Project.create("Marées", Canvas(1920, 1080, 30, 1))
    scene = Scene.create("s", 60)
    scene.nodes = [earth, moon]
    scene.tracks = orbit_tracks + [tide]
    project.scenes.append(scene)
    for frame in (0, 17, 45):
        state = evaluate(project, scene.id, frame)
        m = next(n for n in state.nodes if n.id == moon.id)
        e = next(n for n in state.nodes if n.id == earth.id)
        screen_angle = math.degrees(math.atan2(-m.position[1], m.position[0]))
        diff = (screen_angle - float(e.params["tide_angle_deg"]) + 90) % 180 - 90
        assert abs(diff) < 6, frame


# --- bibliothèque, modèles, crédits --------------------------------------------------------------------
def test_phase13_variants_resolve() -> None:
    kinds = {"celestial", "world_map", "sky", "waves", "ray", "optic", "impacts", "particles", "black_hole"}
    found = {k.split(":")[0] for k in OBJECT_VARIANTS} & kinds
    assert found == kinds
    for key in ("celestial:moon_phase", "celestial:star_betelgeuse", "waves:doppler"):
        assert key in OBJECT_VARIANTS, key
        params, style = split_style(resolve_variant(key)[2])
        assert all(not k.startswith("style_") for k in params)
        assert isinstance(style, dict)


@pytest.mark.parametrize("template_id", PHASE13_TEMPLATES)
def test_phase13_templates_are_valid_and_animated(qapp, template_id: str) -> None:  # type: ignore[no-untyped-def]
    assert template_id in TEMPLATES
    project = create_project("t", Canvas(640, 360, 30, 1), template_id, 6)
    assert validate_project(project) == []
    scene = project.scenes[0]
    assert scene.tracks
    a = render_state_to_image(evaluate(project, scene.id, 10), project.canvas, 320, 180)
    b = render_state_to_image(
        evaluate(project, scene.id, scene.duration_frames - 10), project.canvas, 320, 180
    )
    ha = hashlib.sha256(bytes(a.constBits())).hexdigest()
    hb = hashlib.sha256(bytes(b.constBits())).hexdigest()
    assert ha != hb


def test_credits_name_the_bundled_datasets() -> None:
    project = create_project("t", Canvas(640, 360, 30, 1), "solar_system", 6)
    assert "solarsystemscope" in bundled_datasets_used(project)
    text = "\n".join(credits_lines(project))
    assert "Solar System Scope" in text and "CC BY 4.0" in text
    sky_project = create_project("t", Canvas(640, 360, 30, 1), "night_sky", 6)
    assert "d3celestial" in bundled_datasets_used(sky_project)
    empty = Project.create("vide", Canvas(640, 360, 30, 1))
    assert bundled_datasets_used(empty) == []

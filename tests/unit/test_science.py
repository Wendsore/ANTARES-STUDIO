"""SCI-01 à SCI-06, Gate 8 — unités sourcées, conversions, orbites de Kepler analytique vs numérique."""

from __future__ import annotations

import math

import pytest

from antares_studio.domain.model import Canvas
from antares_studio.resources.templates import create_project
from antares_studio.science.kepler import (
    OrbitElements,
    SimulationError,
    max_position_error,
    position_at,
    simulate_elements,
    simulate_two_body,
    solve_kepler,
    velocity_at,
)
from antares_studio.science.units import AU_M, GM_SUN, Quantity, UnitError, convert
from antares_studio.timeline.evaluator import evaluate
from antares_studio.timeline.presets import apply_preset
from tests.unit.helpers import make_node


def test_sci01_conversions_match_si_references() -> None:
    assert convert(1, "au", "m") == 149_597_870_700.0  # IAU 2012 B2
    assert convert(1, "ly", "km") == pytest.approx(9.4607304725808e12, rel=1e-12)
    assert convert(1, "pc", "au") == pytest.approx(206264.806, rel=1e-6)
    assert convert(3600, "s", "h") == 1.0 and convert(1, "yr", "d") == 365.25
    assert convert(1, "km/h", "m/s") == pytest.approx(1 / 3.6)
    assert convert(180, "deg", "rad") == pytest.approx(math.pi)
    assert convert(1, "ua", "km") == pytest.approx(149_597_870.7)  # alias français
    q = Quantity(1, "ly") + Quantity(63241.077, "au")
    assert q.unit == "ly" and q.value == pytest.approx(2.0, rel=1e-6)
    assert Quantity(1.5, "au").to("km").format() == "2.244e+08 km"


def test_sci02_incompatible_dimensions_are_diagnosed() -> None:
    with pytest.raises(UnitError, match="dimensions incompatibles"):
        convert(1, "km", "s")
    with pytest.raises(UnitError, match="unité inconnue"):
        convert(1, "furlong", "m")
    with pytest.raises(UnitError):
        Quantity(1, "kg") + Quantity(1, "m")


def test_sci06_extreme_values_are_diagnosed_not_silent() -> None:
    with pytest.raises(UnitError, match="non finie"):
        convert(float("nan"), "m", "km")
    with pytest.raises(UnitError, match="non finie"):
        convert(float("inf"), "au", "m")
    with pytest.raises(UnitError):
        convert(True, "m", "km")  # type: ignore[arg-type]
    with pytest.raises(SimulationError):
        OrbitElements(AU_M, 1.0)
    with pytest.raises(SimulationError):
        OrbitElements(-1.0, 0.1)
    with pytest.raises(SimulationError, match="centre"):
        simulate_two_body(GM_SUN, (0.0, 0.0), (0.0, 1.0), 1.0, 10)
    with pytest.raises(SimulationError, match="pas de temps trop grand"):
        # pas de temps énorme devant le temps dynamique : diagnostic explicite, jamais un résultat absurde
        simulate_two_body(GM_SUN, (AU_M, 0.0), (0.0, 29_780.0), 1e9, 200)


def test_sci03_circular_orbit_keeps_radius_and_angle() -> None:
    el = OrbitElements(AU_M, 0.0, GM_SUN)
    assert el.period / 86400 == pytest.approx(365.2569, rel=1e-5)
    for frac in (0.0, 0.25, 0.5, 0.75):
        x, y = position_at(el, frac * el.period)
        assert math.hypot(x, y) == pytest.approx(AU_M, rel=1e-12)
        assert math.atan2(y, x) % (2 * math.pi) == pytest.approx(2 * math.pi * frac % (2 * math.pi), abs=1e-9)
    sim = simulate_elements(el, steps=2000)
    radii = [math.hypot(x, y) for x, y in sim.positions]
    assert max(radii) / AU_M - 1 < 1e-5 and 1 - min(radii) / AU_M < 1e-5
    assert sim.energy_drift < 1e-8


def test_sci04_kepler_equation_and_apsides() -> None:
    for e in (0.0, 0.1, 0.5, 0.9, 0.99):
        for m in (0.0, 0.3, 1.0, 3.0, 6.0):
            ecc = solve_kepler(m, e)
            assert ecc - e * math.sin(ecc) == pytest.approx(m % (2 * math.pi), abs=1e-10)
    el = OrbitElements(AU_M, 0.6, GM_SUN)
    xp, yp = position_at(el, 0.0)
    xa, ya = position_at(el, el.period / 2)
    assert (xp, yp) == pytest.approx((el.periapsis, 0.0), rel=1e-9, abs=1.0)
    assert (xa, ya) == pytest.approx((-el.apoapsis, 0.0), rel=1e-9, abs=1.0)
    # 2e loi : vitesse maximale au périapse, minimale à l'apoapse ; vis-viva respectée
    vp, va = math.hypot(*velocity_at(el, 0.0)), math.hypot(*velocity_at(el, el.period / 2))
    assert vp > va
    assert vp**2 == pytest.approx(GM_SUN * (2 / el.periapsis - 1 / el.a), rel=1e-9)


def test_sci05_gate8_numerical_vs_analytic_convergence_and_energy() -> None:
    el = OrbitElements(AU_M, 0.3, GM_SUN)
    errors, drifts = [], []
    for steps in (500, 1000, 2000):
        sim = simulate_elements(el, steps=steps)
        errors.append(max_position_error(el, sim))
        drifts.append(sim.energy_drift)
    assert errors[-1] < 5e-4 and drifts[-1] < 1e-5
    assert drifts[0] > drifts[1] > drifts[2]  # la conservation s'améliore avec le pas
    # ordre 2 : l'erreur est divisée par ≈ 4 quand le pas est divisé par 2
    assert 3.0 < errors[0] / errors[1] < 5.0 and 3.0 < errors[1] / errors[2] < 5.0


def test_kepler_preset_tracks_follow_ellipse_both_methods() -> None:
    node = make_node("circle", "Planète", position=[0.0, 0.0])
    params = {
        "focus_x": 960.0,
        "focus_y": 540.0,
        "semi_major_px": 300.0,
        "eccentricity": 0.5,
        "duration_frames": 120,
        "samples_per_period": 60,
    }
    for method in ("analytique", "verlet"):
        tracks = apply_preset("kepler", node, {**params, "method": method})
        assert {t.property for t in tracks} == {"position.x", "position.y"}
        xs = {k.frame: k.value for k in tracks[0].keyframes}
        ys = {k.frame: k.value for k in tracks[1].keyframes}
        assert xs[0] == pytest.approx(960 + 150, abs=0.5) and ys[0] == pytest.approx(540, abs=0.5)  # périapse
        assert xs[60] == pytest.approx(960 - 450, abs=1.0) and ys[60] == pytest.approx(
            540, abs=1.0
        )  # apoapse
        assert xs[120] == pytest.approx(xs[0], abs=1.0)  # retour après une révolution
        for f, x in xs.items():  # tous les points sont sur l'ellipse de foyer (960, 540)
            dx, dy = (x - 960) + 300 * 0.5, ys[f] - 540
            assert (dx / 300) ** 2 + (dy / (300 * (1 - 0.25) ** 0.5)) ** 2 == pytest.approx(1.0, abs=2e-3)


def test_kepler_template_exports_parameters_hypotheses_and_sources() -> None:
    project = create_project("Kepler", Canvas(1920, 1080, 30, 1), "kepler_orbit", 10)
    meta = project.scientific_metadata
    assert meta["representation"] == "model" and meta["parameters"]["eccentricity"] == 0.6
    assert "deux corps" in meta["notes"] and len(meta["sources"]) == 2
    scene = project.scenes[0]
    planet = next(n for n in scene.nodes if n.name == "Planète")
    star = next(n for n in scene.nodes if n.name.startswith("Étoile"))
    dist = []
    for f in range(0, scene.duration_frames, 15):
        st = next(s for s in evaluate(project, scene.id, f).nodes if s.id == planet.id)
        dist.append(math.hypot(st.position[0] - star.position[0], st.position[1] - star.position[1]))
    assert max(dist) > 2.5 * min(dist)  # e = 0.6 : apoapse/périapse = 4
    assert any(n.kind == "callout" and "deux corps" in str(n.params["text"]) for n in scene.nodes)

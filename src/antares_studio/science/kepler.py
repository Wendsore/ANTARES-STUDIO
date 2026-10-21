"""Orbites képlériennes : solution analytique et intégration numérique à deux corps (SCI-03 à SCI-06).

Hypothèses explicites : problème à deux corps newtonien, masse du satellite négligeable devant le
corps central (``mu = G·M``), mouvement plan, pas de perturbation. Le corps central est au **foyer**.

Références : équation de Kepler et éléments orbitaux — JPL Solar System Dynamics,
https://ssd.jpl.nasa.gov/planets/approx_pos.html ; constantes nominales IAU 2015 B3 (``units.py``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from antares_studio.science.units import GM_SUN, check_finite


class SimulationError(ValueError):
    """Paramètre physique invalide (excentricité ≥ 1, pas nul, grandeur non finie…)."""


@dataclass(frozen=True)
class OrbitElements:
    """Ellipse képlérienne : demi-grand axe ``a`` (m), excentricité ``e`` (0 ≤ e < 1), ``mu`` (m³/s²)."""

    a: float
    e: float
    mu: float = GM_SUN

    def __post_init__(self) -> None:
        for name, v in (("a", self.a), ("e", self.e), ("mu", self.mu)):
            check_finite(v, name)
        if self.a <= 0 or self.mu <= 0:
            raise SimulationError("demi-grand axe et mu doivent être strictement positifs")
        if not 0.0 <= self.e < 1.0:
            raise SimulationError("l'excentricité d'une orbite fermée vérifie 0 ≤ e < 1")

    @property
    def period(self) -> float:
        """Troisième loi de Kepler : T = 2π √(a³/μ)."""
        return 2 * math.pi * math.sqrt(self.a**3 / self.mu)

    @property
    def periapsis(self) -> float:
        return self.a * (1 - self.e)

    @property
    def apoapsis(self) -> float:
        return self.a * (1 + self.e)

    def energy_per_mass(self) -> float:
        return -self.mu / (2 * self.a)


def solve_kepler(mean_anomaly: float, e: float, tol: float = 1e-12, max_iter: int = 50) -> float:
    """Anomalie excentrique E telle que E − e·sin E = M (Newton–Raphson, convergence quadratique)."""
    m = math.fmod(mean_anomaly, 2 * math.pi)
    ecc = m if e < 0.8 else math.pi
    for _ in range(max_iter):
        f = ecc - e * math.sin(ecc) - m
        ecc_next = ecc - f / (1 - e * math.cos(ecc))
        if abs(ecc_next - ecc) < tol:
            return ecc_next
        ecc = ecc_next
    raise SimulationError("l'équation de Kepler n'a pas convergé")


def position_at(elements: OrbitElements, t: float, t0: float = 0.0) -> tuple[float, float]:
    """Position (x, y) en m dans le plan orbital, foyer à l'origine, périapse sur +x à ``t0``."""
    n = 2 * math.pi / elements.period
    ecc = solve_kepler(n * (t - t0), elements.e)
    x = elements.a * (math.cos(ecc) - elements.e)
    y = elements.a * math.sqrt(1 - elements.e**2) * math.sin(ecc)
    return x, y


def velocity_at(elements: OrbitElements, t: float, t0: float = 0.0) -> tuple[float, float]:
    """Vitesse (m/s) par dérivation de la solution analytique."""
    n = 2 * math.pi / elements.period
    ecc = solve_kepler(n * (t - t0), elements.e)
    de_dt = n / (1 - elements.e * math.cos(ecc))
    vx = -elements.a * math.sin(ecc) * de_dt
    vy = elements.a * math.sqrt(1 - elements.e**2) * math.cos(ecc) * de_dt
    return vx, vy


@dataclass(frozen=True)
class SimulationResult:
    times: tuple[float, ...]
    positions: tuple[tuple[float, float], ...]
    velocities: tuple[tuple[float, float], ...]
    energies: tuple[float, ...]  # énergie mécanique par unité de masse à chaque instant
    dt: float
    method: str

    @property
    def energy_drift(self) -> float:
        """|E_max − E_min| / |E_0| : écart relatif de conservation sur la durée simulée."""
        e0 = self.energies[0]
        return (max(self.energies) - min(self.energies)) / abs(e0) if e0 else float("inf")


def simulate_two_body(
    mu: float,
    r0: tuple[float, float],
    v0: tuple[float, float],
    dt: float,
    steps: int,
) -> SimulationResult:
    """Intégration par Verlet-vitesse (symplectique, ordre 2) du mouvement autour d'un corps au foyer."""
    check_finite(mu, "mu")
    check_finite(dt, "dt")
    for v in (*r0, *v0):
        check_finite(v, "condition initiale")
    if mu <= 0 or dt <= 0 or steps < 1:
        raise SimulationError("mu > 0, dt > 0 et au moins un pas sont requis")
    if math.hypot(*r0) == 0:
        raise SimulationError("position initiale au centre : accélération infinie")

    def accel(x: float, y: float) -> tuple[float, float]:
        r = math.hypot(x, y)
        # stabilité du pas (SCI-05/06) : dt doit rester petit devant le temps dynamique √(r³/μ)
        if dt > 0.2 * math.sqrt(r**3 / mu):
            raise SimulationError(
                f"pas de temps trop grand ({dt:.3g} s) pour le rayon {r:.3g} m : réduire dt "
                f"(≤ {0.2 * math.sqrt(r**3 / mu):.3g} s)"
            )
        r3 = r**3
        return -mu * x / r3, -mu * y / r3

    def energy(x: float, y: float, vx: float, vy: float) -> float:
        return 0.5 * (vx * vx + vy * vy) - mu / math.hypot(x, y)

    x, y = r0
    vx, vy = v0
    ax, ay = accel(x, y)
    times = [0.0]
    pos = [(x, y)]
    vel = [(vx, vy)]
    en = [energy(x, y, vx, vy)]
    for i in range(1, steps + 1):
        x += vx * dt + 0.5 * ax * dt * dt
        y += vy * dt + 0.5 * ay * dt * dt
        ax2, ay2 = accel(x, y)
        vx += 0.5 * (ax + ax2) * dt
        vy += 0.5 * (ay + ay2) * dt
        ax, ay = ax2, ay2
        if not all(math.isfinite(v) for v in (x, y, vx, vy)):
            raise SimulationError(f"divergence numérique au pas {i} (pas de temps trop grand ?)")
        times.append(i * dt)
        pos.append((x, y))
        vel.append((vx, vy))
        en.append(energy(x, y, vx, vy))
    return SimulationResult(tuple(times), tuple(pos), tuple(vel), tuple(en), dt, "verlet")


def simulate_elements(elements: OrbitElements, steps: int, periods: float = 1.0) -> SimulationResult:
    """Simule ``periods`` révolutions depuis le périapse avec ``steps`` pas au total."""
    if steps < 1 or periods <= 0:
        raise SimulationError("steps ≥ 1 et periods > 0 requis")
    r0 = position_at(elements, 0.0)
    v0 = velocity_at(elements, 0.0)
    dt = periods * elements.period / steps
    return simulate_two_body(elements.mu, r0, v0, dt, steps)


def max_position_error(elements: OrbitElements, sim: SimulationResult) -> float:
    """Écart maximal (relatif à ``a``) entre la simulation et la solution analytique aux mêmes instants."""
    worst = 0.0
    for t, (x, y) in zip(sim.times, sim.positions, strict=True):
        xa, ya = position_at(elements, t)
        worst = max(worst, math.hypot(x - xa, y - ya) / elements.a)
    return worst

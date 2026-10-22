"""Simulation gravitationnelle à N corps (plan, newtonienne) : Verlet-vitesse, énergie et quantité de
mouvement contrôlées.

Hypothèses explicites : mécanique newtonienne, corps ponctuels, mouvement plan, pas de collision
(un adoucissement ``softening`` évite la singularité lors d'un passage rapproché, il modifie
légèrement la physique et doit rester très petit devant les distances typiques).

Références :
- chorégraphie en huit à trois corps : A. Chenciner, R. Montgomery, *Annals of Mathematics* 152 (2000)
  881–901 ; conditions initiales numériques de C. Simó (G = 1, masses 1, période ≈ 6,3259) ;
- Verlet-vitesse (symplectique, ordre 2) : L. Verlet, *Phys. Rev.* 159 (1967) 98.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from antares_studio.science.kepler import SimulationError
from antares_studio.science.units import check_finite

MAX_BODIES = 12
MAX_STEPS = 2_000_000


@dataclass(frozen=True)
class Body:
    name: str
    mass: float
    position: tuple[float, float]
    velocity: tuple[float, float]


@dataclass(frozen=True)
class NBodyResult:
    times: tuple[float, ...]
    positions: tuple[tuple[tuple[float, float], ...], ...]  # [instant][corps] -> (x, y)
    energies: tuple[float, ...]
    momenta: tuple[tuple[float, float], ...]
    dt: float
    method: str = "verlet"

    @property
    def energy_drift(self) -> float:
        """|E_max − E_min| / |E_0| sur la durée simulée."""
        e0 = self.energies[0]
        return (max(self.energies) - min(self.energies)) / abs(e0) if e0 else float("inf")

    def track(self, index: int) -> list[tuple[float, float]]:
        return [step[index] for step in self.positions]


def _validate(bodies: list[Body], g: float, dt: float, steps: int, softening: float) -> None:
    if not 2 <= len(bodies) <= MAX_BODIES:
        raise SimulationError(f"entre 2 et {MAX_BODIES} corps requis")
    check_finite(g, "G")
    check_finite(dt, "dt")
    check_finite(softening, "adoucissement")
    if g <= 0 or dt <= 0 or softening < 0:
        raise SimulationError("G > 0, dt > 0 et adoucissement ≥ 0 requis")
    if not 1 <= steps <= MAX_STEPS:
        raise SimulationError(f"nombre de pas entre 1 et {MAX_STEPS}")
    for b in bodies:
        check_finite(b.mass, f"masse de {b.name}")
        for v in (*b.position, *b.velocity):
            check_finite(v, f"condition initiale de {b.name}")
        if b.mass <= 0:
            raise SimulationError(f"la masse de {b.name} doit être strictement positive")


def total_energy(
    masses: list[float], pos: list[list[float]], vel: list[list[float]], g: float, eps2: float
) -> float:
    kinetic = sum(0.5 * m * (v[0] ** 2 + v[1] ** 2) for m, v in zip(masses, vel, strict=True))
    potential = 0.0
    n = len(masses)
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]
            potential -= g * masses[i] * masses[j] / math.sqrt(dx * dx + dy * dy + eps2)
    return kinetic + potential


def _accelerations(masses: list[float], pos: list[list[float]], g: float, eps2: float) -> list[list[float]]:
    n = len(masses)
    acc = [[0.0, 0.0] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]
            r2 = dx * dx + dy * dy + eps2
            if r2 == 0.0:
                raise SimulationError("deux corps au même point : collision (ajoutez un adoucissement)")
            inv_r3 = 1.0 / (r2 * math.sqrt(r2))
            acc[i][0] += g * masses[j] * dx * inv_r3
            acc[i][1] += g * masses[j] * dy * inv_r3
            acc[j][0] -= g * masses[i] * dx * inv_r3
            acc[j][1] -= g * masses[i] * dy * inv_r3
    return acc


def simulate_nbody(
    bodies: list[Body], dt: float, steps: int, g: float = 1.0, softening: float = 0.0
) -> NBodyResult:
    """Intègre ``steps`` pas de ``dt`` ; ``SimulationError`` si une grandeur diverge."""
    _validate(bodies, g, dt, steps, softening)
    masses = [b.mass for b in bodies]
    pos = [list(b.position) for b in bodies]
    vel = [list(b.velocity) for b in bodies]
    eps2 = softening * softening
    acc = _accelerations(masses, pos, g, eps2)

    def momentum() -> tuple[float, float]:
        return (
            sum(m * v[0] for m, v in zip(masses, vel, strict=True)),
            sum(m * v[1] for m, v in zip(masses, vel, strict=True)),
        )

    times = [0.0]
    positions = [tuple((p[0], p[1]) for p in pos)]
    energies = [total_energy(masses, pos, vel, g, eps2)]
    momenta = [momentum()]
    half = 0.5 * dt
    for step in range(1, steps + 1):
        for p, v, a in zip(pos, vel, acc, strict=True):
            v[0] += a[0] * half
            v[1] += a[1] * half
            p[0] += v[0] * dt
            p[1] += v[1] * dt
        acc = _accelerations(masses, pos, g, eps2)
        for v, a in zip(vel, acc, strict=True):
            v[0] += a[0] * half
            v[1] += a[1] * half
        if not all(math.isfinite(c) for p in pos for c in p):
            raise SimulationError(f"divergence numérique au pas {step} : réduisez le pas de temps")
        times.append(step * dt)
        positions.append(tuple((p[0], p[1]) for p in pos))
        energies.append(total_energy(masses, pos, vel, g, eps2))
        momenta.append(momentum())
    return NBodyResult(tuple(times), tuple(positions), tuple(energies), tuple(momenta), dt)


# Chorégraphie en huit (Chenciner–Montgomery), conditions de Simó : G = 1, trois masses égales à 1.
FIGURE_EIGHT_PERIOD = 6.32591398
_X1 = (0.97000436, -0.24308753)
_V3 = (-0.93240737, -0.86473146)


def figure_eight() -> list[Body]:
    return [
        Body("Corps A", 1.0, _X1, (-_V3[0] / 2, -_V3[1] / 2)),
        Body("Corps B", 1.0, (-_X1[0], -_X1[1]), (-_V3[0] / 2, -_V3[1] / 2)),
        Body("Corps C", 1.0, (0.0, 0.0), _V3),
    ]


def binary_star(mass_ratio: float = 0.5, separation: float = 1.0) -> tuple[list[Body], float]:
    """Deux étoiles en orbites circulaires autour du barycentre (G = 1, masse totale 1) et leur période."""
    check_finite(mass_ratio, "rapport de masses")
    if not 0 < mass_ratio <= 1 or separation <= 0:
        raise SimulationError("0 < rapport de masses ≤ 1 et séparation > 0 requis")
    m1 = 1.0 / (1.0 + mass_ratio)
    m2 = 1.0 - m1
    omega = math.sqrt(1.0 / separation**3)  # troisième loi de Kepler : ω² a³ = G (m1 + m2)
    r1, r2 = separation * m2, separation * m1  # distances au barycentre
    bodies = [
        Body("Étoile principale", m1, (r1, 0.0), (0.0, -omega * r1)),
        Body("Compagnon", m2, (-r2, 0.0), (0.0, omega * r2)),
    ]
    return bodies, 2 * math.pi / omega

# Session 2026-10-21 — Phase 8 (partiel) : unités sourcées, orbites de Kepler analytique et numérique

**Agent :** Claude (Claude Code) — **Machine :** `ki`, Debian 13, sans écran — **Branche :** `feat/phase-8-science` (empilée sur `feat/phase-9-packaging`, PR #6) — **PR :** #7. Décisions : ADR-0004.

## Réalisé

- `science/units.py` : constantes IAU/CODATA sourcées, `convert`, `Quantity`, `UnitError`.
- `science/kepler.py` : `OrbitElements` (période par la 3e loi), `solve_kepler`, `position_at`/`velocity_at`, `simulate_two_body` (Verlet-vitesse, énergie suivie, garde de stabilité du pas), `simulate_elements`, `max_position_error`.
- Preset d'animation **Orbite de Kepler** (foyer, a, e, révolutions, sens, direction du périapse, échantillons, méthode analytique/Verlet) ; modèle **Orbite de Kepler (modélisation à deux corps)** avec hypothèses, paramètres et sources exportés dans le manifest.
- Inspecteur : représentations schématique / modélisation / simulation / données mesurées / à l'échelle / mixte ; encadré d'avertissement long replié sur 85 % de la largeur.
- Capture : `docs/images/kepler-2026-10-21.png`.

## Mesures réellement exécutées (Linux)

| Cas | Résultat |
|---|---|
| Période Terre (a = 1 ua, GM☉ IAU 2015) | 365,257 jours (année sidérale de référence 365,256 j) |
| Verlet, e = 0,3, 500 / 1000 / 2000 pas par révolution | erreur de position max 3,6·10⁻⁴ / 8,9·10⁻⁵ / 2,2·10⁻⁵ (× a) ; dérive d'énergie 2,6·10⁻⁶ / 6,6·10⁻⁷ / 1,7·10⁻⁷ (ordre 2 confirmé) |
| Orbite circulaire, 2000 pas | rayon constant à 10⁻⁵ près, dérive d'énergie < 10⁻⁸ |
| Pas trop grand (dt = 10⁹ s à 1 ua) | `SimulationError` explicite, pas de résultat absurde |

Tests : `tests/unit/test_science.py` (8 tests) ; suite complète : voir ligne du journal de `docs/PROJECT_STATUS.md`.

## Reste à faire (phase 8)

Import CSV avec unités et courbes (objet graphe), N-corps simplifié, champ vectoriel ; phase 7 (Blender) non entamée : repli « Blender absent » = aucune fonction 3D, les fonctions 2D ne dépendent de rien.

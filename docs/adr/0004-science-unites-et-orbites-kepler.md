# ADR-0004 — Module science : unités sourcées et orbites de Kepler (analytique + numérique)

**Date :** 2026-10-21 — **Statut :** accepté — **Phase :** 8 (partiel)

## Contexte

Le master prompt (§9.2, §9.3, Gate 8, parcours P3) demande : grandeurs avec unités et sources,
diagnostic des unités incohérentes, modèles Kepler/N-corps comparés à une référence, conservation
vérifiée, hypothèses et paramètres exportés. Le projet doit rester pur Python (sans SciPy obligatoire).

## Décision

1. **`science/units.py`** : constantes exactes/nominales avec leurs sources (IAU 2012 B2 pour l'ua,
   SI/CODATA pour c et G, IAU 2015 B3 pour GM☉/GM⊕, année julienne). Conversion uniquement entre unités
   de même dimension, sinon `UnitError` (SCI-02) ; valeurs non finies refusées (SCI-06).
2. **`science/kepler.py`** : solution analytique (équation de Kepler, Newton–Raphson, ‖ΔE‖ < 10⁻¹²)
   et intégrateur **Verlet-vitesse** (symplectique, ordre 2) pour le problème à deux corps, avec énergie
   mécanique calculée à chaque pas et garde de stabilité (`dt ≤ 0,2 √(r³/μ)`, sinon erreur explicite).
   Le satellite est de masse négligeable ; pas de perturbation. Référence : JPL SSD (éléments képlériens).
3. **Preset `kepler`** (unités d'écran, μ arbitraire, temps vidéo ∝ temps physique) avec choix de méthode
   `analytique` / `verlet` ; **modèle « Orbite de Kepler »** avec étoile au foyer, trajectoire elliptique
   (`ellipse` décalée de −a·e), encadré d'hypothèses, métadonnées `representation = "model"`,
   `parameters`, `notes`, `sources` — exportées dans le manifest (Gate 8).
4. **Représentations** de l'inspecteur alignées sur §9.3 : schématique, modélisation, simulation
   numérique, données mesurées, à l'échelle, mixte.

## Alternatives écartées

- SciPy (`solve_ivp`) : dépendance lourde pour le packaging, inutile pour deux corps.
- RK4 : non symplectique, dérive d'énergie séculaire ; Verlet suffit et se vérifie simplement.
- N-corps général : reporté (hors MVP) ; l'API `simulate_two_body` en est la base.

## Conséquences et preuves

- Tests `tests/unit/test_science.py` : SCI-01 (ua, al, pc, temps, vitesses, alias français), SCI-02,
  SCI-03 (rayon constant, angle attendu, dérive < 10⁻⁸), SCI-04 (équation de Kepler, apsides, vis-viva),
  SCI-05/Gate 8 (erreur ÷ 4 par pas ÷ 2, dérive décroissante), SCI-06, preset sur l'ellipse, modèle.
- Non livré : import CSV avec unités et courbes, N-corps, champ vectoriel (phase 8 à poursuivre).

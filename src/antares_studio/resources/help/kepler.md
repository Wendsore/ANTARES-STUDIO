# Orbites de Kepler et unités

## L'animation « Orbite de Kepler (modélisation) »

Elle place un objet sur une **ellipse** dont un **foyer** est occupé par l'astre central, et respecte la deuxième loi de Kepler : l'objet va **plus vite près du périapse** (le point le plus proche) que loin de lui.

| Réglage | Sens |
|---|---|
| Foyer X, Foyer Y (px) | position de l'astre central dans l'image |
| Demi-grand axe (px) | taille de l'orbite |
| Excentricité (0 ≤ e < 1) | 0 = cercle ; plus elle approche de 1, plus l'ellipse est allongée |
| Nombre de révolutions | tours effectués pendant la durée choisie |
| Sens horaire (à l'écran) | sens de parcours |
| Direction du périapse (°) | orientation de l'ellipse |
| Échantillons par révolution | nombre d'images clés posées par tour |
| Méthode | *Analytique (équation de Kepler)* ou *Numérique (Verlet, énergie contrôlée)* |

### Les deux méthodes

- **Analytique** : résout l'équation de Kepler, M = E − e·sin E, par la méthode de Newton. C'est la solution exacte du problème à deux corps.
- **Numérique (Verlet)** : intègre pas à pas les équations du mouvement avec l'algorithme de Verlet « vitesse », qui conserve bien l'énergie. Un pas trop grand pour l'orbite est refusé avec un message, plutôt que de produire une trajectoire fausse.

Les deux méthodes donnent la même ellipse à la précision de l'image près. La méthode numérique sert à **montrer** qu'une simulation retrouve la loi de Kepler.

### Ce que le modèle suppose

Deux corps seulement, l'astre central fixe, aucune perturbation. Le temps de la vidéo est proportionnel au temps réel : une révolution dure *durée ÷ nombre de révolutions*. Déclarez la représentation **Modélisation** ou **Simulation numérique** dans les [métadonnées](rigueur-scientifique.md).

## Le modèle « Orbite de Kepler »

Bibliothèque, onglet *Modèles* : une scène complète avec un Soleil au foyer, une planète sur une ellipse d'excentricité 0,6, l'orbite tracée, un titre et l'encadré d'échelle.

## Constantes et unités de référence

Les modèles utilisent des valeurs officielles, citées dans leurs sources :

| Grandeur | Valeur | Source |
|---|---|---|
| Unité astronomique (au) | 149 597 870 700 m exactement | UAI 2012, résolution B2 |
| Vitesse de la lumière (c) | 299 792 458 m/s exactement | CODATA, définition du mètre |
| Année julienne | 365,25 jours | UAI |
| Constante gravitationnelle (G) | 6,674 30 × 10⁻¹¹ m³ kg⁻¹ s⁻² | CODATA 2018 |
| Paramètre gravitationnel du Soleil (GM☉) | 1,327 124 4 × 10²⁰ m³ s⁻² | UAI 2015, résolution B3 |

L'année-lumière, environ 9,461 × 10¹⁵ m ou 63 241 au, en découle : c × une année julienne.

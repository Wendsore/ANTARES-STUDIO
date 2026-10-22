# Animations prédéfinies

Une animation prédéfinie pose pour vous les **images clés** d'un mouvement courant. Elle ne modifie que l'objet sélectionné, s'annule avec Ctrl+Z et se retouche ensuite à la main dans la [Timeline](images-cles.md).

## Appliquer une animation

1. Sélectionnez un ou plusieurs objets.
2. Bibliothèque, onglet **Animations**, double-clic sur l'animation ; ou menu **Animation**.
3. Réglez les paramètres puis **Appliquer**.

Les réglages **Début (image)** et **Durée (images)** se comptent en images : à 30 images/s, 60 images = 2 secondes. Le libellé de la durée rappelle la cadence du projet. Par défaut, l'animation commence à l'image courante.

Appliquer une deuxième animation sur la même propriété la remplace ; sur une autre propriété, elle s'ajoute. Exemple : *Apparition* (opacité) puis *Orbite schématique* (position).

## Les animations disponibles

<!-- auto:animations -->

## Interpolation

Le réglage *Interpolation* choisit l'allure du mouvement :

| Choix | Allure |
|---|---|
| Linéaire | vitesse constante (rotations, orbites) |
| Accélération | démarre doucement |
| Décélération | s'arrête doucement |
| Accélération puis décélération | démarre et s'arrête doucement (déplacements naturels) |

## Bon à savoir

- **Orbite schématique** : le bouton « Utiliser la position actuelle de l'objet comme rayon/phase » calcule le rayon et l'angle de départ à partir de l'endroit où vous avez posé l'objet. Combinez-la avec l'objet *Orbite (tracé)* de même centre et même rayon.
- **Orbite de Kepler** : une vraie trajectoire elliptique, calculée analytiquement ou par intégration numérique. Voir [Orbites de Kepler](kepler.md).
- **Tracer la courbe** : ne s'applique qu'à un [graphique](graphiques.md).
- La **boucle** de lecture (case *Boucle* de la Timeline) relance la scène ; une rotation d'un nombre entier de tours boucle sans saut.

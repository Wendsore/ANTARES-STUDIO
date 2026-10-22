# Rigueur scientifique : représentation, échelle, sources

Une animation simplifie toujours. Le spectateur doit savoir **ce qui est exact et ce qui est schématisé**. ANTARES vous aide à le dire, sans vous l'imposer.

## Déclarer la représentation

Cliquez sur le fond du canevas : l'[Inspecteur](inspecteur.md) affiche les **Métadonnées scientifiques** du projet.

| Représentation | Quand la choisir |
|---|---|
| Schématique (visuel arbitraire) | tailles, couleurs et distances choisies pour la lisibilité |
| Modélisation (hypothèses explicites) | un modèle physique simplifié, par exemple deux corps sans perturbation |
| Simulation numérique (algorithme, pas, erreurs) | une intégration pas à pas ; précisez méthode et précision dans les notes |
| Données mesurées (source, incertitude) | des mesures réelles, avec leur source |
| À l'échelle | distances et tailles respectent les proportions réelles |
| Mixte (préciser dans les notes) | plusieurs de ces cas dans la même vidéo |

- **Distances et tailles à l'échelle** : décochez dès que les proportions sont déformées. Les crédits mentionnent alors « Schéma : distances et tailles non à l'échelle ».
- **Notes** : simplifications et hypothèses, en langage clair.

## Avertir dans l'image

**Objet > Avertissement d'échelle (« non à l'échelle »)** ajoute en bas de la scène l'encadré « Schéma : distances et tailles non à l'échelle » et décoche « à l'échelle » dans les métadonnées. Le texte se modifie dans l'Inspecteur, ou par double-clic. Les modèles scientifiques l'incluent déjà.

Le Système solaire est un bon exemple : à l'échelle, sur un écran de 1920 pixels où Neptune serait au bord, la Terre serait à 64 pixels du Soleil et mesurerait bien moins d'un pixel.

## Citer ses sources

Bouton **Sources…** des métadonnées : une ligne par source, avec un libellé et une adresse ou une référence. Exemple : « NASA Planetary Fact Sheet » et `https://nssdc.gsfc.nasa.gov/planetary/factsheet/`. Les sources figurent dans les [crédits](credits.md) et dans le fichier `.credits.txt` exporté.

Les modèles ajoutent eux-mêmes leurs sources (UAI, CODATA, NASA, JPL) sans effacer les vôtres.

## Bonnes pratiques

- Une constante = une source, avec l'unité.
- Distinguez « on observe » (données) de « on modélise » (modèle).
- Préférez les organismes de référence : UAI, BIPM et CODATA, NASA, ESA, agences nationales.
- Dites ce que la vidéo ne montre pas.

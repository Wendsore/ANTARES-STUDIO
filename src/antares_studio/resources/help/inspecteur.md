# L'Inspecteur

L'Inspecteur, à droite, change selon ce qui est sélectionné.

## Un objet sélectionné

1. **Propriétés communes** : nom, position, rotation, échelle, opacité, visible, ordre (plan), verrouillé.
2. **Paramètres** propres au type : rayon, texte, police, colonnes d'un graphique…
3. **Style** : couleurs, épaisseurs, pointillés.

- Les **couleurs** s'affichent en code hexadécimal ; un clic ouvre le sélecteur, transparence comprise.
- Les nombres se règlent au clavier, avec les flèches ou la molette.
- Les champs de **ressource** (image, données CSV, séquence) proposent les fichiers déjà importés dans le projet.

## Le losange ◆ : images clés

Chaque propriété animable porte un losange.

- **Clic** : pose une image clé à l'image courante avec la valeur actuelle, ou la retire s'il y en a déjà une.
- **Clic droit** : supprime toute l'animation de cette propriété.
- Losange **jaune** : la propriété est animée ; **orange** : une clé existe exactement à l'image courante.

Voir [Images clés et Timeline](images-cles.md).

## Plusieurs objets sélectionnés

L'Inspecteur l'indique ; déplacez-les ensemble sur le canevas. Il détaille un objet à la fois.

## Rien n'est sélectionné

L'Inspecteur montre :

- **la scène** : nom, durée en images (l'infobulle donne la durée en secondes), couleur de fond, format du canevas ;
- **les métadonnées scientifiques** du projet : représentation, à l'échelle ou non, notes, sources. Voir [Rigueur scientifique](rigueur-scientifique.md).

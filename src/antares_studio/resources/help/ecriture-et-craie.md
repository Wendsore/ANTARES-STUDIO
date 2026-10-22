# Écriture progressive et styles d'écriture

Un texte ou une équation peut **s'écrire sous les yeux du spectateur**, lettre après lettre, comme au tableau. Cinq façons d'écrire sont proposées, et une collection de styles (craie, feutre, cahier, machine à écrire, néon…) règle en un geste la police, la couleur et la texture.

## Faire écrire un texte ou une équation

1. Sélectionnez le texte ou l'équation.
2. Bibliothèque, onglet **Animations**, double-clic sur **Écrire** : réglez le début et la durée (2 à 3 secondes conviennent pour une ligne).
3. Dans l'[Inspecteur](inspecteur.md), choisissez la **Façon d'écrire** :

| Façon d'écrire | Ce qu'on voit |
|---|---|
| **Tracé puis remplissage** | le contour de chaque lettre se dessine puis se remplit, comme dans les vidéos de 3Blue1Brown |
| **Craie** | chaque lettre se découvre de gauche à droite, comme passée à la craie |
| **Machine à écrire** | les caractères arrivent un à un, curseur en bout de ligne |
| **Lettres en fondu** | chaque lettre apparaît en fondu en montant légèrement |
| **Mots en fondu** | les mots arrivent l'un après l'autre |

Le réglage **Écriture (0 → 1)** est animable avec son losange ◆ : 0 = rien d'écrit, 1 = tout est écrit. **Effacer l'écriture** fait l'inverse. Une équation s'écrit dans l'ordre de lecture : la barre de fraction se trace avant le dénominateur, le trait de la racine se tire comme à la main.

## Styles d'écriture

Bibliothèque, onglet **Effets**, section **Styles d'écriture** : sélectionnez un ou plusieurs textes, encadrés ou équations, puis double-clic. Le style remplace la police, la couleur, la façon d'écrire et les effets ; un seul Ctrl+Z annule le tout.

<!-- auto:styles-ecriture -->

## Le tableau à craie

1. Cliquez dans le vide du canevas : l'Inspecteur montre la scène. Choisissez le **Décor** *Tableau noir (ardoise)* ou *Tableau vert d'école*.
2. Écrivez vos textes et équations, appliquez le style **Craie blanche**, puis l'animation **Écrire**.
3. Une figure (triangle, flèche, cercle) prend l'aspect craie avec l'effet **Craie** (onglet Effets) : réglage **Texture craie** de l'Inspecteur.

Le grain de la craie est fixé au tableau, comme sur une vraie ardoise : un texte qui se déplace « passe » sur le grain. Le modèle **Tableau noir (écriture à la craie)** montre l'ensemble.

## Décors de scène

Dessinés par le logiciel à la taille de l'export, sans image à fournir :

<!-- auto:decors -->

## Polices livrées

Ces polices sont livrées avec ANTARES Studio (licences libres OFL 1.1 ou Apache 2.0) : la vidéo a le même aspect sur tous les ordinateurs. Elles apparaissent en tête de la liste **Police** de l'Inspecteur ; les polices installées sur l'ordinateur suivent.

<!-- auto:polices -->

Les accents français sont présents dans toutes ces polices. Pour une équation, préférez une police lisible (Kalam, EB Garamond, DejaVu Sans) : les polices très décoratives rendent mal les exposants.

Voir aussi : [Équations](equations.md), [Effets et filtres](effets-et-filtres.md), [Animations prédéfinies](animations.md).

# Grilles, transformations et espace courbé

L'objet **Grille** représente un plan quadrillé que l'on peut **transformer** (algèbre linéaire) ou **déformer** (gravitation, onde, tourbillon), vu de dessus ou comme une nappe en perspective.

## Ajouter une grille

Bibliothèque, onglet **Objets**, catégorie **Grilles et espace** :

| Objet | Usage |
|---|---|
| **Repère quadrillé (plan)** | axes et carreaux, base de toute figure |
| **Grille et vecteurs î, ĵ** | transformations linéaires, avec les vecteurs de base en vert et rouge |
| **Espace-temps courbé (nappe)** | nappe en perspective, creusée par une masse |
| **Onde gravitationnelle (nappe)** | rides circulaires qui se propagent |

## Transformation linéaire

Une matrice 2 × 2 \[\[a, b\], \[c, d\]\] agit sur le plan : sa première colonne (a, c) est l'image du vecteur **î**, la seconde (b, d) celle de **ĵ**. Les droites restent droites et parallèles, l'origine reste fixe.

1. Sélectionnez la grille, puis l'animation **Transformation linéaire** : entrez a, b, c, d.
2. La grille d'origine reste en filigrane (réglage *Grille d'origine en filigrane*), pour comparer avant et après.

| Matrice (a, b, c, d) | Effet |
|---|---|
| 1, 1, 0, 1 | cisaillement horizontal |
| 0, −1, 1, 0 | rotation d'un quart de tour |
| 2, 0, 0, 2 | agrandissement ×2 |
| 1, 0, 0, −1 | symétrie par rapport à l'axe horizontal |
| 1, 2, 0.5, 1 | déterminant 0 : le plan s'écrase sur une droite |

Les coefficients sont aussi animables un à un dans l'Inspecteur (losange ◆).

## Déformations

Choisissez la **Déformation** dans l'Inspecteur, puis animez son **Intensité** avec l'animation **Courber l'espace** :

- **Puits de gravité** : vue de dessus, l'espace est attiré vers le centre ; en perspective, la nappe se creuse (profil en 1/r adouci).
- **Onde** : rides circulaires ; l'animation **Onde qui se propage** les fait s'éloigner du centre.
- **Tourbillon** : rotation d'autant plus forte qu'on est près du centre.

Le **Rayon de la déformation** règle sa taille. Une intensité négative inverse l'effet (bosse au lieu de creux).

## Vue en perspective

Cochez **Vue en perspective** : la grille devient une nappe inclinée (*Inclinaison de la vue*, de 0° vue de dessus à 85° rasante). C'est la représentation classique de l'espace-temps courbé par une masse. Le modèle **Espace-temps courbé par une masse** pose une étoile qui descend au fond du creux.

## Rigueur

La nappe creusée est une **analogie** : elle aide à se représenter la courbure, mais l'espace-temps réel a quatre dimensions et la gravité ne « tire » pas les objets vers le bas d'une nappe. Le modèle l'indique par une légende ; gardez-la, ou dites-le dans la narration. Voir [Rigueur scientifique](rigueur-scientifique.md).

## Tracer la grille

L'animation **Tracer la courbe** dessine la grille progressivement, des lignes centrales vers les bords (réglage *Tracé de la grille*).

Voir aussi : [Solides 3D](solides-3d.md), [Animations prédéfinies](animations.md).

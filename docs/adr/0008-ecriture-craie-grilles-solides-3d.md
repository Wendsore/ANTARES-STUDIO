# ADR-0008 — Écriture progressive, craie, grilles déformables et solides 3D

**Date :** 2026-10-22 — **Statut :** accepté — **Phase :** 12 — **Branche :** `feat/phase-12-ecriture-grilles-3d` (empilée sur la PR #13)

## Contexte

Demande du porteur, après la vidéo de démonstration des textes et équations : « Non, c'est pas assez. Je
veux que tu ailles voir, par exemple, les styles de Science for All, où il écrit comme sur un tableau avec
de la craie […]. Est-ce qu'il y a une grille ? Est-ce que j'arrive à représenter, par exemple, une
déformation spatiale ? […] des vidéos comme 3Blue1Brown […]. Est-ce que j'arrive à faire des animations un
peu 3D ? Est-ce que dans ma bibliothèque, j'ai des cubes et des objets de ce type ? »

État avant : textes et équations apparaissaient en bloc (fondu) ; aucune police livrée (polices du système
seulement, aspect variable d'un poste à l'autre) ; aucune texture craie ni décor de tableau ; aucune grille
hormis l'aide au placement de l'éditeur (jamais exportée) ; la 3D se limitait aux modèles glTF importés et
aux séquences Blender. Menée en autonomie : chaque arbitrage est consigné ci-dessous. Contraintes
inchangées : hors ligne, français, PySide6 + NumPy + FFmpeg, même dessin dans l'éditeur et à l'export
(ADR-0001), schéma de projet additif, provenance de toute ressource livrée (ADR-0003).

Références : la description par le porteur des vidéos de Science4All (écriture à la craie sur un
tableau) ; le style des vidéos de 3Blue1Brown tel qu'il est documenté par Manim Community (`Write` : contour puis remplissage ;
`LinearTransformationScene` / `ApplyMatrix` sur un `NumberPlane` ; `ApplyPointwiseFunction` pour les
déformations non linéaires), dont seuls les principes visuels sont repris (aucun code copié).

## Décisions

| # | Question | Retenu | Écarté, et pourquoi |
|---|---|---|---|
| 1 | Comment « écrire » un texte ? | Paramètre animable **`write`** (0 → 1) sur Texte et Équation, et **`write_style`** : *tracé puis remplissage* (façon « Write » de 3Blue1Brown), *craie* (chaque lettre découverte de gauche à droite, bord en biais), *machine à écrire* (curseur), *lettres* et *mots* en fondu. Chaque caractère est une unité dont la progression est décalée de la précédente | Animer l'opacité de copies de l'objet : un objet par lettre, ingérable ; vidéo pré-rendue : rien d'éditable |
| 2 | Découpage en unités | Contours vectoriels de la police (`QPainterPath.addText`) placés par `QTextLayout` (mêmes retours à la ligne et alignements que `drawText`) ; formules : glyphes et traits relevés par la mise en page existante (`layout_glyphs`), triés de gauche à droite (la barre de fraction se trace avant le dénominateur) ; mis en cache | Polices « à un seul trait » (Hershey) pour une vraie écriture au stylo : ensemble limité de glyphes, accents incomplets, rendu maigre ; noté dans « Limites » |
| 3 | `write = 1` | **Dessin habituel inchangé** : un texte entièrement écrit est identique pixel pour pixel à un texte d'un ancien projet (test) | Toujours passer par les contours : petites différences d'anticrénelage avec les projets existants |
| 4 | Anciens projets | `write` et `write_style` absents valent leurs défauts (1, « tracé ») ; `get_property` renvoie désormais la valeur par défaut d'un paramètre ajouté après l'enregistrement d'un projet | Migration du schéma : inutile pour un champ additif |
| 5 | Formule en cours de transformation | L'écriture ne s'applique qu'à la formule de départ (`morph` = 0) | Combiner écriture et transformation : cas sans usage clair |
| 6 | Aspect craie | Effet d'objet **`fx_chalk`** (0 → 1) : grain de 256 × 256 px à graine fixe (bruit fin + amas), qui retire de la matière au tracé ; motif **fixé à l'image** (comme le grain d'une ardoise) ; s'applique à tout objet (texte, formule, polygone) ; préréglage « Craie » | Police « craie » seule : la texture ne suivrait pas les figures ; grain lié à l'objet : texture qui « nage » quand l'objet bouge, et calcul par objet |
| 7 | Polices | **17 familles livrées** (Google Fonts, SIL OFL 1.1, Apache 2.0 pour Permanent Marker et Special Elite), fichiers non modifiés avec leur licence et une empreinte SHA-256 ; chargées à la première mise en page (`ensure_fonts`) ; en tête de la liste **Police** de l'Inspecteur (liste éditable, polices du poste ensuite) ; 6,1 Mo | Dépendre des polices installées : la vidéo change d'un ordinateur à l'autre ; télécharger à la demande : hors ligne exigé |
| 8 | Collection de styles | **16 styles d'écriture** (Bibliothèque > Effets) : craie blanche, jaune, bleue, titre gravé, crayonné, tracé mathématique (3Blue1Brown), feutre, cahier, notes rapides, écriture d'élève, machine à écrire, terminal, titre de vidéo, néon, citation, style simple. Un style fixe police, couleur, façon d'écrire et effets (ceux d'avant sont remis à zéro) sur les textes, encadrés et équations sélectionnés, en un Ctrl+Z ; seules les propriétés que l'objet possède sont touchées (un encadré reçoit la couleur sur son texte) | Styles « réutilisables » définis par l'utilisateur : déjà listé dans « Limites », hors de la demande |
| 9 | Tableau | Champ de scène **`backdrop`** (omis s'il est vide) : *tableau noir*, *tableau vert*, *papier quadrillé*, *cahier à lignes*, *plan d'architecte*, *ciel étoilé* ; dessiné par le logiciel à la taille de sortie (au plus 3840 px, puis agrandi dans l'éditeur très zoomé), mis en cache, graine fixe ; peint avec le fond, donc **absent d'un export transparent** ; Inspecteur de scène > **Décor** | Images de tableau fournies : poids, licence, flou en 4K |
| 10 | Grille | Nouveau type **Grille** : matrice 2 × 2 animable `m_a…m_d` agissant sur les coordonnées mathématiques (y vers le haut), filigrane de la grille d'origine, vecteurs **î** (vert) et **ĵ** (rouge), axes, tracé progressif (`progress`, lignes centrales d'abord) ; lignes subdivisées (8 points par carreau) ; étendue calculée par l'antécédent des coins du cadre (une rotation d'un quart de tour remplit encore le cadre) ; 400 lignes au plus | Champ de vecteurs, repère gradué avec nombres : utiles mais pas demandés, gardés pour plus tard |
| 11 | Déformation spatiale | `warp` : **puits de gravité** (vue de dessus : attraction en R²/(r²+R²) ; en perspective : creux en 1/√(r²+R²), forme classique de l'« espace-temps courbé »), **onde** (rides circulaires, phase animable), **tourbillon** ; intensité et rayon animables ; **vue en perspective** (nappe inclinée de 0 à 85°) | Vraie géométrie de Schwarzschild (plongement de Flamm) : moins lisible pour un débutant ; la nappe reste une analogie, dite par une légende dans le modèle et dans l'aide |
| 12 | Solides 3D | Nouveau type **Solide 3D** : cube, pavé droit, sphère, cylindre, cône, pyramide, tétraèdre, octaèdre, icosaèdre, tore ; maillages générés (orientés vers l'extérieur, volume orienté vérifié) avec arêtes à montrer (arêtes vives, parallèles et méridiens) ; lacet, tangage, roulis, perspective animables ; rendus *faces et arêtes*, *faces*, *fil de fer* (arêtes cachées en pointillé) et *verre* ; éclairage et tri des faces repris des modèles glTF | Moteur 3D (OpenGL, Blender) : rendu différent de l'export ou dépendance lourde ; tampon de profondeur : inutile pour des solides convexes posés côte à côte, limite écrite dans l'aide |
| 13 | Bibliothèque | Les solides sont listés **un par un** (« Cube », « Sphère »…) et les grilles en quatre variantes (repère, vecteurs î ĵ, espace-temps, onde) : identifiants « type:variante » (`OBJECT_VARIANTS`) ; vignettes rendues par le moteur pour les solides | Un seul « Solide 3D » à régler ensuite : la question du porteur était justement « ai-je des cubes dans ma bibliothèque ? » |
| 14 | Animations | 6 nouvelles : **Écrire**, **Effacer l'écriture**, **Rotation 3D**, **Transformation linéaire** (a, b, c, d), **Courber l'espace**, **Onde qui se propage** ; « Tracer la courbe » vaut aussi pour la grille | Une animation par style d'écriture : le style est une propriété, l'animation reste la même |
| 15 | Modèles | 4 nouveaux : **Tableau noir** (théorème de Pythagore à la craie), **Transformation linéaire** (cisaillement), **Espace-temps courbé par une masse** (l'étoile descend au fond du creux, position calculée par la géométrie même de la grille ; légende « analogie »), **Solides 3D en rotation** | Contenu sans repère scientifique : le porteur demande des données réelles et des sources pour le contenu factuel |
| 16 | Sons | 4 bruitages de synthèse, catégorie **Écriture** : craie sur le tableau, machine à écrire, stylo sur papier, effacer le tableau (CC0, mêmes contrôles que les 26 autres) | Enregistrements tiers : licences et hors ligne |

## Non fait (et pourquoi)

- Écriture au tracé d'un seul trait (polices Hershey) : voir décision 2.
- Surfaces z = f(x, y), axes 3D gradués, caméra 3D : la 3D reste une projection par objet (limite écrite).
- Solides qui s'interpénètrent : tri des faces sans tampon de profondeur (limite écrite).
- Styles d'écriture enregistrés par l'utilisateur.

## Conséquences et preuves

- Schéma : uniquement additif (`params.write`, `params.write_style`, `style.fx_chalk`, `scene.backdrop`,
  nouveaux types `grid` et `solid3d`) ; un projet sans ces champs s'enregistre comme avant.
- Tests : voir le journal `docs/session-logs/2026-10-22-ecriture-grilles-3d.md`.
- Paquet : les polices sont dans `resources/**`, déjà inclus par le spec PyInstaller.
- **NON TESTÉ sur Windows 11 réel** : rendu des polices livrées et des solides sous Windows.

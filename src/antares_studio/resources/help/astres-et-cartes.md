# Astres, étoiles, cartes et ciel

ANTARES Studio fournit des **ressources réelles** prêtes à l'emploi : les textures des planètes, de la Lune et du Soleil, des cartes du monde et le ciel étoilé avec ses constellations. Tout est livré avec le logiciel ; leurs licences figurent dans les crédits de vos vidéos.

## Planètes, Lune et Soleil

Bibliothèque, onglet **Objets**, catégorie **Astres**, double-clic. Chaque astre est une sphère texturée éclairée par une source de lumière : jour, nuit et terminateur, nuages et lumières des villes pour la Terre, anneaux de Saturne avec l'ombre de la planète. L'inclinaison de l'axe proposée est la vraie.

<!-- auto:astres -->

Réglages dans l'Inspecteur :

- **Rotation sur lui-même**, **Inclinaison de l'axe**, **Vu depuis** (0 : équateur, 90 : pôle nord). L'animation **Rotation d'un astre** le fait tourner.
- **Lumière : direction** et **hauteur** : d'où vient la lumière du Soleil. À 0°, la lumière vient de derrière l'observateur (astre entièrement éclairé, « pleine lune ») ; à 180°, de derrière l'astre (« nouvelle lune »).
- **Lumière ambiante** : éclaire faiblement le côté nuit.
- **Texture personnelle** : choisissez *Texture personnelle* comme astre et importez une image équirectangulaire (rapport 2:1), par exemple une carte d'exoplanète. Renseignez sa licence dans *Ressources*.

## Phases de la Lune

La variante **Lune (phase : premier quartier)** et l'animation **Phases (lumière qui tourne)** font tourner la lumière autour de la Lune : nouvelle lune → premier quartier → pleine lune → dernier quartier. Le modèle **Phases de la Lune (astres réels, vue depuis la Terre)** montre en même temps l'orbite vue de dessus et la Lune vue depuis la Terre.

## Marées

Le réglage **Marée (exagérée)** dessine deux bourrelets alignés sur l'axe **Marée : direction** : l'un face à l'astre attracteur, l'autre à l'opposé. Deux représentations :

- **Océans** : un bourrelet bleu translucide autour de l'astre ;
- **Astre entier étiré** : toute la planète se déforme.

L'animation **Marées qui suivent un astre** fait tourner les bourrelets avec la Lune : donnez-lui les mêmes réglages (tours, sens, angle de départ) que l'animation **Orbite** de la Lune. Voir le modèle **Marées (Lune en orbite, bourrelets exagérés)**. La déformation est volontairement exagérée : la vraie marée océanique fait moins d'un mètre.

## Étoiles connues

Catégorie **Étoiles connues** : une étoile est un disque lumineux dont la **couleur est calculée à partir de sa température** (rayonnement du corps noir). Rouge en dessous de 4 000 K, blanc vers 6 500 K, bleuté au-delà de 10 000 K. L'astre **Étoile** accepte n'importe quelle température.

<!-- auto:etoiles -->

Les rayons des géantes ne sont pas à l'échelle à l'écran : Bételgeuse a un rayon d'environ 770 fois celui du Soleil.

## Cartes du monde

Catégorie **Cartes et ciel** : planisphère des continents, des pays, contours, Terre vue de l'espace (jour) ou de nuit.

- **Projection** : *Equal Earth* (aires respectées, recommandée pour comparer des surfaces), *équirectangulaire*, *Mercator* (angles respectés, mais le Groenland y paraît aussi grand que l'Afrique).
- **Continent mis en valeur** : les autres continents passent au second plan.
- **Noms des continents**, **Méridiens et parallèles**, **Apparition d'ouest en est** (animable : la carte se dessine d'ouest en est).

## Ciel étoilé

L'objet **Ciel étoilé** affiche les 5 044 étoiles visibles à l'œil nu (magnitude ≤ 6) et les 88 constellations, à leur vraie position.

- **Centre : ascension droite** et **Centre : déclinaison** (en degrés), **Champ de vue**, **Rotation du champ**.
- **Magnitude limite** : n'afficher que les étoiles les plus brillantes.
- **Constellation mise en valeur** : son sigle de l'UAI, par exemple *Ori* pour Orion, *UMa* pour la Grande Ourse.
- **Scintillement** : animé par **Faire avancer le temps**.

Les couleurs des étoiles viennent de leur indice de couleur B−V mesuré.

## Sources des données

<!-- auto:jeux-de-donnees -->

Voir aussi [Provenance et licences](provenance-et-licences.md) et [Crédits](credits.md).

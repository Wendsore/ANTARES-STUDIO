# Solides 3D

La Bibliothèque fournit des **solides** prêts à l'emploi, dessinés par le logiciel : aucun fichier à importer. Pour un objet plus complexe (molécule, satellite), voir [Modèles 3D (glTF)](modeles-3d.md).

## Ajouter un solide

Bibliothèque, onglet **Objets**, catégorie **Solides 3D**, double-clic :

<!-- auto:solides -->

La forme peut être changée ensuite dans l'Inspecteur (*Forme*). Le **pavé droit** a trois proportions réglables (longueur, hauteur, profondeur).

## Orienter et faire tourner

- **Rotation horizontale**, **Inclinaison** et **Roulis** (en degrés) orientent le solide ; tous trois sont animables.
- L'animation **Rotation 3D** le fait tourner sur lui-même (nombre de tours, inclinaison ajoutée).
- La **Rotation** générale de l'objet (en haut de l'Inspecteur) fait tourner l'image dans le plan de l'écran, ce n'est pas une rotation 3D.

## Rendu

| Rendu | Aspect |
|---|---|
| **Faces ombrées et arêtes** | faces éclairées, arêtes visibles en couleur de contour |
| **Faces ombrées** | volume seul |
| **Fil de fer** | arêtes seules ; les arêtes cachées sont en pointillé, comme dans un manuel de géométrie |
| **Verre** | faces transparentes, toutes les arêtes visibles |

La **Perspective** (0 à 1) rapproche l'observateur : 0 donne une vue sans fuite (projection orthographique, celle des manuels), 1 une perspective marquée.

Les couleurs se règlent dans la section *Style* : faces, arêtes, épaisseur des arêtes. Les effets (lueur, ombre portée, craie) s'appliquent aussi.

## Limites

Les faces sont triées de l'arrière vers l'avant, sans tampon de profondeur : deux solides qui s'interpénètrent peuvent se dessiner dans le mauvais ordre. Placez-les côte à côte, ou réglez leur **Ordre (plan)**. Les surfaces de fonctions z = f(x, y) et les axes 3D gradués ne sont pas encore disponibles.

Voir aussi : [Grilles et espace courbé](grilles-et-deformations.md).

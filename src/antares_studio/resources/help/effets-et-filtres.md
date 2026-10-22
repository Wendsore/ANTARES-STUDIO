# Effets et filtres

Deux niveaux de retouche, visibles dans le canevas, l'image PNG et la vidéo exportée (même moteur de dessin).

- Les **effets** s'appliquent à **un objet** : lueur, ombre portée, flou, couleurs. Ils s'animent comme n'importe quelle propriété.
- Les **filtres** s'appliquent à **toute une scène** : étalonnage des couleurs, vignettage, grain de film.

## Appliquer un préréglage

Bibliothèque, onglet **Effets** :

1. **Effets d'objet** : sélectionnez un ou plusieurs objets, puis double-cliquez sur un effet. Il **remplace** les effets précédents de ces objets ; un seul Ctrl+Z annule le tout. **Retirer les effets** remet tout à zéro.
2. **Filtres de scène** : double-clic, et la scène affichée reçoit le filtre. **Aucun filtre** le retire.
3. **Animations d'effet** : sélectionnez un objet, puis double-cliquez (réglages, puis application), comme dans l'onglet *Animations*.

Les groupes et les caméras n'ont pas d'effets : appliquez-les aux objets qu'ils contiennent.

<!-- auto:effets -->

## Régler finement un objet

Sélectionnez l'objet : la section **Effets** de l'[Inspecteur](inspecteur.md) donne chaque réglage, avec son losange ◆ pour l'animer.

| Réglage | Effet |
|---|---|
| Flou (px) | adoucit tout l'objet ; 0 = net |
| Lueur : rayon, couleur, intensité | halo coloré autour des parties visibles |
| Ombre : opacité, flou, décalage X et Y, couleur | ombre portée ; opacité 0 = pas d'ombre |
| Luminosité, contraste, saturation | couleurs de l'objet ; saturation 0 = noir et blanc |

Les distances sont en pixels **du projet** : une lueur de 40 px garde la même taille relative en 720p comme en 4K.

## Régler finement la scène

Cliquez dans le vide du canevas (rien de sélectionné) : la section **Filtres de la scène** de l'Inspecteur propose un **Préréglage** et chaque réglage. Modifier un réglage fait passer le préréglage à « Personnalisé ».

<!-- auto:filtres -->

Le grain de film change à chaque image mais il est **reproductible** : deux exports du même projet donnent exactement les mêmes images.

## Bon usage

- Un effet attire l'œil : réservez la lueur à l'objet dont vous parlez.
- Un filtre unifie une scène ; gardez le même d'une scène à l'autre pour une vidéo cohérente.
- Le flou et la lueur coûtent du calcul : l'aperçu peut ralentir sur un ordinateur modeste, l'export reste exact.

Voir aussi : [Animations prédéfinies](animations.md), [Bruitages et ambiances](bruitages.md).

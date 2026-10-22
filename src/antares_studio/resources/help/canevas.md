# Le canevas : sélectionner, déplacer, zoomer

Le canevas montre la scène **exactement comme dans la vidéo exportée** : même moteur de dessin, mêmes polices, mêmes couleurs. Le cadre sombre autour de l'image ne fait pas partie de la vidéo.

## Sélectionner

| Geste | Effet |
|---|---|
| Clic sur un objet | le sélectionne |
| Maj + clic | ajoute ou retire l'objet de la sélection |
| Glisser sur le fond | cadre de sélection (Maj : ajoute à la sélection) |
| Clic sur le fond | désélectionne tout |
| Échap | désélectionne tout |
| Ctrl+A | sélectionne tous les objets de la scène |

Un objet **verrouillé** est entouré de rouge et ne se déplace pas : déverrouillez-le dans [Scènes et objets](scenes-et-calques.md).

## Déplacer, redimensionner, faire pivoter

- **Glisser** l'objet le déplace (toute la sélection bouge ensemble).
- **Flèches du clavier** : 1 pixel ; **Maj + flèche** : 10 pixels.
- **Poignées carrées** blanches : redimensionnent ; **Maj** conserve les proportions.
- **Poignée ronde orange**, au-dessus du cadre : rotation ; **Maj** par pas de 15°.
- **Double-clic** sur un texte, un encadré ou une équation : modifie son texte.

Chaque geste complet compte pour une seule étape d'annulation (Ctrl+Z).

Pour des valeurs exactes (position en pixels, rotation en degrés, échelle), utilisez l'[Inspecteur](inspecteur.md).

## Se déplacer dans la vue

| Geste | Effet |
|---|---|
| Molette | zoom autour du pointeur |
| Ctrl + + / Ctrl + - | zoom avant / arrière |
| Ctrl+0 | ajuster l'image à la fenêtre |
| Clic molette et glisser, ou Alt + glisser | déplacer la vue |

La barre d'état indique la position du pointeur en pixels de la vidéo et le niveau de zoom.

## Aides visuelles

Ces aides ne sont jamais exportées.

- **Affichage > Afficher la grille** (Ctrl+') : grille de repère.
- **Affichage > Aimanter à la grille** (Ctrl+Maj+') : les déplacements s'alignent sur la grille.
- **Affichage > Zones sûres (sous-titres)** : cadres pointillés des zones que les écrans ne rognent pas. Gardez textes et sous-titres à l'intérieur.

Quand la scène est vide, le canevas affiche un rappel des premiers gestes.

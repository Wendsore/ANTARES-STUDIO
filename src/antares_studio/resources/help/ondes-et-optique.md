# Ondes, lumière et optique

Pour expliquer l'effet Doppler, les interférences, la propagation de la lumière ou la dualité onde-corpuscule.

## Le temps

Les ondes, les photons et les particules avancent avec le réglage **Temps (s)**. Appliquez l'animation **Faire avancer le temps** : le temps de l'objet suit celui de la scène (un facteur l'accélère ou le ralentit).

## Ondes

Bibliothèque, catégorie **Ondes** :

| Variante | Ce qu'elle montre |
|---|---|
| **Ondes circulaires** | une source immobile émet des fronts régulièrement espacés |
| **Effet Doppler** | la source avance : les fronts se resserrent devant (son plus aigu), s'espacent derrière (plus grave) |
| **Cône de Mach** | la source va plus vite que l'onde : les fronts s'enveloppent en un cône de demi-angle arcsin(c/v) |
| **Fentes de Young (champ d'onde)** | deux sources cohérentes ; crêtes et creux qui avancent |
| **Franges d'interférence (intensité)** | l'intensité moyenne : franges brillantes et sombres fixes |
| **Corde** | onde progressive ou stationnaire (nœuds et ventres) |

Réglages : vitesse de l'onde *c*, fréquence, vitesse et direction de la source. La fréquence perçue devant une source qui approche vaut f·c/(c − v) : à v = c/2, elle double. L'option **Fronts : la source reste au centre** garde la source immobile à l'écran.

## Rayons lumineux

Catégorie **Lumière et optique**. Un **Rayon lumineux** suit un chemin de points (modifiable dans l'Inspecteur) et se dessine sous plusieurs formes :

- **Faisceau** lumineux avec une lueur ;
- **Onde** : sinusoïde le long du rayon, qui défile ;
- **Paquets d'onde** qui voyagent, **Photons** (points lumineux) ;
- **Pointillés** ou **fléché**, pour l'optique géométrique.

La **Longueur d'onde réelle (nm)** donne la couleur réelle de la lumière (650 nm : rouge ; 532 nm : vert). L'animation *Tracer* propage le rayon ; **Photons qui voyagent** fait parcourir le chemin aux photons.

## Éléments d'optique

Laser, lampe, miroir, lame séparatrice, lentilles, plaques à une ou deux fentes, écran, détecteur de photons, prisme, polariseur. Les éléments sont dessinés ; c'est à vous de placer les rayons (le logiciel ne calcule pas la réfraction). Le réglage **Allumé / déclenché** allume un détecteur ou un laser ; l'animation **Déclic du détecteur** le fait clignoter.

## Écran de détection : la dualité onde-corpuscule

L'**Écran de détection** montre des impacts de photons tirés au hasard selon la loi d'intensité :

- **Deux fentes** : cos² × sinc², les franges d'interférence ;
- **Une fente** : sinc², la diffraction ;
- **Chemin mesuré** : si l'on sait par quelle fente passe chaque photon, les franges disparaissent.

L'animation **Impacts qui s'accumulent** fait apparaître les photons un à un : d'abord des points au hasard, puis les franges. Le tirage est reproductible (réglage **Tirage (graine)**). Le modèle **Photons et fentes de Young (onde-corpuscule)** l'illustre.

Cette expérience a été réalisée photon par photon par Philippe Grangier, Gérard Roger et Alain Aspect (Institut d'optique, 1986 ; Alain Aspect a reçu le prix Nobel de physique 2022), et avec des électrons un par un par Akira Tonomura (1989).

## Lumière et éclairage

L'objet **Lumière** éclaire la scène :

- **Halo lumineux**, **Rayons** (soleil, éclat) ;
- **Projecteur** : un cône de lumière ;
- **Pénombre** : assombrit toute la scène sauf un cercle, pour mettre un objet en lumière.

Les **Astres** et les **Solides 3D** ont leur propre direction de lumière (*Lumière : direction* et *hauteur*), animable.

Voir aussi [Phénomènes cosmiques](phenomenes-cosmiques.md) et [Grilles, transformations et espace courbé](grilles-et-deformations.md).

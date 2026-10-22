# Sous-titres

Les sous-titres rendent la vidéo accessible aux personnes sourdes ou malentendantes, et lisible sans le son, par exemple dans les transports.

## Écrire des sous-titres

Onglet **Narration**, puis **Sous-titres** :

1. Placez la tête de lecture au début de la phrase.
2. **Ajouter à l'image courante**, ou **Narration > Ajouter un sous-titre à l'image courante**.
3. Dans le tableau, double-cliquez sur **Texte** pour écrire ; réglez **Début (s)** et **Fin (s)**.

Le sous-titre s'affiche sur le canevas, dans la bande du bas, **exactement comme à l'export**.

## Contrôles automatiques

Sous le tableau, ANTARES signale :

- un texte vide ;
- une durée inférieure à 0,5 seconde ;
- un sous-titre qui dépasse la fin de la scène ;
- deux sous-titres qui se chevauchent ;
- un texte trop long pour un téléphone : plus de 2 lignes ou plus de 84 caractères ;
- une **lecture trop rapide** : plus de 17 caractères par seconde ;
- un sous-titre affiché **plus de 7 secondes** : mieux vaut couper la phrase ;
- un **style peu lisible** : contraste insuffisant entre le texte et son fond (règle WCAG), ou fond transparent sans contour contrasté.

## Importer et exporter

- **Importer SRT/VTT…** : fichiers SubRip (`.srt`) ou WebVTT (`.vtt`) encodés en UTF-8. ANTARES demande s'il faut remplacer les sous-titres existants de la scène.
- **Exporter SRT…** : écrit un fichier `.srt` ou `.vtt` pour la scène courante.

## À l'export de la vidéo

Les sous-titres sont **incrustés** dans l'image et écrits aussi dans un fichier `.srt` à côté de la vidéo. Pour une vidéo complète, les sous-titres de toutes les scènes sont fusionnés avec les bons décalages. Les plateformes vidéo acceptent ce `.srt` comme sous-titres activables.

Activez **Affichage > Zones sûres (sous-titres)** pour vérifier que rien d'important n'est caché sous les sous-titres.

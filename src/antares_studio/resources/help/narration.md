# Narration audio

La voix est le cœur d'une vidéo pédagogique. ANTARES **importe** votre enregistrement ; il n'enregistre pas le micro lui-même.

## Enregistrer sa voix

- Avec le dictaphone d'un téléphone, puis transférez le fichier.
- Avec **Audacity** (gratuit, https://www.audacityteam.org), export en WAV ou MP3.
- Pièce calme, micro à une vingtaine de centimètres, une phrase par prise.

## Importer

1. Le projet doit être **enregistré** : le son est copié dans son dossier `audio/`.
2. **Narration > Importer une narration audio…**, ou onglet **Narration**, bouton **Importer une narration…**.
3. Formats acceptés : WAV, MP3, FLAC, OGG, M4A, AAC (lecture par FFmpeg).
4. Le clip est placé à la **tête de lecture** ; une piste **♪** apparaît dans la Timeline avec sa forme d'onde.
5. La fiche de provenance s'ouvre : pour votre propre voix, choisissez « Œuvre personnelle ». Voir [Provenance et licences](provenance-et-licences.md).

Le fichier d'origine n'est jamais modifié : tous les réglages sont appliqués à l'export.

## Régler

Dans le tableau de l'onglet *Audio* :

| Colonne | Rôle |
|---|---|
| Début (s) | moment où le son commence dans la scène |
| Gain | volume (1 = inchangé ; 0,5 = moitié ; 2 = double, risque de saturation) |
| Fondu entrée / sortie (s) | montée et descente progressives |
| Muet | coupe le clip sans le supprimer |
| Durée (s) | durée du fichier, pour information |

- **Placer à l'image courante** cale le clip sélectionné sur la tête de lecture.
- Glisser le clip dans la Timeline le décale aussi.
- **Supprimer** retire le clip du projet ; le fichier reste dans `audio/`.

## Écouter

L'aperçu sonore de l'éditeur fonctionne « au mieux » : selon la machine, il peut rester silencieux. **L'export mixe toujours exactement** les clips, gains et fondus.

Plusieurs clips dans une même scène se superposent (mixage). Chaque scène a ses propres clips.

# Installation, FFmpeg et diagnostics

## Ce dont ANTARES Studio a besoin

| Élément | Obligatoire ? | Rôle |
|---|---|---|
| ANTARES Studio | oui | l'éditeur |
| **FFmpeg** | pour exporter la vidéo et lire les sons | encodage MP4, lecture des fichiers audio, formes d'onde |
| Blender | non | uniquement pour la [planète 3D](planete-3d.md) |

La version Windows préparée avec PyInstaller peut contenir FFmpeg dans son sous-dossier `bin`. Sinon, installez FFmpeg depuis https://ffmpeg.org (rubrique *Download*) et ajoutez-le au `PATH`, ou indiquez son emplacement à ANTARES.

## Vérifier l'installation

**Aide > Diagnostics…** affiche la version d'ANTARES, du système, de Python et de Qt ; il indique si FFmpeg (avec son encodeur H.264), FFprobe et Blender sont trouvés. Joignez ce texte à tout signalement de problème.

Si FFmpeg n'est pas trouvé :

1. **Aide > Chemin de FFmpeg…**
2. Désignez le fichier `ffmpeg.exe` (Windows) ou `ffmpeg` (Linux, macOS).
3. Relancez **Aide > Diagnostics…** pour confirmer.

## Contrôle sans interface

Dans un terminal, la commande suivante vérifie toute la chaîne (modèle, sauvegarde, rendu, export si FFmpeg est présent) et affiche un compte rendu :

```
antares-studio --selftest
```

Voir [Ligne de commande](ligne-de-commande.md).

## Données et vie privée

ANTARES Studio n'envoie rien en ligne. Les préférences (projets récents, disposition des panneaux, thème, favoris, tutoriels terminés) sont stockées localement par Qt (registre Windows ou fichier de configuration).

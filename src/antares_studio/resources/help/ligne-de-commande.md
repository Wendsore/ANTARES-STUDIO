# Ligne de commande

Les mêmes fonctions sont disponibles sans interface, pour automatiser un rendu ou vérifier une installation.

```
antares-studio --version
antares-studio --selftest
antares-studio --export "Ma vidéo.antares" sortie.mp4
antares-studio --export "Ma vidéo.antares" sortie.mp4 --profile draft_720p
antares-studio --export "Ma vidéo.antares" sortie.mp4 --scene "Phases de la Lune"
antares-studio --export "Ma vidéo.antares" sortie.mp4 --all-scenes
antares-studio "Ma vidéo.antares"
```

| Option | Effet |
|---|---|
| `--version` | affiche la version et quitte |
| `--selftest` | contrôle complet sans interface : modèle, sauvegarde, rendu, et export si FFmpeg est présent |
| `--export PROJET SORTIE.mp4` | exporte la première scène, ou celle désignée par `--scene` |
| `--profile` | `draft_720p`, `final_1080p` (par défaut) ou `mobile_720p` |
| `--scene` | nom ou identifiant de la scène |
| `--all-scenes` | toutes les scènes à la suite (vidéo complète) |
| *(chemin seul)* | ouvre ce projet dans l'interface |

Le code de sortie vaut 0 en cas de succès : la commande s'utilise dans un script. Sous Windows, avec la version empaquetée, remplacez `antares-studio` par le chemin de `ANTARES Studio.exe`.

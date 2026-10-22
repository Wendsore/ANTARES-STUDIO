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
| `--profile` | identifiant d'un profil d'[export](export-video.md) : `final_1080p` (par défaut), `draft_720p`, `mobile_720p`, `youtube_1080p`, `vertical_1080x1920`, `square_1080`, `slides_4_3`, `webm_1080p`, `gif_480`, `preview_360p` |
| `--scene` | nom ou identifiant de la scène |
| `--all-scenes` | toutes les scènes à la suite (vidéo complète) |
| `--capture DOSSIER` | enregistre des captures des écrans principaux et `captures.txt` (écran, échelle) pour une recette visuelle |
| *(chemin seul)* | ouvre ce projet dans l'interface |

Le code de sortie vaut 0 en cas de succès : la commande s'utilise dans un script. Sous Windows, avec la version empaquetée, remplacez `antares-studio` par le chemin de `ANTARES Studio.exe`.

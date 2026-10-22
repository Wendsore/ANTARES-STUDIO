# Projets, fichiers et dossiers

## Un projet est un dossier

Un projet ANTARES est un **dossier** dont le nom finit par `.antares`, par exemple `Phases de la Lune.antares`. Il contient :

| Élément | Contenu |
|---|---|
| `project.json` | la description du projet : scènes, objets, animations, sous-titres, métadonnées |
| `assets/` | les images et données importées (copies) |
| `audio/` | les narrations importées (copies) |
| `autosaves/` | les sauvegardes automatiques |
| `renders/` | proposé par défaut pour les vidéos exportées |

Les chemins internes sont **relatifs** : copiez, déplacez ou envoyez le dossier entier (clé USB, archive ZIP), il s'ouvrira ailleurs à l'identique. Les fichiers d'origine que vous importez ne sont jamais modifiés.

## Commandes

| Action | Menu | Raccourci |
|---|---|---|
| Nouveau projet (format, résolution, cadence, durée, modèle) | **Fichier > Nouveau projet…** | Ctrl+N |
| Ouvrir un dossier `.antares` | **Fichier > Ouvrir…** | Ctrl+O |
| Rouvrir un projet récent | **Fichier > Projets récents** | — |
| Enregistrer | **Fichier > Enregistrer** | Ctrl+S |
| Enregistrer une copie ailleurs | **Fichier > Enregistrer sous…** | Ctrl+Maj+S |

Une étoile `*` dans le titre de la fenêtre signale des modifications non enregistrées. En fermant ou en changeant de projet, ANTARES propose d'enregistrer, uniquement si une perte est possible.

## Choisir le format au départ

| Format | Usage |
|---|---|
| 16:9 paysage | YouTube, télévision, vidéoprojecteur |
| 9:16 vertical | téléphone, formats courts |
| 1:1 carré | réseaux sociaux |

La **résolution** (1080p ou 720p) et la **cadence** (30 images/s recommandé ; 24, 25 ou 60 possibles) sont fixées à la création. Les positions des objets sont exprimées en pixels de cette image.

Un projet créé avec une version plus ancienne d'ANTARES s'ouvre normalement : il est mis à jour à l'ouverture, sans toucher au fichier tant que vous n'enregistrez pas.

# Guide 1 — Votre première vidéo : « Pourquoi la Lune change-t-elle de forme ? »

*Parcours P1 du cahier des charges. Validé le 2026-10-21 sur Linux (tests `tests/ui/test_main_window.py`), à confirmer sur Windows 11.*

## 1. Lancer ANTARES Studio

```bash
antares-studio            # ou : python -m antares_studio.app.main
```

L'espace de travail comporte : la **Bibliothèque** (objets, animations, modèles) à gauche, la liste **Scènes et objets**, le **canevas** au centre, l'**Inspecteur** à droite et la **Timeline** en bas. Tout est en français ; aucune ligne de code n'est nécessaire.

## 2. Créer le projet

1. `Fichier > Nouveau projet…` (Ctrl+N).
2. Titre « Phases de la Lune », format 16:9, 1080p, 30 images/s, durée 20 s.
3. Modèle de départ : **Phases de la Lune (Soleil, Terre, Lune en orbite)**, puis « Créer ».

La scène contient déjà le Soleil, la Terre, l'orbite, la Lune animée sur un tour complet, un titre qui apparaît en fondu et la légende « Schéma : distances et tailles non à l'échelle ».

## 3. Modifier les objets

- **Sélectionner** : clic sur un objet (Maj+clic pour en ajouter, ou cadre de sélection sur le fond).
- **Déplacer** : glisser l'objet ; flèches du clavier pour un réglage fin (Maj = 10 px).
- **Redimensionner / pivoter** : poignées carrées (Maj conserve les proportions) ; poignée ronde orange pour la rotation (Maj = pas de 15°).
- **Propriétés** : l'Inspecteur affiche position, rotation, échelle, opacité, puis les paramètres propres (rayon, texte, police, couleurs…). Un clic sur une couleur ouvre le sélecteur.
- **Texte** : double-clic sur un texte pour l'éditer.
- **Ordre et visibilité** : panneau « Scènes et objets » (œil, cadenas, ▲ Monter / ▼ Descendre).
- **Annuler / Rétablir** : Ctrl+Z / Ctrl+Y ; chaque glisser compte pour une seule étape.

## 4. Animer sans programmer

1. Sélectionnez un objet, puis onglet **Animations** de la Bibliothèque (ou menu `Animation`).
2. Double-cliquez sur **Orbite schématique**, **Apparition**, **Translation**, **Rotation**, **Pulsation** ou **Disparition**.
3. Réglez début, durée et paramètres (rayon, centre, nombre de tours, sens…) puis « Appliquer ».

Pour une animation sur mesure : placez la tête de lecture, cliquez sur le losange ◆ à côté d'une propriété dans l'Inspecteur pour poser une **image clé**, déplacez-vous dans le temps, modifiez la valeur. Avec « Clé auto » (Timeline), chaque modification pose une clé.

Lecture : **Espace** ; image par image : **,** et **.** ; Début/Fin : **Début** / **Fin**. La timeline se parcourt à la souris (glisser sur la règle), les losanges se déplacent par glisser, **Suppr** efface une clé sélectionnée.

## 5. Enregistrer et rouvrir

`Fichier > Enregistrer` (Ctrl+S) crée un dossier `Phases de la Lune.antares/` contenant `project.json`, `assets/`, `audio/`, `autosaves/`, `renders/`. Le dossier se déplace ou se copie librement (chemins relatifs). Une sauvegarde automatique est faite toutes les 60 s dans `autosaves/` ; en cas de fichier illisible, ANTARES propose la dernière sauvegarde valide sans jamais écraser l'original.

## 6. Exporter la vidéo

`Fichier > Exporter la vidéo…` (Ctrl+E) : choisissez **Final 1080p** (ou **Brouillon 720p** pour vérifier rapidement), le fichier de sortie, puis « Exporter ». La progression s'affiche ; « Annuler l'export » arrête proprement sans laisser de fichier partiel. À la fin, le fichier est vérifié (résolution, cadence, nombre d'images) et un `*.manifest.json` décrit le rendu.

FFmpeg doit être installé (`Aide > Diagnostics…` l'indique ; `Aide > Chemin de FFmpeg…` permet de le désigner manuellement).

## Ce qui n'est pas encore disponible

Voix off et sous-titres depuis l'interface (en cours, phase 6), recherche d'icônes dans des packs, équations LaTeX, 3D. Voir `docs/PROJECT_STATUS.md`.

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
2. Double-cliquez sur **Orbite schématique**, **Orbite de Kepler** (ellipse autour d'un foyer, méthode analytique ou numérique), **Apparition**, **Translation**, **Rotation**, **Pulsation** ou **Disparition**.
3. Réglez début, durée et paramètres (rayon, centre, nombre de tours, sens…) puis « Appliquer ».

Pour une animation sur mesure : placez la tête de lecture, cliquez sur le losange ◆ à côté d'une propriété dans l'Inspecteur pour poser une **image clé**, déplacez-vous dans le temps, modifiez la valeur. Avec « Clé auto » (Timeline), chaque modification pose une clé.

Lecture : **Espace** ; image par image : **,** et **.** ; Début/Fin : **Début** / **Fin**. La timeline se parcourt à la souris (glisser sur la règle), les losanges se déplacent par glisser, **Suppr** efface une clé sélectionnée.

## 5. Enregistrer et rouvrir

`Fichier > Enregistrer` (Ctrl+S) crée un dossier `Phases de la Lune.antares/` contenant `project.json`, `assets/`, `audio/`, `autosaves/`, `renders/`. Le dossier se déplace ou se copie librement (chemins relatifs). Une sauvegarde automatique est faite toutes les 60 s dans `autosaves/` ; en cas de fichier illisible, ANTARES propose la dernière sauvegarde valide sans jamais écraser l'original.

## 6. Ajouter la narration et les sous-titres

Ouvrez l'onglet **Narration** (à côté de la Timeline, ou `Affichage > Narration`).

- **Audio** : `Narration > Importer un fichier audio…` (WAV, MP3, OGG, FLAC, M4A). Le fichier est copié dans `audio/` du projet et placé à la tête de lecture ; une piste « ♪ nom » apparaît dans la Timeline avec sa forme d'onde. Faites glisser le clip pour le décaler, ou réglez dans le tableau le début (s), le gain, les fondus d'entrée/sortie et « Muet ». Il n'y a pas d'enregistrement micro : enregistrez la voix avec un autre outil (par exemple Audacity) puis importez le fichier.
- **Sous-titres** : placez la tête de lecture, `Narration > Ajouter un sous-titre à la tête de lecture` (Ctrl+Maj+T), puis modifiez début, fin et texte dans le tableau. Le sous-titre s'affiche sur le canevas dans la bande inférieure, exactement comme à l'export. `Importer des sous-titres…` accepte SRT et VTT (UTF-8) ; `Exporter des sous-titres…` écrit un SRT ou VTT. Les chevauchements, les durées trop courtes et les lignes trop longues sont signalés sous le tableau.

Le son de l'éditeur est joué « au mieux » (il peut rester silencieux selon la machine) ; l'export, lui, mixe toujours exactement les clips.

## 7. Provenance, sources et crédits

- **Avertissement d'échelle** : les modèles scientifiques affichent un encadré « non à l'échelle ». Pour l'ajouter à une scène créée à la main : `Objet > Avertissement d'échelle`. Le texte se modifie dans l'inspecteur.
- **Sources scientifiques** : sans objet sélectionné, l'inspecteur montre les **Métadonnées scientifiques** (représentation, à l'échelle, notes, bouton `Sources…`). Les sources apparaissent dans les crédits.
- **Provenance des images et sons** : après chaque import, une fiche demande l'auteur, la source et la licence. « Plus tard » laisse la ressource en « provenance manquante » (visible dans l'onglet **Ressources** de la bibliothèque, double-clic pour compléter). À l'export, une ressource sans provenance ou non redistribuable est signalée.
- **Crédits** : `Fichier > Inventaire des licences et crédits…` liste les ressources et le texte de crédits ; ce texte est écrit à côté de chaque vidéo exportée (`*.credits.txt`). Pour les afficher dans la vidéo, ajoutez le modèle **Crédits** depuis la bibliothèque (onglet Modèles).
- **Équations** : objet **Équation (formule)** (bibliothèque, catégorie Maths). Écrivez par exemple `F = \frac{G m_{1} m_{2}}{r^{2}}` ou `v = \sqrt{\frac{G M}{r}}` ; `\alpha`, `\cdot`, `\to`, `\infty`, `\vec{v}` sont reconnus. Aucune installation LaTeX n'est nécessaire.
- **Données mesurées** : `Objet > Importer des données (CSV) en graphique…` lit un fichier dont l'en-tête porte les unités (`t (s);h (m)`), le copie dans le projet et crée un graphique (colonnes X/Y, bornes, points et titre dans l'inspecteur). L'animation **Tracer la courbe** dessine la courbe progressivement.
- **Favoris** : cochez la case d'un objet, d'une animation ou d'un modèle ; le bouton ★ n'affiche que vos favoris.

## 8. Exporter la vidéo

`Fichier > Exporter la vidéo…` (Ctrl+E) : choisissez **Final 1080p** (ou **Brouillon 720p** pour vérifier rapidement), cochez **Toutes les scènes à la suite** pour la vidéo complète (sinon seule la scène courante est exportée), le fichier de sortie, puis « Exporter ». La progression s'affiche ; « Annuler l'export » arrête proprement sans laisser de fichier partiel. À la fin, le fichier est vérifié (résolution, cadence, nombre d'images, piste audio) et un `*.manifest.json` décrit le rendu. Les sous-titres sont incrustés dans l'image et aussi écrits dans un fichier `.srt` à côté de la vidéo ; les crédits dans un fichier `.credits.txt`.

FFmpeg doit être installé (`Aide > Diagnostics…` l'indique ; `Aide > Chemin de FFmpeg…` permet de le désigner manuellement).

## Ce qui n'est pas encore disponible

Enregistrement micro, packs d'icônes tiers, équations LaTeX, simulations physiques, 3D, installateur Windows. Voir `docs/PROJECT_STATUS.md`.

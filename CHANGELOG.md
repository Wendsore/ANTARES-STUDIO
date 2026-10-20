# Changelog — ANTARES Studio

Toutes les évolutions **effectives** (pas les intentions). Format : date, lot, changements observables.

## [0.1.0.dev0] — 2026-10-21 — Phase 9 (partiel) : ligne de commande et paquet PyInstaller

- `antares-studio --version`, `--selftest` (contrôle d'installation sans interface) et `--export PROJET SORTIE.mp4 [--profile] [--scene]`.
- FFmpeg livré dans `bin/` à côté de l'exécutable empaqueté est détecté automatiquement.
- `packaging/` : spec PyInstaller (mode dossier, fenêtré, sans UPX), `build.py --check`, notices de licences tierces ; job CI Windows qui construit le `.exe`, l'autoteste, exporte un projet modèle et publie l'archive.
- `scripts/bench_scrub.py` : mesure de latence de scrubbing (100 objets).

## [0.1.0.dev0] — 2026-10-21 — Phase 5 : provenance, crédits, avertissement d'échelle, parcours P1

- Fiche de provenance (auteur, source, licence parmi une liste, attribution, redistribution) proposée après chaque import d'image ou d'audio, modifiable depuis l'onglet **Ressources** de la bibliothèque ou `Fichier > Inventaire des licences et crédits…` (statut par ressource, usages, crédits générés, copie/enregistrement).
- Export : avertissement par ressource utilisée sans provenance ou non redistribuable ; fichier `<vidéo>.credits.txt` (sources scientifiques, mention « non à l'échelle », ressources attribuées, logiciel) et crédits + métadonnées scientifiques dans le manifest.
- Nouvel objet **Encadré** (`callout`) et action `Objet > Avertissement d'échelle` ; les modèles Lune, année-lumière et orbite portent l'avertissement en encadré, hors de la bande des sous-titres.
- Nouveaux modèles **Introduction** et **Crédits** (scène générée depuis les sources, ressources et le logiciel).
- Inspecteur : section **Métadonnées scientifiques** (représentation, à l'échelle, notes, sources éditables, annulables).
- Bibliothèque : favoris ★ (cases à cocher, filtre, persistés dans les préférences), recherche étendue aux modèles.
- Tests : AST-03/05/06, SCI-07/08 et parcours P1 complet par l'interface (Gate 5) ; suite totale 97 tests.
- ADR-0003 : provenance, inventaire et crédits.

## [0.1.0.dev0] — 2026-10-21 — Phase 6 : narration et sous-titres

- Modèle et schéma v1 étendus (champs additifs, projets antérieurs lisibles) : `scene.audio` (clips : ressource, décalage en frames, gain, entrée/sortie, fondus, muet) et `scene.subtitles` (début, fin exclusive, texte) ; validation et commandes undo/redo associées.
- Export : mixage audio par FFmpeg (`atrim`, `afade`, `volume`, `adelay`, `amix`, `apad`), la vidéo reste maître de la durée ; sous-titres incrustés par le même painter que la prévisualisation (bande inférieure, police proportionnelle à `min(largeur, hauteur)`), fichier `.srt` compagnon écrit à côté du MP4.
- Panneau **Narration** (onglet à côté de la Timeline) : onglet Audio (import WAV/MP3/OGG/FLAC/M4A copié dans `audio/` avec SHA-256, placement à la tête de lecture, nom, début, gain, fondus, muet) ; onglet Sous-titres (ajout à la tête de lecture, édition en tableau, import/export SRT et VTT UTF-8, diagnostics : chevauchements, durée trop courte, ligne trop longue).
- Timeline : piste « Sous-titres » (blocs) et une piste par clip audio avec forme d'onde (décodage FFmpeg 8 kHz mis en cache) ; glisser un clip modifie son décalage (annulable).
- Lecture audio dans l'éditeur « au mieux » via QtMultimedia (silencieuse sans backend, sans erreur).
- Menu **Narration** : importer un fichier audio, ajouter un sous-titre, importer/exporter des sous-titres.
- Modèles intégrés : légendes remontées au-dessus de la bande réservée aux sous-titres.
- Correctifs CI : garde documentaire redéfinie autour de « MVP candidat : » ; suppression du `.part` tolérante au verrou tardif de Windows.
- Tests : 7 d'intégration audio (AUD-01, 02, 03, 04, 05, 09, fichier manquant), 6 unitaires sous-titres (AUD-06, 07, 08), 4 d'interface narration ; suite totale 85 tests.

## [0.1.0.dev0] — 2026-10-21 — Phases 1 à 4 : éditeur utilisable

- Application `antares-studio` (PySide6, interface en français) : fenêtre avec docks Bibliothèque, Scènes et objets, Inspecteur, Timeline ; disposition persistante et réinitialisable.
- Projet : nouveau (assistant 16:9 / 9:16 / 1:1, 1080p/720p, cadence, modèle), ouvrir, enregistrer, enregistrer sous (dossier `.antares`), récents, indicateur « modifié », autosave 60 s, récupération depuis la dernière sauvegarde valide si le fichier est corrompu (original préservé).
- Canevas : zoom/pan, sélection simple/multiple/cadre, déplacement, poignées d'échelle et de rotation (Maj = contraintes), flèches clavier, grille et aimantation, zones sûres, verrouillage, groupes (Ctrl+G / Ctrl+Maj+G), duplication (Ctrl+D), suppression, double-clic pour éditer un texte.
- Inspecteur : éditeurs typés générés depuis le catalogue (nombres, couleurs avec sélecteur, texte multiligne, police, alignement), bouton ◆ image clé par propriété animable, propriétés de scène (nom, durée, fond).
- Timeline : règle temporelle, tête de lecture, pistes par objet, losanges de keyframes déplaçables et supprimables, scrubbing, lecture/pause/boucle (Espace), image par image, mode « clé auto ».
- Animations : 6 presets (apparition, disparition, translation, rotation, pulsation, orbite) avec dialogue de paramètres ; 3 modèles intégrés (phases de la Lune, année-lumière, orbite et vecteurs) ajoutables comme scène.
- Export : dialogue avec profils (brouillon 720p, final 1080p, mobile 720p), progression, annulation propre, vérification ffprobe, manifest ; diagnostics et chemin FFmpeg configurable ; « À propos » avec mentions LGPL.
- Import d'images (PNG/JPEG/SVG/WebP) copiées dans `assets/` avec SHA-256 ; ressource absente rendue par un cadre explicite, sans plantage.
- Tests : 19 tests d'interface hors écran (pytest-qt) couvrant UI-01…08, UI-13, Gate 1 à 4 ; suite totale 66 tests.
- Correctifs : composition de la transformation du painter avec le décalage de l'éditeur ; reconstruction différée de l'arbre des objets (plantage lors d'un clic sur œil/cadenas).

## [0.1.0.dev0] — 2026-10-20 — Phase 0 : fondations éprouvées

- Recherche comparative Qt natif / Manim Community 0.22.0 / ManimGL 1.7.2 avec prototypes réels et mesures (`docs/research/2026-10-20-moteurs-rendu-2d.md`).
- ADR-0001 : moteur 2D du MVP = rendu Qt (QPainter) + FFmpeg ; Manim CE en adaptateur optionnel ; ManimGL écarté.
- ADR-0002 : dossier projet `Nom.antares/`, schéma JSON v1, temps canonique en frames, évaluateur pur.
- Paquet `antares_studio` : domaine (modèle, catalogue de 11 types d'objets, validation, commandes undo/redo), timeline (interpolations, évaluateur `evaluate(project, scene_id, frame)`, 6 presets MVP), persistance (sérialisation stricte, sauvegarde atomique, autosave, chemins sûrs), rendu (QPainter partagé, pilotage FFmpeg, plan de rendu, exporteur annulable avec vérification ffprobe et manifest).
- Tests : 37 unitaires (MOD/TIM/SEC) + 7 d'intégration (export MP4 réel 1080p/720p, annulation, FFmpeg absent) ; CI Linux (3.12/3.13) et Windows.

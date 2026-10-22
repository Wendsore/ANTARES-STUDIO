# Changelog — ANTARES Studio

Toutes les évolutions **effectives** (pas les intentions). Format : date, lot, changements observables.

## [0.1.0.dev0] — 2026-10-22 — Post-production : effets, filtres, bruitages, formats d'export

- **Effets d'objet** (Bibliothèque > Effets, Inspecteur > Effets) : flou, lueur (rayon, couleur, intensité), ombre portée, luminosité, contraste, saturation ; animables ; 8 préréglages (Lueur d'étoile, Néon bleu, Ombre portée…), appliqués à la sélection en un Ctrl+Z.
- **Filtres de scène** (Bibliothèque > Effets, Inspecteur > Filtres de la scène) : luminosité, contraste, saturation, température, sépia, vignettage, grain de film reproductible ; 8 préréglages (Cinéma, Espace profond, Chaud, Froid, Noir et blanc, Archive sépia, Vif). Identiques dans le canevas, l'image PNG et la vidéo.
- **Animations d'effet** : Secousse, Éclat lumineux, Clignotement, Mise au point, Pulsation lumineuse.
- **Bruitages et ambiances** (Bibliothèque > Sons) : 26 sons créés par le logiciel (transitions, interface, impacts, sciences et espace, ambiances bouclables), écoute, insertion à la tête de lecture avec le rôle « Effet » et une fiche CC0 remplie.
- **Export** : profils **1440p** et **4K 2160p** ; **ProRes 422 HQ** et **ProRes 4444** avec **fond transparent** ; **séquence PNG** (transparence possible, bande-son WAV à côté) ; **bande-son seule** WAV ou MP3 ; **volume normalisé à −14 LUFS** (EBU R128, crêtes ≤ −1,5 dB), case « Volume normalisé » dans Narration ; option CLI `--transparent`.
- Aide : rubriques « Effets et filtres » et « Bruitages et ambiances » ; export, Bibliothèque, Inspecteur, Narration, ligne de commande et limites mis à jour.
- Correctif : les images envoyées à FFmpeg sont toujours converties en RGBA non prémultiplié (nécessaire pour la transparence).
- ADR-0007.

## [0.1.0.dev0] — 2026-10-22 — Vingt-neuf améliorations (PR #12)

- **Animation** : interpolation réglable par image clé (liste de la Timeline, clic droit sur un losange), **éditeur de courbe** (Bézier, préréglages) ; **repères** nommés (M, [ et ]) ; animations **calées** sur un repère, un sous-titre ou un clip audio ; **transitions** d'entrée de scène (fondus, glissements, volet) identiques à l'export ; objet **Caméra** 2D (point visé, zoom, inclinaison).
- **Édition** : copier, couper, coller entre scènes et **entre projets** (images et sons recopiés avec leur licence) ; **guides d'alignement** avec aimantation (Ctrl pour ignorer) ; **Aligner et répartir** ; **édition multiple** dans l'Inspecteur (champ « ≠ ») ; grouper, dégrouper, dupliquer, supprimer annulables en un Ctrl+Z.
- **Sciences** : graphiques en **barres** et **histogrammes** ; **simulation à N corps** avec les modèles « Trois corps en huit » et « Étoile double » ; **Objet > Valeur physique** (constantes sourcées, conversions, écriture × 10ⁿ) ; **transformation d'une formule** en une autre ; **modèles 3D glTF** (.glb) ombrés et orientables.
- **Son et texte** : **enregistrement au micro** (WAV) ; rôle des pistes (voix, musique, effet) et **musique baissée sous la voix** à l'export ; sous-titres contrôlés pour la vitesse de lecture, la durée d'affichage et le contraste.
- **Export** : profils **Plateforme** (YouTube, Shorts/Reels/TikTok, carré, 4:3) avec bandes noires, **WebM** VP9 + Opus, **GIF** animé ; **export en arrière-plan** (panneau Exports, projet figé à l'envoi) ; **aperçu rapide 360p** (Ctrl+Maj+E) ; **image courante en PNG**.
- **Distribution** : **installateur Windows** par utilisateur (Inno Setup, sans droits administrateur), installé, autotesté et désinstallé en CI — **non signé** ; liste de recette Windows 11 et option `--capture` ; **rapport d'incident** local (`Aide > Créer un rapport d'incident…`), rien n'est envoyé.
- **Accompagnement** : **astuces** à la première utilisation de chaque panneau (`Aide > Réafficher les astuces`) ; **3 exemples complets** (accueil et `Fichier > Exemples`), sans voix ; tutoriels 1 et 3 à 7 rejoués en test ; aide : nouvelle rubrique « Modèles 3D (glTF) », 16 rubriques mises à jour, tableau des profils enrichi.
- Correctifs : plantage à la fermeture après un Copier ; journal d'erreurs borné en octets (Windows) ; objet ajouté posé au centième de pixel ; une clé reposée gardait mal son interpolation ; un preset appliqué à des objets non concernés rendait le projet invalide ; défilement horizontal de l'Inspecteur de scène ; en-têtes de la Narration tronqués ; bouton « Close » non traduit.
- ADR-0006.

## [0.1.0.dev0] — 2026-10-22 — Design visuel, centre d'aide et tutoriels interactifs

- Nouvelle apparence : thèmes **sombre** et **clair**, **taille du texte** réglable (`Affichage`), icônes sur les actions et la barre d'outils, logo, vignettes réelles des objets et des modèles dans la Bibliothèque, contrastes conformes WCAG 2.2 AA.
- **Centre d'aide** (`Aide > Centre d'aide`, F1 selon le panneau actif) : 32 rubriques en français, recherche, liens, illustrations ; listes d'objets, d'animations, de profils, de symboles, de modèles et de raccourcis toujours à jour.
- **Tutoriels interactifs** (`Aide > Tutoriels`) : 7 parcours guidés dont les étapes se valident d'elles-mêmes quand l'action est faite, avec « Montre-moi » et indices ; fichier d'exemple NASA fourni.
- **Page d'accueil** au démarrage (désactivable) et **recherche de commandes** (Ctrl+K).
- Export : la vidéo garde le format du projet (un projet vertical 9:16 ou carré n'est plus étiré) ; bouton « Ouvrir le dossier » après l'export.
- Raccourcis : Suppr pour supprimer (plus de conflit avec Ctrl+D), Ctrl+Y et Ctrl+Maj+Z pour rétablir, Ctrl+Maj+S pour enregistrer sous.
- Couleurs transparentes affichées correctement dans l'Inspecteur.
- Les tests n'écrivent plus dans les préférences de l'utilisateur ; le paquet PyInstaller inclut l'aide, les icônes, les exemples et le script Blender, vérifiés par `--selftest`.
- ADR-0005.

## [0.1.0.dev0] — 2026-10-21 — Phase 7 (minimal) : planète 3D par Blender facultatif

- `Objet > Planète 3D (Blender, facultatif)…` : si Blender est installé, rend une planète procédurale en rotation (Cycles CPU, fond transparent) en séquence PNG dans le projet et l'insère comme objet **Séquence d'images** animé sur la durée de la scène ; progression, annulation, messages explicites. Sans Blender : diagnostic et aucune fonction 2D affectée.
- Nouvel objet **Séquence d'images (rendu 3D)** (dossier de ressources, index d'image animable, boucle).
- `scripts/demo_gate6.py` : construit et exporte une démonstration de 5 scènes (126 s) pour la preuve Gate 6 ; narration synthétique déclarée comme telle.
- Correctif : les modèles accumulent leurs sources scientifiques au lieu d'écraser celles des scènes précédentes.

## [0.1.0.dev0] — 2026-10-21 — Export de la vidéo complète

- Dialogue d'export : « Toutes les scènes à la suite (vidéo complète) » ; CLI `--export … --all-scenes`. Chaque scène est rendue puis enchaînée sans ré-encodage ; piste audio silencieuse ajoutée aux scènes muettes ; sous-titres fusionnés (`.srt`), crédits (`.credits.txt`) et manifest listant les scènes.

## [0.1.0.dev0] — 2026-10-21 — Équations rendues localement

- Nouvel objet **Équation (formule)** : mini-langage à syntaxe LaTeX réduite (`^{}`, `_{}`, `\frac`, `\sqrt`, `\vec`, `\hat`, `\bar`, `\text`, lettres grecques, opérateurs), analysé sans exécution, dessiné par le painter partagé (fractions, radicaux, indices), variables en italique ; aucune installation LaTeX requise.
- Commandes inconnues conservées en texte et signalées ; accolades mal appariées tolérées.

## [0.1.0.dev0] — 2026-10-21 — Phase 8 (partiel) : unités et orbites de Kepler

- Module `science` : unités et constantes sourcées (ua IAU 2012, c et G CODATA, GM☉/GM⊕ IAU 2015, année-lumière, parsec), conversions avec contrôle de dimension et diagnostic des valeurs non finies.
- Orbites képlériennes : solution analytique (équation de Kepler) et intégration numérique Verlet-vitesse avec suivi de l'énergie et garde de stabilité du pas ; comparaison numérique/analytique testée (ordre 2).
- Nouveau preset **Orbite de Kepler** (foyer, demi-grand axe, excentricité, révolutions, méthode analytique ou numérique) et modèle **Orbite de Kepler (modélisation à deux corps)** avec hypothèses, paramètres et sources exportés dans le manifest.
- Inspecteur : représentations schématique / modélisation / simulation numérique / données mesurées.
- Import CSV avec unités (`Objet > Importer des données (CSV) en graphique…`) : séparateurs et virgule décimale détectés, diagnostics, refus explicite sans colonne numérique ; nouvel objet **Graphique** (axes avec unités, grille, titre, bornes, points, progression du tracé animable) et preset **Tracer la courbe**.
- ADR-0004.

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

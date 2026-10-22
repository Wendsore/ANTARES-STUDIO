# ANTARES Studio — État opérationnel

Dernière mise à jour : 2026-10-22 (phases 0 à 6 réalisées sur Linux ; design visuel, centre d'aide et tutoriels interactifs livrés, ADR-0005 ; 29 améliorations livrées, ADR-0006, PR #12 ; post-production livrée, ADR-0007).

## Situation réelle

- **Phase active : 8 (suite : CSV, N-corps) et 9 (installateur, validation Windows réelle).** Phases 0 à 6 réalisées sur Linux ; phase 8 entamée (unités, Kepler analytique + numérique, modèle P3) ; phase 9 entamée (CLI, paquet PyInstaller autotesté sur Windows CI) ; phase 7 entamée (planète 3D procédurale par Blender facultatif, séquence d'images).
- Phases 0 à 6 : `DONE` sur Linux (gates prouvés par tests automatisés, voir journal ; Gate 5 = parcours P1 complet par l'interface, Gate 6 = crédits générés et scène « Crédits »). Validation Windows : CI `windows-latest` verte pour le cœur (47 tests, FFmpeg 9.0.2) sur PR #2 ; tests UI Windows à lire sur les PR #3, #4 et #5. Vidéo ≥ 2 min : PROUVÉ sur Linux (démo 5 scènes, 126,00 s vidéo / 126,02 s audio, SRT fusionné, crédits ; `docs/session-logs/2026-10-21-export-complet.md`) avec une narration **synthétique** ; la voix réelle et la revue mobile restent au porteur.
- **MVP candidat : non** (Gates 0–6 prouvés sur Linux ; le parcours P1 reste à reproduire sur Windows, R-005). **Logiciel utilisable : oui, en version de développement** (`antares-studio`) : nouveau projet avec modèles, édition visuelle (sélection, glisser, poignées, inspecteur, calques), 6 presets d'animation et images clés, timeline avec lecture, enregistrement/réouverture/autosave/récupération, export MP4 vérifié avec progression et annulation, narration (clips audio : décalage, gain, fondus, muet, forme d'onde), sous-titres (saisie, import/export SRT/VTT, incrustation à l'export + fichier `.srt` compagnon), provenance des ressources (fiche à l'import, inventaire, avertissements à l'export), crédits générés (`.credits.txt`, scène « Crédits »), avertissement d'échelle, métadonnées scientifiques et sources, favoris, thèmes sombre/clair et taille du texte, centre d'aide intégré (32 rubriques, F1 contextuel), 7 tutoriels interactifs validés sur les actions, accueil, recherche de commandes (Ctrl+K) ; depuis la PR #12 : interpolation par clé et éditeur de courbe, repères et calage sur la narration, transitions de scène, caméra 2D, copier-coller entre projets, guides et alignement, édition multiple, barres et histogrammes, N corps (huit, étoile double), constantes et unités, transformation de formules, modèles glTF, enregistrement micro, musique baissée sous la voix, profils Plateforme, WebM, GIF, export en arrière-plan, aperçu 360p, image PNG, installateur Windows non signé, rapport d'incident, astuces de première utilisation, 3 exemples complets ; depuis la phase 11 : effets d'objet animables, filtres de scène, 26 bruitages et ambiances CC0, export 1440p/4K, ProRes 422 HQ et 4444 transparent, séquence PNG, bande-son WAV/MP3, volume normalisé −14 LUFS. Captures : `docs/images/editeur-theme-sombre-2026-10-22.png`, `docs/images/editeur-theme-clair-2026-10-22.png`, `docs/images/centre-aide-2026-10-22.png`, `docs/images/tutoriel-2026-10-22.png`, `docs/images/accueil-2026-10-22.png`, `docs/images/editeur-phases-lune-2026-10-21.png`, `docs/images/narration-2026-10-21.png`, `docs/images/bibliotheque-provenance-2026-10-21.png`.
- **Non disponible :** packs d'icônes tiers pour le contenu des scènes (géométrie générative locale uniquement ; l'interface utilise Lucide), matrices et écriture progressive des formules, N corps paramétrable dans l'interface, échelle logarithmique, textures glTF et caméra 3D, signature de l'installateur Windows (certificat requis), voix réelle dans les exemples.
- **Tests exécutés :** 390 tests pytest verts sur Linux le 2026-10-22, code de sortie 0 (254 unitaires, 36 intégration export/audio/Blender dont ProRes, PNG transparent et −14 LUFS mesuré, 97 interface dont le parcours P1 complet, les 7 tutoriels joués étape par étape et un enregistrement réel au micro, 3 documentaires), ruff et mypy strict propres.
- **Moteur retenu :** rendu Qt natif + FFmpeg (ADR-0001). **Licence du code :** non choisie (propriétaire).
- **Git :** l'agent ne peut pas fusionner les PR (action refusée par la politique de l'environnement) ; les PR sont empilées : #2 (Phase 0), #3 (phases 1–4), #4 (phase 6), #5 (phase 5), #6 (phase 9 partielle), #7 (phase 8 partielle), #8 (équations), #9 (export complet), #10 (phase 7 Blender), #11 (design, aide et tutoriels), #12 (29 améliorations), #13 (post-production), chacune basée sur la précédente. Le propriétaire fusionne dans l'ordre.

## Commandes

```bash
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/python -m ruff check . && .venv/bin/python -m mypy src
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

## Prochaines actions ordonnées

1. Phase 9 : lire le job `windows-package` de la PR #6 (artefact `ANTARES-Studio-windows-x64.zip`), installation propre et parcours P1 sur Windows 11 par le propriétaire (R-005) ; installateur Inno Setup (PR #12, job `windows-package`) à installer sur ce poste ; latence de scrubbing mesurée (p50 55 ms à 100 objets, `docs/session-logs/2026-10-21-phase9-packaging.md`).
2. Gate 6 : remplacer la narration synthétique de la démo (`scripts/demo_gate6.py`) par une voix off réelle et faire la revue mobile 16:9 (porteur).
3. Phase 8 (suite) : fonctions analytiques et échelle logarithmique dans le graphique, matrices et écriture progressive des formules ; phase 7 (suite) : textures glTF, Eevee avec GPU.
4. Design et aide : relecture des 35 rubriques et des 7 tutoriels par le porteur sur Windows 11 (HiDPI, police Segoe UI) ; dérouler `docs/recette-windows-11.md` sur un vrai poste (micro, installateur, `--capture`).
5. Décisions propriétaire : licence du produit et build FFmpeg (R-002), fusion des PR #2 → #13 (R-006).
6. Signature de l'installateur Windows : achat d'un certificat de signature de code (décision et identité du porteur).

## Journal des sessions

| Date (UTC) | Agent / environnement | Phase / lot | Tests réellement exécutés | Statut | Lien commit/PR |
|---|---|---|---|---|---|
| 2026-10-20 | Initialisation documentaire | Phase 0 : instructions | Voir messages/CI après dépôt | OPEN | — |
| 2026-10-20 | Claude Code, Debian 13 (`ki`) | Phase 0 : recherche, PoC, socle, export | 47 pytest PASS, ruff, mypy | DONE (Linux) ; CI Windows PASS | PR #2 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phases 1–4 : éditeur PySide6 complet (docks, canvas, inspecteur, timeline, export) | 66 pytest PASS (19 UI hors écran), ruff, mypy | DONE (Linux) ; Windows via CI | PR #3 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 6 : clips audio (mixage FFmpeg, forme d'onde), sous-titres SRT/VTT incrustés, panneau Narration, pistes timeline | 85 pytest PASS (AUD-01…09, 4 UI narration), ruff, mypy | DONE (Linux) sauf crédits ; Windows via CI | PR #4 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 5 : provenance des ressources, inventaire des licences, crédits (fichier + scène), encadré d'avertissement d'échelle, métadonnées/sources, favoris, parcours P1 complet | 97 pytest PASS (AST-03/05/06, SCI-07/08, Gate 5 P1 1080p/30), ruff, mypy | DONE (Linux) ; Windows via CI | PR #5 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 9 (partiel) : CLI (--version/--selftest/--export), spec PyInstaller + build, notices tierces, job CI windows-package, banc de scrubbing | bundle Linux autotesté (248 Mo), 102 pytest PASS, ruff, mypy ; .exe construit, autotesté et export réussi sur windows-latest | DONE (partiel, Linux) ; .exe Windows via CI | PR #6 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 8 (partiel) : unités sourcées (IAU/CODATA), équation de Kepler, Verlet symplectique, preset et modèle « Orbite de Kepler », représentations §9.3 ; import CSV avec unités et objet Graphique (tracé progressif) | SCI-01…06 + Gate 8 (8 tests), CSV/graphique (6 tests) ; 116 pytest PASS, ruff, mypy | DONE (partiel, Linux) | PR #7 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Équations : mini-langage analysé sans exécution, mise en page et rendu locaux (fractions, racines, indices, vecteurs), objet « Équation » | 4 tests formule ; 120 pytest PASS, ruff, mypy | DONE (Linux) | PR #8 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Export de la vidéo complète : toutes les scènes enchaînées sans ré-encodage, audio homogène, SRT fusionné, crédits ; CLI `--all-scenes` | 3 tests d'intégration ; 123 pytest PASS, ruff, mypy | DONE (Linux) | PR #9 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 7 : adaptateur Blender (facultatif), planète procédurale rendue en séquence PNG, objet « Séquence d'images », dialogue avec progression | Gate 7 (3 tests, Blender 4.3.2 réel) ; 126 passed, ruff, mypy ; démo Gate 6 : 126 s, dérive 21 ms, décodage OK | DONE (minimal, Linux) ; Windows NON TESTÉ | PR #10 |
| 2026-10-22 | Claude Code, Debian 13 (`ki`) | Design visuel (thèmes, jetons, icônes Lucide, vignettes réelles), centre d'aide (32 rubriques, F1), 7 tutoriels interactifs vérifiés, accueil, Ctrl+K ; export au format du projet ; isolation des préférences ; ressources dans le paquet | 214 passed (dont contrastes WCAG, liens et menus de l'aide, tutoriel 2 complet, export vertical ffprobe) ; ruff, mypy ; paquet Linux autotesté | DONE (Linux) ; Windows NON TESTÉ | PR #11 |
| 2026-10-22 | Claude Code, Debian 13 (`ki`) | 29 améliorations : interpolation et courbes, repères, transitions, caméra 2D, copier-coller, guides, alignement, édition multiple, barres/histogrammes, N corps, unités, morphing, glTF, micro, atténuation, lisibilité, plateformes, GIF/WebM/PNG, file d'exports, aperçu 360p, installateur Inno Setup, recette et `--capture`, rapport d'incident, tutoriels rejoués, astuces, exemples ; ADR-0006 | 320 passed, sortie 0 (dont atténuation mesurée par FFT, GIF/WebM ffprobe, micro réel, 7 tutoriels rejoués) ; ruff, mypy ; tests de correctifs vérifiés par mutation | DONE (Linux) ; installateur via CI ; Windows réel NON TESTÉ ; signature BLOQUÉE (certificat) | PR #12 |
| 2026-10-22 | Claude Code, Debian 13 (`ki`) | Post-production : effets d'objet, filtres de scène, presets d'effet, 26 bruitages CC0, onglets Effets et Sons, 1440p/4K, ProRes 422 HQ / 4444 alpha, séquence PNG, bande-son WAV/MP3, −14 LUFS ; ADR-0007 | 390 passed, sortie 0 (dont alpha ProRes décodé, −14 LUFS mesuré ebur128, pixels d'effets) ; ruff, mypy | DONE (Linux) ; Windows réel NON TESTÉ | PR #13 |

## Suivi des problèmes

| ID | Priorité | État | Problème | Prochaine action |
|---|---|---|---|---|
| R-001 | Haute | CLOSED | Choix de moteur sans benchmark local | ADR-0001 sur mesures |
| R-002 | Haute | OPEN | Distribution Windows / FFmpeg / licences | Choisir build FFmpeg (GPL libx264 vs LGPL openh264) et licence produit — décision propriétaire |
| R-003 | Haute | CLOSED | Cohérence prévisualisation ↔ export | Fonction de dessin unique `paint_scene_state` (ADR-0001) |
| R-004 | Moyenne | CLOSED | Ressources éditoriales libres et attribuables | Fiche de provenance, inventaire, crédits générés (ADR-0003) ; aucun pack tiers intégré |
| R-005 | Moyenne | OPEN | Validation Windows réelle | CI Windows verte pour le cœur ; UI à valider sur PC Windows 11 du propriétaire (HiDPI, polices, chemins) |
| R-006 | Haute | OPEN | Fusion des PR impossible par l'agent | Le propriétaire fusionne #2, #3, #4 puis #5 ; l'agent continue en branches empilées |
| R-007 | Moyenne | OPEN | Lecture audio dans l'éditeur dépend de QtMultimedia (backend FFmpeg de Qt) | Lecture « au mieux » : silencieuse sans backend, l'export reste exact ; vérifier sur Windows 11 |

## Format de mise à jour

Ajoute une ligne au journal par session, ne supprime pas les anciens résultats, et mets à jour les actions et risques. Si un résultat manque, écris `NON TESTÉ`, et non `OK`.

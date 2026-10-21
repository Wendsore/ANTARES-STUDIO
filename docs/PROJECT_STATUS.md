# ANTARES Studio — État opérationnel

Dernière mise à jour : 2026-10-21 (phases 0 à 6 réalisées sur Linux ; parcours P1 complet prouvé par test d'interface).

## Situation réelle

- **Phase active : 8 (suite : CSV, N-corps) et 9 (installateur, validation Windows réelle).** Phases 0 à 6 réalisées sur Linux ; phase 8 entamée (unités, Kepler analytique + numérique, modèle P3) ; phase 9 entamée (CLI, paquet PyInstaller autotesté sur Windows CI) ; phase 7 (Blender) non entamée.
- Phases 0 à 6 : `DONE` sur Linux (gates prouvés par tests automatisés, voir journal ; Gate 5 = parcours P1 complet par l'interface, Gate 6 = crédits générés et scène « Crédits »). Validation Windows : CI `windows-latest` verte pour le cœur (47 tests, FFmpeg 9.0.2) sur PR #2 ; tests UI Windows à lire sur les PR #3, #4 et #5. Vidéo ≥ 2 min avec narration réelle : NON TESTÉ (fixtures synthétiques de quelques secondes).
- **MVP candidat : non** (Gates 0–6 prouvés sur Linux ; le parcours P1 reste à reproduire sur Windows, R-005). **Logiciel utilisable : oui, en version de développement** (`antares-studio`) : nouveau projet avec modèles, édition visuelle (sélection, glisser, poignées, inspecteur, calques), 6 presets d'animation et images clés, timeline avec lecture, enregistrement/réouverture/autosave/récupération, export MP4 vérifié avec progression et annulation, narration (clips audio : décalage, gain, fondus, muet, forme d'onde), sous-titres (saisie, import/export SRT/VTT, incrustation à l'export + fichier `.srt` compagnon), provenance des ressources (fiche à l'import, inventaire, avertissements à l'export), crédits générés (`.credits.txt`, scène « Crédits »), avertissement d'échelle, métadonnées scientifiques et sources, favoris. Captures : `docs/images/editeur-phases-lune-2026-10-21.png`, `docs/images/narration-2026-10-21.png`, `docs/images/bibliotheque-provenance-2026-10-21.png`.
- **Non disponible :** enregistrement micro (import de fichiers uniquement), packs d'icônes tiers (géométrie générative locale uniquement), équations, import CSV/graphes, N-corps, 3D/Blender, installateur Windows (seul le dossier `.zip` PyInstaller existe).
- **Tests exécutés :** 102 tests pytest verts sur Linux le 2026-10-21 (59 unitaires dont CLI, 14 intégration export/audio, 26 interface dont le parcours P1 complet, 3 documentaires), ruff et mypy strict propres.
- **Moteur retenu :** rendu Qt natif + FFmpeg (ADR-0001). **Licence du code :** non choisie (propriétaire).
- **Git :** l'agent ne peut pas fusionner les PR (action refusée par la politique de l'environnement) ; les PR sont empilées : #2 (Phase 0), #3 (phases 1–4, base `feat/phase-0-fondations`), #4 (phase 6, base `feat/phase-1-4-editeur`), #5 (phase 5, base `feat/phase-6-narration`). Le propriétaire fusionne dans l'ordre.

## Commandes

```bash
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/python -m ruff check . && .venv/bin/python -m mypy src
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

## Prochaines actions ordonnées

1. Phase 9 : lire le job `windows-package` de la PR #6 (artefact `ANTARES-Studio-windows-x64.zip`), installation propre et parcours P1 sur Windows 11 par le propriétaire (R-005) ; installateur et signature si identité ; latence de scrubbing mesurée (p50 55 ms à 100 objets, `docs/session-logs/2026-10-21-phase9-packaging.md`).
2. Gate 6 complet : vidéo ≥ 2 min avec narration réelle et revue mobile 16:9 (nécessite une voix off réelle du porteur).
3. Phase 8 (suite) : import CSV avec unités et objet graphe, N-corps simplifié ; équations (rendu SVG local) ; phase 7 Blender optionnel après décision propriétaire.
4. Décisions propriétaire : licence du produit et build FFmpeg (R-002), fusion des PR #2 → #5 (R-006).

## Journal des sessions

| Date (UTC) | Agent / environnement | Phase / lot | Tests réellement exécutés | Statut | Lien commit/PR |
|---|---|---|---|---|---|
| 2026-10-20 | Initialisation documentaire | Phase 0 : instructions | Voir messages/CI après dépôt | OPEN | — |
| 2026-10-20 | Claude Code, Debian 13 (`ki`) | Phase 0 : recherche, PoC, socle, export | 47 pytest PASS, ruff, mypy | DONE (Linux) ; CI Windows PASS | PR #2 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phases 1–4 : éditeur PySide6 complet (docks, canvas, inspecteur, timeline, export) | 66 pytest PASS (19 UI hors écran), ruff, mypy | DONE (Linux) ; Windows via CI | PR #3 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 6 : clips audio (mixage FFmpeg, forme d'onde), sous-titres SRT/VTT incrustés, panneau Narration, pistes timeline | 85 pytest PASS (AUD-01…09, 4 UI narration), ruff, mypy | DONE (Linux) sauf crédits ; Windows via CI | PR #4 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 5 : provenance des ressources, inventaire des licences, crédits (fichier + scène), encadré d'avertissement d'échelle, métadonnées/sources, favoris, parcours P1 complet | 97 pytest PASS (AST-03/05/06, SCI-07/08, Gate 5 P1 1080p/30), ruff, mypy | DONE (Linux) ; Windows via CI | PR #5 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 9 (partiel) : CLI (--version/--selftest/--export), spec PyInstaller + build, notices tierces, job CI windows-package, banc de scrubbing | bundle Linux autotesté (248 Mo), 102 pytest PASS, ruff, mypy ; .exe construit, autotesté et export réussi sur windows-latest | DONE (partiel, Linux) ; .exe Windows via CI | PR #6 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 8 (partiel) : unités sourcées (IAU/CODATA), équation de Kepler, Verlet symplectique, preset et modèle « Orbite de Kepler », représentations §9.3 | SCI-01…06 + Gate 8 (8 tests) ; suite complète : voir PR | DONE (partiel, Linux) | PR #7 |

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

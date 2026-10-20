# ANTARES Studio — État opérationnel

Dernière mise à jour : 2026-10-21 (éditeur complet, phases 1 à 4 réalisées sur Linux).

## Situation réelle

- **Phase active : 5 — bibliothèque, provenance, parcours P1 complet ; puis 6 — narration et sous-titres.**
- Phases 0 à 4 : `DONE` sur Linux (gates prouvés par tests automatisés, voir journal). Validation Windows : CI `windows-latest` verte pour le cœur (47 tests, FFmpeg 9.0.2) sur PR #2 ; tests UI Windows à lire sur la PR suivante.
- **Logiciel utilisable : oui, en version de développement** (`antares-studio`) : nouveau projet avec modèles, édition visuelle (sélection, glisser, poignées, inspecteur, calques), 6 presets d'animation et images clés, timeline avec lecture, enregistrement/réouverture/autosave/récupération, export MP4 vérifié avec progression et annulation. Capture : `docs/images/editeur-phases-lune-2026-10-21.png`.
- **Non disponible :** voix off/sous-titres depuis l'interface, recherche d'icônes/packs, équations, 3D, installateur Windows.
- **Tests exécutés :** 66 tests pytest verts sur Linux le 2026-10-21 (37 unitaires, 7 intégration/export, 19 interface, 3 documentaires), ruff et mypy strict propres.
- **Moteur retenu :** rendu Qt natif + FFmpeg (ADR-0001). **Licence du code :** non choisie (propriétaire).
- **Git :** l'agent ne peut pas fusionner les PR (action refusée par la politique de l'environnement) ; les PR sont empilées : #2 (Phase 0) puis #3 (phases 1–4, base `feat/phase-0-fondations`). Le propriétaire fusionne dans l'ordre.

## Commandes

```bash
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/python -m ruff check . && .venv/bin/python -m mypy src
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

## Prochaines actions ordonnées

1. Phase 6 (anticipée, besoin P1) : panneau Audio — import WAV/MP3 dans `audio/`, décalage, gain, fondus, forme d'onde simple ; sous-titres SRT/VTT (import/édition/export et incrustation à l'export) ; crédits/attribution exportés.
2. Phase 5 : fiche de provenance/licence à l'import d'une ressource, inventaire des licences, packs d'icônes locaux (SVG générés), recherche dans la bibliothèque, avertissement « non à l'échelle » comme objet dédié.
3. Phase 9 (partiel) : packaging Windows (PyInstaller) et test d'installation propre ; latence de scrubbing mesurée sur projet de 100 objets.
4. Phase 7/8 : équations (SVG), simulation Kepler/N-corps, Blender optionnel.

## Journal des sessions

| Date (UTC) | Agent / environnement | Phase / lot | Tests réellement exécutés | Statut | Lien commit/PR |
|---|---|---|---|---|---|
| 2026-10-20 | Initialisation documentaire | Phase 0 : instructions | Voir messages/CI après dépôt | OPEN | — |
| 2026-10-20 | Claude Code, Debian 13 (`ki`) | Phase 0 : recherche, PoC, socle, export | 47 pytest PASS, ruff, mypy | DONE (Linux) ; CI Windows PASS | PR #2 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phases 1–4 : éditeur PySide6 complet (docks, canvas, inspecteur, timeline, export) | 66 pytest PASS (19 UI hors écran), ruff, mypy | DONE (Linux) ; Windows via CI | PR #3 |

## Suivi des problèmes

| ID | Priorité | État | Problème | Prochaine action |
|---|---|---|---|---|
| R-001 | Haute | CLOSED | Choix de moteur sans benchmark local | ADR-0001 sur mesures |
| R-002 | Haute | OPEN | Distribution Windows / FFmpeg / licences | Choisir build FFmpeg (GPL libx264 vs LGPL openh264) et licence produit — décision propriétaire |
| R-003 | Haute | CLOSED | Cohérence prévisualisation ↔ export | Fonction de dessin unique `paint_scene_state` (ADR-0001) |
| R-004 | Moyenne | OPEN | Ressources éditoriales libres et attribuables | Inventaire et outil de crédits (Phase 5) |
| R-005 | Moyenne | OPEN | Validation Windows réelle | CI Windows verte pour le cœur ; UI à valider sur PC Windows 11 du propriétaire (HiDPI, polices, chemins) |
| R-006 | Haute | OPEN | Fusion des PR impossible par l'agent | Le propriétaire fusionne #2 puis #3 ; l'agent continue en branches empilées |

## Format de mise à jour

Ajoute une ligne au journal par session, ne supprime pas les anciens résultats, et mets à jour les actions et risques. Si un résultat manque, écris `NON TESTÉ`, et non `OK`.

# ANTARES Studio — État opérationnel

Dernière mise à jour : 2026-10-20 (fin de Phase 0).

## Situation réelle

- **Phase active : 1 — socle domaine, UI et persistance.** Phase 0 : `DONE` sur Linux (Gate 0 prouvé), validation Windows en attente du job CI.
- **Logiciel développé : non** (pas encore d'interface utilisable). Le cœur sans Qt existe et est testé : modèle, validation, undo/redo, évaluateur temporel, presets, persistance, export MP4 vérifié.
- **Tests exécutés :** 47 tests pytest verts sur Linux le 2026-10-20 (voir `docs/session-logs/2026-10-20-phase0-fondations.md`).
- **Validations Windows 11 :** NON TESTÉ localement ; job `windows-latest` dans `.github/workflows/ci.yml`.
- **Moteur retenu :** rendu Qt natif + FFmpeg (ADR-0001) ; Manim Community en adaptateur optionnel ; ManimGL écarté.
- **Licence du code ANTARES :** non choisie (décision du propriétaire). Contraintes connues : PySide6 LGPLv3, FFmpeg GPL si libx264.

## Commandes

```bash
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/python -m ruff check . && .venv/bin/python -m mypy src
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

## Prochaines actions ordonnées

1. Phase 1 : fenêtre principale PySide6 (menus FR, docks, canvas de prévisualisation), nouveau/ouvrir/enregistrer/enregistrer sous, indicateur modifié, autosave et récupération ; tests `pytest-qt` hors écran. Gate 1 : créer, sauver, rouvrir une scène sans perte ; corruption détectée sans perte.
2. Phase 2 : éditeur de scène (sélection, déplacement, poignées, inspecteur, calques).
3. Phase 3 : timeline interactive et presets depuis l'UI.
4. Phase 4 : dialogue d'export (profils, progression, annulation) sur l'exporteur existant.

## Journal des sessions

| Date (UTC) | Agent / environnement | Phase / lot | Tests réellement exécutés | Statut | Lien commit/PR |
|---|---|---|---|---|---|
| 2026-10-20 | Initialisation documentaire | Phase 0 : instructions | Voir messages/CI après dépôt | OPEN | — |
| 2026-10-20 | Claude Code, Debian 13 (`ki`) | Phase 0 : recherche, PoC, socle, export | 47 pytest PASS, ruff, mypy | DONE (Linux) | branche `feat/phase-0-fondations` |

## Suivi des problèmes

| ID | Priorité | État | Problème | Prochaine action |
|---|---|---|---|---|
| R-001 | Haute | CLOSED | Choix de moteur sans benchmark local | ADR-0001 sur mesures |
| R-002 | Haute | OPEN | Distribution Windows / FFmpeg / licences | Choisir build FFmpeg (GPL libx264 vs LGPL openh264) et licence produit — décision propriétaire |
| R-003 | Haute | CLOSED | Cohérence prévisualisation ↔ export | Fonction de dessin unique `paint_scene_state` (ADR-0001) |
| R-004 | Moyenne | OPEN | Ressources éditoriales libres et attribuables | Inventaire et outil de crédits (Phase 5) |
| R-005 | Moyenne | OPEN | Validation Windows réelle | Lire le job CI Windows ; tester sur PC Windows 11 du propriétaire |

## Format de mise à jour

Ajoute une ligne au journal par session, ne supprime pas les anciens résultats, et mets à jour les actions et risques. Si un résultat manque, écris `NON TESTÉ`, et non `OK`.

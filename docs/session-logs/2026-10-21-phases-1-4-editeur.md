# Session 2026-10-21 — Phases 1 à 4 : éditeur PySide6 complet

**Agent :** Claude (Claude Code) — **Machine :** `ki`, Debian 13, sans écran (`QT_QPA_PLATFORM=offscreen`) — **Branche :** `feat/phase-1-4-editeur` (empilée sur `feat/phase-0-fondations`, PR #2).

## Réalisé

`src/antares_studio/app/` : `document.py` (pont domaine ↔ Qt, auto-clé), `canvas_widget.py`, `main_window.py`, `inspector_dock.py`, `layers_dock.py`, `library_dock.py`, `timeline_dock.py`, `export_dialog.py`, `preset_dialog.py`, `dialogs.py`, `settings.py`, `diagnostics.py`, `main.py` ; `resources/templates.py` (3 modèles), `resources/assets.py` (import d'images). Guide : `docs/user-guide/01-premiere-video.md`. Capture : `docs/images/editeur-phases-lune-2026-10-21.png`.

## Tests réellement exécutés (Linux)

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests -q   # 66 passed
.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check . && .venv/bin/python -m mypy src
```

| Gate | Preuve |
|---|---|
| 1 | `test_ui01_gate1_save_reopen_preserves_everything` (états identiques aux frames 0/150/299 après réouverture), `test_gate1_corrupt_project_offers_recovery_without_loss`, `test_gate1_unreadable_without_autosave_reports_error` |
| 2 | glisser (1 pas d'annulation), poignée d'échelle, cadre de sélection + groupe/dégroupe, inspecteur ↔ modèle, raccourcis, calques (œil/cadenas) |
| 3 | `test_ui06_timeline_scrub_and_keyframes` (clé auto, interpolation à mi-chemin, scrubbing par clic, lecture non bloquante), `test_preset_from_library_applies_orbit` |
| 4 | `test_ui13_export_dialog_runs_in_background_and_verifies` (20 images 720p, manifest), `test_ui13_export_cancel_leaves_no_file` |

Windows 11 : NON TESTÉ localement ; job CI `windows-latest` sur la PR #3.

## Incidents corrigés pendant la session

1. `paint_scene_state` : `setWorldTransform(..., combine=False)` effaçait le décalage de vue → objets dessinés hors des poignées. Corrigé (`combine=True`), vérifié par capture.
2. `LayersDock.refresh()` appelé dans le gestionnaire `itemChanged` détruisait l'item en cours de modification → `RuntimeError`/segfault. Corrigé par reconstruction différée (`QTimer.singleShot(0)`).
3. Tests UI : la boîte modale « modifications non enregistrées » bloquait la fermeture par pytest-qt → `before_close_func` marque l'état propre.
4. Tests d'intégration : fixture `qapp` locale (`QGuiApplication`) incompatible avec les widgets → fixture pytest-qt.

## Décisions

- L'agent n'a pas le droit de fusionner les PR dans cet environnement (refus de l'outil) : branches empilées, fusion par le propriétaire.
- Clips audio prévus dans `project.settings["audio"][scene_id]` (sans changement de schéma) jusqu'à l'ADR audio de la phase 6.

## Prochaine action

Phase 6 anticipée : panneau Audio (import WAV/MP3, décalage, gain, fondus) et sous-titres SRT/VTT avec incrustation à l'export, pour boucler le parcours P1 avec narration.

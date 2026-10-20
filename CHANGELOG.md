# Changelog — ANTARES Studio

Toutes les évolutions **effectives** (pas les intentions). Format : date, lot, changements observables.

## [0.1.0.dev0] — 2026-10-20 — Phase 0 : fondations éprouvées

- Recherche comparative Qt natif / Manim Community 0.22.0 / ManimGL 1.7.2 avec prototypes réels et mesures (`docs/research/2026-10-20-moteurs-rendu-2d.md`).
- ADR-0001 : moteur 2D du MVP = rendu Qt (QPainter) + FFmpeg ; Manim CE en adaptateur optionnel ; ManimGL écarté.
- ADR-0002 : dossier projet `Nom.antares/`, schéma JSON v1, temps canonique en frames, évaluateur pur.
- Paquet `antares_studio` : domaine (modèle, catalogue de 11 types d'objets, validation, commandes undo/redo), timeline (interpolations, évaluateur `evaluate(project, scene_id, frame)`, 6 presets MVP), persistance (sérialisation stricte, sauvegarde atomique, autosave, chemins sûrs), rendu (QPainter partagé, pilotage FFmpeg, plan de rendu, exporteur annulable avec vérification ffprobe et manifest).
- Tests : 37 unitaires (MOD/TIM/SEC) + 7 d'intégration (export MP4 réel 1080p/720p, annulation, FFmpeg absent) ; CI Linux (3.12/3.13) et Windows.

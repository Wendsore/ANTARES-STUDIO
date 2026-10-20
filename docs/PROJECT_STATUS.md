# ANTARES Studio — État opérationnel

Dernière mise à jour : 2026-10-21 (phase 6 narration et sous-titres réalisée sur Linux, après les phases 0 à 4).

## Situation réelle

- **Phase active : 5 — bibliothèque, provenance, crédits, parcours P1 complet.** La phase 6 (narration, sous-titres) a été anticipée car le parcours P1 l'exige.
- Phases 0 à 4 et 6 : `DONE` sur Linux (gates prouvés par tests automatisés, voir journal). Phase 6 : crédits/attribution à l'export non faits (reportés en phase 5 avec la provenance). Validation Windows : CI `windows-latest` verte pour le cœur (47 tests, FFmpeg 9.0.2) sur PR #2 ; tests UI Windows à lire sur les PR #3 et #4.
- **MVP candidat : non** (parcours P1 avec narration à prouver sur Windows). **Logiciel utilisable : oui, en version de développement** (`antares-studio`) : nouveau projet avec modèles, édition visuelle (sélection, glisser, poignées, inspecteur, calques), 6 presets d'animation et images clés, timeline avec lecture, enregistrement/réouverture/autosave/récupération, export MP4 vérifié avec progression et annulation, narration (clips audio : décalage, gain, fondus, muet, forme d'onde) et sous-titres (saisie, import/export SRT/VTT, incrustation à l'export + fichier `.srt` compagnon). Captures : `docs/images/editeur-phases-lune-2026-10-21.png`, `docs/images/narration-2026-10-21.png`.
- **Non disponible :** enregistrement micro (import de fichiers uniquement), crédits/attribution exportés, fiche de provenance à l'import, recherche d'icônes/packs, équations, 3D, installateur Windows.
- **Tests exécutés :** 85 tests pytest verts sur Linux le 2026-10-21 (43 unitaires, 14 intégration export/audio, 25 interface, 3 documentaires), ruff et mypy strict propres.
- **Moteur retenu :** rendu Qt natif + FFmpeg (ADR-0001). **Licence du code :** non choisie (propriétaire).
- **Git :** l'agent ne peut pas fusionner les PR (action refusée par la politique de l'environnement) ; les PR sont empilées : #2 (Phase 0), #3 (phases 1–4, base `feat/phase-0-fondations`), #4 (phase 6, base `feat/phase-1-4-editeur`). Le propriétaire fusionne dans l'ordre.

## Commandes

```bash
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/python -m ruff check . && .venv/bin/python -m mypy src
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

## Prochaines actions ordonnées

1. Phase 5 : fiche de provenance/licence à l'import d'une ressource (image et audio), inventaire des licences, crédits/attribution générés à l'export (fin de vidéo + fichier texte), packs d'icônes locaux (SVG générés), avertissement « non à l'échelle » comme objet dédié.
2. Parcours P1 complet prouvé de bout en bout (modèle Lune + narration + sous-titres + crédits → MP4) par un test d'intégration et une exécution sur Windows.
3. Phase 9 (partiel) : packaging Windows (PyInstaller) et test d'installation propre ; latence de scrubbing mesurée sur projet de 100 objets.
4. Phase 7/8 : équations (SVG), simulation Kepler/N-corps, Blender optionnel.

## Journal des sessions

| Date (UTC) | Agent / environnement | Phase / lot | Tests réellement exécutés | Statut | Lien commit/PR |
|---|---|---|---|---|---|
| 2026-10-20 | Initialisation documentaire | Phase 0 : instructions | Voir messages/CI après dépôt | OPEN | — |
| 2026-10-20 | Claude Code, Debian 13 (`ki`) | Phase 0 : recherche, PoC, socle, export | 47 pytest PASS, ruff, mypy | DONE (Linux) ; CI Windows PASS | PR #2 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phases 1–4 : éditeur PySide6 complet (docks, canvas, inspecteur, timeline, export) | 66 pytest PASS (19 UI hors écran), ruff, mypy | DONE (Linux) ; Windows via CI | PR #3 |
| 2026-10-21 | Claude Code, Debian 13 (`ki`) | Phase 6 : clips audio (mixage FFmpeg, forme d'onde), sous-titres SRT/VTT incrustés, panneau Narration, pistes timeline | 85 pytest PASS (AUD-01…09, 4 UI narration), ruff, mypy | DONE (Linux) sauf crédits ; Windows via CI | PR #4 |

## Suivi des problèmes

| ID | Priorité | État | Problème | Prochaine action |
|---|---|---|---|---|
| R-001 | Haute | CLOSED | Choix de moteur sans benchmark local | ADR-0001 sur mesures |
| R-002 | Haute | OPEN | Distribution Windows / FFmpeg / licences | Choisir build FFmpeg (GPL libx264 vs LGPL openh264) et licence produit — décision propriétaire |
| R-003 | Haute | CLOSED | Cohérence prévisualisation ↔ export | Fonction de dessin unique `paint_scene_state` (ADR-0001) |
| R-004 | Moyenne | OPEN | Ressources éditoriales libres et attribuables | Inventaire et outil de crédits (Phase 5) |
| R-005 | Moyenne | OPEN | Validation Windows réelle | CI Windows verte pour le cœur ; UI à valider sur PC Windows 11 du propriétaire (HiDPI, polices, chemins) |
| R-006 | Haute | OPEN | Fusion des PR impossible par l'agent | Le propriétaire fusionne #2, #3 puis #4 ; l'agent continue en branches empilées |
| R-007 | Moyenne | OPEN | Lecture audio dans l'éditeur dépend de QtMultimedia (backend FFmpeg de Qt) | Lecture « au mieux » : silencieuse sans backend, l'export reste exact ; vérifier sur Windows 11 |

## Format de mise à jour

Ajoute une ligne au journal par session, ne supprime pas les anciens résultats, et mets à jour les actions et risques. Si un résultat manque, écris `NON TESTÉ`, et non `OK`.

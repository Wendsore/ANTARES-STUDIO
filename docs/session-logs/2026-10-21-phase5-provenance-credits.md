# Session 2026-10-21 — Phase 5 : provenance, crédits, avertissement d'échelle, parcours P1

**Agent :** Claude (Claude Code) — **Machine :** `ki`, Debian 13, sans écran (`QT_QPA_PLATFORM=offscreen`), FFmpeg 7.1.5 — **Branche :** `feat/phase-5-provenance-credits` (empilée sur `feat/phase-6-narration`, PR #4) — **PR :** #5.

## Réalisé

- `resources/licenses.py` (pur) : choix de licences, statut calculé, inventaire avec usages, avertissements de provenance, lignes de crédits.
- Domaine : type `callout` (encadré), commandes `SetAssetLicense` et `SetProjectMetadata` (annulables).
- Rendu/export : dessin de l'encadré (painter partagé), avertissements de provenance dans le plan, fichier `<vidéo>.credits.txt`, crédits et métadonnées scientifiques dans le manifest.
- Modèles : avertissement d'échelle en encadré dans les trois modèles scientifiques ; nouveaux modèles « Introduction » et « Crédits » (générés depuis le projet).
- Interface : `provenance_dialog.py` (fiche de provenance, inventaire des licences et crédits, sources scientifiques) ; onglet « Ressources » et favoris (★, persistés) dans la bibliothèque ; section « Métadonnées scientifiques » dans l'inspecteur (représentation, échelle, notes, sources) ; menu `Objet > Avertissement d'échelle`, `Fichier > Inventaire des licences et crédits…` ; fiche proposée après import d'image/audio.
- Documentation : ADR-0003, guide utilisateur §7, statut, changelog, captures `docs/images/bibliotheque-provenance-2026-10-21.png`, `docs/images/inventaire-licences-2026-10-21.png`.

## Décisions prises en autonomie

Voir ADR-0003. En plus :

| Question | Choix | Raison |
|---|---|---|
| Ordre des phases | Phase 5 après la phase 6 | Les crédits dépendent de la provenance ; la narration était nécessaire au parcours P1 |
| Rayon de l'orbite du modèle « Orbite et vecteurs » | 320 → 230 px (base 1080p) | Laisser la place à l'encadré d'avertissement sous l'orbite |
| Largeur initiale des docks de gauche | 300 px | Quatre onglets de bibliothèque lisibles sans défilement |
| Test P1 | Test d'interface complet (90 images 1080p/30, audio, sous-titres, crédits, réouverture) | Gate 5 exige le parcours sans code ; durée courte pour rester exécutable en CI |

## Tests réellement exécutés (Linux)

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests -q   # 97 passed
.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check . && .venv/bin/python -m mypy src
```

| Cas | Preuve |
|---|---|
| AST-03 | `test_ast03_asset_without_provenance_is_flagged_and_warned_in_plan`, `test_ast03_non_redistributable_asset_warns` |
| AST-05 | `test_ast05_favorites_filter_and_persist` (filtre déterministe, persistance entre fenêtres) |
| AST-06 | `test_ast06_credits_report_is_faithful`, `test_provenance_dialog_inventory_and_sources` |
| SCI-07 | `test_sci07_templates_carry_a_visible_scale_warning[3 modèles]` : encadré présent, visible aux images 0/milieu/fin, bordure et texte mesurés sur l'image rendue, hors bande des sous-titres |
| SCI-08 | `test_sci08_sources_are_in_metadata_and_manifest_credits`, sources éditées depuis l'inspecteur (annulables) |
| Gate 5 / P1 | `test_gate5_p1_moon_phases_end_to_end` : modèle Lune 16:9, inspecteur, avertissement d'échelle, voix off à 0,5 s avec fiche, deux sous-titres, scène Crédits, export 1920×1080/30 (90 images, audio, `.srt`, `.credits.txt`, manifest sans avertissement), réouverture identique aux images 0/45/89 |

Windows 11 : NON TESTÉ localement ; job CI `windows-latest` sur la PR #5.

## Incidents corrigés pendant la session

1. Encadré d'avertissement à `hauteur − 250` : bas de boîte à 865 px, dans la bande des sous-titres (864) → `hauteur − 265`.
2. Inventaire non rafraîchi pour le document initial : connexion déplacée dans `_connect_document`.
3. Compteur « Sources… (n) » figé après modification : rafraîchi sur `changed`.
4. Deux sous-titres chevauchés dans le parcours P1 (60 images par défaut) : fin du premier ajustée, comme le ferait l'utilisateur dans le tableau.

## Reste à faire

Validation Windows réelle (R-005), packaging (phase 9), licence produit (R-002).

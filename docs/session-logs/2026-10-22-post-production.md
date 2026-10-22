# Session 2026-10-22 — Post-production : effets, filtres, bruitages, formats d'export

**Agent :** Claude (Claude Code) — **Machine :** `ki`, Debian 13, sans écran, FFmpeg 7.1 (prores_ks, libmp3lame présents) — **Branche :** `feat/phase-11-post-production` (empilée sur `feat/phase-10-ameliorations`, PR #12). Décisions : ADR-0007.

## Demande

« Fais donc un travail sur la post prod, le rendu, les tailles, les formats, les filtres si ce n'est pas encore fait. Je veux aussi une bonne bibliothèque d'effets et de bruits. » En autonomie (arbitrages consignés dans l'ADR-0007).

## Réalisé

1. **Effets d'objet** (`domain/effects.py`, `rendering/effects.py`) : flou, lueur, ombre portée, luminosité, contraste, saturation ; clés `style.fx_*` animables, absentes par défaut ; calque hors écran + NumPy, rayons à l'échelle de sortie.
2. **Filtres de scène** (`scene.post`) : étalonnage, température, sépia, vignettage, grain reproductible ; appliqués par `FrameRenderer` (canevas, PNG, export, transitions).
3. **Préréglages et animations** : 8 effets d'objet, 8 filtres, 5 presets (Secousse, Éclat lumineux, Clignotement, Mise au point, Pulsation lumineuse).
4. **Interface** : onglets Bibliothèque **Effets** et **Sons** ; Inspecteur : sections **Effets** et **Filtres de la scène** ; case **Volume normalisé** (Narration) ; case **Fond transparent** (export).
5. **Bruitages** (`audio/sfx.py`) : 26 sons synthétisés (5 catégories), déterministes, WAV 16 bits 48 kHz, CC0 ; écoute, insertion à la tête de lecture (copie dans `audio/`, rôle Effet, fiche remplie, une étape d'annulation).
6. **Export** : 1440p, 4K 2160p, ProRes 422 HQ, ProRes 4444 avec alpha, séquence PNG (transparente possible, bande-son WAV à côté, mise en place atomique, refus d'écraser un dossier étranger), bande-son seule WAV/MP3, normalisation EBU R128 −14 LUFS par défaut, CLI `--transparent`.
7. **Aide** : rubriques « Effets et filtres » et « Bruitages et ambiances » (catalogues générés depuis le code), 6 rubriques mises à jour (35 au total).

## Tests réellement exécutés (Linux)

- Suite complète : **390 passed, code de sortie 0** (254 unitaires, 36 intégration, 97 interface, 3 documentaires) ; ruff et mypy strict propres (82 fichiers).
- Nouveaux : `test_effects.py` (pixels rendus), `test_sfx.py` (26 sons), `test_export_post.py` (vrai FFmpeg : 4K, ProRes, alpha décodé, PNG, MP3, −14 LUFS mesuré par `ebur128` à ±1 LU, effets visibles dans la vidéo décodée), `test_post_production.py` (Bibliothèque, Inspecteur, annulation, insertion CC0), catalogue de l'aide.
- `test_aud03…` : la normalisation y est désactivée explicitement, le test mesurant le gain du clip seul.
- Captures vérifiées à l'œil (onglets Effets et Sons, sections Effets et Filtres, lueur dans le canevas).
- Mesures (i5-4310U, 1080p) : filtres de scène 85–165 ms par image, 5 objets avec effets ≈ 280 ms.

## Non fait / non testé

- Changement de cadence à l'export (décision, ADR-0007 §19) ; effets sur groupes et caméras ; séquence PNG de toutes les scènes.
- **NON TESTÉ sur Windows 11 réel** ; lecture du ProRes 4444 dans un logiciel de montage non vérifiée (aucun sur `ki`).

# Session 2026-10-21 — Export de la vidéo complète (toutes les scènes)

**Agent :** Claude (Claude Code) — **Machine :** `ki`, Debian 13, sans écran, FFmpeg 7.1.5 — **Branche :** `feat/export-projet-complet` (empilée sur `feat/phase-8-equations`, PR #8) — **PR :** #9.

## Pourquoi

Gate 6 exige « une vidéo complète ≥ 2 min avec narration, sous-titres et crédits ». L'export ne traitait qu'une scène. L'enchaînement se fait sans ré-encodage (démultiplexeur `concat` de FFmpeg, `-c copy`), chaque scène ayant la même structure de flux : vidéo H.264 + audio AAC stéréo 48 kHz (piste silencieuse `anullsrc` si la scène n'a aucun clip).

## Réalisé

- `exporter.export_project(project, profile_id, output, progress, cancel, assets, ffmpeg_path, scene_ids)` : rendu par scène dans un dossier temporaire, concaténation, vérification (somme des images, résolution, piste audio), remplacement atomique, SRT fusionné avec décalage, `.credits.txt`, manifest (liste des scènes).
- `RenderPlan.silent_audio` ; `_verify` exige la piste audio dans ce cas.
- Dialogue d'export : case « Toutes les scènes à la suite (vidéo complète) » ; CLI : `--export … --all-scenes`.

## Tests réellement exécutés (Linux)

`tests/integration/test_export_project.py` : 3 scènes (12 + 9 + 15 images, une avec voix, deux silencieuses) → 36 images, audio présent, durée = 1,200 s ± 0,1 (pas de dérive), progression monotone jusqu'à 36/36, SRT décalé de 21 images pour la 3e scène, crédits et manifest, aucun fichier temporaire restant, décodage complet sans erreur ; drapeau CLI ; projet sans scène refusé. Suite complète : voir la ligne du journal dans `docs/PROJECT_STATUS.md`.

## Preuve Gate 6 (durée) — voir section suivante, ajoutée après exécution

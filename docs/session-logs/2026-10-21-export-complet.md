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

## Preuve Gate 6 (durée) — exécutée le 2026-10-21 sur `ki`

Script `scripts/demo_gate6.py` (ajouté avec la PR #10) : projet de 5 scènes construit à partir des modèles intégrés (Introduction 12 s, Phases de la Lune 40 s, Comparaison d'échelles 30 s, Orbite de Kepler 30 s, Crédits 14 s), sous-titres saisis, **narration = signal synthétique** (tonalité douce générée en WAV, déclaré comme tel dans les crédits) faute de voix enregistrée disponible sur la machine. Export « toutes les scènes » en `draft_720p`, puis mesures `ffprobe`/`ffmpeg` (`scratchpad/gate6_probe.sh`) :

| Mesure | Valeur |
|---|---|
| Résolution, cadence | 1280×720, 30 i/s |
| Images (manifest = flux) | 3780 = 360 + 1200 + 900 + 900 + 420 |
| Durée vidéo / audio | 126,00 s / 126,02 s (dérive 21 ms) |
| Décodage complet (`ffmpeg -f null`) | OK, aucune erreur |
| Temps de rendu | 129 s (i5-4310U, 2 cœurs) |
| Compagnons | `.srt` fusionné (1er sous-titre 00:00:00,500 ; dernier 00:01:37,500 → 00:01:51,500), `.credits.txt` (sources des modèles, logiciels, mention de la narration synthétique), `.mp4.manifest.json` (5 scènes) |

Le gate « vidéo ≥ 2 min avec narration, sous-titres et crédits » est tenu sur la durée, la synchronisation et les fichiers compagnons. **Ce qui reste au porteur :** remplacer la tonalité par une voix réelle (import d'un WAV/MP3 dans le dock Narration) et faire la revue mobile 16:9 ; aucune limite logicielle ne s'y oppose.

Décision annexe prise en construisant la démo : les modèles ajoutaient leurs sources en **écrasant** la liste `sources` du projet (le dernier modèle gagnait). `templates.add_sources` les accumule désormais sans doublon ; vérifié : Lune + échelles + Kepler → 5 sources distinctes.

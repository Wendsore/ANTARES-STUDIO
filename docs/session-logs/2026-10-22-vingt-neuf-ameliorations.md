# Session 2026-10-22 — Vingt-neuf améliorations

**Agent :** Claude (Claude Code) — **Machine :** `ki`, Debian 13, sans écran, FFmpeg 7.1.5, micro intégré — **Branche :** `feat/phase-10-ameliorations` (empilée sur `feat/phase-6-design-aide`, PR #11) — **PR :** #12. Décisions : ADR-0006.

## Demande

« Propose 29 améliorations », puis « implémente les améliorations », en autonomie complète (aucune question, arbitrages consignés).

## Réalisé, par lot

1. **Animation** (`efde1a4`) : interpolation par clé, éditeur de courbe de Bézier, édition multiple, annulation groupée.
2. **Édition** (`44935bc`) : copier/couper/coller entre scènes et projets, aligner et répartir, guides d'alignement.
3. **Scènes** (`cbf99d9`) : repères, calage d'animation, transitions de scène, caméra 2D.
4. **Formats et file d'exports** (`5c331d2`) : GIF, WebM, profils Plateforme, aperçu 360p, PNG, file en arrière-plan, rôles audio et atténuation, lisibilité des sous-titres.
5. **Sciences** (`50703d6`) : barres et histogrammes, N corps, valeur physique, morphing de formules, glTF.
6. **Distribution** (`6b96121`) : micro, rapport d'incident, `--capture` et liste de recette Windows 11, installateur Inno Setup en CI.
7. **Accompagnement** : tutoriels 1 et 3 à 7 rejoués en test, astuces de première utilisation, 3 exemples complets (accueil et Fichier > Exemples), aide (1 rubrique nouvelle, 16 mises à jour, tableau des profils), illustrations régénérées, ADR-0006.

## Tests réellement exécutés (Linux)

- `pytest` complet : **319 passed** (203 unitaires, 27 intégration, 86 interface, 3 documentaires) ; ruff, ruff format, mypy strict propres.
- Mesures réelles : atténuation de la musique mesurée par FFT sur le fichier exporté ; GIF et WebM contrôlés par ffprobe ; bandes noires mesurées sur l'image ; enregistrement d'un vrai WAV par le micro de `ki`.
- Tests des correctifs vérifiés **par mutation** (le correctif retiré, le test échoue) : interpolation conservée par `SetKeyframe`, objets ignorés par un preset, absence de défilement horizontal de l'Inspecteur.
- Contrôle visuel : bulle d'astuce, page d'accueil avec la galerie d'exemples, Inspecteur de scène, captures `--capture`.

## Non fait / limites

- Windows 11 réel : NON TESTÉ (micro, installateur hors CI, HiDPI) ; la liste `docs/recette-windows-11.md` est à dérouler sur un vrai poste.
- Signature de l'installateur : BLOQUÉE (certificat de signature de code à acheter).
- Exemples sans voix réelle (sous-titres seulement) ; textures glTF ignorées ; N corps non paramétrable dans l'interface.

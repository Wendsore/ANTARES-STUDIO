# R-2026-01 — Choix du moteur de rendu 2D pour le MVP (Qt natif / Manim Community / ManimGL)

**Date :** 2026-10-20 — **Agent :** Claude (session autonome) — **Environnement :** Debian 13 (trixie) x86_64, Intel Core i5-4310U (2 cœurs / 4 threads), 7,6 Go RAM, pas de GPU dédié, sans serveur d'affichage (Xvfb pour les essais OpenGL), Python 3.13.5, uv 0.x, FFmpeg 7.1.5 (paquet Debian, `libx264` activé donc build GPL).

**Question :** quel moteur permet, dès le MVP, une prévisualisation réactive et un export MP4 déterministe à partir d'un unique `SceneState` évalué au temps `t`, avec un coût d'installation Windows acceptable et des licences compatibles avec une distribution locale et gratuite ?

**Non vérifié dans cette session :** tout comportement Windows 11. Les essais ci-dessous sont Linux uniquement.

## Sources officielles consultées (le 2026-10-20)

| Source | Version / état | Apport |
|---|---|---|
| https://pypi.org/pypi/PySide6/json | 6.12.0 publiée le 2026-10-08, `requires_python >=3.10,<3.16`, licence `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | version à figer |
| https://www.qt.io/licensing/open-source-lgpl-obligations | — | obligations LGPLv3 : liaison dynamique, fourniture des sources Qt ou offre écrite, mention visible, droit de relier/rétro-ingénierie, pas de canal de distribution restrictif |
| https://doc.qt.io/qtforpython-6/licenses.html | — | composants tiers à créditer (icônes Material Apache-2.0 dans les exemples) |
| https://pypi.org/pypi/manim/json | Manim Community 0.22.0 publiée le 2026-10-08, `requires_python >=3.11`, MIT ; dépend de `av>=15` (FFmpeg embarqué via PyAV), `manimpango`, `pycairo`, `moderngl`, `scipy`, `numpy>=2.1` | ~33 distributions, 411 Mo installés |
| https://github.com/ManimCommunity/manim/releases | 0.22.0 (08 oct.), 0.21.0 (10 août), 0.20.1 (27 fév.) ; 0.22.0 : nouveau `Manager` de rendu, OpenGL écrit un fichier par défaut, encodeur configurable | projet maintenu activement |
| https://docs.manim.community/en/stable/installation/uv.html | — | Linux : compilation de ManimPango/pycairo (`build-essential python3-dev libcairo2-dev libpango1.0-dev`) ; Windows : roues binaires, parfois MSVC Build Tools ; LaTeX optionnel |
| https://pypi.org/pypi/manimgl/json | ManimGL 1.7.2 publiée le 2024-12-13, MIT, `requires_python` non déclaré ; dépend de `pydub`, `PyOpenGL`, `moderngl_window`, `matplotlib`, `sympy`… | dernière publication il y a 22 mois |
| https://github.com/3b1b/manim | Python ≥ 3.10, FFmpeg, OpenGL, LaTeX optionnel, Pango + en-têtes sous Linux ; pas de promesse de prévisualisation temps réel intégrable | installation Windows via clone + `pip install -e .` |
| https://pypi.org/pypi/manimpango/json | 0.7.0 ; roues Windows/macOS cp310→cp315, **aucune roue Linux** (sdist seul) | explique l'échec initial Linux |
| https://ffmpeg.org/legal.html | — | build avec `libx264` = GPL ; chemin LGPL : liaison dynamique, sources publiées, notice, pas de bibliothèque GPL |
| https://pypi.org/pypi/pyinstaller/json | 6.22.3, GPLv2+ avec exception permettant les programmes non libres | candidat packaging Windows |

## Essais reproductibles

Scène de référence commune : fond sombre, Terre (cercle bleu), orbite (cercle fin), Lune parcourant 360° en 5 s à vitesse constante, flèche tangentielle de vitesse suivant la Lune, texte « Schéma non à l'échelle — Terre et Lune » avec fondu. 1920×1080, 30 i/s, 150 images.

### E1 — Qt natif (`scripts/poc/phase0_qt_renderer.py`)

```bash
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python "PySide6==6.12.0" "numpy>=2.1" "pillow>=11" pytest pytest-qt ruff mypy
.venv/bin/python scripts/poc/phase0_qt_renderer.py out.mp4                       # 1080p
.venv/bin/python scripts/poc/phase0_qt_renderer.py out720.mp4 --width 1280 --height 720
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames,codec_name,duration -of default=nw=1 out.mp4
ffmpeg -v error -i out.mp4 -f null -
```

Résultats (3 exécutions 1080p) : `total_s` = 5,33 / 5,09 / 5,08 / 5,05 s dont dessin QPainter 1,9–2,2 s ; 720p : 2,47 s. ffprobe : `h264 1920x1080 30/1 nb_frames=150 duration=5.000000`, décodage complet OK. Images extraites aux frames 0/75/149 : à la frame 75 la Lune est à gauche (θ = π) et la flèche pointe vers le haut, conforme au calcul `evaluate()`. Démarrage `QApplication` à froid : 0,21 s. Aucune dépendance native hors PySide6 ; plate-forme `offscreen` suffit (pas d'OpenGL, pas d'écran).

### E2 — Manim Community 0.22.0 (`scripts/poc/phase0_manimce_scene.py`)

```bash
sudo apt-get install -y build-essential python3-dev pkg-config libcairo2-dev libpango1.0-dev   # Linux uniquement
uv venv venv-manimce --python 3.13 && uv pip install --python venv-manimce/bin/python "manim==0.22.0"
venv-manimce/bin/manim -qh --fps 30 --media_dir mce_out scripts/poc/phase0_manimce_scene.py EarthMoon
```

- Première installation : **échec** `fatal error: cairo.h: No such file or directory` (ManimPango n'a pas de roue Linux) ; après en-têtes : 19,7 s d'installation, import OK, PyAV 19.0.1 embarqué.
- Rendu : 8,59 / 8,73 / 8,48 s (dont démarrage ~2 s). ffprobe : `h264 1920x1080 30/1 150 frames 5.000 s`, décodage OK. Image à la frame 75 cohérente (Lune à gauche ; flèche vers le bas car Manim utilise un repère y vers le haut : même géométrie, convention d'écran différente).
- Qualité : texte Pango net, antialiasing propre. API riche (morphing, LaTeX via Tex externe) mais le rendu est piloté par un script Python exécuté : pour une scène éditée visuellement il faudrait **générer du code** puis l'exécuter, soit un aller-retour non WYSIWYG et une surface d'exécution de code à sécuriser.

### E3 — ManimGL 1.7.2 (`scripts/poc/phase0_manimgl_scene.py`)

```bash
uv venv venv-manimgl --python 3.13 && uv pip install --python venv-manimgl/bin/python "manimgl==1.7.2" "setuptools<81" audioop-lts
xvfb-run -a -s "-screen 0 1920x1080x24" venv-manimgl/bin/manimgl scripts/poc/phase0_manimgl_scene.py EarthMoon -w --hd --video_dir mgl_out
```

Quatre obstacles successifs, tous reproduits :

1. `ModuleNotFoundError: No module named 'pkg_resources'` (setuptools 84 l'a retiré) → contourné par `setuptools<81`.
2. `ModuleNotFoundError: No module named 'pyaudioop'` (pydub sur Python 3.13 où `audioop` a disparu) → contourné par `audioop-lts`.
3. `pyglet.display.xlib.NoSuchDisplayException` : **l'import même de `manimlib` exige un serveur d'affichage** ; impossible sans Xvfb, donc inutilisable en CI headless et fragile pour un rendu en arrière-plan.
4. `manimgl --fps 30` → `TypeError: unsupported operand type(s) for /: 'int' and 'str'` (bogue CLI, l'option n'est pas convertie).

Sans `--fps` : rendu réussi en **33,8 s** (OpenGL logiciel llvmpipe, `user 1m40`), ffprobe `h264 1920x1080 30/1 150 frames 5.000 s`, décodage OK. Mais la couleur de la flèche (`color=`) et la couleur de fond ont été ignorées (API différente de Manim CE pour les mêmes noms), confirmant qu'il n'existe pas d'API commune.

## Synthèse comparative (barème du protocole de recherche)

| Critère (poids) | Qt natif | Manim CE 0.22 | ManimGL 1.7.2 |
|---|---|---|---|
| Stabilité / doc (20 %) | Qt 6.12 LTS-grade, doc complète | actif, doc complète | dernière version 12/2024, 3 incompatibilités Py 3.13 |
| Intégration au modèle interne (20 %) | directe : `SceneState → QPainter` partagé preview/export | génération de code + sous-processus | idem + affichage obligatoire |
| Qualité de sortie (15 %) | bonne (antialiasing QPainter, polices système) | excellente (Pango, morphing, LaTeX) | bonne, OpenGL |
| Performance CPU modeste (15 %) | 5,1 s / 150 img 1080p | 8,6 s | 33,8 s (GL logiciel) |
| Ergonomie éditeur (15 %) | WYSIWYG réel | non WYSIWYG | non WYSIWYG |
| Licence / distribution (10 %) | LGPLv3 (obligations connues) + FFmpeg | MIT + PyAV (FFmpeg) + Pango | MIT + OpenGL + Pango |
| Maintenance (5 %) | Qt Company | communauté active | 3b1b seul, publication rare |
| **Éliminatoire ?** | non | non | **oui pour le MVP** : exige un affichage à l'import, bogues CLI, pas de version compatible Python 3.13 sans contournements |

## Conclusion

- **Confiance élevée** : le moteur 2D du MVP est un rendu Qt natif (QPainter) alimenté par un évaluateur pur ; FFmpeg encode le flux RGBA. C'est la seule option où prévisualisation et export partagent le **même code de dessin**, sans génération de script ni exécution de code.
- **Manim Community** est conservé comme **adaptateur d'export optionnel** (phase ≥ 5) pour les scènes mathématiques avancées (morphing, LaTeX), dans un environnement séparé, jamais comme format natif.
- **ManimGL** est écarté du MVP ; réévaluation seulement si une version publiée supporte Python ≥ 3.12 sans affichage obligatoire.
- ADR associée : `docs/adr/0001-moteur-rendu-2d-mvp.md`. Travaux restants : validation Windows 11 (installation PySide6, chemins FFmpeg avec espaces, HiDPI), mesure de la latence de scrubbing dans l'éditeur réel.

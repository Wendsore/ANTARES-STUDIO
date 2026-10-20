# ADR-0001 — Moteur de rendu 2D du MVP : rendu Qt natif + FFmpeg, Manim CE en adaptateur optionnel

**Date :** 2026-10-20 — **Statut :** acceptée — **Décideur :** agent autonome, sur mesures (voir `docs/research/2026-10-20-moteurs-rendu-2d.md`)

## Contexte

Le master prompt demande une prévisualisation réactive et un export MP4 produits à partir d'un même `SceneState` évalué au temps `t`, sans exécution de code issu du projet, sur PC Windows 11 modeste, hors ligne. Le souhait initial était ManimGL ; la décision devait être prise après prototypes.

## Options évaluées

1. **Rendu Qt natif** : évaluateur pur → `QPainter` sur `QImage` (export) et sur `QGraphicsView` (éditeur) → flux RGBA vers FFmpeg.
2. **Manim Community 0.22.0** : génération d'un script Python par scène puis rendu en sous-processus.
3. **ManimGL 1.7.2** : idem avec le paquet `manimgl`.

## Décision

- Le moteur de prévisualisation **et** d'export du MVP est le **rendu Qt natif** (option 1). Une seule fonction de dessin `paint_scene_state(painter, state)` est partagée par l'éditeur et l'exporteur ; FFmpeg (exécutable externe, détecté ou configuré) encode.
- **Manim Community** devient un **adaptateur d'export optionnel**, isolé dans un extra `[manim]` et un environnement séparé, pour les scènes mathématiques avancées. Il n'est jamais le format natif et n'est pas requis pour ouvrir, éditer ou exporter un projet.
- **ManimGL** est **écarté** du MVP. Aucune des deux variantes n'est installée dans l'environnement principal.

## Justification (faits mesurés)

| | Qt natif | Manim CE | ManimGL |
|---|---|---|---|
| 150 images 1080p (Linux, i5-4310U) | 5,1 s | 8,6 s | 33,8 s (GL logiciel) |
| Affichage requis | non (`offscreen`) | non | **oui, dès l'import** |
| Python 3.13 | OK | OK | 3 contournements (`setuptools<81`, `audioop-lts`, bug `--fps`) |
| Build natif Linux | aucun | ManimPango/pycairo à compiler | idem + OpenGL |
| Préviz = export | même code | génération de code, non WYSIWYG | idem, API divergente |
| Licence | LGPLv3 (Qt) | MIT | MIT |

Le rendu Qt est le seul chemin où l'éditeur montre exactement ce qui sera exporté, sans transformer la scène en code exécutable (exigence de sécurité §3.5).

## Conséquences

- Dépendance principale : `PySide6==6.12.0` (figée ; `PySide6-Essentials` à préférer pour le packaging). Obligations LGPLv3 à respecter lors de la distribution : liaison dynamique (le cas des roues PySide6), fourniture des sources Qt ou offre écrite, notice visible dans « À propos », aucune restriction de rétro-ingénierie.
- FFmpeg : exécutable externe. Le build Debian utilisé contient `libx264` (GPL). Pour la distribution Windows, choisir entre un build GPL (avec publication des sources conforme) et un build LGPL avec `libopenh264` ou encodeur matériel ; décision de licence du produit renvoyée au propriétaire (ADR ultérieure).
- Les équations LaTeX ne sont pas disponibles nativement au MVP ; un rendu d'équations simple (texte stylé/SVG) sera fourni, Manim CE ou un rendu MathML/SVG pouvant venir ensuite.
- Retour arrière : le format de projet est indépendant du moteur ; un `RenderBackend` Manim CE peut être branché sans toucher au domaine.

## Alternatives écartées

- Export par capture du widget : interdit par le master prompt (non déterministe).
- QGraphicsScene comme moteur d'export : dessiner via `QGraphicsScene.render()` serait possible mais couple l'export à des objets d'interface ; on garde une fonction de dessin pure sur `QPainter`, le widget d'édition l'appelant à son tour.

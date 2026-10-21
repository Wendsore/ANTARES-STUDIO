# Session 2026-10-21 — Équations rendues localement (objet « Équation (formule) »)

**Agent :** Claude (Claude Code) — **Machine :** `ki`, Debian 13, sans écran — **Branche :** `feat/phase-8-equations` (empilée sur `feat/phase-8-science`, PR #7) — **PR :** #8.

## Pourquoi sans LaTeX

Le master prompt (§5, §6.1 « Maths : rendu équation … fallback SVG », §7 sécurité : « expressions LaTeX dangereuses » interdites par défaut) et la contrainte « ne pas exiger une installation LaTeX pour ouvrir un projet ». Décision : un **mini-langage** à syntaxe familière (sous-ensemble LaTeX) analysé en arbre et dessiné par le painter partagé ; aucune commande n'est exécutée, une commande inconnue reste du texte et est signalée. Pas de dépendance (ni TeX, ni Matplotlib mathtext, ni SymPy).

## Réalisé

- `science/formula.py` : analyseur pur (`^{}`, `_{}`, `\frac{}{}`, `\sqrt{}`, `\vec{}`, `\hat{}`, `\bar{}`, `\text{}`, lettres grecques et opérateurs usuels, `\,` espace fine, `\{ \}` littéraux), diagnostics (accolade non fermée ou orpheline, argument manquant, commande inconnue), `plain()` (transcription linéaire).
- `rendering/formula_layout.py` : mesure (boîtes au-dessus/au-dessous de la ligne de base) et dessin ; indices/exposants à 65 %, fractions avec barre, radical, flèche/chapeau/barre ; variables latines en italique (ISO 80000-2, désactivable).
- Type d'objet **Équation (formule)** (catégorie « Maths » de la bibliothèque) : texte, police, taille animable, couleur, fond ; sélection et poignées sur la boîte mesurée ; export WYSIWYG.
- Capture : `docs/images/equations-2026-10-21.png`.

## Tests réellement exécutés (Linux)

`tests/unit/test_formula.py` (4 tests) : structures et symboles, robustesse (`\input`, `\write18` et accolades mal appariées → texte + diagnostics, jamais d'exception), mise en page (fraction > 1,6 × hauteur d'une ligne, exposant plus étroit et plus haut, racine plus large), rendu (pixels blancs dans la boîte, barre de fraction continue ≥ 60 px), aller-retour JSON. Suite complète **120 tests verts**, ruff et mypy propres.

## Reste à faire

Morphing entre formules (hors MVP), matrices, écriture progressive d'une formule (preset « écrire »), modèle « Équation pas à pas ».

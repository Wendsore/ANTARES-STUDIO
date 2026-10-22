# Session 2026-10-22 — Écriture à la craie, grilles déformables, solides 3D

**Agent :** Claude (Claude Code) — **Machine :** `ki`, Debian 13, sans écran — **Branche :** `feat/phase-12-ecriture-grilles-3d` (empilée sur `feat/phase-11-post-production`, PR #13). Décisions : ADR-0008.

## Demande

Après la vidéo de démonstration des textes et équations : « Non, c'est pas assez. Je veux […] les styles de Science for All, où il écrit comme sur un tableau avec de la craie […]. Est-ce qu'il y a une grille ? Est-ce que j'arrive à représenter […] une déformation spatiale ? […] des vidéos comme 3Blue1Brown […]. Des animations un peu 3D ? Est-ce que dans ma bibliothèque, j'ai des cubes et des objets de ce type ? » En autonomie.

## Réalisé

1. **Écriture progressive** (`rendering/writing.py`) : paramètres `write` (animable) et `write_style` sur Texte et Équation ; 5 façons (tracé puis remplissage, craie, machine à écrire, lettres, mots) ; mise en page par `QTextLayout`, formules par `layout_glyphs` ; à `write = 1`, dessin habituel inchangé.
2. **Craie et décors** : effet `fx_chalk` (grain fixé à l'image, graine fixe), préréglage « Craie » ; `scene.backdrop` (6 décors procéduraux, `rendering/backdrops.py`), Inspecteur de scène > Décor.
3. **Polices** : 17 familles Google Fonts livrées (`resources/fonts/`, licences jointes, SHA-256 dans le README du dossier), `resources/fonts.py`, liste éditable dans l'Inspecteur, mentions dans « À propos » et `THIRD_PARTY_NOTICES.md`.
4. **Styles d'écriture** (`domain/text_styles.py`) : 16 styles, Bibliothèque > Effets, une étape d'annulation.
5. **Grille** (`rendering/grid.py`, type `grid`) : matrice animable, î ĵ, filigrane, puits de gravité / onde / tourbillon, perspective.
6. **Solides 3D** (`rendering/solids.py`, type `solid3d`) : 10 formes, 4 rendus, perspective ; listés un par un dans la Bibliothèque (`OBJECT_VARIANTS`).
7. **Animations** : Écrire, Effacer l'écriture, Rotation 3D, Transformation linéaire, Courber l'espace, Onde qui se propage. **Modèles** : Tableau noir, Transformation linéaire, Espace-temps courbé, Solides 3D. **Sons** : catégorie Écriture (craie, machine à écrire, stylo, effacer).
8. **Aide** : 3 rubriques nouvelles (38 au total), catalogues générés (styles, polices, décors, solides) ; équations, objets, Bibliothèque, limites mises à jour.
9. `get_property` renvoie la valeur par défaut d'un paramètre absent (projets enregistrés avant l'ajout d'un paramètre).

## Correctifs trouvés en chemin

- Grille tournée d'un quart de tour : les lignes ne couvraient plus le cadre (étendue calculée par la norme de l'inverse). Désormais antécédent des coins du cadre ; test de régression vérifié **en échec sur l'ancien calcul**, vert sur le nouveau.
- Sommet du cône à 10⁻⁶ près : maillage non fermé (détecté par le test de fermeture) ; sommet exact.
- Inspecteur : la liste des polices montrait la fin de la description (« …leau, très lisible ») ; la Bibliothèque défilait horizontalement avec les libellés longs. Vus sur capture, corrigés.

## Tests réellement exécutés (Linux)

- Suite complète : `448 passed in 276.02s`, code de sortie 0 (306 unitaires, 36 intégration, 103 interface, 3 documentaires).
- Nouveaux tests : 45 unitaires (`tests/unit/test_ecriture_grilles_solides.py`) et 6 d'interface (`tests/ui/test_ecriture_3d_ui.py`) ; `test_rotated_grid_still_fills_the_frame` échoue sur l'ancien calcul d'étendue des lignes (vérifié).
- `ruff format`, `ruff check` : propres ; `mypy` strict : aucune erreur sur 88 fichiers.
- Windows : non testé (machine Linux) ; la CI Windows de la PR fait foi.
- Nouveaux : `tests/unit/test_ecriture_grilles_solides.py` (45 tests : progression, ordre de lecture, pixels écrits à 0 / 0,5 / 1 pour chaque façon, égalité pixel à pixel avec un ancien texte, craie, polices chargées et licences, styles, décors et export transparent, mathématiques de la grille, maillages fermés et orientés, volume de la sphère, faces visibles du cube, modes de rendu, presets, variantes, modèles), `tests/ui/test_ecriture_3d_ui.py` (6 tests : Bibliothèque, style en un Ctrl+Z, animation Écrire, liste des polices, décor, modèles) ; `test_timeline.py` étendu aux nouvelles animations.
- Vidéo de démonstration exportée par le moteur réel : 55,0 s, 1920 × 1080, 30 i/s, 1650 images, AAC 48 kHz (6 scènes) ; images extraites et vérifiées à l'œil.

## Non fait / non testé

- Écriture au tracé d'un seul trait, surfaces z = f(x, y), axes 3D, solides qui s'interpénètrent (ADR-0008).
- **NON TESTÉ sur Windows 11 réel** (polices livrées, solides, décors).

# Session 2026-10-30 — Personnages chibis 2D

**Agent :** Claude (Claude Code) — **Machine :** `ki`, Debian 13, sans écran — **Branche :** `feat/phase-14-personnages-chibi` (empilée sur `feat/phase-13-astres-ondes-optique`, PR #15). Décisions : ADR-0010.

## Demande

« Créer un chibi qui va pouvoir présenter les choses […] un jeune Africain qui parle, qui a des mouvements standards, toutes les émotions possibles, des vêtements différents […] plusieurs personnages : un très ironique, un hyper scientifique qui explique, un qui doute, un toujours énervé. » Après la proposition 3D (VRM, suivi caméra) : « pour le moment, propose-moi des chibis 2D images fixes, donc je pourrais changer pendant une présentation. On va commencer par là. »

**État avant** : aucun personnage ; seul l'objet *Image* pour poser un dessin importé.

## Réalisé

1. **Catalogue pur** `domain/characters.py` (sans Qt) : 22 émotions, 10 poses, 5 regards, 7 tenues, 7 coiffures, 4 barbes, 3 lunettes, 3 couvre-chefs, 6 teints, 6 fiches de jeu.
2. **Dessin** `rendering/chibi.py` : SVG original composé par le code, rendu par `QSvgRenderer` (cache par thread), signes de bande dessinée lisibles en miroir.
3. **Type Personnage** (`character`) : émotion, pose, regard, tenue, lunettes, couvre-chef et miroir animables (palier) ; couleurs de tenue et de cheveux ; Bibliothèque > Personnages (6 variantes, vignettes rendues).
4. **Modèle** « Dialogue de personnages (émotions et bulles) » : rotation synchrone de la Lune, source NASA lue.
5. **Aide** : rubrique « Personnages chibis » (42 au total) avec tableaux générés ; Bibliothèque et limites.

## Retour du porteur et seconde passe

« Le chibi actuel est beaucoup trop enfantin […] mon chibi, celui qui doit me représenter […] un ingénieur, quelqu'un qui fait de la techno, avec des traits africains », avec neuf photos du porteur. Réponse : réglage **Proportions → Adulte stylisé** et trois fiches *ingénieur* tirées des photos (doudoune sans manches sur sweat rouge, gilet haute visibilité et casque, veste en jean doublée) ; les chibis sont conservés. Logo de l'employeur non reproduit. ADR-0010 §12–14.

## Preuves

- Planches vérifiées à l'œil (fiches, émotions, poses, tenues, coiffures) ; défauts corrigés : poings cachés derrière la tête (victoire), tresses débordant du crâne, bande rouge de colère remplacée par un dégradé, manches courtes invalides en SVG (attribut en double, personnage vide).
- `tests/unit/test_personnages.py` (17) et `tests/ui/test_personnages_ui.py` (2) ; suite complète : 511 passed, sortie 0 ; ruff, ruff format, mypy propres.
- Vidéo d'essai 1080p (première passe, chibis) : dialogue, défilé des 22 émotions, six fiches ; seconde vidéo (52 s, h264 + aac, images décodées vérifiées) avec l’ingénieur adulte face au sceptique et ses trois tenues.

## Reste

- Synchronisation labiale, suivi caméra, 3D : proposés, non commencés (ADR-0010, Conséquences).
- Windows réel non testé (CI Windows seulement).

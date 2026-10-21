# Recherche — Blender en ligne de commande pour une planète 3D (phase 7)

**Date :** 2026-10-21 — **Machine :** `ki` (Debian 13, i5-4310U 2c/4t, sans GPU, sans écran).

## Sources officielles

- Rendu en ligne de commande : https://docs.blender.org/manual/en/latest/advanced/command_line/render.html (`-b` arrière-plan, `--python`, `--` pour les arguments du script, `-f`/`-a`).
- Licence : Blender est sous GPL v2+ (https://www.blender.org/about/license/) ; un programme externe qui le lance en sous-processus n'est pas un travail dérivé ; les rendus produits appartiennent à l'auteur.
- Version installée : Blender 4.3.2 (paquet Debian `blender`, dépôt officiel de la distribution).

## Mesures réellement exécutées

| Essai | Résultat |
|---|---|
| Sphère lisse, texture procédurale (bruit → dégradé), soleil, caméra, Cycles **CPU** 16 échantillons, 320×240, 24 images, `blender -b --python … --` | 24 PNG RGBA, **26 s** au total, aucune erreur, aucun affichage requis |
| Même scène via l'adaptateur de l'application, 96×96, 4 échantillons, 6 images (test Gate 7) | 6 PNG, progression `Saved:` lue ligne à ligne, insertion comme séquence, export MP4 720p avec audio réussi |
| Eevee | NON TESTÉ : requiert OpenGL/GPU, inadapté à une machine sans écran ; Cycles CPU retenu |

## Décisions

- Blender reste **facultatif et externe** : détection (`PATH`, `ANTARES_BLENDER`, dossiers `Program Files` sous Windows), diagnostic explicite, aucune fonction 2D n'en dépend (test « absence tolérée »).
- Le rendu produit une **séquence PNG** placée dans `assets/planete-3d-*/` du projet (ressource de type `sequence`, fiche de provenance « géométrie générée ») lue par l'objet **Séquence d'images** dont l'index d'image est animé sur la durée de la scène : durée identique à la timeline, composition 2D/3D par le painter partagé, export inchangé.
- Pas de GLB/glTF, caméra ni textures importées pour l'instant (ressources tierces à qualifier, master prompt §9.1) ; la planète procédurale suffit au Gate 7 minimal.

## Limites

Temps CPU élevé pour de grandes images (1080p × 300 images ≈ plusieurs minutes à dizaines de minutes sur `ki`) ; prévoir un rendu à taille réduite puis mise à l'échelle par l'objet. Blender n'est pas livré dans le paquet PyInstaller (taille, GPL) : l'utilisateur l'installe s'il le souhaite.

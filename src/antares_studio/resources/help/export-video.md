# Exporter la vidéo

## Lancer l'export

1. **Fichier > Exporter la vidéo…** (Ctrl+E).
2. Choisissez un **profil** (tableau ci-dessous).
3. Cochez **Toutes les scènes à la suite (vidéo complète)** pour enchaîner toutes les scènes ; sinon seule la scène affichée est exportée.
4. Vérifiez le **Fichier de sortie**. Par défaut il est proposé dans le dossier `renders/` du projet ; **Parcourir…** pour le changer.
5. **Exporter**.

## Les profils

<!-- auto:profils -->

Toutes les vidéos sont en **MP4, vidéo H.264 et son AAC**, lisibles partout : téléphones, navigateurs, plateformes vidéo, logiciels de montage. Les dimensions du tableau valent pour un projet 16:9. Pour un projet vertical ou carré, le petit côté du profil (720 ou 1080 pixels) est appliqué au format du projet : un projet 9:16 exporté en *Final 1080p* donne 1080 × 1920, sans déformation.

## Pendant l'export

- La progression s'affiche image par image. Le rendu tourne en arrière-plan : la fenêtre d'export reste réactive.
- **Annuler l'export** (ou Échap) arrête proprement : aucun fichier partiel n'est laissé.
- Les **avertissements** (ressource sans provenance, par exemple) s'affichent avant le rendu.

## Après l'export

ANTARES **vérifie** le fichier produit (dimensions, nombre d'images, durée, présence du son) et affiche le résultat. **Ouvrir le dossier** affiche la vidéo dans l'explorateur de fichiers.

À côté de la vidéo :

| Fichier | Contenu |
|---|---|
| `nom.mp4` | la vidéo |
| `nom.srt` | les sous-titres, s'il y en a ; pour une vidéo complète, ceux de toutes les scènes |
| `nom.credits.txt` | les [crédits](credits.md) |
| `nom.mp4.manifest.json` | le compte rendu technique : profil, durées, scènes, vérifications |

## Ce que l'export garantit

- **Ce que vous voyez est ce que vous obtenez** : le canevas et l'export utilisent le même moteur de dessin.
- Toutes les images sont calculées, même si l'aperçu en a sauté.
- Le son est mixé exactement : décalages, gains, fondus.
- Une vidéo complète enchaîne les scènes sans réencodage ; une scène sans son reçoit une piste silencieuse pour rester synchronisée.

Exporter sans ouvrir l'interface : voir [Ligne de commande](ligne-de-commande.md). Problème d'export : voir [Dépannage](depannage.md).

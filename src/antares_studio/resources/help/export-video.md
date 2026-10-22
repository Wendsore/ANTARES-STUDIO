# Exporter la vidéo

## Lancer l'export

1. **Fichier > Exporter la vidéo…** (Ctrl+E).
2. Choisissez un **profil** (tableau ci-dessous) ; une ligne d'explication s'affiche sous la liste.
3. Cochez **Toutes les scènes à la suite (vidéo complète)** pour enchaîner toutes les scènes ; sinon seule la scène affichée est exportée.
4. Vérifiez le **Fichier de sortie**. Par défaut il est proposé dans le dossier `renders/` du projet ; **Parcourir…** pour le changer. L'extension suit le profil (`.mp4`, `.webm`, `.gif`, `.mov`, `.wav`, `.mp3`) ; pour une séquence PNG, c'est le nom d'un **dossier**.
5. **Exporter** pour suivre l'export dans la fenêtre, ou **En arrière-plan** pour continuer à travailler (voir plus bas).

## Les profils

<!-- auto:profils -->

- **Usage** : MP4 (vidéo H.264, son AAC), lisible partout. Les dimensions valent pour un projet 16:9 ; pour un projet vertical ou carré, le petit côté du profil est appliqué au format du projet : un projet 9:16 exporté en *Final 1080p* donne 1080 × 1920, sans déformation.
- **Plateforme** : le cadre est **imposé** par la plateforme. Si le format du projet diffère, l'image est centrée avec des **bandes noires**, jamais étirée.
- **WebM** : vidéo VP9 et son Opus, formats libres pour les pages web.
- **GIF animé** : sans son, 15 images/s au plus (des images sont sautées si le projet est plus rapide), palette de couleurs calculée pour chaque vidéo. Un GIF est lourd : gardez-le court.
- **1440p et 4K** : mêmes réglages que *Final 1080p*, en plus grand. La 4K demande environ quatre fois plus de temps de rendu.
- **Montage** : pour retravailler la vidéo dans un logiciel de montage (DaVinci Resolve, Premiere, Final Cut, Kdenlive).
  - **ProRes 422 HQ** (`.mov`, son PCM sans perte) : qualité quasi intacte, fichier lourd (environ 30 Mo par seconde en 1080p).
  - **ProRes 4444 avec transparence** : la case **Fond transparent** est cochée d'office ; le fond de scène n'est pas peint, seuls les objets restent, pour les incruster par-dessus une autre vidéo.
  - **Séquence d'images PNG** : un dossier `image_00000.png`, `image_00001.png`… (transparence possible avec la même case) et, si la scène a du son, `bande-son.wav` à côté. Une séquence s'exporte scène par scène. Un dossier existant n'est remplacé que s'il ne contient qu'une séquence ; sinon l'export refuse et ne touche à rien.
- **Audio** : la **bande-son seule** (voix, musique, bruitages mixés), en WAV sans perte ou en MP3, pour un podcast ou un montage son. Une scène sans clip donne du silence de la bonne durée.

Le volume de tous les profils avec son est **normalisé à −14 LUFS** par défaut (voir [Narration audio](narration.md)). Les [effets et filtres](effets-et-filtres.md) sont toujours inclus.

## Export en arrière-plan

**En arrière-plan** envoie l'export dans le panneau **Exports** (**Affichage > Exports**) et ferme la fenêtre : vous continuez à éditer pendant le rendu. La vidéo correspond au projet **tel qu'il était au moment de l'envoi** ; les modifications suivantes n'y figurent pas. Plusieurs exports s'enchaînent dans l'ordre. Dans le panneau : progression, **Annuler**, **Ouvrir le dossier**, **Retirer les travaux finis**. En quittant ANTARES pendant un export, une question vous laisse choisir de l'annuler ou de rester.

## Aperçu rapide et image fixe

- **Fichier > Aperçu rapide (360p)** (Ctrl+Maj+E) : exporte la scène en petit format, très vite, en arrière-plan, puis l'ouvre dans le lecteur vidéo du système. Idéal pour vérifier un rythme ou une synchronisation.
- **Fichier > Exporter l'image courante (PNG)…** : enregistre l'image affichée, à la résolution du projet, caméra et transition comprises (vignette, illustration d'un document).

## Pendant l'export

- La progression s'affiche image par image. Le rendu tourne en arrière-plan : la fenêtre d'export reste réactive.
- **Annuler l'export** (ou Échap) arrête proprement : aucun fichier partiel n'est laissé.
- Les **avertissements** (ressource sans provenance, par exemple) s'affichent avant le rendu.

## Après l'export

ANTARES **vérifie** le fichier produit (dimensions, nombre d'images, durée, présence du son) et affiche le résultat. **Ouvrir le dossier** affiche la vidéo dans l'explorateur de fichiers.

À côté de la vidéo :

| Fichier | Contenu |
|---|---|
| `nom.mp4` | la vidéo (ou `nom.mov`, `nom.wav`… selon le profil ; un dossier `nom/` pour une séquence PNG) |
| `nom.srt` | les sous-titres, s'il y en a ; pour une vidéo complète, ceux de toutes les scènes |
| `nom.credits.txt` | les [crédits](credits.md) |
| `nom.mp4.manifest.json` | le compte rendu technique : profil, durées, scènes, vérifications |

## Ce que l'export garantit

- **Ce que vous voyez est ce que vous obtenez** : le canevas et l'export utilisent le même moteur de dessin.
- Toutes les images sont calculées, même si l'aperçu en a sauté.
- Le son est mixé exactement : décalages, gains, fondus, [musique baissée sous la voix](narration.md) et volume normalisé (mesuré en EBU R128 par les tests automatiques).
- Une vidéo complète enchaîne les scènes sans réencodage (sauf le GIF, recalculé pour garder une palette commune) ; une scène sans son reçoit une piste silencieuse pour rester synchronisée.

Exporter sans ouvrir l'interface : voir [Ligne de commande](ligne-de-commande.md). Problème d'export : voir [Dépannage](depannage.md).

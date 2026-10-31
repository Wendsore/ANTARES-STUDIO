# Ce qui n'est pas encore possible

ANTARES Studio est en version de développement. Voici, honnêtement, ce qu'il ne fait pas encore.

## Création et animation

- Éditer à la souris les sommets d'un polygone.
- Styles réutilisables et palettes de marque.
- Glisser-déposer depuis la Bibliothèque vers le canevas : utilisez le double-clic.
- Transitions de **sortie** propres à une scène : la transition se règle sur l'entrée de la scène suivante.

## Son

- Marqueurs sur la forme d'onde, réduction de bruit, égaliseur.
- Bruitages : uniquement les sons de synthèse fournis ; pas de banque de sons enregistrés.
- Le niveau d'atténuation de la musique sous la voix n'est pas réglable (environ 15 dB).
- L'enregistrement au micro n'a été vérifié que sous Linux ; sous Windows, il reste à confirmer sur un vrai poste.

## Post-production et export

- Changer la cadence à l'export (par exemple projet à 30 images/s exporté en 25 ou 60) : la vidéo garde la cadence du projet.
- Effets sur un groupe entier ou sur une caméra : appliquez-les aux objets.
- Séquence PNG de toutes les scènes à la suite : exportez-la scène par scène.
- Normalisation du volume sur l'ensemble d'une vidéo complète : chaque scène est normalisée séparément.
- Effets de transition personnalisés : seules les transitions fournies (fondu, glissements, volet) existent.

## Sciences

- Champs de vecteurs, tableaux et matrices dans les équations.
- Échelle logarithmique et plusieurs courbes par graphique.
- Simulations à N corps réglables depuis l'interface : seuls les modèles « Trois corps en huit » et « Étoile double » sont fournis.

## 3D

- Textures, animations et squelettes des modèles glTF (seules la forme et la couleur de base sont dessinées) ; fichiers `.gltf` à ressources séparées (exportez en `.glb`).
- Caméra 3D et rendu GPU : la caméra est un cadrage 2D.
- Surfaces de fonctions z = f(x, y), axes 3D gradués ; solides qui s'interpénètrent (tri des faces sans tampon de profondeur).
- Polices « à un seul trait » (écriture au stylo tracée trait par trait) : l'écriture progressive dessine le contour des lettres.

## Astres, ondes et optique

- Modèles 3D maillés des planètes : les astres sont des sphères texturées calculées par le logiciel (pas de relief ni de cratères en volume).
- Les textures fournies ont une résolution de 2 048 × 1 024 : un astre très agrandi (plein écran en 4K) devient flou ; importez une texture plus fine comme *Texture personnelle*.
- Le trou noir est une illustration : la déviation de la lumière n'est pas calculée par la relativité générale.
- Les éléments d'optique ne calculent pas la réfraction ni la réflexion : placez les rayons vous-même.
- Le ciel étoilé ne calcule pas l'heure ni le lieu d'observation (horizon) : choisissez le centre du champ en coordonnées célestes.
- Pas de carte d'une région à grande échelle (pays seul, ville) : seuls les planisphères sont fournis.

## Personnages

- En style **Réaliste**, les signes de bande dessinée (« ? », « ! », étincelles, vapeur) ne sont pas dessinés : ajoutez une bulle si besoin.
- Les personnages sont des images fixes en 2D : pas de 3D, pas de marche ni de geste animé image par image ; l'émotion et la pose changent d'un coup à l'image clé.
- La bouche ne suit pas encore la voix enregistrée (pas de synchronisation labiale automatique) : alternez vous-même **Explique** et **Neutre**.
- Pas de suivi de vos mouvements par la caméra.
- On ne peut pas encore importer son propre dessin de personnage découpé en pièces : importez une image fixe avec l'objet **Image**.

## Exemples

- Les exemples complets n'ont pas de voix : seuls les sous-titres portent le texte. Enregistrez votre narration au micro.

## Distribution

- Installateur Windows **signé** : l'installateur existe mais n'est pas signé (un certificat de signature de code est nécessaire) ; SmartScreen peut avertir.
- Validation complète sur Windows 11 par un utilisateur : en cours (liste de recette fournie).
- Traductions autres que le français.

La liste à jour se trouve dans le fichier `docs/PROJECT_STATUS.md` du projet.

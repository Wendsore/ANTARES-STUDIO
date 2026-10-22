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

## Exemples

- Les exemples complets n'ont pas de voix : seuls les sous-titres portent le texte. Enregistrez votre narration au micro.

## Distribution

- Installateur Windows **signé** : l'installateur existe mais n'est pas signé (un certificat de signature de code est nécessaire) ; SmartScreen peut avertir.
- Validation complète sur Windows 11 par un utilisateur : en cours (liste de recette fournie).
- Traductions autres que le français.

La liste à jour se trouve dans le fichier `docs/PROJECT_STATUS.md` du projet.

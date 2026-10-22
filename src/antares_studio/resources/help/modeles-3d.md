# Modèles 3D (glTF)

ANTARES affiche des modèles 3D au format **glTF 2.0**, le format ouvert des sites de modèles et de Blender. Le rendu est simple et rapide : faces ombrées par une lumière fixe, dans la couleur de base de chaque matériau, sans texture.

## Importer un modèle

1. Le projet doit être **enregistré** : le fichier est copié dans son dossier `assets/`.
2. **Objet > Importer un modèle 3D (glTF, .glb)…** et choisissez le fichier.
3. La fiche de provenance s'ouvre : indiquez l'auteur et la licence du modèle. Voir [Provenance et licences](provenance-et-licences.md).

Formats acceptés :

- **`.glb`** (un seul fichier) : recommandé ;
- **`.gltf`** seulement si ses données sont **incluses dans le fichier**. Un `.gltf` accompagné de fichiers `.bin` séparés est refusé avec un message : exportez-le en `.glb` (dans Blender : *Fichier > Exporter > glTF 2.0*, format « glTF Binary »).

Limite : 100 000 triangles. Au-delà, simplifiez le modèle (Blender : modificateur *Decimate*).

## Régler et animer

Dans l'Inspecteur :

- **Taille à l'écran** ;
- **Rotation horizontale (°)** et **Inclinaison (°)** : tournent le modèle sur lui-même ; animez-les avec le losange ◆ pour le faire pivoter ;
- position, échelle et opacité, comme les autres objets.

## Ce qui n'est pas pris en charge

Textures, animations et squelettes contenus dans le fichier sont ignorés : seules la forme et la couleur de base des matériaux sont dessinées. Pour une planète réaliste rendue en 3D, voir [Planète 3D avec Blender](planete-3d.md).

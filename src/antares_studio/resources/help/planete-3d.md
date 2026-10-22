# Planète 3D avec Blender (facultatif)

ANTARES Studio est un logiciel **2D**. Pour une planète en relief, il peut faire appel à **Blender** (gratuit, licence GPL, https://www.blender.org) s'il est installé. Sans Blender, cette fonction est simplement indisponible et tout le reste fonctionne.

## Installer et vérifier

1. Installez Blender depuis https://www.blender.org.
2. **Aide > Diagnostics…** doit afficher « Blender : … » avec sa version.
3. Si Blender est installé ailleurs, définissez la variable d'environnement `ANTARES_BLENDER` avec le chemin complet de l'exécutable, puis relancez ANTARES.

## Créer la planète

1. Enregistrez le projet : les images rendues sont rangées dans son dossier `assets/`.
2. **Objet > Planète 3D (Blender, facultatif)…**
3. Réglez le nombre d'**images rendues**, la **taille**, les **tours sur la durée**, les **échantillons Cycles** (qualité, au prix du temps) et les couleurs des **océans** et des **continents**.
4. Lancez le rendu. La progression s'affiche ; le rendu s'annule à tout moment.

Blender calcule en arrière-plan une sphère texturée, inclinée de 23,4°, qui tourne sur elle-même, sur fond transparent. ANTARES l'insère comme objet **Séquence d'images (rendu 3D)** animé sur toute la durée de la scène : déplacez-le, redimensionnez-le et animez-le comme n'importe quel objet.

## Temps de rendu

Le rendu Cycles se fait sur le processeur. Comptez de quelques secondes à quelques minutes selon le nombre d'images, la taille et les échantillons. Commencez avec peu d'images pour essayer.

L'import de modèles 3D (glTF, GLB), la caméra animée et le rendu GPU ne sont pas encore disponibles.

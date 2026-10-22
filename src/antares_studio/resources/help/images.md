# Images importées

## Importer une image

1. Enregistrez le projet : l'image est **copiée** dans son dossier `assets/`. ANTARES le propose si ce n'est pas fait.
2. **Objet > Importer une image…** (Ctrl+I).
3. Formats : PNG, JPEG, SVG, BMP, WebP.
4. Un objet **Image** est ajouté au centre de la vue, et la fiche de provenance s'ouvre ([provenance](provenance-et-licences.md)).

L'image d'origine n'est jamais modifiée. Le dossier du projet reste autonome : il contient sa propre copie.

## Régler l'image

Dans l'[Inspecteur](inspecteur.md) :

- **Ressource** : remplace l'image par une autre image déjà importée, en gardant position et animations ;
- **Largeur** ; **Hauteur** (0 = proportionnelle) ;
- **Teinte** : colore l'image (transparente par défaut, sans effet) ;
- opacité, rotation, échelle et animations comme pour tout objet.

## Où trouver des images libres

Préférez des images dont la licence autorise la réutilisation et notez-la :

- NASA Image and Video Library (https://images.nasa.gov) : en général libre de droits, sauf mention contraire ;
- ESA (https://www.esa.int/ESA_Multimedia) : souvent CC BY-SA 3.0 IGO, à vérifier image par image ;
- Wikimedia Commons (https://commons.wikimedia.org) : licence indiquée sur chaque fichier.

Une image trouvée sur un moteur de recherche n'est pas libre par défaut.

## Image absente

Si le fichier a disparu du dossier `assets/`, l'objet affiche un cadre rouge en pointillés, à l'écran comme à l'export. Réimportez l'image, puis choisissez-la dans **Ressource**.

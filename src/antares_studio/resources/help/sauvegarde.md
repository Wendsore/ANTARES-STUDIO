# Sauvegarde automatique et récupération

## Sauvegarde automatique

Dès que le projet a été **enregistré une première fois**, ANTARES écrit une copie toutes les 60 secondes dans le sous-dossier `autosaves/` du projet. Le message « Sauvegarde automatique effectuée. » apparaît brièvement dans la barre d'état. Un projet jamais enregistré n'a pas encore de dossier : enregistrez-le tôt.

Chaque enregistrement est **atomique** : le fichier est écrit à part puis remplacé d'un coup. Une coupure de courant pendant l'écriture ne peut pas laisser un `project.json` à moitié écrit.

## Après une panne ou une fermeture brutale

En rouvrant le projet, si une sauvegarde automatique est **plus récente** que le dernier enregistrement, ANTARES propose « Récupération après interruption ». Répondez **Oui** pour reprendre là où vous en étiez, puis enregistrez. Le projet enregistré reste intact tant que vous n'enregistrez pas.

## Si le fichier du projet est illisible

ANTARES propose d'ouvrir la **dernière sauvegarde automatique valide**. Le fichier abîmé est mis de côté dans `autosaves/`, jamais effacé. S'il n'existe aucune sauvegarde valide, le message l'indique et le fichier d'origine n'est pas modifié.

## Annuler et rétablir

**Édition > Annuler** (Ctrl+Z) et **Édition > Rétablir** (Ctrl+Y ou Ctrl+Maj+Z) couvrent toutes les modifications du projet : objets, animations, sons, sous-titres, métadonnées, provenance des ressources.

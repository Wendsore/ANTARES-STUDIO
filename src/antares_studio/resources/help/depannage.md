# Dépannage et messages d'erreur

Commencez toujours par **Aide > Diagnostics…** : il indique ce qui manque.

## Export

| Message ou symptôme | Cause | Que faire |
|---|---|---|
| « FFmpeg : introuvable » dans la fenêtre d'export | FFmpeg n'est pas installé ou pas trouvé | installez-le, puis **Aide > Chemin de FFmpeg…** ([installation](installation.md)) |
| Diagnostics : « encodeur H.264 (libx264) : NON » | build de FFmpeg sans libx264 | installez un build complet de FFmpeg |
| « Avertissement : … provenance … » | une ressource utilisée n'a pas de licence complète | complétez sa fiche ([provenance](provenance-et-licences.md)) ; l'export continue |
| « Indiquez un fichier de sortie. » | champ vide | **Parcourir…** |
| « Export impossible » avec détails | FFmpeg a échoué (disque plein, dossier protégé, nom invalide) | lisez les dernières lignes des détails ; essayez un autre dossier |
| Vidéo sans son | aucun clip, clips muets ou gain nul | vérifiez l'onglet *Audio* ; une scène sans clip reçoit volontairement une piste silencieuse |

## Sons et images

| Message | Cause | Que faire |
|---|---|---|
| « Enregistrez d'abord le projet… » | sons, images et données sont copiés dans le dossier du projet | **Ctrl+S**, puis recommencez |
| « Ce fichier n'est pas un audio lisible » | format non reconnu ou fichier abîmé | convertissez en WAV ou MP3 (par exemple avec Audacity) |
| Pas de son pendant la lecture | l'aperçu sonore dépend de la machine | l'export, lui, contient le son ; vérifiez avec un brouillon |
| Pas de forme d'onde | FFmpeg introuvable | voir [installation](installation.md) |
| Cadre rouge en pointillés à la place d'une image | fichier absent du dossier `assets/` | réimportez l'image ([images](images.md)) |
| « Le fichier doit être encodé en UTF-8. » (sous-titres) | fichier SRT/VTT dans un autre encodage | réenregistrez-le en UTF-8 avec un éditeur de texte |

## Données (CSV)

| Message | Que faire |
|---|---|
| « aucune colonne numérique : vérifiez le séparateur et le format des nombres » | séparez les colonnes par `;`, `,` ou tabulation ; nombres sans unité dans les cellules |
| « … cellule(s) non numérique(s) ignorée(s) » | normal si une colonne contient du texte ; sinon corrigez les cellules |
| « fichier trop volumineux » ou « trop de lignes » | limites : 32 Mo et 200 000 lignes ; réduisez l'échantillonnage |

## Projet

| Situation | Que faire |
|---|---|
| « Récupération après interruption » à l'ouverture | **Oui** reprend la dernière sauvegarde automatique ([sauvegarde](sauvegarde.md)) |
| « Projet illisible » | acceptez la récupération proposée ; le fichier abîmé est conservé dans `autosaves/` |
| « Dossier non vide » à l'enregistrement | choisissez un nouveau nom : ANTARES n'écrit pas dans un dossier qui n'est pas un projet |
| Un objet ne bouge pas au clic | il est verrouillé ou masqué : voir [Scènes, calques et groupes](scenes-et-calques.md) |
| « Sélectionnez d'abord un objet… » | une animation s'applique à l'objet sélectionné |
| Panneau disparu | **Affichage > Réinitialiser la disposition** |

## Blender

| Message | Que faire |
|---|---|
| « Blender est introuvable » | installez Blender ou définissez `ANTARES_BLENDER` ([planète 3D](planete-3d.md)) |
| Rendu très long | réduisez images, taille ou échantillons |

## Signaler un problème

**Aide > Créer un rapport d'incident…** produit un fichier `.zip` lisible à joindre à votre demande : diagnostics, structure du projet (nombre de scènes, d'objets, types), et erreurs inattendues enregistrées par ANTARES. **Aucun contenu** du projet (textes, images, sons) n'y figure, votre dossier personnel est remplacé par `~`, et **rien n'est envoyé** : vous décidez à qui le transmettre.

Ajoutez les étapes pour reproduire et le message exact.

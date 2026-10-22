# Recette visuelle et fonctionnelle sur Windows 11

Cette liste se remplit **sur un vrai poste Windows 11**. Les tests automatiques de la CI Windows
(`windows-latest`, sans écran) ne remplacent pas cette vérification : ils ne voient ni l'échelle
d'affichage, ni les polices de substitution, ni le micro, ni SmartScreen.

## 1. Préparer

1. Installer avec `ANTARES-Studio-<version>-setup.exe` (artefact `ANTARES-Studio-windows-x64-setup`
   de la CI). SmartScreen affiche « Éditeur inconnu » : l'installateur n'est pas signé (certificat
   non acheté). Cliquer « Informations complémentaires » puis « Exécuter quand même ».
2. Noter : version de Windows (`winver`), échelle d'affichage (Paramètres > Écran), carte graphique.
3. Dans un terminal : `"%LOCALAPPDATA%\Programs\ANTARES Studio\ANTARES Studio.exe" --capture "%USERPROFILE%\Desktop\captures-antares"`
   (chemin par défaut d'une installation pour l'utilisateur courant). Le dossier reçoit 9 images et
   `captures.txt` (système, écran, rapport de pixels). Les préférences ne sont pas touchées.

## 2. Captures à comparer

| Image | À vérifier | OK / remarque |
|---|---|---|
| `01-editeur-sombre.png` | Menus et barre d'outils lisibles, icônes nettes (pas floues ni pixelisées), aucun texte coupé | |
| `02-editeur-clair.png` | Même chose en thème clair ; contraste suffisant des libellés gris | |
| `03-editeur-texte-150.png` | Texte à 150 % : aucun libellé tronqué dans l'Inspecteur, la Bibliothèque, la Timeline | |
| `04-narration.png` | En-têtes du tableau complets (« Fondu entrée (s) », « Rôle ») ; bouton « Enregistrer au micro… » | |
| `05-accueil.png` | Page d'accueil entière visible, boutons alignés | |
| `06-export.png` | Liste des profils groupée (Usage, Plateforme, Format) ; boutons « En arrière-plan » et « Exporter » | |
| `07-constantes-unites.png` | Valeurs avec exposants (10⁸) bien rendus, pas de carré à la place d'un caractère | |
| `08-courbe-interpolation.png` | Courbe et poignées visibles, boutons « Appliquer » / « Annuler » en français | |
| `09-centre-aide.png` | Rubrique « Exporter la vidéo » lisible, images affichées | |

Recommencer l'étape 3 avec l'échelle d'affichage Windows à **150 %** puis **200 %** (déconnexion
parfois nécessaire) et comparer : `captures.txt` doit indiquer le rapport de pixels 1,5 puis 2.

## 3. Parcours à faire à la main

| Parcours | Résultat attendu | OK / remarque |
|---|---|---|
| Nouveau projet « Phases de la Lune », lecture (Espace) | Animation fluide, son coupé proprement à l'arrêt | |
| Narration > Enregistrer au micro… (avec un micro branché) | Durée qui avance ; à l'arrêt, une piste « narration-… » apparaît, fiche de provenance « Œuvre personnelle » | |
| Même dialogue micro débranché | Message « Aucun micro détecté », bouton désactivé | |
| Paramètres Windows > Confidentialité > Micro : accès refusé | Message clair, aucune fermeture inattendue | |
| Exporter en « GIF animé » puis « WebM » | Fichiers lisibles dans le navigateur (Edge) ; le GIF est muet | |
| Exporter en arrière-plan puis continuer à éditer | Panneau Exports : progression, « Terminé », « Ouvrir le dossier » ouvre l'Explorateur | |
| Fichier > Aperçu rapide (Ctrl+Maj+E) | La vidéo 360p s'ouvre dans le lecteur par défaut | |
| Fichier > Exporter l'image courante (PNG) | Image à la taille du projet | |
| Édition > Copier, puis Coller dans un autre projet ouvert | Objets et animations recopiés, image importée si besoin | |
| Aide > Créer un rapport d'incident | Fichier .zip lisible, aucun nom de dossier personnel en clair | |
| Désinstaller (Paramètres > Applications) | Programme retiré ; projets et préférences conservés | |

## 4. Rendre compte

Joindre le dossier de captures, `captures.txt`, cette liste remplie et, en cas de problème, le
rapport d'incident (Aide > Créer un rapport d'incident…).

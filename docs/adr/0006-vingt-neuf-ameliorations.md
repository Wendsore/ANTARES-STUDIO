# ADR-0006 — Vingt-neuf améliorations : animation, édition, scènes, sciences, son, export, distribution, accompagnement

**Date :** 2026-10-22 — **Statut :** accepté — **Phase :** transverse (5 à 9) — **Branche :** `feat/phase-10-ameliorations` (PR #12)

## Contexte

Le porteur a demandé 29 améliorations proposées après la PR #11, puis « implémente les améliorations », en
autonomie complète : aucune question, chaque arbitrage décidé et consigné ici. Contraintes inchangées :
hors ligne, français, PySide6 + FFmpeg seuls, format de projet v1 lisible par les versions précédentes
(champs additifs), rendu identique éditeur / export (ADR-0001), aucune ressource sans provenance (ADR-0003).

## Décisions générales

1. **Schéma de projet : uniquement des champs additifs, omis quand ils valent leur défaut.** Repères
   (`scene.markers`), transition d'entrée (`scene.transition`), rôle des clips audio (`role`), points de
   Bézier d'une clé (`bezier`), réglage `project.settings["ducking"]` (écrit seulement s'il vaut `False`).
   Un projet qui ne les utilise pas s'enregistre sans aucune de ces clés (testé) : un utilisateur de la
   version précédente rouvre ses projets sans migration.
2. **Toute action utilisateur = une étape d'annulation.** `UndoStack.begin_macro/end_macro` et
   `ProjectDocument.macro` regroupent grouper, dégrouper, dupliquer, supprimer, coller, aligner, répartir,
   l'édition multiple dans l'Inspecteur et l'insertion d'une valeur physique.
3. **Réutiliser avant de créer** : un seul `FrameRenderer` (transitions, caméra) pour l'éditeur, l'image
   PNG et l'export ; un seul `RenderWorker` pour le dialogue d'export et la file d'arrière-plan ; un seul
   mécanisme `ParamSpec.choices` (liste déroulante + validation) pour les nouveaux paramètres à choix.

## Arbitrages, option retenue et raison

| # | Question | Retenu | Écarté, et pourquoi |
|---|---|---|---|
| 1–2 | Où régler l'interpolation ? | Liste « Interpolation » de la Timeline + clic droit sur un losange ; « Courbe personnalisée… » ouvre l'éditeur (notation CSS `cubic-bezier`, préréglages) | Réglage dans l'Inspecteur : l'interpolation appartient à la clé, pas à la propriété |
| 1 | Une clé reposée doit-elle garder son interpolation ? | Oui (`SetKeyframe(easing=None)`) — c'était un défaut : elle repassait en linéaire | — |
| 3 | Transition d'entrée ou de sortie ? | **D'entrée**, prise sur les premières images de la scène : la durée totale ne change pas, la synchronisation son/sous-titres non plus | Chevauchement des scènes : décale tout le son et les sous-titres |
| 4 | Raccourcis des repères | M, [ et ] (conventions des logiciels de montage), libres dans l'application | — |
| 5 | Caméra 3D ou 2D ? | Objet **Caméra 2D** (point visé, zoom, inclinaison animables) ; « Voir à travers la caméra » décochable pour la placer | Caméra 3D : aucun moteur 3D temps réel dans l'éditeur |
| 6 | Synchroniser une animation | Liste « Caler sur » du dialogue de preset (repère jusqu'au suivant, sous-titre, clip audio) | Lien dynamique repère → animation : complexité et ambiguïtés à l'édition |
| 7 | Coller dans un autre projet | Copie autonome relue par les validateurs du format ; fichier identique réutilisé (SHA-256), sinon recopié **avec sa fiche de licence** | Collage sans ressources : objets cassés |
| 8 | Guides d'alignement | Bords et centres des objets et du canevas, aimantation, Ctrl pour ignorer, désactivables (Affichage) | — |
| 9 | Aligner un objet seul | Sur le canevas | Ne rien faire : surprenant |
| 10 | Verrouiller / masquer | Déjà présent (œil, cadenas) : rien ajouté, documenté | — |
| 11 | Valeurs différentes en édition multiple | Champ marqué « ≠ » ; la saisie s'applique à tous en une étape | Champ vide : confondu avec une valeur nulle |
| 12 | Histogrammes et barres : nouvel objet ? | **Variante de l'objet Graphique** (`chart_type` : courbe, barres, histogramme ; `bins`) | Nouvel objet : doublon du chargement CSV, des axes et des unités |
| 13 | N corps : interface de saisie ? | Bibliothèque `science.nbody` (Verlet-vitesse, énergie et quantité de mouvement suivies) + 2 modèles vérifiables (huit de Chenciner–Montgomery, étoile double) ; trajectoires posées en pistes de position | Éditeur de conditions initiales : risque d'orbites instables présentées comme justes |
| 14 | Où mettre constantes et unités ? | **Objet > Valeur physique (constantes et unités)…**, écriture française (× 10ⁿ), insertion d'un texte | Nouveau menu « Sciences » : un menu de plus pour un seul dialogue |
| 15 | Morphing de formules | Paramètre « Transformer en » + preset « Transformer la formule » ; symboles communs appariés (`SequenceMatcher`) qui glissent, autres en fondu | Morphing de contours : illisible pour des symboles |
| 16 | Quels glTF accepter ? | **GLB, ou `.gltf` à données intégrées** ; `.bin` séparés refusés avec le conseil d'exporter en `.glb` ; 100 000 triangles au plus ; couleur de base des matériaux, sans texture | Dépendance (trimesh, pygltflib) : poids et licence ; fichiers externes : un projet copié perdrait ses buffers |
| 17 | Format d'enregistrement micro | WAV via QtMultimedia, fiche « Œuvre personnelle » préremplie, projet enregistré exigé (comme l'import) | Compression à l'enregistrement : perte avant montage |
| 18 | Atténuation de la musique | **Activée par défaut**, rôle « Musique » explicite ; `sidechaincompress` FFmpeg à l'export | Désactivée par défaut : la musique couvre la voix, défaut le plus fréquent des débutants |
| 19 | Lisibilité des sous-titres | Vitesse > 17 car./s, affichage > 7 s, contraste du style (WCAG 4,5:1) ajoutés aux diagnostics existants | — |
| 20 | Formats des plateformes | Profils « Plateforme » à cadre imposé, **bandes noires** si le format diffère | Recadrage automatique : coupe le contenu scientifique |
| 21 | GIF | 480p, 15 images/s au plus (images sautées, durée conservée), palette par fichier ; vidéo complète réencodée pour une palette commune | — |
| 22 | Export en arrière-plan : quel projet ? | **Copie figée à l'envoi** (deepcopy + résolveur des ressources) ; file séquentielle ; question à la fermeture si des exports sont en cours | Export de l'état courant : la vidéo dépendrait des éditions faites pendant le rendu |
| 23 | Aperçu rapide | Profil 360p `ultrafast` en arrière-plan, ouvert dans le lecteur du système (Ctrl+Maj+E) | Lecteur intégré : QtMultimedia variable selon les postes |
| 24 | Installateur Windows | **Inno Setup par utilisateur** (`PrivilegesRequired=lowest`), installé, autotesté puis désinstallé en CI. **Non signé** | MSI/WiX : chaîne plus lourde ; installation machine : droits admin |
| 25 | Recette Windows 11 | Liste à remplir sur un vrai poste + `--capture DOSSIER` (9 écrans, échelle) | Prétendre la recette faite depuis Linux : interdit (AGENTS.md) |
| 26 | Rapport d'incident | `.zip` lisible **local** (diagnostic, structure du projet, erreurs journalisées ≤ 200 ko), dossier personnel remplacé par `~`, **aucun contenu** du projet, rien envoyé | Envoi automatique : contraire au fonctionnement hors ligne |
| 27 | Rejouer les tutoriels | Tutoriels 1 et 3 à 7 joués en test par l'interface réelle (le 2 l'était déjà) | — |
| 28 | Astuces de première utilisation | Bulle posée sur la fenêtre (ne vole pas le focus), une fois par panneau, à la **première entrée du focus par l'utilisateur** (le focus initial au démarrage est ignoré), jamais pendant un tutoriel ; « Ne plus afficher d'astuces » et **Aide > Réafficher les astuces** ; textes limités aux gestes réellement disponibles (ex. : Alt + glisser, pas la barre d'espace) | Infobulles modales ; astuce au démarrage : concurrence la page d'accueil |
| 29 | Galerie d'exemples | 3 projets complets construits à partir des modèles intégrés (titre, scènes, sous-titres minutés pour passer les contrôles, repères, transitions, crédits), sur l'accueil et dans **Fichier > Exemples**, ouverts non enregistrés ; une seule représentation scientifique par exemple. **Aucune voix** : dit sur l'accueil, dans l'aide et dans « Limites » | Narration synthétique : présentée comme voix, trompeuse ; fichiers d'exemple sur disque : à maintenir à chaque évolution du format |

## Correctifs trouvés en chemin (tests qui échouent sur l'ancien code, vérifié par mutation)

- `SetKeyframe` remettait l'interpolation d'une clé existante en « linéaire » ;
- un preset appliqué à une sélection mêlant des objets non concernés produisait un projet invalide :
  ces objets sont maintenant ignorés et signalés (`apply_preset_values` → liste des objets ignorés) ;
- l'Inspecteur de scène défilait horizontalement (listes trop larges) : listes compactes, durée de
  transition sur sa propre ligne ;
- `AddMarker` rendait inopérant l'objet retourné (copie) ; en-têtes de la Narration tronqués ; bouton
  « Close » non traduit ; identifiant de rubrique d'aide invalide pour le panneau Exports.

## Conséquences et preuves

- 319 tests pytest verts sur Linux (contre 214) : 203 unitaires, 27 intégration (dont GIF, WebM, bandes
  noires, atténuation mesurée par FFT, GIF de projet complet, transition décodée au milieu d'un fondu),
  86 interface (dont 6 tutoriels rejoués, enregistrement réel au micro de `ki`), 3 documentaires ;
  ruff et mypy strict propres.
- Aide intégrée : 33 rubriques (nouvelle : « Modèles 3D (glTF) ») ; chaque chemin de menu cité est
  vérifié contre la vraie barre de menus.
- **NON TESTÉ sur Windows 11 réel** : micro, installateur hors CI, captures `--capture`, rendu HiDPI (R-005).
- **Bloqué** : signature de l'installateur (certificat de signature de code à acheter, décision du porteur).

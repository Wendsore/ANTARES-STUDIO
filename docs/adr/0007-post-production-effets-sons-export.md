# ADR-0007 — Post-production : effets d'objet, filtres de scène, bruitages, formats et volume d'export

**Date :** 2026-10-22 — **Statut :** accepté — **Phase :** 11 (post-production) — **Branche :** `feat/phase-11-post-production` (empilée sur la PR #12)

## Contexte

Demande du porteur : « Fais donc un travail sur la post prod, le rendu, les tailles, les formats, les
filtres si ce n'est pas encore fait. Je veux aussi une bonne bibliothèque d'effets et de bruits. »
Menée en autonomie (aucune question), chaque arbitrage est consigné ici. Contraintes inchangées : hors
ligne, français, PySide6 + NumPy + FFmpeg seuls, rendu identique éditeur / PNG / export (ADR-0001),
format de projet v1 lisible par les versions précédentes (champs additifs), aucune ressource sans
provenance (ADR-0003).

État avant : aucun effet ni filtre ; profils jusqu'au 1080p (MP4, WebM, GIF) ; pas de transparence,
pas de format de montage, pas d'export du son seul, pas de normalisation du volume (listée dans
« Limites ») ; aucune banque de sons.

## Décisions

| # | Question | Retenu | Écarté, et pourquoi |
|---|---|---|---|
| 1 | Où stocker les effets d'un objet ? | Clés `style.fx_*` **présentes seulement si réglées** ; absentes = valeur par défaut (`get_property`, évaluateur) ; animables comme toute propriété de style | Ajout aux `KindSpec.style` : alourdit chaque objet enregistré et l'Inspecteur de tous les types ; champ `node.effects` séparé : schéma, commandes et pistes à dupliquer |
| 2 | Quels effets d'objet ? | Flou, lueur (rayon, couleur, intensité), ombre portée (opacité, flou, décalage, couleur), luminosité, contraste, saturation | Contour lumineux, biseau, distorsions : peu utiles pour un schéma scientifique, coûteux |
| 3 | Comment les calculer ? | L'objet est dessiné dans un calque hors écran à la résolution de sortie, puis NumPy : flou gaussien approché par **3 flous en boîte** (sommes cumulées), couleurs en une **matrice 3×3 + décalage**, alpha prémultiplié ; rayons multipliés par l'échelle du dessin (une lueur de 40 px garde sa taille relative en 720p comme en 4K) ; garde-fou 4096² px (au-delà : objet sans effet plutôt qu'une allocation de plusieurs Go) | `QGraphicsEffect` : propre aux widgets, absent du chemin d'export ; SciPy / OpenCV : dépendance lourde pour trois opérations |
| 4 | Groupes et caméras | **Sans effets** (pas de section, pas de piste) | Effet sur un groupe : demande de rendre le groupe à part, ordre de dessin à revoir — noté dans « Limites » |
| 5 | Filtres de scène | Champ `scene.post` (dictionnaire, **omis s'il est vide**) : luminosité, contraste, saturation, température, sépia, vignettage, grain ; appliqué dans `FrameRenderer` donc partout (canevas, PNG, export, transitions) | Filtre par plan ou par calque d'effets : modèle plus lourd sans besoin exprimé |
| 6 | Grain reproductible ? | 8 champs de bruit précalculés (graine fixe), choisis par `crc32(scène:image)` : deux exports identiques octet pour octet, grain qui varie d'une image à l'autre | Bruit aléatoire à chaque image : exports non reproductibles, tests impossibles |
| 7 | Préréglages | 8 effets d'objet (Lueur d'étoile, Néon bleu, Ombre portée, Arrière-plan flou, Estompé, Noir et blanc, Couleurs vives, Retirer) et 8 filtres (Aucun, Cinéma, Espace profond, Chaud, Froid, Noir et blanc, Archive sépia, Vif). Un préréglage d'objet **remplace** tous les effets de l'objet, en une étape d'annulation | Préréglages cumulatifs : résultat imprévisible après deux clics |
| 8 | Animations d'effet | 5 presets ajoutés au catalogue existant : Secousse (pseudo-aléatoire **reproductible**, amortie, retour exact), Éclat lumineux, Clignotement (paliers), Mise au point, Pulsation lumineuse ; listés dans les onglets Animations **et** Effets | Système d'animation séparé : doublon des presets |
| 9 | Où les proposer ? | Bibliothèque : nouvel onglet **Effets** (objet / scène / animations) ; Inspecteur : section **Effets** (objet) et **Filtres de la scène** (rien de sélectionné, préréglage + réglages fins, « Personnalisé » si modifié) | Menu dédié : un chemin de plus pour la même action |
| 10 | Banque de sons : d'où ? | **Sons synthétisés localement** par NumPy (26 sons, 5 catégories : Transitions, Interface, Impacts, Sciences et espace, Ambiances), graine fixe par son, WAV 16 bits mono 48 kHz, crête −1 dB (ambiances −9 à −16 dB, bouclables), fondus anti-clic ; **CC0**, auteur « ANTARES Studio (son de synthèse) » | Banque téléchargée (Freesound…) : en ligne, licences hétérogènes à vérifier une par une ; fichiers WAV livrés : poids du paquet et du dépôt |
| 11 | Insertion d'un son | Calculé une fois dans un cache (dossier des préférences), **copié dans `audio/`** du projet (projet enregistré exigé, comme l'import), clip de rôle **Effet** à la tête de lecture, fiche de licence remplie ; une seule étape d'annulation | Référence au cache : un projet copié perdrait ses sons |
| 12 | Tailles | Profils **Final 1440p** et **Final 4K 2160p** (petit côté appliqué au format du projet, comme les autres profils d'usage) | 8K : temps de rendu déraisonnable sur les machines visées |
| 13 | Formats de montage | **ProRes 422 HQ** et **ProRes 4444** (`prores_ks`, `.mov`, son PCM) ; **séquence PNG** (écrite par Qt, sans FFmpeg) dans un dossier mis en place d'un coup, bande-son WAV à côté | DNxHR : moins répandu chez les débutants ; séquences TIFF/EXR : inutiles pour du 8 bits |
| 14 | Transparence | Case **Fond transparent**, active seulement pour ProRes 4444 et PNG (cochée d'office en ProRes 4444) ; le fond de scène n'est pas peint ; option CLI `--transparent` ; refusée (erreur claire) pour les autres profils | Transparence en WebM VP9 : prise en charge inégale des lecteurs et logiciels de montage |
| 15 | Son seul | Profils **WAV** et **MP3** : même mixage que la vidéo, sans flux image ; une scène sans clip donne du silence de la bonne durée ; vidéo complète par concaténation | Export audio séparé dans un autre menu : doublon du dialogue d'export |
| 16 | Volume | **Normalisation EBU R128 à −14 LUFS, crêtes ≤ −1,5 dBTP** (`loudnorm`, une passe), **activée par défaut**, case « Volume normalisé » dans Narration (`project.settings["loudnorm"]` écrit seulement s'il vaut `False`) ; par scène | Deux passes (mesure puis correction) : double le temps du mixage ; −16 LUFS : plus bas que YouTube, qui ne remonte pas le son ; −23 LUFS (télévision) : trop bas pour le web |
| 17 | Séquence PNG de toutes les scènes | **Refusée** avec un message (« scène par scène ») | Numérotation continue entre scènes : transitions et noms de dossiers à concevoir pour un usage rare |
| 18 | Écrasement | Un dossier de séquence existant n'est remplacé que s'il ne contient que des `.png`/`.wav` ; sinon refus **avant tout rendu** | Remplacer tout dossier du même nom : risque de détruire des documents de l'utilisateur |
| 19 | Changer la cadence à l'export (25/50/60 i/s) | **Non fait** : la vidéo garde la cadence du projet ; écrit dans « Limites » | Rééchantillonnage temporel : interpolation ou images dupliquées, synchronisation son/sous-titres à revalider |

## Correctifs et vérifications en chemin

- Les images passaient à FFmpeg en `rgba` **non prémultiplié** sans conversion : invisible tant que tout
  était opaque, faux avec la transparence (et avec les filtres de scène, qui produisent des images
  prémultipliées). `_frame_bytes` convertit désormais en RGBA8888 (test ProRes 4444 : alpha 0 au coin,
  255 au centre).
- Performances mesurées sur `ki` (i5-4310U, image 1080p) : filtres de scène ≈ 85–165 ms (576 ms avant
  optimisation : plans contigus `order="C"`, matrice unique, `np.maximum/minimum` au lieu de `np.clip`),
  5 objets avec effets ≈ 280 ms. L'aperçu ralentit sur une machine modeste ; l'export reste exact.
- Aide « Narration » : la phrase « il n'enregistre pas le micro » contredisait la section suivante, corrigée.

## Conséquences et preuves

- Tests : voir le journal de session (suite complète, code de sortie 0). Nouveaux : `test_effects.py`
  (pixels rendus : lueur hors du disque, ombre décalée, flou, gris ; aller-retour du fichier ; validation),
  `test_sfx.py` (26 sons : crête exacte, pas de NaN, pas de composante continue, bords à zéro,
  déterminisme, WAV octet pour octet), `test_export_post.py` (vrai FFmpeg : 4K, ProRes 422 HQ et 4444 avec
  alpha décodé, séquence PNG transparente + bande-son, refus d'écraser un dossier étranger, MP3, bande-son
  de projet complet, **−14 LUFS mesuré par le filtre `ebur128`** à ±1 LU, effets et filtre visibles dans
  la vidéo décodée), `test_post_production.py` (Bibliothèque, Inspecteur, annulation, insertion d'un son
  avec sa fiche CC0).
- Aide : 2 rubriques nouvelles (« Effets et filtres », « Bruitages et ambiances »), 6 mises à jour ;
  catalogues générés depuis le code (effets, filtres, sons, profils).
- Schéma : uniquement additif (`style.fx_*`, `scene.post`, `settings.loudnorm`), omis par défaut.
- **NON TESTÉ sur Windows 11 réel** : écoute des sons, ProRes dans un logiciel de montage Windows.
- La lecture des fichiers ProRes 4444 avec alpha dans DaVinci Resolve / Premiere n'a pas été vérifiée
  (aucun de ces logiciels sur `ki`) ; vérifié : FFmpeg relit le canal alpha.

# ANTARES Studio — PROMPT DIRECTEUR / Cahier des charges exécutable

**Révision : 1.0 — 20 octobre 2026**  
**Référentiel officiel :** https://github.com/Wendsore/ANTARES-STUDIO  
**Nom :** ANTARES Studio — *Scientific Animation & Storytelling Studio*  
**État :** spécification et protocole de réalisation ; pas de fonctionnalité annoncée comme implémentée.

> **INSTRUCTION À L'AGENT :** Lire d'abord `AGENTS.md`. Tu dois construire le logiciel, pas seulement créer des maquettes, listes de fonctionnalités ou descriptions. Enchaîne recherche, code, tests, correction et documentation à chaque livraison. Continue de manière autonome quand les critères de qualité sont satisfaits ; arrête uniquement pour un blocage réel, un choix irréversible ou un acte nécessitant l'accord du propriétaire.

---

## 1. Mission et résultat observable

Concevoir, implémenter, tester et distribuer une application de bureau **Windows 11 d'abord**, avec prise en charge Linux ensuite, permettant à une seule personne disposant de peu de temps libre de produire des vidéos de vulgarisation scientifique professionnelles, sans écrire du Python pour les opérations courantes. L'utilisateur choisit des objets, pictogrammes, schémas, équations, graphes et éléments 3D, les positionne, anime leurs propriétés sur une timeline, synchronise sa narration, puis exporte une vidéo reproductible. Il doit rester maître de son outil, de ses fichiers et du processus de création.

**Vocation éditoriale :** sciences, astronomie, astrophysique, physique, mathématiques ; public particulièrement visé : Afrique francophone, sans exclure d'autres publics. Français de qualité, concepts expliqués sans jargon inutile, exemples contextualisés, sous-titres, voix enregistrée par le créateur, respect des variations culturelles et linguistiques, accessibilité et différenciation entre science établie et simplification visuelle. Ne pas copier les chartes, logos, contenus ou styles propriétaires d'El Jj, ScienceClic ou 3Blue1Brown ; s'inspirer du principe des animations pédagogiques programmatiques.

**Promesse ergonomique à éprouver**, pas à proclamer a priori : créer en moins de temps une vidéo pédagogique courte grâce à une interface visuelle et à des modèles réutilisables. Mesurer le temps réel sur des parcours représentatifs. **Objectif produit :** 80 % des actions courantes sans code ; support Python optionnel et clairement séparé.

### 1.1 Personae et tâches

- **Créateur débutant pressé :** ouvre un modèle « phases de la Lune », remplace textes et couleurs, modifie quelques mouvements, importe une voix off, exporte en MP4.
- **Vulgarisateur intermédiaire :** construit une explication en plusieurs scènes, combine schémas, vecteurs, graphes et formules ; ajuste keyframes, timings et styles sans quitter l'éditeur.
- **Créateur scientifique avancé :** importe données CSV, définit unités/échelles, lance une simulation reproductible, ajuste caméra, utilise scripts dans un espace explicitement autorisé.
- **Enseignant sur PC moyen / hors ligne :** prépare une leçon sans compte, sans service payant, sans connexion Internet obligatoire ; utilise proxies de prévisualisation et rendus de basse résolution.

### 1.2 Trois parcours phares à garantir

**P1 — « Pourquoi les phases de la Lune ? »** Créer projet 16:9 ; ajouter Soleil, Terre, Lune schématiques ; positionner et animer une orbite ; afficher une légende « schéma non à l'échelle » ; ajouter voix off et sous-titres ; exporter 1080p/30 fps ; fermer et rouvrir le projet sans perdre de propriété.

**P2 — « Qu'est-ce qu'une année-lumière ? »** Choisir template comparaison d'échelles, flèches et textes ; afficher valeurs avec unités cohérentes ; construire un zoom/transition, relire et exporter ; citer les sources des constantes.

**P3 — « Une orbite, une vitesse, une gravitation »** Afficher vecteurs et trajectoires ; opposer orbite illustrative et simulation numérique avec paramètres, hypothèses et unités. P3 s'étend progressivement lors des phases avancées.

---

## 2. Périmètre, priorités et exclusion

### MVP strict (critères de première livraison utilisable)

1. Application PySide6 démarrable Windows 11, interface en français, menus/fenêtres dockables.
2. Nouveau/ouvrir/sauver/sauver sous, projet portable, récupération simple après crash, undo/redo.
3. Scène 2D avec formes, cercle, ligne, flèche, texte, images PNG/SVG, groupes, calques, ordre, guides, sélection multiple.
4. Inspecteur contextuel et bibliothèque de ressources de base ; glisser-déposer si validé.
5. Timeline image par image avec keyframes sur position/rotation/échelle/opacité, interpolation contrôlable et boucle ; six presets au minimum : apparition, disparition, translation, rotation, pulsation, orbite schématique.
6. Lecture/pause/scrubbing avec réponse suffisante pour montage courant, sans bloquer l'interface.
7. Import voix off locale WAV/MP3 (selon décodeurs validés), positionnement audio, réglage volume simple.
8. Rendu vidéo MP4 H.264 1080p/30 fps ; mode brouillon 720p ; progression, annulation et messages d'erreur ; preuve réelle d'export et de lecture.
9. Trois modèles pédagogiques simples, tutoriel pour créer une scène et un guide utilisateur.
10. Tests automatiques et tests Windows réels documentés. Pas de qualification « terminé » sans parcours P1 prouvé.

**Hors MVP :** marketplace, hébergement cloud, génération de vidéos par IA, transfert vers YouTube, personnages parlants, simulation relativiste, Blender obligatoire, tracking physique 3D avancé, montage multipiste complexe, collaboration temps réel, plugins tiers non sécurisés, 4K/60 fps obligatoire. Ces fonctions restent en vision long terme sans fragiliser le socle.

### Priorités MoSCoW

- **Must :** scénario P1, prévisualisation utilisable, persistence, timeline, audio de base, export, autonomie hors ligne, traçabilité des tests.
- **Should :** templates, recherche d'icônes, réglages caméra, sous-titres, paramétrage de graphes, styles globaux, raccourcis, packs d'assets.
- **Could :** 3D native, simulations, graphes spécialisés, visualisations de données, bibliothèque de scènes communautaires, assistants locaux optionnels.
- **Won't before product maturity :** système de paiement, moteur d'IA distant obligatoire, dépendance au cloud, microservices distribués.

---

## 3. Fondations techniques — hypothèses à vérifier, non dogmes

### 3.1 Modèle multicouche

```text
                 APPLICATION PySide6 / Qt
Accueil | Palette | Scène | Inspecteur | Timeline | Audio | Export
                          |
                Commandes métier / Undo-Redo
                          |
                 Modèle de projet versionné
Scènes, nœuds, propriétés, ressources, animations, métadonnées
                          |
                Evaluateur pur état(scene, t)
                          |
               Render plan / frame scheduler
             /             |                 \
 Prévisualisation Qt   Export 2D/Manim      Adaptateur Blender (plus tard)
             \             |                 /
                  Composition FFmpeg
                          |
                 MP4 / images / audio
```

- **Domaine pur** (sans Qt) : scènes, nœuds, propriétés, unités, keyframes, courbes temporelles, rendu logique, validation, sérialisation et migrations. Doit pouvoir être testé en `pytest` sur runner headless.
- **UI** : Qt Widgets avec QGraphicsView/QGraphicsScene ou approche GPU seulement si mesures le justifient ; dock widgets, scènes et inspecteur. Ne jamais coupler la logique de sauvegarde au widget.
- **Évaluation temporelle** : `evaluate(project, scene_id, t_seconds) -> SceneState` sans dépendance au temps réel, identique à la prévisualisation et à la construction du rendu final.
- **Rendu** : pipeline planifiable et annulable, moteur 2D principal à choisir expérimentalement ; FFmpeg pour assembler et encoder. Tout moteur tiers est un adaptateur, jamais le format natif de projet.
- **3D plus tard** : appels Blender via CLI/processus externe, génération de scène sécurisée, import GLB/glTF, caméra et compositing, gestion de version/blocage si Blender absent.
- **Calcul** : NumPy/SciPy pour simulation ; SymPy et système de formules selon preuve d'intégration. Éviter d'exiger une installation LaTeX complète pour simplement ouvrir un projet.

### 3.2 ManimGL et Manim Community — décision à prendre en Phase 0

Le souhait initial est ManimGL. **Ne pas conclure que ManimGL offre automatiquement un éditeur interactif et un pipeline simple à embarquer**. Comparer avec Manim Community sur API, qualité du rendu, morphing, génération des équations, intégration Windows, dépendances FFmpeg/TeX/OpenGL, temps de rendu, portabilité, packaging, mise à jour et isolation. Si nécessaire, utiliser Qt pour prévisualiser et compiler la scène en commandes Manim pour le rendu ; ce sera une intégration **non WYSIWYG parfaite** tant que la parité n'est pas démontrée. Ne pas installer les deux variantes dans le même environnement sans justification/isolement explicite. Une alternative (moteur 2D propre sur Qt + export FFmpeg) est admissible si elle démontre une meilleure cohérence pour le MVP, en conservant l'adaptateur Manim comme axe de développement.

**Test décisif en Phase 0 :** cercle + flèche + formule/texte + orbite, script reproductible, 5 secondes exportables, comparaison à la prévisualisation, dépendances identifiées, possibilité d'installation sur Windows, coût d'intégration mesuré. Rédiger ADR après résultats, pas avant.

### 3.3 Contrats de modules (à adapter par ADR)

```python
class ProjectStore(Protocol):
    def load(self, path: Path) -> "Project": ...
    def save_atomic(self, project: "Project", path: Path) -> None: ...

class TimelineEvaluator(Protocol):
    def evaluate(self, project: "Project", scene_id: str, time_s: float) -> "SceneState": ...

class RenderBackend(Protocol):
    @property
    def capabilities(self) -> "RenderCapabilities": ...
    def render(self, job: "RenderJob", callbacks: "RenderCallbacks") -> "RenderResult": ...
```

Ces signatures décrivent les responsabilités ; l'agent peut les modifier après tests et ADR. Ne pas introduire de framework complexe ou plugin system avant de vérifier une implémentation simple.

### 3.4 Données et format de projet

Structure visée :

```text
MonFilm.antares/                 # dossier projet ou archive à définir par ADR
  project.json                   # version de schéma, project_id, settings, scenes
  assets/                        # originaux redistribuables ou références documentées
  audio/                         # narrations et sons originaux
  licenses/                      # attributions et licences
  autosaves/                     # sauvegardes datées, sans écraser manuellement
  cache/                         # régénérable, non autoritatif
  renders/                       # sorties exportées, séparées des données sources
```

Exemple de direction de schéma, NON contrat figé :

```json
{
  "schema_version": 1,
  "project_id": "uuid",
  "title": "Phases de la Lune",
  "locale": "fr-FR",
  "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1},
  "scenes": [
    {
      "id": "scene-001",
      "duration_frames": 300,
      "nodes": [
        {"id": "node-001", "kind": "circle", "name": "Terre", "parent_id": null,
         "position": [0, 0], "scale": [1, 1], "rotation_deg": 0,
         "style": {"fill": "#2677B8"}, "visible": true}
      ],
      "tracks": [
        {"target_id": "node-001", "property": "position.x",
         "keyframes": [{"frame": 0, "value": 0}, {"frame": 299, "value": 100, "easing": "linear"}]}
      ]
    }
  ],
  "assets": [],
  "scientific_metadata": {"representation": "schematic", "to_scale": false}
}
```

**Contraintes :** IDs stables, valeurs validées, pas de chemins absolus codés en dur, normalisation des unités/angles, version de schéma explicite, sauvegarde atomique (temp + remplacement), imports isolés, migration contrôlée avec backup préalable, cache régénérable, désérialisation sans exécution de code, protection ZIP slip/path traversal. Canonicaliser le temps en **frames ou ticks rationnels** pour éviter les dérives audio/vidéo ; éviter les floats en clefs de temps si une représentation entière suffit. Les fichiers projets corrompus doivent produire des erreurs diagnostiquables, pas effacer des données.

### 3.5 Contrats de sécurité et robustesse

- Chemins d'assets résolus sous racine de projet ; toute ressource externe explicitement approuvée. Contrôle des symlinks et chemins normalisés.
- Interdire par défaut l'exécution de scripts arbitraires, expressions Python, macros téléchargées ou expressions LaTeX dangereuses. Exécution avancée explicite seulement avec avertissement et isolation selon évaluation des risques.
- Démarrage sans accès Internet ; pas de télémétrie, pas de compte ni de téléchargement implicite.
- Processus de rendu externe avec timeout configurable, annulation via terminate puis kill contrôlé, log structuré et nettoyage ciblé sans supprimer les fichiers utilisateur.
- Bornes sur taille d'assets, mémoire, complexité d'import, durée et nombre de frames pour éviter les blocages.
- Contrôle de licences des dépendances (PySide6, Blender, FFmpeg et variantes d'encodeurs, polices, modèles, audio), SBOM ou inventaire, attribution exportable ; licence ANTARES proposée à décision humaine.
- Installateurs signés seulement si une identité et signature existent ; ne jamais feindre un binaire signé.

---

## 4. Ergonomie du studio : zéro code pour la création ordinaire

### 4.1 Flux utilisateur attendu

1. **Accueil** : Nouveau, Ouvrir, Récents, Modèles, Apprendre, Diagnostics.
2. **Assistant de projet** : titre, ratio 16:9/9:16/1:1, 1080p/720p, 30 fps, palette, fond, langue, modèle ; valeurs par défaut intelligibles.
3. **Espace studio** : bibliothèque à gauche (recherche, filtres, favoris), canvas central (grille, guides, zoom, focus), inspecteur à droite (onglets contexte), timeline en bas (zoom temporel, pistes, waveform), barre de menus/raccourcis en haut.
4. **Création** : drag/drop ou double-clic objet, positionnement précis et aimantation, renommage, duplication, groupes, visibilité/verrouillage, styles réutilisables.
5. **Animation** : cliquer objet → preset « orbite » → sélectionner centre, durée, rayon, vitesse et sens → aperçu immédiat → ajuster keyframes si besoin.
6. **Narration** : importer audio, voir forme d'onde, placer marqueurs ; ajouter sous-titres ; appliquer styles.
7. **Export** : format/résolution/qualité, rapport de compatibilité, rendu indépendant, progression et annulation, accès au fichier final.

### 4.2 Composants UI obligatoires et états

- Panels redimensionnables, persistants, accessibles clavier, restaurables en configuration usine ; thème sombre et clair seulement si maintenables.
- Canvas : sélection unique/multiple, poignées de déplacement/rotation/échelle, zoom fluide, pan, snap, alignement/distribution, zone de sécurité sous-titres, overlays commutables. Aucune opération courante ne doit nécessiter ouverture d'une console Python.
- Inspecteur : position en coordonnées explicites (pixels ou unités de scène documentées), rotation en degrés, couleur (hex + sélecteur), police, opacité, durée, comportement de boucle ; widgets propres aux types d'objets.
- Timeline : pistes par objet et audio, verrouillage, masque, retour temporel, insertion/suppression de keyframes, glisser-déplacer de clés, multi-sélection, duplication, interpolation linéaire/ease-in/ease-out ; historique undo/redo cohérent.
- Bibliothèque : aperçu réellement représentatif, tags, catégories, provenance/licences visibles, remplacements d'asset en gardant les animations, packs offline.
- Interface en français **par défaut**, labels clairs et messages d'erreurs utiles (quoi, pourquoi, action possible). Préparer traduction par catalogues, pas chaînes dispersées.
- Accueil tutoriel de 10 minutes (à éprouver), raccourcis Ctrl+S, Ctrl+Z/Ctrl+Y, Space lecture, Delete, Ctrl+D, Ctrl+O, Ctrl+N ; respecter variantes plateforme.
- État de projet modifié `*`, autosave non intrusif, restauration après crash, confirmations uniquement quand une perte réelle de données est possible.
- **Accessibilité** : navigation clavier, contrastes suffisants, taille de texte adaptable, zones cliquables raisonnables, ne pas coder le sens par la seule couleur ; options sous-titres.

### 4.3 Réduction radicale du temps de production

- Presets prédéfinis ; commandes recherchables ; réglages par défaut adaptés à l'astronomie ; duplications de scène ; variables globales ; styles réutilisables ; palettes de marque.
- Templates : introduction, définition, comparaison d'échelle, animation de trajectoire, expérience simplifiée, équation pas à pas, conclusion, crédits, « idée reçue vs réalité ».
- Packs locaux : corps célestes schématiques, observatoires, satellites, lunettes astronomiques, fusées stylisées, lasers, vecteurs, axes, particules, mesures physiques, cartes simplifiées, personnages inclusifs sous droits vérifiés.
- Storyboard visuel : script voix off, durée estimée par scène, emplacement visuel, source et message scientifique ; édition complètement manuelle possible.
- Interactions réutilisables : « suivre objet », « orbiter autour », « faire pointer une flèche », « apparaître au mot-clé », « compteur numérique », « tracer courbe », « faire tourner à vitesse constante », « zoomer vers une zone ».

---

## 5. Catalogue d'objets : type → propriétés → outils spécifiques

Chaque objet doit respecter un contrat uniforme : identifiant, parent, position/rotation/échelle, durée de vie, ordre Z, visibilité/verrouillage, nom, sérialisation, sélection, duplication, groupe, keyframes possibles, rendu et limites documentées.

| Famille | Exemples | Outils/propriétés contextuels |
|---|---|---|
| Formes 2D | cercle, rectangle, ellipse, étoile, ligne, polygone, Bézier | remplissage, contour, courbure, largeur, pointillés, jonctions |
| Diagrammes | flèches, connecteurs, boîtes, repères, annotations | ancres, orientation, angle, point de référence, suivre un nœud |
| Texte | titre, paragraphe, légende, crédit | police, alignement, contour, taille, retour ligne, écriture progressive |
| Maths | LaTeX/équation, matrice, fraction, vecteur | rendu équation, transformations/morphing si moteur compatible, fallback SVG |
| Graphiques | axes, fonctions, points, histogramme, courbe de données | bornes, ticks, unité, légende, progression, synchronisation temporelle |
| Image et SVG | PNG, JPEG, SVG et icônes | cadrage, masquage si support, teinte, transparence, chemin d'asset |
| Astronomie | soleil, étoiles, planètes, lunes, orbites, comète, constellation | rayon, couleurs, sens, période, échelle et avertissements scientifiques |
| Caméra 2D | viewport, zoom, pan | cadrage, cible, chemin et durée, easing |
| Audio | voix, musique, bruitages | volume, fondu, début/fin, waveform, silence |
| 3D (après MVP) | sphère, globe, cube, planète texturée, GLB | matériaux, axes, lumière, caméra, profondeur, rendu proxy |
| Simulation (avancée) | N-corps simplifié, champ vectoriel, pendule, rayons | unités, méthodes numériques, tolérance, conditions initiales |

Objets 3D et simulation ne doivent pas être décrits comme entièrement éditables avant d'avoir démontré l'ensemble de leurs outils spécifiques. Les ressources de référence doivent être librement redistribuables ou générées localement.

---

## 6. Système d'animation et de mouvement

### 6.1 Base mathématique

- Timeline à durée finie avec temps canonique quantifié à la frame ; mapping déterministe `frame → state` ; scrubbing indépendamment de la vitesse de lecture.
- Propriétés animables à valeur typée : scalaire, vecteur 2/3D, couleur RGBA, angle avec politique explicite de wrap, visibilité discrète ; erreurs de type anticipées.
- Interpolations : step, linéaire, cubic/ease-in/ease-out ; elastic/bounce plus tard, testées mathématiquement et limitées pour éviter les dépassements absurdes.
- Keyframes : édition, duplication, décalage, sélection multiple, changement interpolation, collisions et durée hors plage gérés explicitement.
- Boucles : nombre fini, répétition, ping-pong, délai, offset, phase initiale ; scrubbing identique avant/après sauvegarde.
- Presets paramétrables (non destructifs) convertibles en keyframes ou expression temporelle native validée ; superposition de presets/règles selon priorités définies.
- Paths : Bézier et orbites à centre sélectionnable ; suivre le chemin, orienter tangentiellement, position/rotation dissociables.
- Cible/parent/groupes : résoudre ordre d'évaluation et cycles de dépendance (détection plutôt qu'infini).

### 6.2 Presets progressifs

**MVP :** entrée, sortie, translation, rotation, pulsation, orbite schématique. **V1+ :** oscillation, zoom caméra, tracer une ligne, écrire du texte, surligner, compteur, déplacement le long de courbe, morphing lorsque types compatibles, suivi de cible, mouvement de particules, rebond. Un preset doit exposer seulement ses paramètres pertinents (durée, angle, répétition...), avec aperçu et bouton réinitialiser.

### 6.3 Exemples d'acceptation

- Terre immobile et Lune en orbite 360°/10 s avec lecture en boucle ; même position exacte à frame donnée avant/après sauvegarde.
- Une flèche suit un objet malgré l'ajout d'un décalage, sans changement du fichier source d'animation ; si le suivi n'est pas implémenté, test attendu XFAIL documenté, pas faux positif.
- Une rotation exacte de 1 tour suit convention constante et fait une boucle sans saut visible au point de raccord.
- Une animation de 30 fps exporte le nombre de frames prévu pour une durée déterminée ; audio ne dérive pas de manière perceptible.

---

## 7. Prévisualisation et moteurs de rendu

### 7.1 Une vérité logique, plusieurs qualités de rendu

La prévisualisation et l'export consomment **le même `SceneState`** évalué au temps `t`; les moteurs graphiques peuvent produire de petites différences d'anticrénelage, de police ou d'éclairage, mais ne doivent pas avoir d'écarts de position, timing, opacité ou logique. Les écarts visuels tolérés doivent être mesurés et documentés. Ne pas relancer Manim à chaque événement souris si cela introduit des latences prohibitives.

### 7.2 Pipeline obligatoire

1. Valider projet, assets, licences et dépendances disponibles.
2. Figurer une *render plan* immuable (fps, dimensions, scènes, frames, version outils).
3. Préparer les assets et caches cohérents.
4. Calculer les frames dans l'ordre, assembler au besoin avec FFmpeg ; ne jamais bloquer la boucle GUI.
5. Mixer/recadrer audio, mapper sous-titres et crédits selon config.
6. Encoder dans un fichier temporaire, vérifier succès avec `ffprobe` (durée, résolution, fps, audio, possibilité de décodage), puis déplacer atomiquement vers la destination.
7. Sur erreur/annulation : rendre message lisible, conserver logs utiles, nettoyer **uniquement** ses temporaires et préserver ancien export valide.
8. Enregistrer manifest de rendu (timestamp, version logiciel/moteur, config, hashes des sources essentielles, avertissements).

Profil **brouillon** : 720p, priorité rapidité ; **final MVP** : 1920×1080, 30 fps, MP4 H.264 compatible large public ; H.264 dépend de l'encodeur FFmpeg effectivement installé et de ses obligations de licence. Prévoir export image PNG et 9:16 après MVP ; pas de promesse 4K/60 fps sans benchmark. Dégrader gracieusement ou informer si codec indisponible.

### 7.3 Effets de bord à maîtriser

- Vidéo de 0 image, durée négative, créneau audio en dehors de timeline, aspect ratio incohérent, police indisponible, SVG malformé, scène interrompue.
- Temps d'export après mise en veille, annulation pendant écriture, disque plein, fichier destination ouvert, codec absent, FFmpeg path avec espaces/unicode sous Windows.
- Couleurs sRGB cohérentes, alpha dans séquence intermédiaire, ordre Z et blending stable, police/encodage des caractères accentués.
- Vitesse preview réduite sur CPU sans GPU, caching, proxies et sélection d'une scène seulement.

---

## 8. Audio, montage léger et narration

- Import narrations WAV/MP3 et musique avec licences ; lecture locale, waveform dérivée, markers, décalage temporel, gain, mute, fades simples.
- Pas de destructive editing de l'original ; segments référencés avec `in/out`.
- Sous-titres SRT/VTT import/export, édition manuelle, style par défaut lisible sur smartphone, arrière-plan/contour, safe zones, langues futures ; validation d'encodage, chevauchements et durée.
- Synchroniser animations à marqueurs de narration, **pas obligatoirement** à une IA de transcription.
- Mixage sans saturation évidente ; test d'intégration pour audio stéréo/mono, fréquences communes et silence.
- Storyboard texte/scènes : plan, voix, visuel, durée cible, notes de provenance ; jamais imposer un outil cloud.
- Plus tard : transcription locale facultative, aide vocale, génération de sous-titres facultative, montage à plusieurs pistes, ducking, ambiance audio et normalisation ; plugins seulement si autorisés.

---

## 9. Bibliothèque scientifique, intégrité éditoriale et inclusivité

### 9.1 Ressources et découverte

Bibliothèque locale avec recherche textuelle, aperçu, catégories, tags, favoris, provenance, auteur/licence, packs signés/vérifiés si distribués. Prévoir géométrie générative locale comme solution sans assets tiers. Ne pas intégrer des éléments non redistribuables. Exports comportent crédits/attribution si requis.

### 9.2 Modèles pédagogiques prioritaires

- Orbites circulaires schématiques, phases de la Lune et éclipses géométriques simplifiées.
- Système solaire schématique (tailles/distances non à l'échelle) ; alternative à l'échelle avec navigation adaptée.
- Vitesse, accélération, vecteurs, forces, gravitation newtonienne, Kepler.
- Spectre lumineux, propagations d'ondes, fréquences et longueurs d'onde.
- Fonctions, équations, limites, dérivées, intégrales, probabilités, repères 2D.
- Comparaison de grandeurs/échelles, axes du temps, graphiques de données.
- Plus tard : simulations N-corps, lentille gravitationnelle approximative explicitée, relativité, diagrammes d'espace-temps ; aucune prétention de fidélité sans références scientifiques et tests numériques.

### 9.3 Exactitude scientifique

Modèles doivent séparer : **schématique** (visuel arbitraire), **modélisation** (hypothèses explicites), **simulation numérique** (algorithme/conditions initiales/erreurs) et **données mesurées** (source, incertitude). Les paramètres physiques sont exprimés avec unités, référentiel, valeur et citation ; afficher avertissements d'échelle. Vérifier dimensions, conservation approximative quand attendue, tests limites et comparaison à solution analytique ou référence. La science reste corrigible : permettre à l'auteur de modifier textes et hypothèses et d'insérer ses propres sources.

### 9.4 Public africain francophone

- Langue française par défaut ; typographies lisibles, exemples accessibles, terminologie compréhensible, vidéos consultables sur téléphone.
- Présets exports raisonnables en taille pour bande passante limitée ; sous-titres et contrastes favorisant diffusion sur écrans variés.
- Personnages, cartes, repères visuels diversifiés sans représentations stéréotypées ; focus sur faits scientifiques universels.
- Calendriers et exemples locaux quand pertinents (ciel observable selon latitude/longitude, événements astronomiques), **jamais** de données de localisation inventées.
- UI hors ligne, ressources de base embarquées sous licences valides, aucune dépendance à un paiement/compte.

---

## 10. Performance, observabilité et expérience matérielle

**Cible initiale indicative** à valider sur machines réelles : PC Windows 11 à CPU ordinaire, RAM 8 à 16 Go, GPU intégré possible, stockage SSD ; meilleur matériel accélère rendus. Ne pas optimiser uniquement pour une station haut de gamme. Mesurer sur profils modestes et documenter les écarts.

- Ouverture d'un projet de 10 scènes et ~100 objets : benchmark de latence après fixture définie.
- Déplacement simple à l'aperçu : objectif perceptuel fluide, mesurer médiane et p95 et limiter les recalculs inutiles.
- Scrubbing à 30 fps : priorité à la réponse de l'UI ; si le rendu lourd ne suit pas, afficher frames proxy et indicator « preview ».
- Mémoire : vérifier croissance après ouvertures/fermetures répétées et exports successifs, éviter cache illimité.
- Processus long : progress bar, journal, annulation, pas de `QApplication.processEvents()` pour masquer un blocage architectural.
- Logs structurés avec niveaux, rotation locale, diagnostic exportable sans identifiants/secrets, exception handler, rapport de crash contrôlé sans télémétrie.
- Périmètre de compatibilité Windows testé : chemins longs/unicode, moniteur HiDPI, changement DPI, FFmpeg avec espace dans path, Windows Defender/SmartScreen (documenter, ne pas contourner).

---

## 11. Plan de phases autonomes — ordre, livrables, critères bloquants

**Règle :** phase = ensemble de lots verticaux courts ; travailler avec tests à chaque lot. L'agent peut poursuivre d'une phase à la suivante **une fois les critères bloquants prouvés**, sans approbation de routine. Ne marquer `DONE` que sur preuves ; `PARTIAL` sinon. Une fonction prévue au futur n'empêche pas de livrer un MVP plus tôt. Garder le dépôt exploitable après chaque lot.

### Phase 0 — Exploration & fondations éprouvées

- Inspecter repository et environnement, identifier licences, versions Python compatibles, dépendances, installation Windows.
- Comparer ManimGL/Manim Community/renderer Qt sur critères et prototypes ; vérifier exports et timings. Vérifier PySide6 + FFmpeg + packaging minimal.
- Rédiger ADR moteur, schéma projet v1, modèle d'évaluation temporelle, matrice risques/licences, artefacts de recherche reproductibles.
- Créer prototype vertical réel (cercle, flèche, texte, mouvement, 5 s de vidéo) et tests de base ; versionner commandes.
- **Gate 0 :** au moins un chemin `project -> évaluation -> export` réellement démontré, dépendances et échecs documentés, pas de mélange d'API Manim. Sinon phase `PARTIAL`; corriger avant de s'engager dans une architecture massive.

### Phase 1 — Socle domaine, UI et persistence

- Python packaging, architecture propre, PySide6 docks, projet nouveau/ouvrir/enregistrer ; validation JSON, IDs, asset paths, sauvegarde atomique, undo/redo ; autosave + recovery minimal.
- **Gate 1 :** création puis réouverture de scène avec conservation exacte de nœuds/états ; corruption détectée sans perte d'ancien projet ; tests domaine + Qt smoke.

### Phase 2 — Éditeur de scène 2D sans code

- Formes, texte, flèches, PNG/SVG, zoom/pan, glisser-déposer, sélection multiple, groupes, calques, inspecteur, alignements et édition visuelle.
- **Gate 2 :** reconstituer depuis l'UI une scène pédagogique d'au moins 10 objets avec couleurs, tailles et labels puis rouvrir ; action undo/redo vérifiée ; tests d'interface headless + vérification Windows.

### Phase 3 — Timeline & presets

- Évaluateur pur de keyframes, interpolation, scrubbing, timeline, durée scène, six presets MVP et boucles ; keyframes éditables, mouvement d'orbite et paramètres.
- **Gate 3 :** animation Terre/Lune 10 s déterministe, frame t=0 / t=5 / t=10 vérifiées, boucle sans saut selon convention ; persistence et commandes UI vérifiées.

### Phase 4 — Pipeline de rendu/export

- Compilation en render plan, gestion FFmpeg, audio minimum, export 720p brouillon / 1080p final, logs/progression/annulation, ffprobe, chemins robustes.
- **Gate 4 :** MP4 test réel (vidéo de référence, résolution, fps, durée et décodage corrects), annulation sans corruption, pas de blocage GUI, frame de rendu conforme à état logique.

### Phase 5 — Bibliothèque d'objets et modèles scientifiques

- Recherche, favoris, provenance, packs d'assets locaux, graphes/axes/vecteurs/formules selon MVP, modèles Lune, comparaison de distances et orbite simple ; avertissements d'échelles.
- **Gate 5 :** parcours P1 « phases de la Lune » exécuté sans code, sauvegardé et exporté, avec provenance scientifique documentée ; inventaire d'assets sans violation de licences.

### Phase 6 — Narration, sous-titres et finition MVP

- Pistes audio, waveform si faisable, marqueurs, fades, SRT/VTT, styles export, templates intro/outro, assistants de création et guide débutant.
- **Gate 6 :** vidéo complète ≥ 2 min (ou durée justifiée si ressource insuffisante) avec narration, sous-titres et crédits ; revue des exports 16:9 sur mobile ; aucune dérive audio/vidéo notable selon métriques.
- **MILESTONE :** version MVP candidate si Gate 0-6 validés et parcours P1 reproductible sur Windows.

### Phase 7 — 3D / Blender facultatif isolé

- Qualifier Blender CLI, modèles GLB/glTF, caméra, lumière et textures conformes ; compositing 2D/3D et animation de planète ; mode de repli si Blender absent.
- **Gate 7 :** planète 3D en rotation, durée identique à timeline, intégrée à séquence 2D + audio ; Blender absent ne bloque pas fonctions 2D ; test de rendu en environnement contrôlé.

### Phase 8 — Simulation & données scientifiques

- Import CSV avec unités, courbes, paramètres scientifiques, modèles numériques (N-corps simplifié ou Kepler), reproductibilité et qualité numérique, annotations des hypothèses.
- **Gate 8 :** simulation numérique comparée à référence/solution et test de conservation/écart ; export explicite avec paramètres, hypothèses et référence scientifique.

### Phase 9 — Optimisation, distribution, stabilité

- Cache/proxies, profilage, ouverture de gros projets, guides, crash recovery, packaging Windows signé si autorisé, installateur, tests smoke clean install, dépendances et licences incluses ; Linux ensuite.
- **Gate 9 :** installer en environnement Windows propre, créer/sauver/ouvrir/exporter et désinstaller sans perdre les projets utilisateur ; inventaire licences et tests perf documentés.

### Phase 10 — Écosystème modulaire (uniquement après maturation)

- Packs de modèles validés, animations avancées, interface Python **sécurisée et optionnelle**, import/export de styles et templates, automatisation de séquences, IA locale optionnelle avec consentement ; extension vers Linux selon preuve technique.
- **Gate 10 :** chaque extension est désactivable, ne compromet pas les projets antérieurs et conserve la compatibilité des tests.

---

## 12. Critères globaux d'acceptation et qualités transversales

La stratégie détaillée est dans [`TEST_STRATEGY.md`](TEST_STRATEGY.md). Aucun lot accepté sans :

- **Fonctionnement fonctionnel observable** (pas uniquement code écrit).
- **Tests verts nécessaires** selon catégorie ; logs et plateforme réels archivés sans secrets.
- **Persistance** : recharger sans changement non expliqué ; migrations compatibles.
- **Rendu** : état temporel cohérent à frames clés ; audio/vidéo vérifiés avec `ffprobe` et décodage quand pertinent.
- **Sécurité** : données projet non exécutées, chemins contrôlés, secrets absents, assets licites.
- **Performance** : au moins relever les mesures sur cas représentatifs ; aucune affirmation sans benchmark.
- **Ergonomie** : parcours de bout en bout réalisé en mode sans code, contrôles visibles et erreurs actionnables.
- **Qualité scientifique** : modèles commentés, unité/échelle, sources.
- **Traçabilité** : changements expliqués, doc, tests, ADR, status, commit, PR réels.

Chaque bug reproduit reçoit un test de non-régression. Aucun « désactiver le test pour passer CI » sans justification explicite. Les tests nécessitant Qt, Windows, ffmpeg, Blender ou GPU sont catégorisés pour ne pas masquer un manque de couverture. Les gates imposent une validation Windows réelle pour les promesses Windows.

---

## 13. Organisation du repository et règles d'intégration

Arborescence **cible**, créer seulement au fur et à mesure :

```text
ANTARES-STUDIO/
  AGENTS.md
  README.md
  pyproject.toml
  .github/workflows/ci.yml
  docs/
    ANTARES_MASTER_PROMPT.md
    RESEARCH_PROTOCOL.md
    TEST_STRATEGY.md
    PROJECT_STATUS.md
    adr/
    research/
    session-logs/
    user-guide/
  src/antares_studio/
    app/          # présentation Qt
    domain/       # objet métier et scènes
    timeline/     # évaluation temporelle
    persistence/  # schéma, migrations, assets
    rendering/    # plan, supervision, backends
    audio/        # narration, mixage
    science/      # modèles, unités, validation
    resources/    # catalogue/licences
  tests/
    unit/
    integration/
    ui/
    visual/
    fixtures/
  examples/
  scripts/
  assets/         # droits de redistribution vérifiés
```

### 13.1 Discipline Git

- Repository unique `https://github.com/Wendsore/ANTARES-STUDIO.git` ; `main` stable.
- Un dossier déjà cloné **ne se réinitialise pas**. Sur dépôt vide, initialiser avec README si nécessaire ; ne pas écraser un historique existant.
- En environnement agent, travailler idéalement en branche `feat/phase-N-sujet` ou `fix/sujet`, push sans `--force`, PR vers `main`, merge uniquement selon règles du propriétaire et protections du dépôt.
- Commits concis et atomiques (`feat`, `fix`, `test`, `docs`, `chore`), liens vers tests/ADR et issues.
- Vérifier `git diff --check`, état de branche, fichiers sensibles, gitignore, format et tests avant push.
- Ne pas utiliser de token GitHub dans code/config ; identité déjà connectée, credential manager ou application authentifiée.
- Fournir le hash réel des commits et URLs uniquement après succès confirmé.

### 13.2 Fichiers de suivi

- `docs/PROJECT_STATUS.md` : vérité sur phase, tâches, limites et prochaine action.
- `docs/session-logs/YYYY-MM-DD-<session>.md` : faits observés, commandes/tests et décisions.
- `docs/adr/0001-*.md` : décisions techniques importantes et alternatives.
- `docs/research/YYYY-MM-DD-*.md` : ressources consultées, versions et conclusions.
- `CHANGELOG.md` : évolutions effectives et versions, non fonctions simplement prévues.
- `docs/user-guide/` : tutoriels réellement validés.

### 13.3 Gestion des versions et composants

Choisir version Python, PySide6, Manim, FFmpeg, Blender et leurs contraintes après tests ; figer dépendances avec lock reproductible quand viable. Éviter « dernière version » dans recettes fixes. Définir matrices Windows/Linux, CPU/GPU et absence d'outil ; plan de mise à jour et rollback. CI minimal sur Linux pour pure Python + tests doc et outils présents ; CI Windows pour UI/packaging autant que possible. Les étapes GPU/3D lourdes peuvent être nightly/manuelles mais DOIVENT être réelles avant promesse utilisateur.

---

## 14. Consignes de comportement de l'agent et prise de décision

### Tu dois

1. Explorer dépôt existant et contexte à chaque démarrage ; ne pas recréer sans inspection.
2. Avancer par étapes verticales autonomes, implémenter en priorité un parcours fonctionnel, tenir `main` stable.
3. Chercher des sources officielles actuelles avant dépendance majeure, relever licence et contraintes Windows ; tester un PoC.
4. Mesurer au lieu d'imaginer ; consigner incertitudes et alternatives dans ADR.
5. Écrire tests conjointement au code, passer les gates, corriger avant nouvelle fonctionnalité.
6. Respecter sécurité, licences des médias et vie privée ; aucun coût récurrent imposé.
7. Produire un mini-livrable vérifiable à chaque session et expliquer les limites réelles.
8. Réutiliser les APIs publiques et conserver le format de projet indépendant des moteurs.
9. Tenir la documentation, la progression et les risques à jour pour un agent repreneur.
10. Si tu as du temps restant et aucune condition bloquante, lancer la prochaine tâche prioritaire : ne pas finir par « veux-tu que je continue ? ».

### Tu ne dois pas

- Déclarer une fonction « opérationnelle » sans test sur environnement adapté.
- Installer à l'aveugle une chaîne lourde, peu compatible ou juridiquement problématique.
- Mélanger `manim` et `manimgl` comme s'ils étaient un paquet unique.
- Démarrer la 3D avancée avant la viabilité du montage 2D.
- Utiliser un serveur/cloud/API payante comme prérequis.
- Coller toute la logique dans un unique fichier gigantesque, coupler sérialisation à Qt, ou exporter par capture aléatoire du canvas.
- Supposer le rendu WYSIWYG sans comparaison.
- Faire semblant d'avoir testé Windows depuis Linux ; prétendre qu'un commit a été poussé sans confirmation.
- Supprimer fichiers utilisateur, forcer des pushes, publier vidéos ou changer la licence sans accord.
- Demander des clarifications facultatives pour éviter de travailler ; choisir défaut raisonnable, consigner et continuer.

### Critères d'escalade au propriétaire

Escalader uniquement en cas de : dépense/abonnement, changement juridique/licence, risque sérieux de perte de données, suppression/force push, publication au nom de l'utilisateur, accès manquant bloquant, décision de produit irréversible avec impact important. Pour une alternative technique réversible, prendre une décision documentée et poursuivre.

---

## 15. Première mission exécutable immédiatement

**DÉMARRER PHASE 0, PUIS CONTINUER SELON LES GATES.**

1. Vérifier URL du dépôt, état Git, fichiers, branche et historique sans `git init` intempestif ; lire toutes les instructions.
2. Produire environnement minimal reproductible ; détecter OS/Python/Qt/FFmpeg ; ne pas prétendre avoir exécuté Windows si ce n'est pas le cas.
3. Rechercher et comparer ManimGL, Manim Community et rendu Qt ; versions/installations/licences ; choisir un expérimentation qui isole les dépendances.
4. Prototyper cercle, flèche, texte et une orbite sur 5 secondes ; mesurer temps de rendu et visualiser sortie réelle quand accessible.
5. Concevoir schéma projet et évaluation `frame → state`, tests de sérialisation et keyframes ; faire export test réel.
6. Produire ADR n° 0001, sources, commandes, tests et état du projet. Si Gate 0 passe, engager le premier lot Phase 1 **sans attendre un nouveau prompt**.
7. À chaque session suivante, reprendre `docs/PROJECT_STATUS.md` et poursuivre le prochain lot, tant que la session et les accès le permettent.

**Définition du succès final :** un créateur peut fabriquer une vidéo de science convaincante, l'enregistrer, la rouvrir et l'exporter depuis une UI en français, sur sa machine, de façon fiable et sans programmer chaque animation. Le logiciel appartient fonctionnellement à son utilisateur ; les animations restent reproductibles, compréhensibles et réutilisables.
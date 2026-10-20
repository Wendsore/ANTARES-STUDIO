# ANTARES Studio — Stratégie de qualité, tests et gates de livraison

**État :** plan normatif pour l'agent ; les cas ci-dessous sont des **tests à implémenter**, pas des tests applicatifs déclarés comme réussis. À chaque phase, les transformer en tests exécutables et conserver la preuve du résultat.

## A. Politique de preuve et matrice d'exécution

Chaque test/report doit contenir identifiant, fonctionnalité, niveau, plateforme, environnement exact, commande, jeu d'entrée, résultat attendu/observé, statut `PASS | FAIL | SKIP | XFAIL | NOT_RUN`, durée quand mesurée, commit associé et lien éventuel à un artefact. `SKIP` ne vaut pas `PASS`. Les **tests Windows réels** sont requis avant d'annoncer une compatibilité Windows éprouvée. Les mocks suffisent pour isoler un composant, mais pas pour démontrer un export vidéo, un décodage ou une installation.

**Pyramide :** domaine pur (rapides, nombreux) → adaptateurs/intégration (FFmpeg, SVG, audio, moteurs) → UI (pytest-qt ou Qt Test) → end-to-end réelle sur Windows → visuels/AV + benchmarks + packaging. Séparer suites `fast`, `integration`, `ui`, `render`, `slow`, `windows`, `gpu`, `packaging`, `security` avec marqueurs adaptés quand le code sera créé.

**Commandes cibles** (à implémenter via `pyproject.toml`, ne pas présenter comme actuellement disponibles) :

```bash
python -m pip install -e '.[dev]'
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest -q tests/unit
python -m pytest -q tests/integration -m 'not gpu'
python -m pytest -q tests/ui
python -m pytest -q tests/visual
python -m pytest -q tests/security
python -m pytest -q tests/e2e
```

### Gate de CI par niveau

- **Sur chaque PR :** contrôles statiques, tests unitaires et d'intégration disponibles, tests sauvegarde/timeline, UI smoke headless quand fiable, scan secrets/dépendances/licences configurés, `git diff --check`, doc links minimum.
- **Sur Windows réel / release candidate :** création/édition/sauvegarde/rechargement, render engine effectif, FFmpeg/ffprobe, audio/sous-titres, installer + désinstaller, DPI/Unicode/chemins.
- **Nightly/manuel si charge trop élevée :** rendus HD longs, Blender, 3D/GPU, résistance mémoire, benchmark PC faible, tests scientifiques longs.
- **Conditions de merge :** PR passant les checks disponibles, pas d'erreur de sécurité critique, documentation de toute limitation. Ne pas merger si tests critiques applicables sont rouges, même si des tests d'un autre groupe passent.

## B. Catalogue de tests par composant

### B1 — Modèle de scène, sérialisation et persistence

| ID | Cas | Critère vérifiable |
|---|---|---|
| MOD-01 | Créer 100 objets variés et IDs | IDs uniques, hiérarchie valide, propriétés typées |
| MOD-02 | Sérialisation round-trip | `deserialize(serialize(p))` équivalent selon comparaison canonique |
| MOD-03 | Sauvegarde atomique | Ancien projet lisible si interruption simulée avant remplacement |
| MOD-04 | Ouverture projet corrompu | Erreur expliquée ; aucun écrasement ni exécution arbitraire |
| MOD-05 | Migration N → N+1 | Backup créé ; valeurs et références préservées |
| MOD-06 | Asset relatif et répertoire déplacé | Réouverture portable sans chemin absolu de machine |
| MOD-07 | Fichier manquant | Placeholder/erreur explicite ; pas de crash |
| MOD-08 | Undo/redo création, suppression, déplacement | État exactement restauré, y compris keyframes |
| MOD-09 | Autosave et recovery | Restauration du dernier autosave valide, choix de conserver original |
| MOD-10 | Conflit/corruption de schéma | Rejet avec diagnostic et sans altérer les données |
| MOD-11 | Cas limite chemins Unicode/espaces Windows | Projet sans perte d'assets ni erreur de parsing |
| MOD-12 | Hiérarchie cyclique | Cycle détecté et rejeté, pas de récursion infinie |

### B2 — Timeline mathématique

| ID | Cas | Critère vérifiable |
|---|---|---|
| TIM-01 | Interpolation linéaire 0→10 | À mi-durée la valeur est 5 avec tolérance numérique définie |
| TIM-02 | Cadence 300 frames à 30 fps | Temps canonique cohérent ; total exact attendu |
| TIM-03 | Keyframe même frame | Politique de collision stable/documentée |
| TIM-04 | Boucle et ping-pong | Valeurs de jointure cohérentes, pas de saut non prévu |
| TIM-05 | Ease-in/out | Monotonie et bornes suivant easing choisi |
| TIM-06 | Angles | 350°→10° suit politique `shortest arc` ou explicite |
| TIM-07 | Orbite 360° | Position initiale/finale correcte, échantillons cardinaux vérifiés |
| TIM-08 | Scrub t1,t2,t1 | Même état à t1 (pureté/déterminisme) |
| TIM-09 | Ordre de keyframes permuté | Résultat invariant après normalisation |
| TIM-10 | Valeurs invalides | NaN/inf, négatif, unité invalide rejetés ou normalisés explicitement |
| TIM-11 | Dépendances parent/target | Résolution stable ; cycles protégés |
| TIM-12 | Keyframes sauvegardés/rechargés | Résultat identique aux frames clés |

### B3 — Interface de montage et accessibilité

| ID | Cas | Critère vérifiable |
|---|---|---|
| UI-01 | Nouveau projet et assistant | Paramètres visibles et enregistrés |
| UI-02 | Glisser objet sur scène | Objet visible, sélectionné, inspecteur correct |
| UI-03 | Déplacement, échelle, rotation | Valeurs inspecteur et modèle synchrones |
| UI-04 | Multi-sélection/groupes/calques | Pas de perte de sélection ou transformation |
| UI-05 | Raccourcis clavier | Sauver, ouvrir, undo, redo, duplication, lecture |
| UI-06 | Timeline keyframe + lecture | Changement observable au temps t ; UI reste responsive |
| UI-07 | Accueil et modèle P1 | Écran de départ compréhensible sans Python |
| UI-08 | Fermeture modifications non sauvegardées | Avertissement approprié, pas de perte silencieuse |
| UI-09 | Contrôles via clavier | Parcours essentiels sans souris ; focus visible |
| UI-10 | DPI 100/150/200 %, thème | Aucun contrôle critique hors écran ou illisible |
| UI-11 | Textes FR/accentués | Pas de corruption encodage, rognage ni glyphes manquants |
| UI-12 | Panneau masqué/restauré | Layout réinitialisable et persisté |
| UI-13 | Cliquer exporter, progression et annuler | Pas de gel pendant tâches longues ; feedback clair |

### B4 — Rendu visuel, fidélité et déterminisme

| ID | Cas | Critère vérifiable |
|---|---|---|
| REN-01 | Export 5 s/30 fps | Durée/framerate/frames cohérents avec `ffprobe` |
| REN-02 | 1080p/720p | Résolution réelle conforme au profil |
| REN-03 | Image clé aux frames 0, 75, 149 | État logique et position/opacité visuelle cohérents |
| REN-04 | Test PNG géométrie simple | Similarité pixel/SSIM tolérancée selon environnement |
| REN-05 | Ordre Z et transparence | Superpositions, alpha et couleurs respectés |
| REN-06 | Chemins avec accents, espaces | Export et ffprobe réussis sur Windows |
| REN-07 | FFmpeg/codec absent | Message utile, aucun crash ni fichier final fictif |
| REN-08 | Annulation à 50 % | Processus terminé, fichier antérieur intact |
| REN-09 | Disque insuffisant | Erreur actionnable, sauvegarde projet intacte |
| REN-10 | Version moteur incompatible | Détection avant export, pas de rendu silencieusement faux |
| REN-11 | Batch rendu 10 fois | Pas de fuite mémoire importante et résultats conformes |
| REN-12 | MP4 décodabilité réelle | Lecture via FFmpeg/ffprobe et sondage d'images, pas seulement existence du fichier |

### B5 — Audio, sous-titres et narration

| ID | Cas | Critère vérifiable |
|---|---|---|
| AUD-01 | Import WAV mono/stéréo | Métadonnées et durée correctes |
| AUD-02 | Import MP3 | Compatibilité codec validée, erreur sinon |
| AUD-03 | Audio offset 1.2 s | Décalage audible/mesurable au rendu |
| AUD-04 | Fondu de gain | Enveloppe de volume conforme aux valeurs |
| AUD-05 | Longueur vidéo vs audio | Pas de dérive > seuil validé selon durée de fixture |
| AUD-06 | Sous-titres UTF-8 SRT/VTT | Accents/horodatages préservés |
| AUD-07 | Sous-titres chevauchés | Diagnostic ou règle de conflit documentée |
| AUD-08 | Safe zones 16:9 et 9:16 | Sous-titres lisibles dans gabarits pris en charge |
| AUD-09 | Import multimédia invalide | Pas d'exécution ni crash, erreur explicite |

### B6 — Ressources, packs et conformité

| ID | Cas | Critère vérifiable |
|---|---|---|
| AST-01 | Import SVG/PNG valides | Aperçu et export avec proportions respectées |
| AST-02 | SVG hostile/complexe | Limites mémoire/temps et sanitation ; pas de script exécuté |
| AST-03 | Asset sans provenance | Avertissement ou refus dans pack redistribuable |
| AST-04 | Import pack ZIP traversal | Pas d'écriture hors destination |
| AST-05 | Tags/recherche/favoris | Résultats déterministes et persistance |
| AST-06 | Licences de tiers | Rapport auteur/URL/licence/attribution fidèle |
| AST-07 | Modèle 3D absent/non conforme | Pas de crash 2D, message explicite |

### B7 — Sciences et exactitude

| ID | Cas | Critère vérifiable |
|---|---|---|
| SCI-01 | Conversion m/km/UA | Résultats selon référence SI et tolérance |
| SCI-02 | Détection d'unité incohérente | Diagnostic plutôt que combinaison physique absurde |
| SCI-03 | Orbite circulaire simplifiée | Rayon constant et angle attendu pour cas test |
| SCI-04 | Kepler / trajectoire | Cas analytique ou référence validée |
| SCI-05 | Simulation stabilité du pas | Convergence et erreur documentées |
| SCI-06 | Grandeurs extrêmes | Pas de NaN/overflow non diagnostiqué |
| SCI-07 | Présentation non à l'échelle | Avertissement présent et exporté selon template |
| SCI-08 | Provenance des constantes | Sources et unités affichées dans métadonnées |

### B8 — Sécurité, résilience, distribution

| ID | Cas | Critère vérifiable |
|---|---|---|
| SEC-01 | Fichier projet avec expression exécutable | Aucun `eval/exec` implicite |
| SEC-02 | Path traversal absolu/relatif | Rejet des accès hors racine autorisée |
| SEC-03 | Sous-processus FFmpeg | Arguments sous forme liste sans injection shell |
| SEC-04 | Logs | Aucun secret/token et aucune donnée sensible inutile |
| SEC-05 | Scan dépendances/licences | Rapport conservé, incompatibilités bloquantes traitées |
| SEC-06 | Annuler import/rendu | Nettoyage ciblé, processus enfant arrêté |
| SEC-07 | Plusieurs sauvegardes concurrentes | Sérialisation/lock ou protection contre écrasement |
| SEC-08 | Crash et redémarrage | Restauration d'un projet valide |
| PKG-01 | Installer Windows neuf | Lancement sans environnement Python préinstallé si promesse produit |
| PKG-02 | Assets/FFmpeg/Qt embarqués ou détectés | Diagnostic clair si dépendance manquante |
| PKG-03 | Désinstaller | Les projets personnels restent conservés |
| PKG-04 | Linux futur | Démarrage et tests réels avant affichage « supporté » |

## C. Tests de parcours (E2E) véritables

### E2E-01 — Vidéo « phases de la Lune », sans code

**Prérequis :** build Windows du logiciel, moteurs nécessaires correctement installés, assets libres locaux, voix synthétique/test locale générée par les tests. **Actions :** nouveau projet 1920×1080 30 fps ; insérer trois objets célestes ; associer boucle orbitale ; textes « Soleil / Terre / Lune » ; déplacer/retimer ; import voix ; sous-titres ; sauvegarder ; quitter ; relancer ; ouvrir ; exporter MP4. **Assert :** mêmes paramètres et keyframes avant/après ; durée vidéo correcte ; au moins trois images de référence conformes ; audio présent et synchrone ; sous-titres corrects si phase correspondante atteinte ; UI non bloquée ; erreurs absentes. Conserver script d'automatisation, logs, vidéo courte de référence et version testée. Ne pas produire une vidéo de 2 minutes en CI PR si coût disproportionné ; réserver au job long.

### E2E-02 — Comparaison d'échelles

Créer un modèle « année-lumière » avec graphes et texte ; modifier vitesse et couleurs ; effectuer undo/redo ; sauver/ouvrir ; export ; confirmer unité et source affichées. Contrôler spécifiquement accentuation et typographies sur Windows.

### E2E-03 — Import et erreurs

Ouvrir projet avec image absente et une seconde référence malformée ; l'UI doit rester utilisable, proposer une réparation et ne jamais détruire la sauvegarde d'origine. Lancer rendu sans ffmpeg, confirmer diagnostic et reprise après installation.

### E2E-04 — Longue séance de montage

Ouvrir 20 projets en succession et modifier 100 objets dans un projet ; zoom/scrubbing rapide, plusieurs undo/redo, puis export ; mesurer CPU/RAM et temps UI ; relever p50/p95 sur machine déclarée, sans confondre métrique et cible.

### E2E-05 — 3D (phase 7)

Désactiver Blender : montage 2D intact. Réactiver Blender compatible : importer planète GLB libre, animer 360°, exporter 2D+3D+audio. Vérifier temps et correspondance timeline.

## D. Stratégie des golden images et de l'audio

- Enregistrer **fixtures synthétiques déterministes** de petite taille et image attendue des propriétés logiques.
- Comparer images PNG pour rendus de référence, avec tolérances documentées sur chaque plateforme (MAE, SSIM ou perceptual delta quand justifié). Ne pas comparer deux MP4 compressés par hash binaire.
- Exécuter `ffprobe` pour flux, dimensions, fps, durée, encodeur, timebase, puis `ffmpeg -f null -` pour vérifier décodabilité ; calculer éventuellement bruit/audio silence et décalage sur signal de test.
- Tous les tests nécessitant ressources externes sont marqués pour assurer des skips **visibles** dans le rapport.
- Si rendu modifié volontairement, documenter motif, image avant/après, approbation et mise à jour des références ; ne pas accepter les goldens automatiquement.

## E. Benchmarks et seuils à définir sur preuves

Établir baselines locales et CI : démarrage à froid, ouverture 10 scènes/100 objets, latence drag, scrub frames par seconde, temps export 5 s 720p, RAM avant/après 10 exports, consommation sans GPU. Spécifier hardware (CPU, RAM, OS, GPU), versions, médias fixtures. Fixer ensuite des budgets réalistes par ADR ; régression > budget échoue ou déclenche alerte documentée. Aucun chiffre de vitesse « garanti » sans mesure.

## F. Gates par phase (renvoi au master prompt)

| Gate | Obligations minimales pour `DONE` |
|---|---|
| 0 | Sources + ADR + PoC export réel + tests préliminaires |
| 1 | MOD-01/02/03/04/08, Qt smoke, reopen projet |
| 2 | UI-01 à UI-05 et 10 objets 2D sans code |
| 3 | TIM-01/02/04/07/08/12 et test visuel animation orbite |
| 4 | REN-01/02/03/07/08/12 et parcours export fonctionnel |
| 5 | AST-01/03/06, SCI-07/08, P1 complet sans code |
| 6 | AUD-01/03/05/06, sortie avec narration, sous-titres et crédits |
| 7 | E2E-05, Blender absent et présent, cohérence temporelle |
| 8 | SCI-01 à SCI-06 selon fonctionnalités réellement livrées |
| 9 | PKG-01/02/03, Windows E2E, benchmarks/rapport licences |
| 10 | Isolation extensions, migration et tests de compatibilité |

Un gate ne peut pas être déclaré `DONE` si une obligation est non exécutée ou `SKIP` sans dérogation explicite de portée limitée et visible ; **ne jamais transformer les tests futurs en validations présentes**.

## G. Compte rendu type d'une exécution

```markdown
# RUN — AAAA-MM-JJ HH:MM UTC — commit <sha>
Plateforme : Windows 11 build XYZ / Ubuntu XX — CPU/RAM/GPU.
Python / Qt / FFmpeg / Manim / Blender : versions réellement interrogées.
Commandes : `...`
Tests : pass N / fail N / skip N / xfail N / non exécutés N.
Extraits significatifs des logs et chemin des artefacts, sans secrets.
Différences visuelles, audio et vidéos (durée/fps/résolution réels).
Gate : PASS/PARTIAL/FAIL ; blocages ; issue/PR ; prochaine action.
```

## H. Tests continus et autonomie

L'agent doit programmer lui-même ces tests au fur et à mesure de la construction, installer un CI adapté, analyser ses échecs et corriger avant de poursuivre. **Pas de tests « verts » purement simulés** pour des features non codées. Ne pas installer un runner ou GPU payant sans accord ; réduire les fixtures et déplacer les charges lourdes en nightly si nécessaire, sans masquer les exigences avant release.
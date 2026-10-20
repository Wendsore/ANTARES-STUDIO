# AGENTS.md — Contrat de travail des agents ANTARES Studio

Tu es l'agent de réalisation de **ANTARES Studio**. Les consignes de ce fichier sont opérationnelles et persistantes ; les détails fonctionnels, critères et phases sont dans `docs/ANTARES_MASTER_PROMPT.md`. Travaille dans le dépôt officiel `Wendsore/ANTARES-STUDIO` uniquement.

## Mission

Produire un logiciel local de bureau réellement utilisable pour fabriquer facilement des vidéos scientifiques de qualité : édition visuelle, objets, mouvements, animation, narration, export, puis 3D/simulation. L'utilisateur dispose de peu de temps. Optimise les interactions, la réutilisabilité et la stabilité. **La première vidéo utilisable est prioritaire sur la couverture fonctionnelle exhaustive.**

## Démarrage de chaque session, sans exception

1. Inspecte `pwd`, `git status --short`, `git branch --show-current`, `git remote -v` ; vérifie que le dépôt est le bon avant tout push.
2. Lis `README.md`, ce fichier, `docs/ANTARES_MASTER_PROMPT.md`, `docs/TEST_STRATEGY.md`, `docs/RESEARCH_PROTOCOL.md`, `docs/PROJECT_STATUS.md`, les ADR et les journaux de tests existants.
3. Inspecte les répertoires réellement présents et les fichiers modifiés ; ne suppose pas l'existence de modules annoncés dans la documentation.
4. Choisis le **prochain plus petit lot vertical** selon la phase en cours, les dépendances et les tests qui échouent ; rédige les critères mesurables avant d'implémenter.
5. Exécute les vérifications possibles localement ; distingue tests exécutés, ignorés, indisponibles et échoués.
6. Mets à jour l'état du projet, notes de session, ADR, risques, documentation, commandes et tests ; commits atomiques sur une branche de travail et PR si disponible.

## Cycle autonome obligatoire

**Observer → rechercher → comparer → décider → expérimenter → implémenter → tester → corriger → documenter → publier → poursuivre.**

- Réalise les étapes successives **sans attendre une approbation humaine de routine**. Si une phase réussit ses critères, poursuis la suivante avec un nouveau lot limité.
- Recherche d'abord les documents officiels et sources primaires. Consigne URL, version, date de consultation, enseignement et reproduction d'expérience dans `docs/research/` (à créer au besoin).
- Crée un mini-prototype pour chaque dépendance/moteur critique (Windows, packaging, export, mix 2D/3D, formules) avant une intégration coûteuse.
- Documente les alternatives et compromis par ADR. Une décision réversible ne justifie pas d'arrêter le travail.
- Si tu rencontres un échec : reproduis, réduis le cas, diagnostique, corrige, ajoute un test de non-régression, recommence. Ne contourne jamais un test par suppression du test.
- Pour chaque livrable, prouve qu'une fonctionnalité est observable depuis l'interface, enregistrable, rechargeable et exportable selon son périmètre.
- Si la session doit se terminer, laisse le dépôt dans un état exploitable avec une prochaine action précise, pas une affirmation vague.

## Autorisations / limites d'autonomie

**Autorisés :** lecture et recherche publiques, essais techniques locaux, ajout/édition de code, doc et tests, installation de dépendances libres dans un environnement isolé conforme au projet, exécution des tests/rendus de démonstration, création de branches, commits, PR, mises à jour non destructrices.

**Ne pas faire sans consentement explicite :** dépense/abonnement, achat API ou média, divulgation d'informations privées, publication externe d'une vidéo au nom de l'utilisateur, changement de visibilité du dépôt, effacement de données utilisateur, réécriture d'historique, `push --force`, suppression de branche partagée, release publique, activation de télémétrie, téléchargement/exécution de binaires non vérifiés, changement de licence juridique. Ne jamais stocker de secrets dans Git.

**Blocage :** si des permissions, une licence ambiguë, un choix financier ou une action destructive empêchent la suite, ouvre/actualise une issue ou consigne `BLOCKED` dans `docs/PROJECT_STATUS.md`, cite le fait exact, la commande et l'impact, puis traite une autre tâche indépendante si possible. Ne simule jamais une action indisponible.

## Règles techniques

- Python avec typage et isolation de l'interface Qt de la logique métier. Cœur de scène pur testable **sans Qt** ; moteurs de rendu/adaptateurs en processus externes ou frontières claires.
- Prévisualisation différente du rendu final, mais évaluateur temporel commun. **Aucun `eval`/`exec` de contenu de projet non fiable**, scripts Python d'utilisateur désactivés par défaut et traités comme code exécutable seulement avec consentement clair.
- IDs stables, schéma de projet versionné, opérations undo/redo, sauvegarde atomique, autosave distinct, récupération après crash, références d'assets relatives avec protections contre traversées de chemin, migration et sauvegarde préalable.
- Pas de réseau nécessaire à la création ou à l'export ; aucune télémétrie ou compte obligatoire. Prévoir fonctionnement sans GPU adapté via solution de repli documentée.
- Moteur ManimGL demandé comme piste privilégiée **à évaluer objectivement** ; ne pas lui imposer la prévisualisation temps réel sans mesures. Comparer Manim Community. Dépendances optionnelles gardées séparées. Blender uniquement après MVP.
- Séparer fidélité scientifique et schéma pédagogique : unités, échelles, hypothèses, limites, source. Pas de simulation affichée comme exacte si elle ne l'est pas.
- Aucune image, police, icône, musique ou texture tiers sans fiche de provenance/licence et vérification de redistribution. Utiliser des ressources synthétiques générées localement dans les tests.

## Tests et preuves

- Respecte `docs/TEST_STRATEGY.md` ; introduis tests unitaires et d'intégration avec la fonctionnalité correspondante.
- Minimum pour un lot : format/lint/type-check selon étape, tests ciblés, tests de régression, test de sauvegarde/réouverture pour objets, test de rendu sur frames clés pour animation, test UI de l'action critique si UI touchée.
- Vérifie les comportements négatifs : fichier corrompu, codec manquant, asset absent, chemin invalide, annulation, erreur moteur, espace disque réduit, échelle/unité incorrecte, migration d'ancienne version.
- Tests visuels basés sur images de référence versionnées **et** tolérances raisonnées ; hashes stricts seulement sur sorties déterministes de modèle, pas sur MP4 soumis aux variations du codec.
- N'invente **jamais** un test réalisé sur Windows, un benchmark ou une action GitHub. En CI Linux seule, indique que la validation Windows reste à faire jusqu'à un runner Windows réel.

## Definition of Done (DoD)

Un lot ne passe en `DONE` que lorsque : critères d'acceptation atteints, preuves exécutées et horodatées, tests passés ou limitation explicitement enregistrée, aucune régression critique, documentation et migration à jour, aucun secret/asset illégal, état du dépôt propre et commits traçables. Une phase ne passe en `DONE` que si tous ses critères bloquants sont vérifiés. Sinon `PARTIAL` ou `BLOCKED`.

## Rapport de fin de session — format

- Phase/lot et objectif ; décisions avec sources et ADR.
- Fichiers modifiés, comportement concret observable, commandes exactes de lancement.
- Tests exécutés : commandes, plateforme, nombre passé/échoué/ignoré, artefacts et échecs connus.
- Performance/mémoire si mesurées, sans estimation inventée.
- Branche/commit/PR et état réel des opérations distantes.
- Risques, bloqueurs, prochaine action exécutable de taille raisonnable.

## Sources prioritaires

Voir `docs/RESEARCH_PROTOCOL.md`. En cas de contradiction, les consignes de sécurité et instructions explicites du propriétaire prévalent ; consigner toute adaptation. **Lire le code et l'état réel avant de croire les résumés.**
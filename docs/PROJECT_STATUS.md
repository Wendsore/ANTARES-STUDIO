# ANTARES Studio — État opérationnel

Dernière mise à jour : 2026-10-20 (initialisation documentaire).

## Situation réelle

- **Phase active : 0 — vérification d'architecture et prototypes de faisabilité.**
- **Logiciel développé : non.** Les fichiers initiaux sont des consignes et référentiels, pas un MVP.
- **Tests exécutés :** vérification documentaire locale lors de l'initialisation ; renseigner le résultat de chaque exécution dans les comptes rendus.
- **Validations Windows 11 :** non exécutées.
- **Moteur final :** non sélectionné ; comparaison ManimGL / Manim Community / moteur de rendu 2D à effectuer.
- **Licence du code ANTARES :** non choisie.

## Prochaines actions ordonnées

1. Lire le contrat d'agent et le master prompt ; créer `docs/adr/`, `docs/research/`, `docs/session-logs/`.
2. Inventorier environnement Python, Qt, FFmpeg, moteurs disponibles, pilotes GPU, et tester la compatibilité sous Windows 11.
3. Comparer prévisualisation native Qt, génération ManimGL, Manim Community et autres alternatives ; mesurer latence de scrubbing et coût du rendu.
4. Dessiner le premier schéma JSON du projet et un évaluateur pur au temps `t` (avec tests sérialisation et interpolation).
5. Produire le prototype vertical : cercle, flèche, texte, deux animations, rendu MP4 via FFmpeg ; exécuter les tests d'intégration correspondants.
6. Écrire ADR et recommandations, choisir le moteur du MVP sur preuves, commencer la Phase 1 sans attente de validation de routine.

## Journal des sessions

| Date (UTC) | Agent / environnement | Phase / lot | Tests réellement exécutés | Statut | Lien commit/PR |
|---|---|---|---|---|---|
| 2026-10-20 | Initialisation documentaire | Phase 0 : instructions | Voir messages/CI après dépôt | OPEN | À compléter |

## Suivi des problèmes

| ID | Priorité | État | Problème | Prochaine action |
|---|---|---|---|---|
| R-001 | Haute | OPEN | Choix de moteur sans benchmark local | Prototype et ADR |
| R-002 | Haute | OPEN | Distribution Windows / FFmpeg / licences | Vérifier chaînes de licences et packaging |
| R-003 | Haute | OPEN | Cohérence prévisualisation ↔ export | Modèle temporel unique + tests |
| R-004 | Moyenne | OPEN | Ressources éditoriales libres et attribuables | Inventaire et outil de crédits |

## Format de mise à jour

Ajoute une ligne au journal par session, ne supprime pas les anciens résultats, et mets à jour les actions et risques. Si un résultat manque, écris `NON TESTÉ`, et non `OK`.
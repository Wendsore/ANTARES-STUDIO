# Guide 1 — Votre première vidéo

Ce guide est désormais **dans le logiciel** : `Aide > Centre d'aide` (F1), rubrique « Parcours complet :
votre première vidéo », et `Aide > Tutoriels` pour l'apprendre pas à pas. La source unique est
`src/antares_studio/resources/help/premiere-video.md` (lisible aussi dans le dépôt) ; voir ADR-0005.

## Tutoriels intégrés et leur validation

Chaque étape se valide automatiquement quand l'action est réellement faite dans l'interface.

| Tutoriel | Étapes | Ce qui est prouvé par les tests |
|---|---|---|
| 1. Découvrir l'espace de travail | 8 | aucune étape validée sans action (`tests/unit/test_help_content.py`) ; zones « Montre-moi » présentes (`tests/ui/test_help_ui.py`) ; parcours complet NON joué automatiquement |
| 2. Créer votre première scène | 10 | parcours complet joué étape par étape dans la fenêtre réelle (`test_tutorial_premiere_scene_walkthrough`) |
| 3. Animer sans programmer | 7 | aucune étape validée sans action ; parcours complet NON joué automatiquement |
| 4. Ajouter la voix et les sous-titres | 6 | aucune étape validée sans action ; parcours complet NON joué automatiquement |
| 5. Une scène scientifique rigoureuse | 8 | aucune étape validée sans action ; import des données d'exemple avec provenance testé ; parcours complet NON joué automatiquement |
| 6. Images, provenance et crédits | 4 | aucune étape validée sans action ; parcours complet NON joué automatiquement |
| 7. Exporter la vidéo | 3 | aucune étape validée sans action ; parcours complet NON joué automatiquement |

Validé sur Linux le 2026-10-22 ; à confirmer sur Windows 11.

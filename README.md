# ANTARES Studio

**Scientific Animation & Storytelling Studio** — logiciel de bureau de création de vidéos scientifiques 2D/3D, visuel, local et extensible, conçu notamment pour la vulgarisation de l'astronomie, de l'astrophysique, des mathématiques et de la physique en français auprès d'un public africain francophone.

> **État au démarrage :** dépôt de cadrage et d'orchestration de développement. La présence de documents ne signifie PAS que l'application ou ses tests fonctionnels sont implémentés.

## Point d'entrée pour l'agent

1. Lire [`AGENTS.md`](AGENTS.md) en entier.
2. Lire [`docs/ANTARES_MASTER_PROMPT.md`](docs/ANTARES_MASTER_PROMPT.md), référentiel produit et plan de développement.
3. Lire [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md) et [`docs/RESEARCH_PROTOCOL.md`](docs/RESEARCH_PROTOCOL.md).
4. Lire et mettre à jour [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) à chaque session.
5. **Démarrer la Phase 0**, produire les preuves de faisabilité, puis poursuivre de façon autonome dans les limites indiquées dans `AGENTS.md`.

## Principes du produit

- Création sans code pour les usages courants ; contrôle Python avancé optionnel.
- Prévisualisation interactive fluide, timeline réversible, sauvegarde portable et rendu déterministe.
- Windows 11 prioritaire, Linux à terme, fonctionnement hors ligne, sans abonnement obligatoire.
- Un format de projet indépendant des moteurs ; intégrations Manim Community/ManimGL/Blender **à qualifier et isoler**, pas de mélange implicite d'API.
- Ressources visuelles, audio et scientifiques sous licences documentées ; pas de téléchargement silencieux.
- Priorité au **premier parcours utilisable de bout en bout**, plutôt qu'à l'accumulation de fonctionnalités inachevées.

## Dépôt

Dépôt officiel : https://github.com/Wendsore/ANTARES-STUDIO

Au stade du cadrage, les contrôles vérifient la cohérence documentaire. Les tests d'interface, de rendu, de montage et de distribution devront être implémentés et exécutés au fur et à mesure du développement ; voir la stratégie de tests.

## Licence

**À décider explicitement avant publication de code sous licence.** Ne pas présumer que ce dépôt ou ses futurs contenus sont déjà sous une licence open source déterminée. La distribution des binaires et des composants tiers devra faire l'objet d'un inventaire et d'une revue de conformité.
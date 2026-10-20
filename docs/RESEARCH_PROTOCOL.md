# Protocole de recherche technique et scientifique — ANTARES Studio

## Recherche indépendante obligatoire

Pour toute décision structurante (moteur, UI, rendu, format 3D, sécurité, codec, packaging, simulation), l'agent doit :

1. Formuler une question vérifiable et les critères (ergonomie, coût, maturité, licences, performance, distribution Windows, reproductibilité et mode hors ligne).
2. Rechercher prioritairement documentation officielle, dépôt source, changelog/releases, API, licences et issues mainteneurs. Utiliser discussions techniques tierces comme signaux, jamais comme uniques preuves.
3. Vérifier la date de publication **et** la version réellement testée ; ne jamais confondre tutoriel ancien et API actuelle.
4. Confronter au moins deux options raisonnables, dont le statu quo/minimal viable ; si une seule option existe, justifier.
5. Réaliser un prototype exécutable minimal et consigner OS, version Python, versions installées, commandes, sorties, limitations, durée/mémoire si mesurées.
6. Décider au moyen d'une ADR (`docs/adr/NNNN-titre.md`) contenant contexte, options, décision, alternatives, conséquences et stratégie de retour arrière.
7. Consigner la source (URL, auteur/projet, version, consultée le, apport, fiabilité) sous `docs/research/`.
8. Revoir la décision après incident, incompatibilité, changement important de dépendance ou nouvelle exigence.

## Sources documentaires de départ (points de départ, pas garanties de compatibilité)

- ManimGL (projet 3Blue1Brown) : https://github.com/3b1b/manim ; https://3b1b.github.io/manim/
- Manim Community : https://docs.manim.community/en/stable/ ; https://github.com/ManimCommunity/manim
- PySide6 / Qt for Python : https://doc.qt.io/qtforpython-6/ ; https://doc.qt.io/qt-6/licensing.html
- Blender, mode batch et API : https://docs.blender.org/manual/en/latest/advanced/command_line/ ; https://docs.blender.org/api/current/
- FFmpeg : https://ffmpeg.org/documentation.html ; https://ffmpeg.org/legal.html
- NumPy : https://numpy.org/doc/stable/ ; SciPy : https://docs.scipy.org/doc/scipy/ ; SymPy : https://docs.sympy.org/latest/
- Python packaging : https://packaging.python.org/ ; pytest : https://docs.pytest.org/ ; GitHub Actions : https://docs.github.com/en/actions
- NASA data / images : https://science.nasa.gov/ ; https://images.nasa.gov/ (vérifier chaque condition de réutilisation, crédits et marques)
- ESA : https://www.esa.int/ (vérifier les conditions propres à chaque ressource)
- IAU : https://www.iau.org/ (nomenclature, désignations et ressources scientifiques)
- NIST SI : https://physics.nist.gov/cuu/Units/ ; CODATA : https://physics.nist.gov/cuu/Constants/

**Note vérifiée lors du cadrage :** les deux variantes de Manim ne partagent pas automatiquement leur procédure d'installation ; `manimgl` est le paquet Python de ManimGL. PySide6 s'appuie sur le régime LGPLv3/GPLv3 ou licence commerciale. Blender offre une interface de rendu hors interface graphique. Ces affirmations ne suffisent pas à établir la compatibilité de l'ensemble ni les droits de redistribution du produit final : refaire la vérification des versions et licences à la date d'intégration.

## Rubrique sources scientifiques

Toute scène physique doit préciser `type: schematic | model | simulation | measured`, référentiel, unités SI, intervalles temporels, équations, approximation, conditions initiales, sources des constantes et domaine de validité. Éviter les échelles trompeuses ; prévoir une légende « distances et tailles non à l'échelle » quand nécessaire. Les affirmations controversées doivent être séparées des résultats établis ; ne jamais inventer une mesure.

## Barème de choix suggéré

Pour un composant candidat, évaluer : stabilité/documentation (20 %), intégration dans le modèle interne (20 %), qualité de sortie (15 %), performance sur matériel courant (15 %), ergonomie (15 %), licence/distribution (10 %), maintenance (5 %). Les poids sont ajustables par ADR ; une incompatibilité de licence, de sécurité ou d'installation est **éliminatoire** même si le total est bon.

## Licences et sécurité des ressources

À l'import, stocker : provenance, auteur, URL, hash SHA-256, licence exacte, attribution requise, droit de modification/redistribution et date de vérification. Refuser l'intégration d'un asset dont les droits de redistribution ne sont pas vérifiés. Pour les tests, privilégier SVG générés localement, sons synthétiques, modèles géométriques primitifs. Ne pas assimiler « disponible gratuitement » à « libre ».

Ne pas exécuter des scripts Python associés à des packs, du LaTeX arbitraire ou des commandes depuis un projet non fiable. Valider chemins, extensions et formats, isoler les outils externes, plafonner taille/temps/mémoire selon les risques. Confirmer avant de déclencher du code utilisateur avancé.

## Modèle de fiche de recherche

```markdown
# R-AAAA-NN — Question
Date ; agent ; environnement ; problème et hypothèses.
Alternatives / sources officielles (URL, version, consultée le).
Essais et commandes reproductibles ; résultats bruts ; captures/rendus.
Risques, licences, maturité, performance mesurée et coût d'installation.
Conclusion, niveau de confiance, ADR associée et travaux restants.
```
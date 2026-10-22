# ADR-0005 — Système de design de l'éditeur, aide intégrée et tutoriels vérifiés

**Date :** 2026-10-22 — **Statut :** accepté — **Phase :** transverse (ergonomie, master prompt §4)

## Contexte

Demande du porteur : « travaille le design visuel et tu mettras une rubrique aide et tuto complète pour
apprendre l'utilisation complète du logiciel ». L'éditeur utilisait le style natif de Qt, des couleurs
codées en dur dans plusieurs widgets et aucune aide intégrée (seul un guide Markdown dans `docs/`).
Contraintes : hors ligne, français, PySide6 seul, rendu identique sous Windows 11 et Linux, export vidéo
indépendant de l'apparence de l'éditeur, aucune ressource tierce sans licence qualifiée.

## Décisions

1. **Style Fusion + palette Qt + une feuille de style globale** (`app/theme.py`). Fusion est le seul
   style livré identique sur toutes les plateformes ; la palette couvre les widgets standard et la
   feuille de style ajoute des rôles (`role=primary`, `hint`, `warning`, `card`…) plutôt que des
   couleurs locales. Toutes les couleurs sont des **jetons** d'une `Palette` ; les widgets dessinés à la
   main (canevas, timeline) lisent les jetons au moment du dessin, si bien qu'un changement de thème
   s'applique sans redémarrage.
2. **Deux thèmes, sombre (défaut, adapté au montage) et clair**, et une **taille de texte** réglable
   (90 à 150 %), dans `Affichage`, mémorisées dans les préférences. Les couples texte/fond respectent
   4,5:1 et les composants (bordures, focus, images clés) 3:1 (WCAG 2.2, critères 1.4.3 et 1.4.11),
   vérifiés par `tests/unit/test_theme.py`. Le contenu des scènes n'utilise aucun jeton : la vidéo
   exportée est identique quel que soit le thème.
3. **Icônes Lucide** (`lucide-static` 1.51.0, ISC, part Feather MIT) : sous-ensemble de 68 SVG copiés
   sans modification, archive npm vérifiée par son empreinte SHA-512, recolorés au chargement
   (`currentColor`) et rendus par `QSvgRenderer` (QtSvg, indépendant du greffon d'images `qsvg`, donc
   valable dans le paquet PyInstaller). Logo ANTARES dessiné pour le projet. Les vignettes de la
   Bibliothèque (objets, modèles) sont produites **par le moteur de rendu réel**, pas par des images.
4. **Aide intégrée en Markdown, source unique** : 32 rubriques dans `resources/help/*.md`, affichées par
   `QTextBrowser.setMarkdown` (dialecte GitHub, tableaux) dans un centre d'aide non modal (sommaire,
   recherche insensible aux accents, historique, liens entre rubriques, F1 contextuel selon le panneau
   actif, Maj+F1 « Qu'est-ce que c'est ? »). Les listes qui changent avec le code (objets, animations,
   profils d'export, symboles des formules, modèles, tutoriels, raccourcis) sont **générées** depuis les
   catalogues réels (`<!-- auto:clé -->`) : l'aide ne peut pas les contredire. Les chemins de menu cités
   en gras sont confrontés à la vraie barre de menus par un test. Le guide `docs/user-guide/01` devient un
   renvoi vers cette source unique.
5. **Tutoriels interactifs vérifiés sur l'état réel** (`help/tutorials.py`, sans Qt) : 7 parcours,
   46 étapes dont 44 validées automatiquement par une vérification `check(état, état de départ)` sur une
   copie du projet et de l'état d'interface. Comparer au départ interdit une validation « gratuite »
   (testé pour chaque étape). « Montre-moi » fait clignoter la zone concernée ; un indice est disponible.
   Les données d'exemple (planètes, NASA Planetary Fact Sheet, domaine public aux États-Unis) sont
   livrées avec leur provenance renseignée.
6. **Accueil** au démarrage (désactivable) : nouveau, ouvrir, récents, modèles avec vignette réelle,
   tutoriels (terminés cochés), état de FFmpeg. **Palette de commandes** (Ctrl+K) sur toutes les actions
   des menus. Indication des premiers gestes sur une scène vide (éditeur seulement).
7. **Corrections découvertes en écrivant l'aide** (l'aide décrit le comportement réel, pas l'inverse) :
   - export : la taille de sortie suit le format du projet (`output_size`) ; un projet 9:16 ou 1:1
     n'est plus étiré dans un cadre 16:9 (test qui échoue sur l'ancien code : 1280×720 au lieu de 720×1280) ;
   - raccourcis : Supprimer = Suppr seul (le raccourci standard Qt inclut Ctrl+D sous KDE/GNOME, en
     conflit avec Dupliquer), Rétablir = Ctrl+Y et Ctrl+Maj+Z, Enregistrer sous = Ctrl+Maj+S explicite
     (le standard Qt n'a pas de liaison sous Windows pour certaines actions) ;
   - bouton de couleur : une couleur `#RRGGBBAA` était lue par Qt comme `#AARRGGBB` (blanc transparent
     affiché jaune) ; passage par `rgba()` et libellé « Transparent ».
8. **Préférences isolées pour les tests et scripts** : `QSettings(organisation, application)` ignore
   `setDefaultFormat`/`setPath` ; les tests écrivaient donc les préférences réelles. `AppSettings` lit
   désormais `ANTARES_SETTINGS_DIR` (fichier INI explicite, hérité par les sous-processus) ; sans la
   variable, l'emplacement natif est inchangé, et les préférences des utilisateurs sont conservées.

## Alternatives écartées

- **Qt Quick / QML** : réécriture complète de l'interface, risque élevé, sans gain pour un éditeur de
  bureau à docks.
- **Thème tiers (qt-material, QDarkStyle)** : dépendance et licence supplémentaires, contrôle partiel
  des contrastes ; Fusion + palette suffit.
- **Aide HTML ou Qt Help (`.qch`, QtHelp + Assistant)** : chaîne de compilation et module en plus ; le
  Markdown se lit aussi dans le dépôt et se teste simplement.
- **Tutoriels en surimpression bloquante** : fragiles (positions de widgets), empêchent d'explorer ;
  remplacés par un panneau à côté de l'interface et une mise en évidence ponctuelle.
- **Pack d'icônes Material Symbols** (Apache 2.0) : plus lourd ; style Lucide plus cohérent au trait.

## Conséquences et preuves

- 214 tests pytest verts sur Linux (contre 127), dont : contrastes des deux thèmes ; rubriques, liens,
  images et sections générées ; chemins de menu cités ; raccourcis uniques ; F1 contextuel ; recherche ;
  palette ; accueil ; changement de thème ; parcours complet du tutoriel 2 étape par étape ; import des
  données d'exemple avec provenance ; export vertical réel vérifié par ffprobe ; isolation des
  préférences (échoue sur l'ancien constructeur).
- Paquet PyInstaller Linux reconstruit : aide, icônes, exemples et script Blender inclus ; l'autotest
  contrôle désormais ces ressources (`--selftest`).
- NON TESTÉ sur Windows 11 réel (HiDPI, polices, rendu Fusion) : CI Windows seulement (R-005). Le
  conflit Ctrl+D est corrigé de façon préventive, sans reproduction possible hors bureau KDE/GNOME.

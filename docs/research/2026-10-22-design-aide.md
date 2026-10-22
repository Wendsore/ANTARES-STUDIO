# Recherche — Système de design Qt, aide Markdown et tutoriels (2026-10-22)

**Machine :** `ki` (Debian 13, sans écran, `QT_QPA_PLATFORM=offscreen`), PySide6 6.12.0.

## Sources consultées

- Qt 6 — `QTextDocument::setMarkdown` et `QTextDocument::MarkdownDialectGitHub` (tableaux, listes,
  liens) : https://doc.qt.io/qt-6/qtextdocument.html ; `QTextBrowser::loadResource` pour les images
  locales : https://doc.qt.io/qt-6/qtextbrowser.html
- Qt 6 — table des raccourcis standard par plateforme (`QKeySequence::StandardKey`) :
  https://doc.qt.io/qt-6/qkeysequence.html#standard-shortcuts. Constats : `Delete` comprend Ctrl+D sous
  KDE et GNOME ; `Redo` vaut Ctrl+Y sous Windows et Ctrl+Maj+Z ailleurs ; certaines clés n'ont pas de
  liaison sous Windows. D'où des raccourcis explicites dans l'application.
- Qt 6 — `QSettings` : le constructeur (organisation, application) utilise le format natif ; vérifié
  localement : il écrit `~/.config/<org>/<app>.conf` même après `setDefaultFormat(IniFormat)` et
  `setPath(...)`, alors que le constructeur avec format explicite respecte `setPath`.
  https://doc.qt.io/qt-6/qsettings.html
- Qt 6 — style Fusion : https://doc.qt.io/qt-6/qstylefactory.html ; feuilles de style :
  https://doc.qt.io/qt-6/stylesheet-reference.html (images des flèches de `QSpinBox`/`QComboBox` : un
  fichier est requis, d'où des PNG générés une fois par couleur dans le dossier temporaire).
- W3C — WCAG 2.2, critères 1.4.3 (contraste du texte, 4,5:1) et 1.4.11 (contraste non textuel, 3:1),
  définition de la luminance relative : https://www.w3.org/TR/WCAG22/
- Lucide — licence ISC et mention Feather (MIT) : https://lucide.dev/license ; paquet
  `lucide-static` 1.51.0 téléchargé depuis le registre npm, intégrité SHA-512 comparée au champ
  `dist.integrity` du registre avant extraction.
- NASA NSSDCA — Planetary Fact Sheet (D. R. Williams) :
  https://nssdc.gsfc.nasa.gov/planetary/factsheet/ (distance moyenne au Soleil, période orbitale
  sidérale), consultée le 2026-10-22 ; publication d'une agence fédérale américaine (17 U.S.C. § 105).

## Vérifications locales

| Point | Résultat |
|---|---|
| Contrastes des jetons (deux thèmes) | tous ≥ 4,5:1 pour le texte et ≥ 3:1 pour les composants après correction de 3 couples (bordure de champ sombre, accent clair, images clés en thème clair) |
| Rendu SVG par `QSvgRenderer` dans le paquet PyInstaller Linux | icônes affichées, autotest « Ressources » réussi |
| Export d'un projet 1080×1920 avant correction | vidéo 1280×720 (image étirée) ; après : 720×1280 (ffprobe) |
| Préférences pendant la suite de tests avant correction | écrites dans `~/.config/Wendsore/ANTARES Studio.conf` ; après : dossier temporaire uniquement |

## Limites

Rendu sur un vrai écran Windows 11 (HiDPI 125–150 %, police Segoe UI) non observé : à valider par le
porteur. Les captures de `docs/images/*-2026-10-22.png` viennent de la plateforme Qt hors écran.

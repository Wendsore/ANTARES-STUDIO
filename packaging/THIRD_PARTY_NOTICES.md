# ANTARES Studio — composants tiers et licences

Ce fichier accompagne chaque dossier distribuable d'ANTARES Studio (phase 9). ANTARES Studio lui-même
n'a pas encore de licence décidée (voir README).

| Composant | Version livrée | Licence | Obligations / notes |
|---|---|---|---|
| Qt for Python (PySide6, shiboken6) et bibliothèques Qt | 6.12.0 | LGPL v3 | Liaison dynamique (bibliothèques `Qt6*.dll` / `libQt6*.so` remplaçables dans le dossier `_internal`) ; mention dans « Aide > À propos » ; sources Qt disponibles sur https://code.qt.io et sur demande auprès du distributeur ; aucune restriction de rétro-ingénierie. https://www.qt.io/licensing |
| Python (interpréteur embarqué) | 3.12 (CI) / 3.13 (dev) | PSF License | https://docs.python.org/3/license.html |
| NumPy | ≥ 2.1 | BSD-3-Clause | https://numpy.org/doc/stable/license.html |
| PyInstaller (outil de construction, non livré) | 6.22.3 | GPL v2+ avec exception | L'exception autorise la distribution d'applications empaquetées sous une licence quelconque ; le bootloader inclus est couvert par cette exception. https://pyinstaller.org/en/stable/license.html |
| FFmpeg / ffprobe (optionnel, dossier `bin/`) | selon le build déposé | LGPL v2.1+ ou GPL v2+ selon les options de compilation (libx264 ⇒ GPL) | Non livré par défaut : l'application utilise FFmpeg du PATH ou le chemin configuré. Si un build est livré dans `bin/`, joindre sa LICENSE et ses sources ou une offre écrite (GPL). Décision propriétaire R-002. https://ffmpeg.org/legal.html |
| Icônes Lucide (`lucide-static`, sous-ensemble de 68 SVG) | 1.51.0 | ISC ; icônes dérivées de Feather : MIT | Texte complet des deux licences livré dans `antares_studio/resources/icons/LICENSE-lucide.txt` ; mention dans « Aide > À propos ». https://lucide.dev/license |
| Données d'exemple « planètes : période et distance » | NASA Planetary Fact Sheet (consulté le 2026-10-22) | Domaine public aux États-Unis (publication d'une agence fédérale, 17 U.S.C. § 105) ; données factuelles | Source citée dans `resources/examples/README.md` et dans la provenance de l'actif importé. https://nssdc.gsfc.nasa.gov/planetary/factsheet/ |
| Polices d'écriture livrées (17 familles : Architects Daughter, Bebas Neue, Cabin Sketch, Caveat, Comic Neue, Courier Prime, EB Garamond, Fredericka the Great, Gloria Hallelujah, Indie Flower, Kalam, Lora, Montserrat, Patrick Hand, Shadows Into Light ; Permanent Marker et Special Elite) | Google Fonts, `main` au 2026-10-22 | SIL OFL 1.1 ; Apache 2.0 pour Permanent Marker et Special Elite | Fichiers non modifiés ni renommés (noms réservés OFL respectés) ; licence complète dans chaque dossier `antares_studio/resources/fonts/<famille>/` ; empreintes SHA-256 dans `resources/fonts/README.md` ; mention dans « Aide > À propos ». https://openfontlicense.org |
| Police DejaVu Sans (si présente sur le système) | système | Bitstream Vera / DejaVu (libre) | Non embarquée ; Qt utilise une police de substitution si absente. |

Les ressources (images, sons) importées dans un projet par l'utilisateur ne sont pas couvertes ici : leur
provenance est consignée dans le projet (`Fichier > Inventaire des licences et crédits…`).

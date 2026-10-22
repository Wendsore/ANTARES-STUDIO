"""Polices livrées avec ANTARES Studio (licences libres OFL 1.1 ou Apache 2.0, fichiers de Google Fonts).

Une vidéo doit avoir le même aspect sur tous les postes : ces polices sont chargées par l'application
elle-même (``ensure_fonts``) au lieu de dépendre de celles installées sur l'ordinateur.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent / "fonts"


@dataclass(frozen=True)
class BundledFont:
    family: str  # nom de famille vu par Qt
    folder: str  # sous-dossier de ``fonts/``
    category: str
    usage: str
    license: str  # identifiant SPDX


FONT_CATEGORIES: tuple[str, ...] = ("Craie et tableau", "Manuscrit", "Machine à écrire", "Titres", "Lecture")

BUNDLED_FONTS: tuple[BundledFont, ...] = (
    BundledFont(
        "Cabin Sketch", "cabinsketch", "Craie et tableau", "lettres crayonnées, effet craie", "OFL-1.1"
    ),
    BundledFont(
        "Fredericka the Great",
        "frederickathegreat",
        "Craie et tableau",
        "titres gravés, tableau d'école",
        "OFL-1.1",
    ),
    BundledFont(
        "Kalam", "kalam", "Craie et tableau", "écriture d'enseignant au tableau, très lisible", "OFL-1.1"
    ),
    BundledFont(
        "Architects Daughter",
        "architectsdaughter",
        "Craie et tableau",
        "capitales d'ingénieur, schémas",
        "OFL-1.1",
    ),
    BundledFont("Caveat", "caveat", "Manuscrit", "écriture rapide au feutre, notes", "OFL-1.1"),
    BundledFont("Patrick Hand", "patrickhand", "Manuscrit", "écriture de cahier, régulière", "OFL-1.1"),
    BundledFont("Indie Flower", "indieflower", "Manuscrit", "écriture ronde et décontractée", "OFL-1.1"),
    BundledFont("Shadows Into Light", "shadowsintolight", "Manuscrit", "écriture fine au stylo", "OFL-1.1"),
    BundledFont(
        "Gloria Hallelujah", "gloriahallelujah", "Manuscrit", "écriture d'élève, bande dessinée", "OFL-1.1"
    ),
    BundledFont("Permanent Marker", "permanentmarker", "Manuscrit", "gros marqueur, slogans", "Apache-2.0"),
    BundledFont(
        "Special Elite", "specialelite", "Machine à écrire", "machine à écrire usée, archives", "Apache-2.0"
    ),
    BundledFont(
        "Courier Prime", "courierprime", "Machine à écrire", "machine à écrire nette, code", "OFL-1.1"
    ),
    BundledFont("Bebas Neue", "bebasneue", "Titres", "capitales hautes, titres de vidéo", "OFL-1.1"),
    BundledFont("Montserrat", "montserrat", "Titres", "moderne et géométrique", "OFL-1.1"),
    BundledFont("Comic Neue", "comicneue", "Titres", "ton amical, jeune public", "OFL-1.1"),
    BundledFont(
        "EB Garamond", "ebgaramond", "Lecture", "classique, citations, histoire des sciences", "OFL-1.1"
    ),
    BundledFont("Lora", "lora", "Lecture", "serif contemporain, textes longs", "OFL-1.1"),
)
BUNDLED_BY_FAMILY: dict[str, BundledFont] = {f.family: f for f in BUNDLED_FONTS}

_loaded: set[str] = set()


def ensure_fonts() -> set[str]:
    """Enregistre les polices livrées auprès de Qt (une fois ; nécessite une application Qt).

    Retourne les familles disponibles. Une police illisible est ignorée : le texte retombe sur la police
    par défaut au lieu de bloquer le rendu.
    """
    if _loaded:
        return _loaded
    from PySide6.QtGui import QFontDatabase

    for path in sorted(FONTS_DIR.rglob("*.ttf")):
        idx = QFontDatabase.addApplicationFont(str(path))
        if idx >= 0:
            _loaded.update(QFontDatabase.applicationFontFamilies(idx))
    if not _loaded:
        _loaded.add("")  # rien de chargé : ne pas retenter à chaque texte
    return _loaded

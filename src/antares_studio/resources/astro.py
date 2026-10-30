"""Ressources astronomiques intégrées : textures des astres, cartes du monde, ciel étoilé (ADR-0009).

Tout vient de sources publiques identifiées, livrées avec le logiciel (empreintes dans
``resources/astro/README.md``) : rien n'est téléchargé à l'exécution. Les valeurs numériques sont
recopiées telles quelles de leur source, citée pour chaque astre ; aucune n'est inventée.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
TEXTURES = ROOT / "astro" / "textures"


@dataclass(frozen=True)
class Dataset:
    id: str
    label: str
    license: str
    url: str
    credit: str  # ligne de crédits (attribution exigée par CC BY 4.0, reconnaissance pour les autres)


DATASETS: dict[str, Dataset] = {
    d.id: d
    for d in (
        Dataset(
            "solarsystemscope",
            "Textures des astres",
            "CC-BY-4.0",
            "https://www.solarsystemscope.com/textures/",
            "Textures planétaires : Solar System Scope (INOVE), d'après les données NASA — CC BY 4.0",
        ),
        Dataset(
            "naturalearth",
            "Cartes du monde (pays, continents)",
            "public-domain",
            "https://www.naturalearthdata.com/",
            "Cartes : Natural Earth (domaine public)",
        ),
        Dataset(
            "d3celestial",
            "Étoiles et constellations",
            "BSD-3-Clause",
            "https://github.com/ofrohn/d3-celestial",
            "Ciel : d3-celestial (Olaf Frohn, BSD-3), catalogue Hipparcos (ESA)",
        ),
        Dataset(
            "nasa_factsheet",
            "Caractéristiques des planètes",
            "public-domain",
            "https://nssdc.gsfc.nasa.gov/planetary/factsheet/",
            "Données planétaires : NASA NSSDCA, Planetary Fact Sheet (domaine public)",
        ),
        Dataset(
            "wikidata",
            "Caractéristiques des étoiles",
            "CC0-1.0",
            "https://www.wikidata.org/",
            "Données stellaires : Wikidata (CC0), consultées le 2026-10-30",
        ),
    )
}


@dataclass(frozen=True)
class Body:
    """Astre du Système solaire ; chiffres de la NASA Planetary Fact Sheet (Soleil : valeurs nominales
    UAI 2015, résolution B3). Une période de rotation négative signifie une rotation rétrograde."""

    id: str
    label: str
    texture: str
    diameter_km: float
    rotation_h: float
    obliquity_deg: float
    sun_distance_mkm: float | None  # 10⁶ km (Lune : distance à la Terre)
    orbital_period_d: float | None
    moons: int | None
    atmosphere: str = ""  # couleur du limbe éclairé, vide = aucune
    emissive: bool = False  # astre qui brille par lui-même
    night_texture: str = ""
    clouds_texture: str = ""
    rings: bool = False
    alt_texture: str = ""  # Vénus : surface radar sous l'atmosphère


BODIES: dict[str, Body] = {
    b.id: b
    for b in (
        Body("sun", "Soleil", "sun.jpg", 1_391_400, 609.12, 7.25, None, None, None, emissive=True),
        Body("mercury", "Mercure", "mercury.jpg", 4879, 1407.6, 0.034, 57.9, 88.0, 0),
        Body(
            "venus",
            "Vénus",
            "venus_atmosphere.jpg",
            12104,
            -5832.5,
            177.4,
            108.2,
            224.7,
            0,
            atmosphere="#F3D9A0",
            alt_texture="venus_surface.jpg",
        ),
        Body(
            "earth",
            "Terre",
            "earth_daymap.jpg",
            12756,
            23.9,
            23.4,
            149.6,
            365.2,
            1,
            atmosphere="#7FB8FF",
            night_texture="earth_nightmap.jpg",
            clouds_texture="earth_clouds.jpg",
        ),
        Body("moon", "Lune", "moon.jpg", 3475, 655.7, 6.7, 0.384, 27.3, None),
        Body("mars", "Mars", "mars.jpg", 6792, 24.6, 25.2, 228.0, 687.0, 2, atmosphere="#E8A27A"),
        Body("jupiter", "Jupiter", "jupiter.jpg", 142_984, 9.9, 3.1, 778.5, 4331, 95, atmosphere="#E9DCC6"),
        Body(
            "saturn",
            "Saturne",
            "saturn.jpg",
            120_536,
            10.7,
            26.7,
            1432.0,
            10_747,
            274,
            atmosphere="#EEDFB8",
            rings=True,
        ),
        Body("uranus", "Uranus", "uranus.jpg", 51_118, -17.2, 97.8, 2867.0, 30_589, 28, atmosphere="#B8F0F4"),
        Body(
            "neptune", "Neptune", "neptune.jpg", 49_528, 16.1, 28.3, 4515.0, 59_800, 16, atmosphere="#7FA8FF"
        ),
    )
}

# anneaux de Saturne (texture Solar System Scope) : rayons intérieur et extérieur en rayons de Saturne
SATURN_RING_TEXTURE = "saturn_ring_alpha.png"
SATURN_RING_RADII = (1.236, 2.327)
MILKY_WAY_TEXTURE = "stars_milky_way.jpg"


@dataclass(frozen=True)
class FamousStar:
    """Étoile connue : valeurs Wikidata (élément ``qid``) ; ``None`` si Wikidata ne donne rien de
    cohérent. Quand Wikidata cite plusieurs valeurs, on garde leur moyenne et ``note`` les conserve."""

    id: str
    label: str
    constellation: str
    hip: int | None
    temperature_k: float
    radius_sun: float | None
    mass_sun: float | None
    distance_ly: float | None
    qid: str
    note: str = ""


_PC = 3.26156  # années-lumière par parsec

FAMOUS_STARS: dict[str, FamousStar] = {
    s.id: s
    for s in (
        FamousStar(
            "sun", "Soleil", "—", None, 5772.0, 1.0, 1.0, 1.581e-5, "Q525", "Teff : valeur nominale UAI 2015"
        ),
        FamousStar("sirius", "Sirius A", "Grand Chien", 32349, 9845.0, 1.7144, 2.063, 8.6, "Q13415844"),
        FamousStar("vega", "Véga", "Lyre", 91262, 9550.0, 2.818, 2.135, 7.67 * _PC, "Q3427"),
        FamousStar(
            "rigel", "Rigel", "Orion", 24436, 12130.0, 76.5, 18.0, 860.0, "Q12126", "rayon : 74,1 et 78,9"
        ),
        FamousStar(
            "betelgeuse",
            "Bételgeuse",
            "Orion",
            27989,
            3654.0,
            768.0,
            None,
            548.0,
            "Q12124",
            "masse : 14 à 17,8",
        ),
        FamousStar(
            "antares", "Antarès", "Scorpion", 80763, 3400.0, 680.0, None, 550.0, "Q12166", "masse : 12,4 à 16"
        ),
        FamousStar(
            "aldebaran",
            "Aldébaran",
            "Taureau",
            21421,
            3914.0,
            44.6,
            1.13,
            20.43 * _PC,
            "Q12170",
            "rayon : 44,13 et 45,1",
        ),
        FamousStar("deneb", "Deneb", "Cygne", 102098, 8700.0, 203.0, 21.0, 1640.0, "Q12179"),
        FamousStar("achernar", "Achernar", "Éridan", 7588, 15000.0, 7.3, 6.7, 43.0 * _PC, "Q12183"),
        FamousStar("altair", "Altaïr", "Aigle", 97649, 7377.0, 1.7, 1.7, 17.0, "Q12975"),
        FamousStar("polaris", "Étoile polaire", "Petite Ourse", 11767, 6206.0, 30.0, 6.0, 432.0, "Q12980"),
        FamousStar("arcturus", "Arcturus", "Bouvier", 69673, 4251.0, 25.4, 1.3, 36.7, "Q12985"),
        FamousStar(
            "pollux", "Pollux", "Gémeaux", 37826, 4835.0, 9.05, None, 33.7, "Q13028", "rayon : 8,8 et 9,3"
        ),
        FamousStar("bellatrix", "Bellatrix", "Orion", 25336, 21840.0, 6.0, 8.4, 121.0 * _PC, "Q13066"),
        FamousStar("spica", "Spica", "Vierge", 65474, 25300.0, 7.4, None, 93.0 * _PC, "Q13008"),
        FamousStar("canopus", "Canopus", "Carène", 30438, 7557.0, None, None, 310.0, "Q12189"),
    )
}

# noms français des étoiles brillantes quand ils diffèrent du nom anglais du catalogue
STAR_NAMES_FR: dict[str, str] = {
    "Betelgeuse": "Bételgeuse",
    "Vega": "Véga",
    "Aldebaran": "Aldébaran",
    "Antares": "Antarès",
    "Altair": "Altaïr",
    "Regulus": "Régulus",
    "Polaris": "Étoile polaire",
    "Rigil Kentaurus": "Alpha du Centaure",
}

CONTINENTS_FR: dict[str, str] = {
    "Africa": "Afrique",
    "Asia": "Asie",
    "Europe": "Europe",
    "North America": "Amérique du Nord",
    "South America": "Amérique du Sud",
    "Oceania": "Océanie",
    "Antarctica": "Antarctique",
}
# position des étiquettes de continent (longitude, latitude), choisie à l'œil sur les terres
CONTINENT_LABELS: dict[str, tuple[float, float]] = {
    "Africa": (20.0, 5.0),
    "Asia": (90.0, 48.0),
    "Europe": (18.0, 52.0),
    "North America": (-100.0, 45.0),
    "South America": (-60.0, -15.0),
    "Oceania": (134.0, -25.0),
    "Antarctica": (20.0, -80.0),
}


def texture_path(name: str) -> Path:
    return TEXTURES / name


@lru_cache(maxsize=2)
def countries(detail: str = "50m") -> list[dict[str, Any]]:
    """Pays Natural Earth (nom français, continent, géométrie GeoJSON allégée)."""
    name = "countries_110m.json" if detail == "110m" else "countries_50m.json"
    data = json.loads((ROOT / "geo" / name).read_text(encoding="utf-8"))
    return list(data["features"])


@lru_cache(maxsize=1)
def stars() -> tuple[list[list[Any]], dict[str, str]]:
    """Étoiles de magnitude ≤ 6 : [hip, ra°, dec°, mag, B−V] et noms propres (anglais) par HIP."""
    data = json.loads((ROOT / "sky" / "stars.json").read_text(encoding="utf-8"))
    return data["stars"], data["names_en"]


@lru_cache(maxsize=1)
def constellations() -> list[dict[str, Any]]:
    """88 constellations de l'UAI (Serpent en deux parties) : id, nom français, latin, tracés (ra°, dec°)."""
    data = json.loads((ROOT / "sky" / "constellations.json").read_text(encoding="utf-8"))
    return list(data["constellations"])


def star_name_fr(name_en: str) -> str:
    return STAR_NAMES_FR.get(name_en, name_en)

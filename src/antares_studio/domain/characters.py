"""Catalogue des personnages chibis : émotions, poses, tenues, coiffures, fiches de jeu (ADR-0010).

Données pures, sans Qt : le domaine (``kinds``) y prend ses listes de choix, le moteur de rendu
(``rendering.chibi``) la description visuelle de chaque émotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SKIN_TONES: tuple[tuple[str, str, str], ...] = (
    ("ebene", "Ébène", "#4A2C1F"),
    ("fonce", "Brun foncé", "#653C22"),
    ("brun", "Brun", "#85522F"),
    ("cuivre", "Cuivré", "#A2663A"),
    ("caramel", "Caramel", "#BE8552"),
    ("miel", "Miel", "#D7A06C"),
)
SKIN_CHOICES = tuple((k, label) for k, label, _ in SKIN_TONES)
SKIN_HEX = {k: hex_ for k, _l, hex_ in SKIN_TONES}


@dataclass(frozen=True)
class Emotion:
    id: str
    label: str
    eyes: str  # forme des yeux (voir ``_eyes``)
    brows: tuple[float, float]  # (hauteur, inclinaison) : > 0 = levé ; inclinaison > 0 = intérieur abaissé
    mouth: str
    extras: tuple[str, ...] = ()
    brow_right: tuple[float, float] | None = None  # sourcil droit différent (ironie, doute)
    lid: float = 0.0  # paupière (0 ouverte, 1 mi-close)


EMOTIONS: tuple[Emotion, ...] = (
    Emotion("neutre", "Neutre", "normal", (0, 0), "soft"),
    Emotion("explique", "Explique (calme, bouche ouverte)", "normal", (3, 0), "talk"),
    Emotion("joie", "Joie", "happy", (5, 0), "big_smile", ("blush",)),
    Emotion("rire", "Fou rire", "happy", (7, -2), "laugh", ("blush", "laugh_tears")),
    Emotion("enthousiasme", "Enthousiasme", "star", (7, 0), "big_smile", ("sparkles",)),
    Emotion("emerveille", "Émerveillé", "star", (8, -3), "o", ("sparkles",)),
    Emotion("fierte", "Fier de lui", "closed", (6, 0), "smile", ("sparkles_small",)),
    Emotion("ironie", "Ironique", "normal", (-1, 2), "smirk", (), (9, -3), 0.55),
    Emotion("clin_oeil", "Clin d'œil complice", "wink", (4, 0), "smirk"),
    Emotion("surprise", "Surprise", "wide", (12, -2), "o", ("exclaim",)),
    Emotion("peur", "Peur", "wide", (9, -7), "wavy_open", ("sweat",)),
    Emotion("doute", "Doute", "doubt", (-3, 4), "doubt", ("question",), (8, -2)),
    Emotion("reflexion", "Réflexion", "look_up", (2, 0), "pout", ("thinking",), (7, -1)),
    Emotion("confusion", "Confusion", "normal", (4, -5), "wavy", ("question2", "sweat"), (-2, 4)),
    Emotion("agacement", "Agacement", "normal", (-2, 5), "flat", ("anger_small",), None, 0.45),
    Emotion("colere", "Colère", "angry", (-4, 9), "grit", ("anger", "red")),
    Emotion("fureur", "Fureur (crie)", "angry", (-5, 11), "shout", ("anger", "steam", "red")),
    Emotion("tristesse", "Tristesse", "sad", (2, -8), "frown", ("tears",)),
    Emotion("deception", "Déception", "sad", (0, -5), "frown_small", ("gloom",), None, 0.45),
    Emotion("gene", "Gêne", "look_side", (3, -6), "wavy", ("blush_strong", "sweat")),
    Emotion("degout", "Dégoût", "doubt", (-3, 7), "disgust", ("gloom",), (-3, 7)),
    Emotion("ennui", "Ennui", "normal", (-1, 0), "flat", ("sigh",), None, 0.6),
)
EMOTION_CHOICES = tuple((e.id, e.label) for e in EMOTIONS)
EMOTION_BY_ID = {e.id: e for e in EMOTIONS}

POSES: tuple[tuple[str, str], ...] = (
    ("repos", "Bras le long du corps"),
    ("explique", "Explique (main ouverte)"),
    ("montre", "Montre sur le côté"),
    ("index", "Index levé (point important)"),
    ("salut", "Salue de la main"),
    ("menton", "Main au menton (réfléchit)"),
    ("bras_croises", "Bras croisés"),
    ("hanches", "Poings sur les hanches"),
    ("haussement", "Hausse les épaules"),
    ("victoire", "Bras levés (victoire)"),
)
OUTFITS: tuple[tuple[str, str], ...] = (
    ("tshirt", "T-shirt et jean"),
    ("chemise", "Chemise"),
    ("blouse", "Blouse de laboratoire"),
    ("sweat", "Sweat à capuche"),
    ("dashiki", "Dashiki (tunique brodée)"),
    ("costume", "Costume et cravate"),
    ("maillot", "Maillot de foot"),
    ("doudoune", "Doudoune sans manches sur sweat"),
    ("gilet_hv", "Gilet haute visibilité"),
    ("veste_jean", "Veste en jean doublée sur sweat"),
    ("polo", "Polo"),
)
HAIRS: tuple[tuple[str, str], ...] = (
    ("court", "Cheveux courts"),
    ("afro", "Afro"),
    ("tresses", "Tresses collées"),
    ("locks", "Locks (dreadlocks)"),
    ("macarons", "Deux macarons (afro puffs)"),
    ("nattes", "Tresses longues (box braids)"),
    ("rase", "Rasé"),
)
BEARDS: tuple[tuple[str, str], ...] = (
    ("aucune", "Aucune"),
    ("courte", "Barbe courte"),
    ("bouc", "Bouc et moustache"),
    ("moustache", "Moustache"),
)
GLASSES: tuple[tuple[str, str], ...] = (
    ("aucune", "Aucunes"),
    ("rondes", "Rondes"),
    ("rectangles", "Rectangulaires"),
    ("fines", "Fine monture métallique"),
    ("protection", "Lunettes de protection"),
)
HATS: tuple[tuple[str, str], ...] = (
    ("aucun", "Aucun"),
    ("casquette", "Casquette"),
    ("kufi", "Calot (kufi)"),
    ("casque", "Casque de chantier"),
)
PROPORTIONS: tuple[tuple[str, str], ...] = (
    ("chibi", "Chibi (grosse tête, style enfantin)"),
    ("adulte", "Adulte stylisé"),
)
GAZES: tuple[tuple[str, str], ...] = (
    ("face", "Vers le public"),
    ("gauche", "À gauche"),
    ("droite", "À droite"),
    ("haut", "En haut"),
    ("bas", "En bas"),
)


@dataclass(frozen=True)
class Personality:
    """Fiche de jeu : apparence et attitude de départ d'un personnage."""

    id: str
    label: str
    params: dict[str, Any]
    style: dict[str, str]


PERSONALITIES: tuple[Personality, ...] = (
    Personality(
        "ingenieur",
        "L'ingénieur",
        {
            "proportions": "adulte",
            "emotion": "explique",
            "pose": "explique",
            "outfit": "doudoune",
            "hair": "court",
            "beard": "courte",
            "glasses": "fines",
            "skin": "fonce",
        },
        {"fill": "#1E1F22", "accent": "#A3202E"},
    ),
    Personality(
        "ingenieur_terrain",
        "L'ingénieur sur le terrain",
        {
            "proportions": "adulte",
            "emotion": "neutre",
            "pose": "montre",
            "outfit": "gilet_hv",
            "hair": "court",
            "beard": "courte",
            "glasses": "protection",
            "hat": "casque",
            "skin": "fonce",
        },
        {"fill": "#FF5A1F", "accent": "#1B1B1E", "hat_color": "#F4F4F2"},
    ),
    Personality(
        "ingenieur_detente",
        "L'ingénieur décontracté",
        {
            "proportions": "adulte",
            "emotion": "joie",
            "pose": "salut",
            "outfit": "veste_jean",
            "hair": "court",
            "beard": "courte",
            "glasses": "rectangles",
            "skin": "fonce",
        },
        {"fill": "#3F6A9A", "accent": "#B3212C"},
    ),
    Personality(
        "presentateur",
        "Le présentateur",
        {"emotion": "explique", "pose": "explique", "outfit": "tshirt", "hair": "court", "skin": "fonce"},
        {"fill": "#E07A2E", "accent": "#2E5E8C"},
    ),
    Personality(
        "presentatrice",
        "La présentatrice",
        {"emotion": "joie", "pose": "salut", "outfit": "dashiki", "hair": "macarons", "skin": "brun"},
        {"fill": "#2F8F83", "accent": "#F2B630"},
    ),
    Personality(
        "scientifique",
        "Le scientifique",
        {
            "emotion": "explique",
            "pose": "index",
            "outfit": "blouse",
            "hair": "court",
            "beard": "bouc",
            "glasses": "rondes",
            "skin": "ebene",
        },
        {"fill": "#F4F6F8", "accent": "#3D7DD8"},
    ),
    Personality(
        "ironique",
        "L'ironique",
        {"emotion": "ironie", "pose": "bras_croises", "outfit": "sweat", "hair": "locks", "skin": "cuivre"},
        {"fill": "#4C6B3C", "accent": "#D9C27A"},
    ),
    Personality(
        "sceptique",
        "Le sceptique",
        {"emotion": "doute", "pose": "menton", "outfit": "chemise", "hair": "afro", "skin": "brun"},
        {"fill": "#7FA8D6", "accent": "#3B3A4A"},
    ),
    Personality(
        "rouspeteur",
        "Le râleur (toujours énervé)",
        {
            "emotion": "colere",
            "pose": "hanches",
            "outfit": "maillot",
            "hair": "tresses",
            "beard": "courte",
            "hat": "casquette",
            "skin": "fonce",
        },
        {"fill": "#C9302C", "accent": "#F5F5F5"},
    ),
)
PERSONALITY_BY_ID = {p.id: p for p in PERSONALITIES}

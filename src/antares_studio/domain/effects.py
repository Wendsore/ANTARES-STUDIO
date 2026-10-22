"""Effets visuels par objet (flou, lueur, ombre portée, réglages de couleur) et filtres de scène.

Les effets d'objet sont des clés ``fx_*`` du dictionnaire ``style`` : absentes, elles valent leur défaut
(aucun effet), si bien qu'un projet sans effet s'enregistre comme avant. Elles sont animables comme
toute propriété de style. Les filtres de scène (``scene.post``) s'appliquent à l'image entière, après
la transition : même rendu dans l'éditeur, l'image PNG et la vidéo.
"""

from __future__ import annotations

from typing import Any

from antares_studio.domain.kinds import ParamSpec

# objets sans dessin propre : pas d'effet (un groupe n'a pas d'image, la caméra cadre)
NO_EFFECT_KINDS = frozenset({"group", "camera"})

EFFECTS: tuple[ParamSpec, ...] = (
    ParamSpec("fx_blur", "float", 0.0, True, "Flou (px)", min=0, max=200),
    ParamSpec("fx_glow", "float", 0.0, True, "Lueur : rayon (px)", min=0, max=200),
    ParamSpec("fx_glow_color", "color", "#FFD27A", True, "Lueur : couleur"),
    ParamSpec("fx_glow_strength", "float", 1.0, True, "Lueur : intensité", min=0, max=4),
    ParamSpec("fx_shadow", "float", 0.0, True, "Ombre : opacité (0 → 1)", min=0, max=1),
    ParamSpec("fx_shadow_blur", "float", 12.0, True, "Ombre : flou (px)", min=0, max=200),
    ParamSpec("fx_shadow_dx", "float", 8.0, True, "Ombre : décalage X (px)", min=-500, max=500),
    ParamSpec("fx_shadow_dy", "float", 8.0, True, "Ombre : décalage Y (px)", min=-500, max=500),
    ParamSpec("fx_shadow_color", "color", "#000000", True, "Ombre : couleur"),
    ParamSpec("fx_brightness", "float", 0.0, True, "Luminosité (−1 → 1)", min=-1, max=1),
    ParamSpec("fx_contrast", "float", 1.0, True, "Contraste (1 = inchangé)", min=0, max=3),
    ParamSpec("fx_saturation", "float", 1.0, True, "Saturation (0 = noir et blanc)", min=0, max=3),
    ParamSpec("fx_chalk", "float", 0.0, True, "Texture craie (0 → 1)", min=0, max=1),
)
EFFECTS_BY_NAME: dict[str, ParamSpec] = {p.name: p for p in EFFECTS}


def supports_effects(kind: str) -> bool:
    return kind not in NO_EFFECT_KINDS


def effect_values(style: dict[str, Any]) -> dict[str, Any]:
    """Toutes les valeurs d'effet d'un style, défauts compris."""
    return {p.name: style.get(p.name, p.default) for p in EFFECTS}


def has_effects(style: dict[str, Any]) -> bool:
    v = effect_values(style)
    return (
        float(v["fx_blur"]) > 0.05
        or (float(v["fx_glow"]) > 0.05 and float(v["fx_glow_strength"]) > 0.0)
        or float(v["fx_shadow"]) > 0.0
        or abs(float(v["fx_brightness"])) > 1e-6
        or abs(float(v["fx_contrast"]) - 1.0) > 1e-6
        or abs(float(v["fx_saturation"]) - 1.0) > 1e-6
        or float(v["fx_chalk"]) > 0.0
    )


# --- préréglages d'effets d'objet (Bibliothèque > Effets) ------------------------------------------
OBJECT_LOOKS: dict[str, tuple[str, str, dict[str, Any]]] = {
    "glow_star": (
        "Lueur d'étoile",
        "Halo doré autour de l'objet : étoiles, Soleil, points lumineux.",
        {"fx_glow": 40.0, "fx_glow_color": "#FFD27A", "fx_glow_strength": 1.6},
    ),
    "glow_neon": (
        "Néon bleu",
        "Lueur bleue vive, pour les tracés et les textes de titre.",
        {"fx_glow": 18.0, "fx_glow_color": "#4FC3F7", "fx_glow_strength": 2.0},
    ),
    "drop_shadow": (
        "Ombre portée",
        "Ombre douce décalée : détache un texte ou un encadré du fond.",
        {"fx_shadow": 0.6, "fx_shadow_blur": 14.0, "fx_shadow_dx": 6.0, "fx_shadow_dy": 8.0},
    ),
    "soft_focus": (
        "Arrière-plan flou",
        "Flou marqué : met un objet au second plan sans le cacher.",
        {"fx_blur": 8.0},
    ),
    "muted": (
        "Estompé",
        "Moins de couleur et de contraste : objet secondaire, rappel d'une étape passée.",
        {"fx_saturation": 0.35, "fx_contrast": 0.8, "fx_brightness": -0.1},
    ),
    "black_white": ("Noir et blanc", "Objet en niveaux de gris.", {"fx_saturation": 0.0}),
    "vivid": (
        "Couleurs vives",
        "Saturation et contraste renforcés.",
        {"fx_saturation": 1.5, "fx_contrast": 1.15},
    ),
    "chalk": (
        "Craie",
        "Grain de craie sur le tableau : traits irréguliers, poudre qui accroche. Texte, formule, tracé.",
        {"fx_chalk": 0.65},
    ),
    "no_effect": ("Retirer les effets", "Remet tous les effets de l'objet à zéro.", {}),
}


# animations prédéfinies qui jouent sur les effets (identifiants de timeline.presets) : rangées aussi
# dans l'onglet Effets de la Bibliothèque
EFFECT_PRESETS: tuple[str, ...] = ("flash", "glow_pulse", "focus", "blink", "shake")


# --- filtres de scène (étalonnage) ---------------------------------------------------------------
SCENE_POST: tuple[ParamSpec, ...] = (
    ParamSpec("brightness", "float", 0.0, False, "Luminosité (−1 → 1)", min=-1, max=1),
    ParamSpec("contrast", "float", 1.0, False, "Contraste (1 = inchangé)", min=0, max=3),
    ParamSpec("saturation", "float", 1.0, False, "Saturation (0 = noir et blanc)", min=0, max=3),
    ParamSpec("temperature", "float", 0.0, False, "Température (−1 froid → 1 chaud)", min=-1, max=1),
    ParamSpec("sepia", "float", 0.0, False, "Sépia (0 → 1)", min=0, max=1),
    ParamSpec("vignette", "float", 0.0, False, "Vignettage (0 → 1)", min=0, max=1),
    ParamSpec("grain", "float", 0.0, False, "Grain de film (0 → 1)", min=0, max=1),
)
SCENE_POST_BY_NAME: dict[str, ParamSpec] = {p.name: p for p in SCENE_POST}

SCENE_LOOKS: dict[str, tuple[str, str, dict[str, float]]] = {
    "none": ("Aucun filtre", "Image telle que dessinée.", {}),
    "cinema": (
        "Cinéma",
        "Contraste doux, couleurs légèrement retenues, vignettage discret.",
        {"contrast": 1.12, "saturation": 0.9, "vignette": 0.35, "grain": 0.08},
    ),
    "deep_space": (
        "Espace profond",
        "Image plus froide et plus contrastée, bords assombris : scènes d'astronomie.",
        {"temperature": -0.35, "contrast": 1.2, "brightness": -0.05, "vignette": 0.45},
    ),
    "warm": ("Chaud", "Lumière dorée, accueillante.", {"temperature": 0.4, "saturation": 1.08}),
    "cold": ("Froid", "Lumière bleutée, clinique.", {"temperature": -0.45}),
    "black_white": ("Noir et blanc", "Niveaux de gris contrastés.", {"saturation": 0.0, "contrast": 1.15}),
    "retro": (
        "Archive (sépia)",
        "Teinte sépia, grain et vignettage : documents historiques.",
        {"sepia": 0.8, "grain": 0.25, "vignette": 0.5, "contrast": 0.95},
    ),
    "vivid": ("Vif", "Couleurs saturées pour les réseaux sociaux.", {"saturation": 1.35, "contrast": 1.1}),
}


def post_values(post: dict[str, Any]) -> dict[str, float]:
    return {p.name: float(post.get(p.name, p.default)) for p in SCENE_POST}


def post_is_neutral(post: dict[str, Any]) -> bool:
    v = post_values(post)
    return all(abs(v[p.name] - float(p.default)) < 1e-6 for p in SCENE_POST)

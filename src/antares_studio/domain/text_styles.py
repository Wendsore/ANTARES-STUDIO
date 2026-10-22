"""Styles d'écriture prêts à l'emploi (Bibliothèque > Effets) : police livrée, couleur, texture et façon
d'apparaître. Appliqués d'un double-clic aux textes, encadrés et équations sélectionnés ; seules les
propriétés que l'objet possède sont modifiées (un encadré n'a pas d'écriture progressive).

Chaque style remet aussi les effets d'objet à zéro avant d'appliquer les siens : passer de « Néon » à
« Craie » ne garde pas la lueur bleue.
"""

from __future__ import annotations

from typing import Any

TEXT_STYLE_KINDS = frozenset({"text", "callout", "formula"})

CHALK_WHITE = "#F4F1E8"

# identifiant -> (libellé, description, valeurs « params.x » / « style.x »)
TEXT_STYLES: dict[str, tuple[str, str, dict[str, Any]]] = {
    "chalk": (
        "Craie blanche (tableau)",
        "Écriture d'enseignant à la craie, lettre par lettre de gauche à droite. Sur un décor « Tableau ».",
        {
            "params.font_family": "Kalam",
            "params.write_style": "chalk",
            "style.fill": CHALK_WHITE,
            "style.fx_chalk": 0.6,
        },
    ),
    "chalk_yellow": (
        "Craie jaune (mise en valeur)",
        "Craie de couleur pour le résultat à retenir, la formule encadrée.",
        {
            "params.font_family": "Kalam",
            "params.write_style": "chalk",
            "style.fill": "#F6E27F",
            "style.fx_chalk": 0.6,
        },
    ),
    "chalk_blue": (
        "Craie bleue (annotation)",
        "Craie bleu clair pour les remarques et les flèches d'explication.",
        {
            "params.font_family": "Kalam",
            "params.write_style": "chalk",
            "style.fill": "#9ED4F2",
            "style.fx_chalk": 0.6,
        },
    ),
    "chalk_title": (
        "Titre gravé à la craie",
        "Grandes lettres crayonnées pour le titre au tableau.",
        {
            "params.font_family": "Fredericka the Great",
            "params.write_style": "chalk",
            "style.fill": CHALK_WHITE,
            "style.fx_chalk": 0.45,
        },
    ),
    "sketch": (
        "Crayonné (esquisse)",
        "Lettres doublées au crayon, aspect brouillon : idées, hypothèses.",
        {
            "params.font_family": "Cabin Sketch",
            "params.write_style": "chalk",
            "style.fill": CHALK_WHITE,
            "style.fx_chalk": 0.3,
        },
    ),
    "math_trace": (
        "Tracé mathématique (3Blue1Brown)",
        "Serif élégant ; le contour de chaque lettre se dessine puis se remplit.",
        {"params.font_family": "EB Garamond", "params.write_style": "trace", "style.fill": "#FFFFFF"},
    ),
    "marker": (
        "Feutre sur tableau blanc",
        "Gros feutre bleu marine, sur fond clair (« Papier quadrillé » ou blanc).",
        {"params.font_family": "Permanent Marker", "params.write_style": "chalk", "style.fill": "#1D3557"},
    ),
    "notebook": (
        "Cahier d'écolier (encre bleue)",
        "Écriture régulière à l'encre bleue, sur un décor « Cahier à lignes ».",
        {"params.font_family": "Patrick Hand", "params.write_style": "chalk", "style.fill": "#1F3A93"},
    ),
    "quick_notes": (
        "Notes rapides (stylo)",
        "Écriture vive et penchée, pour les annotations en marge. Sur fond clair.",
        {"params.font_family": "Caveat", "params.write_style": "chalk", "style.fill": "#263238"},
    ),
    "student": (
        "Écriture d'élève",
        "Écriture ronde et appliquée, ton amical. Sur fond clair.",
        {"params.font_family": "Gloria Hallelujah", "params.write_style": "chalk", "style.fill": "#37474F"},
    ),
    "typewriter": (
        "Machine à écrire (archives)",
        "Caractères frappés un à un avec curseur : documents historiques, dates, lettres.",
        {"params.font_family": "Special Elite", "params.write_style": "typewriter", "style.fill": "#F5F0E1"},
    ),
    "code": (
        "Terminal (code, données)",
        "Machine à écrire nette en vert terminal.",
        {"params.font_family": "Courier Prime", "params.write_style": "typewriter", "style.fill": "#7CF29A"},
    ),
    "youtube_title": (
        "Titre de vidéo (capitales)",
        "Hautes capitales avec ombre portée, mot par mot : miniatures et titres.",
        {
            "params.font_family": "Bebas Neue",
            "params.write_style": "words",
            "style.fill": "#FFFFFF",
            "style.fx_shadow": 0.7,
            "style.fx_shadow_blur": 10.0,
            "style.fx_shadow_dx": 5.0,
            "style.fx_shadow_dy": 6.0,
        },
    ),
    "neon": (
        "Néon",
        "Lettres lumineuses bleues, lettre par lettre en fondu.",
        {
            "params.font_family": "Montserrat",
            "params.write_style": "letters",
            "style.fill": "#E1F5FE",
            "style.fx_glow": 18.0,
            "style.fx_glow_color": "#4FC3F7",
            "style.fx_glow_strength": 1.8,
        },
    ),
    "quote": (
        "Citation (italique classique)",
        "Serif classique en italique, mot par mot : citations de savants, définitions.",
        {
            "params.font_family": "Lora",
            "params.italic": True,
            "params.write_style": "words",
            "style.fill": "#F5F0E1",
        },
    ),
    "plain": (
        "Style simple (par défaut)",
        "Retour à la police par défaut, en blanc, sans effet.",
        {"params.font_family": "DejaVu Sans", "params.write_style": "trace", "style.fill": "#FFFFFF"},
    ),
}


def style_values(style_id: str, kind: str) -> dict[str, Any]:
    """Valeurs du style ``style_id`` applicables à un objet ``kind`` (effets d'objet remis à zéro)."""
    from antares_studio.domain.effects import EFFECTS
    from antares_studio.domain.kinds import spec_for

    if style_id not in TEXT_STYLES or kind not in TEXT_STYLE_KINDS:
        return {}
    spec = spec_for(kind)
    params = {p.name for p in spec.params}
    style = {p.name for p in spec.style}
    values: dict[str, Any] = {f"style.{p.name}": p.default for p in EFFECTS}
    for path, value in TEXT_STYLES[style_id][2].items():
        group, _, name = path.partition(".")
        known = name in params if group == "params" else name in style or name.startswith("fx_")
        if known:
            values[path] = value
    if kind == "callout" and "style.fill" in values:  # encadré : la couleur du style va au texte
        values["style.text_color"] = values.pop("style.fill")
    return values

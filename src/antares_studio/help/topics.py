"""Rubriques du centre d'aide : fichiers Markdown locaux + sections générées depuis le code.

Les sections générées (``<!-- auto:objets -->`` …) sont produites à partir des catalogues réels
(types d'objets, animations, profils d'export, symboles des équations, modèles) : elles ne peuvent
pas diverger du logiciel. La liste des raccourcis, qui dépend de la fenêtre Qt, est fournie par
l'appelant via ``extra={"raccourcis": ...}``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

HELP_DIR = Path(__file__).resolve().parent.parent / "resources" / "help"
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "resources" / "examples"
AUTO = re.compile(r"<!--\s*auto:([a-z_-]+)\s*-->")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\((?!https?:|mailto:)([^)#\s]+\.md)(?:#[^)]*)?\)")


@dataclass(frozen=True)
class Topic:
    id: str
    section: str
    title: str
    keywords: str = ""  # synonymes pour la recherche


TOPICS: tuple[Topic, ...] = (
    Topic("bienvenue", "Bien démarrer", "Bienvenue dans ANTARES Studio", "accueil présentation"),
    Topic("installation", "Bien démarrer", "Installation, FFmpeg et diagnostics", "installer ffmpeg windows"),
    Topic("interface", "Bien démarrer", "L'espace de travail", "panneaux fenêtre dock menus"),
    Topic("tutoriels", "Bien démarrer", "Apprendre avec les tutoriels", "tutoriel guide apprendre"),
    Topic("premiere-video", "Bien démarrer", "Parcours complet : votre première vidéo", "p1 lune exemple"),
    Topic("projets", "Projets", "Projets, fichiers et dossiers", "ouvrir enregistrer nouveau antares"),
    Topic("sauvegarde", "Projets", "Sauvegarde automatique et récupération", "autosave crash panne"),
    Topic("canevas", "Créer", "Le canevas : sélectionner, déplacer, zoomer", "poignées zoom grille"),
    Topic("objets", "Créer", "Catalogue des objets", "forme cercle texte flèche"),
    Topic("inspecteur", "Créer", "L'Inspecteur", "propriétés couleur position"),
    Topic("scenes-et-calques", "Créer", "Scènes, calques et groupes", "ordre plan visibilité verrou"),
    Topic("bibliotheque", "Créer", "La Bibliothèque et les favoris", "recherche favori"),
    Topic(
        "effets-et-filtres",
        "Créer",
        "Effets et filtres",
        "lueur ombre flou glow étalonnage vignettage grain sépia post-production",
    ),
    Topic(
        "ecriture-et-craie",
        "Créer",
        "Écriture progressive, craie et styles d'écriture",
        "écrire lettre craie tableau noir police manuscrit machine à écrire 3blue1brown décor",
    ),
    Topic("modeles", "Créer", "Modèles pédagogiques", "template gabarit"),
    Topic("animations", "Animer", "Animations prédéfinies", "preset orbite apparition"),
    Topic("images-cles", "Animer", "Images clés et Timeline", "keyframe clé lecture"),
    Topic("narration", "Son et texte", "Narration audio", "voix son audio mp3 wav"),
    Topic("sous-titres", "Son et texte", "Sous-titres", "srt vtt accessibilité"),
    Topic(
        "bruitages", "Son et texte", "Bruitages et ambiances", "bruit son effet sonore whoosh ambiance cc0"
    ),
    Topic(
        "rigueur-scientifique",
        "Sciences",
        "Rigueur scientifique : représentation, échelle, sources",
        "échelle",
    ),
    Topic("equations", "Sciences", "Équations", "formule latex maths"),
    Topic("graphiques", "Sciences", "Graphiques de données (CSV)", "csv courbe données tableur"),
    Topic("kepler", "Sciences", "Orbites de Kepler et unités", "orbite ellipse verlet unités"),
    Topic("planete-3d", "Sciences", "Planète 3D avec Blender (facultatif)", "blender 3d planète"),
    Topic(
        "grilles-et-deformations",
        "Sciences",
        "Grilles, transformations et espace courbé",
        "grille matrice algèbre linéaire déformation espace-temps gravité onde relativité 3blue1brown",
    ),
    Topic("solides-3d", "Sciences", "Solides 3D", "cube sphère pyramide cylindre cône polyèdre tore 3d"),
    Topic("modeles-3d", "Sciences", "Modèles 3D (glTF)", "gltf glb 3d modèle objet import"),
    Topic("images", "Ressources", "Images importées", "png svg jpeg photo"),
    Topic("provenance-et-licences", "Ressources", "Provenance et licences", "licence droits auteur"),
    Topic("credits", "Ressources", "Crédits", "générique sources"),
    Topic(
        "export-video",
        "Exporter",
        "Exporter la vidéo",
        "mp4 rendu export youtube 4k prores png transparence wav mp3 lufs",
    ),
    Topic("ligne-de-commande", "Exporter", "Ligne de commande", "cli terminal selftest"),
    Topic("raccourcis", "Référence", "Raccourcis clavier", "clavier touches"),
    Topic("personnalisation", "Référence", "Thème, taille du texte et disposition", "clair sombre police"),
    Topic("depannage", "Référence", "Dépannage et messages d'erreur", "erreur problème bug"),
    Topic("glossaire", "Référence", "Glossaire", "définition vocabulaire"),
    Topic("limites", "Référence", "Ce qui n'est pas encore possible", "limites feuille de route"),
)
TOPICS_BY_ID: dict[str, Topic] = {t.id: t for t in TOPICS}
DEFAULT_TOPIC = "bienvenue"


def sections() -> list[tuple[str, list[Topic]]]:
    out: list[tuple[str, list[Topic]]] = []
    for t in TOPICS:
        if not out or out[-1][0] != t.section:
            out.append((t.section, []))
        out[-1][1].append(t)
    return out


def topic_path(topic_id: str) -> Path:
    return HELP_DIR / f"{topic_id}.md"


def raw_markdown(topic_id: str) -> str:
    return topic_path(topic_id).read_text(encoding="utf-8")


def topic_markdown(topic_id: str, extra: dict[str, str] | None = None) -> str:
    """Markdown d'une rubrique, sections automatiques développées ; ``KeyError`` si elle n'existe pas."""
    if topic_id not in TOPICS_BY_ID:
        raise KeyError(topic_id)
    given = extra or {}

    def expand(m: re.Match[str]) -> str:
        key = m.group(1)
        if key in given:
            return given[key]
        gen = GENERATED.get(key)
        return gen() if gen else "*(section indisponible dans cette version)*"

    return AUTO.sub(expand, raw_markdown(topic_id))


def internal_links(markdown: str) -> list[str]:
    """Rubriques citées par des liens relatifs ``[texte](rubrique.md)``."""
    return [m.group(1).removesuffix(".md") for m in LINK.finditer(markdown)]


# --- recherche --------------------------------------------------------------------------------------
def fold(text: str) -> str:
    """Minuscules sans accents, pour une recherche tolérante (« echelle » trouve « Échelle »)."""
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


def search(query: str, extra: dict[str, str] | None = None) -> list[tuple[Topic, int]]:
    """Rubriques contenant tous les mots de ``query`` ; score : titre (10) > mots-clés (5) > texte (1)."""
    words = [w for w in fold(query).split() if len(w) >= 2]
    if not words:
        return []
    results: list[tuple[Topic, int]] = []
    for t in TOPICS:
        title, keys = fold(t.title), fold(t.keywords)
        try:
            body = fold(topic_markdown(t.id, extra))
        except OSError:
            body = ""
        score = 0
        for w in words:
            s = 10 * title.count(w) + 5 * keys.count(w) + body.count(w)
            if s == 0:
                score = 0
                break
            score += s
        if score:
            results.append((t, score))
    return sorted(results, key=lambda r: -r[1])


def snippet(topic_id: str, query: str, width: int = 90) -> str:
    """Extrait du texte autour de la première occurrence d'un mot de ``query`` (sans balises Markdown)."""
    text = re.sub(r"[#*`>|_\[\]]", "", topic_markdown(topic_id))
    text = re.sub(r"\(([^)]*\.md|https?://[^)]*)\)", "", text)
    text = re.sub(r"\s+", " ", text)
    folded = fold(text)
    words = [w for w in fold(query).split() if len(w) >= 2]
    pos = min((folded.find(w) for w in words if folded.find(w) >= 0), default=-1)
    if pos < 0:
        return text[:width].strip() + "…"
    start = max(0, pos - width // 3)
    return ("…" if start else "") + text[start : start + width].strip() + "…"


# --- sections générées ------------------------------------------------------------------------------
def _objects() -> str:
    from antares_studio.domain.kinds import KINDS

    lines = ["| Objet | Réglages propres | Animables |", "|---|---|---|"]
    for spec in KINDS.values():
        params = ", ".join(p.label or p.name for p in spec.params) or "—"
        anim = ", ".join(p.label or p.name for p in (*spec.params, *spec.style) if p.animatable) or "—"
        lines.append(f"| **{spec.label}** | {params} | {anim} |")
    return "\n".join(lines)


def _animations() -> str:
    from antares_studio.timeline.presets import PRESETS

    out = []
    for spec in PRESETS.values():
        params = ", ".join(p.label for p in spec.params)
        out.append(f"### {spec.label}\n\n{spec.description}\n\n*Réglages :* {params}.\n")
    return "\n".join(out)


def _profiles() -> str:
    from antares_studio.rendering.plan import PROFILES

    lines = [
        "| Profil | Groupe | Fichier | Image | Identifiant (`--profile`) |",
        "|---|---|---|---|---|",
    ]
    for p in PROFILES.values():
        frame = f"{p.width} × {p.height}" + (" imposé" if p.fixed_frame else "") if p.has_video else "—"
        fps = f", {p.max_fps:g} images/s au plus" if p.max_fps else ""
        alpha = ", transparence possible" if p.alpha else ""
        sound = "" if p.has_audio else ", sans son"
        file = "dossier d'images" if p.is_sequence else f"`{p.suffix}`"
        lines.append(f"| **{p.label}** | {p.group} | {file}{sound} | {frame}{fps}{alpha} | `{p.id}` |")
    return "\n".join(lines)


def _effects() -> str:
    from antares_studio.domain.effects import EFFECT_PRESETS, OBJECT_LOOKS
    from antares_studio.timeline.presets import PRESETS

    lines = ["| Effet d'objet | Usage |", "|---|---|"]
    lines += [f"| **{label}** | {desc} |" for label, desc, _v in OBJECT_LOOKS.values()]
    lines += ["", "Animations d'effet :", ""]
    lines += [f"- **{PRESETS[k].label}** — {PRESETS[k].description}" for k in EFFECT_PRESETS]
    return "\n".join(lines)


def _scene_looks() -> str:
    from antares_studio.domain.effects import SCENE_LOOKS

    lines = ["| Filtre de scène | Rendu |", "|---|---|"]
    lines += [f"| **{label}** | {desc} |" for label, desc, _v in SCENE_LOOKS.values()]
    return "\n".join(lines)


def _sounds() -> str:
    from antares_studio.audio import sfx

    out: list[str] = []
    for cat in sfx.CATEGORIES:
        out += [f"### {cat}", "", "| Son | Usage |", "|---|---|"]
        out += [f"| **{s.label}** | {s.description} |" for s in sfx.SOUNDS.values() if s.category == cat]
        out.append("")
    return "\n".join(out).rstrip()


def _symbols() -> str:
    from antares_studio.science.formula import SYMBOLS

    items = [f"`\\{k}` → {v}" for k, v in SYMBOLS.items()]
    rows = ["| Commande | | Commande | | Commande | |", "|---|---|---|---|---|---|"]
    for i in range(0, len(items), 3):
        chunk = [x.split(" → ") for x in items[i : i + 3]]
        cells = [c for pair in chunk for c in pair]
        cells += [""] * (6 - len(cells))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def _templates() -> str:
    from antares_studio.resources.templates import TEMPLATES

    return "\n".join(f"- **{label}**" for label, _builder in TEMPLATES.values())


def _example_files() -> str:
    files = sorted(p.name for p in EXAMPLES_DIR.glob("*.csv"))
    return "\n".join(f"- `{name}`" for name in files) or "- (aucun)"


def _tutorials() -> str:
    from antares_studio.help.tutorials import TUTORIALS

    return "\n".join(f"- **{t.title}** ({t.minutes} min) — {t.summary}" for t in TUTORIALS)


def _text_styles() -> str:
    from antares_studio.domain.kinds import WRITE_STYLES
    from antares_studio.domain.text_styles import TEXT_STYLES

    ways = dict(WRITE_STYLES)
    lines = ["| Style | Police | Écriture | Usage |", "|---|---|---|---|"]
    for label, desc, values in TEXT_STYLES.values():
        font = values.get("params.font_family", "—")
        way = ways.get(str(values.get("params.write_style", "")), "—").split(" (")[0]
        lines.append(f"| **{label}** | {font} | {way} | {desc} |")
    return "\n".join(lines)


def _fonts() -> str:
    from antares_studio.resources.fonts import BUNDLED_FONTS

    lines = ["| Police | Famille | Usage | Licence |", "|---|---|---|---|"]
    lines += [f"| **{f.family}** | {f.category} | {f.usage} | {f.license} |" for f in BUNDLED_FONTS]
    return "\n".join(lines)


def _backdrops() -> str:
    from antares_studio.domain.model import BACKDROPS

    return "\n".join(f"- **{label}**" for key, label in BACKDROPS.items() if key)


def _solids() -> str:
    from antares_studio.domain.kinds import SOLID_SHAPES

    return ", ".join(f"**{label}**" for _shape, label in SOLID_SHAPES) + "."


GENERATED = {
    "objets": _objects,
    "animations": _animations,
    "profils": _profiles,
    "symboles": _symbols,
    "modeles": _templates,
    "exemples": _example_files,
    "tutoriels": _tutorials,
    "effets": _effects,
    "filtres": _scene_looks,
    "sons": _sounds,
    "styles-ecriture": _text_styles,
    "polices": _fonts,
    "decors": _backdrops,
    "solides": _solids,
}

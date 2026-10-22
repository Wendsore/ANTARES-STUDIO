"""Catalogue des types de nœuds : paramètres par défaut, propriétés animables, validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from antares_studio.domain.colors import is_color


@dataclass(frozen=True)
class ParamSpec:
    name: str
    type: str  # "float" | "int" | "bool" | "str" | "color" | "vec2" | "points" | "asset"
    default: Any
    animatable: bool = False
    label: str = ""  # libellé FR pour l'inspecteur
    min: float | None = None
    max: float | None = None
    choices: tuple[tuple[str, str], ...] = ()  # (valeur, libellé FR) : liste déroulante dans l'inspecteur


@dataclass(frozen=True)
class KindSpec:
    kind: str
    label: str
    params: tuple[ParamSpec, ...] = ()
    style: tuple[ParamSpec, ...] = ()
    container: bool = False
    extra_animatable: tuple[str, ...] = field(default_factory=tuple)

    def default_params(self) -> dict[str, Any]:
        return {p.name: _copy(p.default) for p in self.params}

    def default_style(self) -> dict[str, Any]:
        return {p.name: _copy(p.default) for p in self.style}


def _copy(v: Any) -> Any:
    return list(v) if isinstance(v, list) else v


_FILL = ParamSpec("fill", "color", "#2677B8", animatable=True, label="Remplissage")
_STROKE = ParamSpec("stroke", "color", "#FFFFFF00", animatable=True, label="Contour")
_STROKE_W = ParamSpec("stroke_width", "float", 0.0, animatable=True, label="Épaisseur du contour", min=0)
_DASH = ParamSpec("dash", "bool", False, label="Pointillés")

_SHAPE_STYLE = (_FILL, _STROKE, _STROKE_W, _DASH)
_LINE_STYLE = (
    ParamSpec("stroke", "color", "#F2A93B", animatable=True, label="Couleur"),
    ParamSpec("stroke_width", "float", 4.0, animatable=True, label="Épaisseur", min=0),
    _DASH,
)

KINDS: dict[str, KindSpec] = {
    spec.kind: spec
    for spec in (
        KindSpec(
            "circle",
            "Cercle",
            params=(ParamSpec("radius", "float", 80.0, True, "Rayon", min=0),),
            style=_SHAPE_STYLE,
        ),
        KindSpec(
            "ellipse",
            "Ellipse",
            params=(
                ParamSpec("rx", "float", 120.0, True, "Rayon horizontal", min=0),
                ParamSpec("ry", "float", 70.0, True, "Rayon vertical", min=0),
            ),
            style=_SHAPE_STYLE,
        ),
        KindSpec(
            "rect",
            "Rectangle",
            params=(
                ParamSpec("width", "float", 200.0, True, "Largeur", min=0),
                ParamSpec("height", "float", 120.0, True, "Hauteur", min=0),
                ParamSpec("corner_radius", "float", 0.0, True, "Arrondi", min=0),
            ),
            style=_SHAPE_STYLE,
        ),
        KindSpec(
            "polygon",
            "Polygone",
            params=(
                ParamSpec("points", "points", [[-60.0, 50.0], [60.0, 50.0], [0.0, -60.0]], False, "Sommets"),
                ParamSpec("closed", "bool", True, False, "Fermé"),
            ),
            style=_SHAPE_STYLE,
        ),
        KindSpec(
            "star",
            "Étoile",
            params=(
                ParamSpec("points_count", "int", 5, False, "Branches", min=3, max=24),
                ParamSpec("outer_radius", "float", 60.0, True, "Rayon externe", min=0),
                ParamSpec("inner_radius", "float", 25.0, True, "Rayon interne", min=0),
            ),
            style=(
                ParamSpec("fill", "color", "#FFD966", animatable=True, label="Remplissage"),
                _STROKE,
                _STROKE_W,
            ),
        ),
        KindSpec(
            "line",
            "Ligne",
            params=(ParamSpec("end", "vec2", [200.0, 0.0], True, "Extrémité"),),
            style=_LINE_STYLE,
        ),
        KindSpec(
            "arrow",
            "Flèche",
            params=(
                ParamSpec("end", "vec2", [200.0, 0.0], True, "Extrémité"),
                ParamSpec("head_size", "float", 18.0, True, "Taille de la pointe", min=0),
            ),
            style=_LINE_STYLE,
        ),
        KindSpec(
            "text",
            "Texte",
            params=(
                ParamSpec("text", "str", "Texte", False, "Texte"),
                ParamSpec("font_family", "str", "DejaVu Sans", False, "Police"),
                ParamSpec("font_size", "float", 48.0, True, "Taille", min=1),
                ParamSpec("bold", "bool", False, False, "Gras"),
                ParamSpec("italic", "bool", False, False, "Italique"),
                ParamSpec("align", "str", "center", False, "Alignement"),
                ParamSpec("max_width", "float", 0.0, False, "Largeur max (0 = libre)", min=0),
            ),
            style=(
                ParamSpec("fill", "color", "#FFFFFF", animatable=True, label="Couleur"),
                ParamSpec("stroke", "color", "#00000000", animatable=True, label="Contour"),
                ParamSpec("stroke_width", "float", 0.0, animatable=True, label="Épaisseur du contour", min=0),
            ),
        ),
        KindSpec(
            "callout",
            "Encadré (légende, avertissement)",
            params=(
                ParamSpec("text", "str", "Schéma : distances et tailles non à l'échelle", False, "Texte"),
                ParamSpec("font_family", "str", "DejaVu Sans", False, "Police"),
                ParamSpec("font_size", "float", 30.0, True, "Taille", min=1),
                ParamSpec("bold", "bool", False, False, "Gras"),
                ParamSpec("padding", "float", 18.0, True, "Marge intérieure", min=0),
                ParamSpec("corner_radius", "float", 10.0, False, "Arrondi", min=0),
                ParamSpec("max_width", "float", 0.0, False, "Largeur max (0 = libre)", min=0),
            ),
            style=(
                ParamSpec("fill", "color", "#263238CC", animatable=True, label="Fond"),
                ParamSpec("text_color", "color", "#FFFFFF", animatable=True, label="Couleur du texte"),
                ParamSpec("stroke", "color", "#F2A93B", animatable=True, label="Bordure"),
                ParamSpec(
                    "stroke_width", "float", 2.0, animatable=True, label="Épaisseur de la bordure", min=0
                ),
            ),
        ),
        KindSpec(
            "image",
            "Image",
            params=(
                ParamSpec("asset_id", "asset", "", False, "Ressource"),
                ParamSpec("width", "float", 300.0, True, "Largeur", min=0),
                ParamSpec("height", "float", 0.0, True, "Hauteur (0 = proportionnelle)", min=0),
            ),
            style=(ParamSpec("tint", "color", "#FFFFFF00", animatable=True, label="Teinte"),),
        ),
        KindSpec(
            "formula",
            "Équation (formule)",
            params=(
                ParamSpec("text", "str", "E = m c^{2}", False, "Formule"),
                ParamSpec("font_family", "str", "DejaVu Sans", False, "Police"),
                ParamSpec("font_size", "float", 56.0, True, "Taille", min=1),
                ParamSpec("italic", "bool", True, False, "Variables en italique"),
                ParamSpec("morph_to", "str", "", False, "Transformer en (formule cible)"),
                ParamSpec("morph", "float", 0.0, True, "Transformation (0 → 1)", min=0, max=1),
            ),
            style=(
                ParamSpec("fill", "color", "#FFFFFF", animatable=True, label="Couleur"),
                ParamSpec("background", "color", "#00000000", animatable=True, label="Fond"),
            ),
        ),
        KindSpec(
            "chart",
            "Graphique (courbe de données)",
            params=(
                ParamSpec("data_asset_id", "asset", "", False, "Données (CSV)"),
                ParamSpec(
                    "chart_type",
                    "str",
                    "line",
                    False,
                    "Représentation",
                    choices=(
                        ("line", "Courbe"),
                        ("bars", "Barres (une par ligne)"),
                        ("histogram", "Histogramme"),
                    ),
                ),
                ParamSpec("bins", "int", 10, False, "Classes de l'histogramme", min=1, max=200),
                ParamSpec("x_column", "str", "", False, "Colonne X"),
                ParamSpec("y_column", "str", "", False, "Colonne Y"),
                ParamSpec("width", "float", 640.0, True, "Largeur", min=10),
                ParamSpec("height", "float", 400.0, True, "Hauteur", min=10),
                ParamSpec("title", "str", "", False, "Titre"),
                ParamSpec("x_min", "float", 0.0, False, "X min (0 = auto)"),
                ParamSpec("x_max", "float", 0.0, False, "X max (0 = auto)"),
                ParamSpec("y_min", "float", 0.0, False, "Y min (0 = auto)"),
                ParamSpec("y_max", "float", 0.0, False, "Y max (0 = auto)"),
                ParamSpec("progress", "float", 1.0, True, "Progression du tracé (0–1)", min=0, max=1),
                ParamSpec("line_width", "float", 3.0, True, "Épaisseur de la courbe", min=0),
                ParamSpec("show_points", "bool", False, False, "Afficher les points"),
                ParamSpec("show_grid", "bool", True, False, "Grille"),
                ParamSpec("font_size", "float", 18.0, False, "Taille des libellés", min=4),
            ),
            style=(
                ParamSpec("stroke", "color", "#4FC3F7", animatable=True, label="Couleur de la courbe"),
                ParamSpec("fill", "color", "#0B102080", animatable=True, label="Fond"),
                ParamSpec("axis_color", "color", "#CFD8DC", animatable=True, label="Axes et texte"),
            ),
        ),
        KindSpec(
            "image_sequence",
            "Séquence d'images (rendu 3D)",
            params=(
                ParamSpec("sequence_asset_id", "asset", "", False, "Séquence (dossier)"),
                ParamSpec("frame_count", "int", 1, False, "Nombre d'images", min=1),
                ParamSpec("frame_index", "float", 0.0, True, "Image affichée (0 = première)", min=0),
                ParamSpec("width", "float", 400.0, True, "Largeur", min=0),
                ParamSpec("height", "float", 0.0, True, "Hauteur (0 = proportionnelle)", min=0),
            ),
            style=(ParamSpec("tint", "color", "#FFFFFF00", animatable=True, label="Teinte"),),
        ),
        KindSpec(
            "model3d",
            "Modèle 3D (glTF)",
            params=(
                ParamSpec("model_asset_id", "asset", "", False, "Modèle (.glb)"),
                ParamSpec("size", "float", 400.0, True, "Taille à l'écran", min=1),
                ParamSpec("yaw_deg", "float", 30.0, True, "Rotation horizontale (°)"),
                ParamSpec("pitch_deg", "float", 20.0, True, "Inclinaison (°)"),
            ),
        ),
        KindSpec("group", "Groupe", container=True),
        KindSpec(
            "camera",
            "Caméra (cadrage animé)",
            # position = point visé (centre de l'image), rotation = inclinaison du cadre
            params=(ParamSpec("zoom", "float", 1.0, True, "Zoom (1 = cadre entier)", min=0.05, max=50.0),),
        ),
        KindSpec(
            "orbit_path",
            "Orbite (tracé)",
            params=(ParamSpec("radius", "float", 300.0, True, "Rayon", min=0),),
            style=(
                ParamSpec("stroke", "color", "#FFFFFF40", animatable=True, label="Couleur"),
                ParamSpec("stroke_width", "float", 2.0, animatable=True, label="Épaisseur", min=0),
                ParamSpec("dash", "bool", True, label="Pointillés"),
            ),
        ),
    )
}

BASE_ANIMATABLE: tuple[str, ...] = (
    "position.x",
    "position.y",
    "rotation_deg",
    "scale.x",
    "scale.y",
    "opacity",
    "visible",
)

BASE_LABELS: dict[str, str] = {
    "position.x": "Position X",
    "position.y": "Position Y",
    "rotation_deg": "Rotation (°)",
    "scale.x": "Échelle X",
    "scale.y": "Échelle Y",
    "opacity": "Opacité",
    "visible": "Visible",
}


def spec_for(kind: str) -> KindSpec:
    try:
        return KINDS[kind]
    except KeyError:
        raise ValueError(f"type de nœud inconnu : {kind!r}") from None


def animatable_properties(kind: str) -> list[str]:
    spec = spec_for(kind)
    props = list(BASE_ANIMATABLE)
    props += [f"params.{p.name}" for p in spec.params if p.animatable]
    props += [f"style.{p.name}" for p in spec.style if p.animatable]
    from antares_studio.domain.effects import EFFECTS, supports_effects

    if supports_effects(kind):
        props += [f"style.{p.name}" for p in EFFECTS if p.animatable]
    return props


def property_label(kind: str, path: str) -> str:
    if path in BASE_LABELS:
        return BASE_LABELS[path]
    spec = spec_for(kind)
    group, _, name = path.partition(".")
    for p in spec.params if group == "params" else spec.style if group == "style" else ():
        if p.name == name:
            return p.label or p.name
    from antares_studio.domain.effects import EFFECTS_BY_NAME

    if group == "style" and name in EFFECTS_BY_NAME:
        return EFFECTS_BY_NAME[name].label
    return path


def check_param_value(spec: ParamSpec, value: Any) -> str | None:
    """Retourne un message d'erreur ou None si la valeur respecte ``spec``."""
    t = spec.type
    if t == "float":
        if isinstance(value, bool) or not isinstance(value, int | float):
            return f"{spec.name} : nombre attendu"
        if value != value or value in (float("inf"), float("-inf")):
            return f"{spec.name} : nombre non fini"
        if spec.min is not None and value < spec.min:
            return f"{spec.name} : minimum {spec.min}"
        if spec.max is not None and value > spec.max:
            return f"{spec.name} : maximum {spec.max}"
    elif t == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            return f"{spec.name} : entier attendu"
        if spec.min is not None and value < spec.min:
            return f"{spec.name} : minimum {spec.min}"
        if spec.max is not None and value > spec.max:
            return f"{spec.name} : maximum {spec.max}"
    elif t == "bool":
        if not isinstance(value, bool):
            return f"{spec.name} : booléen attendu"
    elif t in ("str", "asset"):
        if not isinstance(value, str):
            return f"{spec.name} : texte attendu"
        if spec.choices and value not in {c for c, _l in spec.choices}:
            return f"{spec.name} : valeur parmi {', '.join(c for c, _l in spec.choices)} attendue"
    elif t == "color":
        if not is_color(value):
            return f"{spec.name} : couleur #RRGGBB[AA] attendue"
    elif t == "vec2":
        if not (isinstance(value, list) and len(value) == 2 and all(_finite(v) for v in value)):
            return f"{spec.name} : couple [x, y] attendu"
    elif t == "points":
        if not (
            isinstance(value, list)
            and all(isinstance(p, list) and len(p) == 2 and all(_finite(v) for v in p) for p in value)
        ):
            return f"{spec.name} : liste de couples [x, y] attendue"
    return None


def _finite(v: Any) -> bool:
    return (
        isinstance(v, int | float)
        and not isinstance(v, bool)
        and v == v
        and v not in (float("inf"), float("-inf"))
    )

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

# écriture progressive des textes et des formules (``rendering.writing``)
WRITE_STYLES: tuple[tuple[str, str], ...] = (
    ("trace", "Tracé puis remplissage (façon 3Blue1Brown)"),
    ("chalk", "Craie : chaque lettre de gauche à droite"),
    ("typewriter", "Machine à écrire (avec curseur)"),
    ("letters", "Lettres qui apparaissent en fondu"),
    ("words", "Mots qui apparaissent en fondu"),
)
_WRITE = ParamSpec("write", "float", 1.0, True, "Écriture (0 → 1)", min=0, max=1)
_WRITE_STYLE = ParamSpec("write_style", "str", "trace", False, "Façon d'écrire", choices=WRITE_STYLES)

GRID_WARPS: tuple[tuple[str, str], ...] = (
    ("none", "Aucune"),
    ("gravity", "Puits de gravité (masse au centre)"),
    ("wave", "Onde (gravitationnelle)"),
    ("swirl", "Tourbillon"),
)
SOLID_SHAPES: tuple[tuple[str, str], ...] = (
    ("cube", "Cube"),
    ("box", "Pavé droit"),
    ("sphere", "Sphère"),
    ("cylinder", "Cylindre"),
    ("cone", "Cône"),
    ("pyramid", "Pyramide à base carrée"),
    ("tetrahedron", "Tétraèdre"),
    ("octahedron", "Octaèdre"),
    ("icosahedron", "Icosaèdre"),
    ("torus", "Tore"),
)
SOLID_MODES: tuple[tuple[str, str], ...] = (
    ("shaded_edges", "Faces ombrées et arêtes"),
    ("shaded", "Faces ombrées"),
    ("wireframe", "Fil de fer (arêtes cachées en pointillé)"),
    ("transparent", "Verre (faces transparentes)"),
)
# --- astres, cartes, ciel, ondes, optique, phénomènes cosmiques (ADR-0009) ---
BODY_CHOICES: tuple[tuple[str, str], ...] = (
    ("sun", "Soleil"),
    ("mercury", "Mercure"),
    ("venus", "Vénus"),
    ("earth", "Terre"),
    ("moon", "Lune"),
    ("mars", "Mars"),
    ("jupiter", "Jupiter"),
    ("saturn", "Saturne"),
    ("uranus", "Uranus"),
    ("neptune", "Neptune"),
    ("star", "Étoile (couleur selon sa température)"),
    ("custom", "Texture personnelle (carte équirectangulaire)"),
)
TIDE_MODES: tuple[tuple[str, str], ...] = (
    ("ocean", "Océans : bourrelets autour de l'astre"),
    ("body", "Astre entier étiré (déformation exagérée)"),
)
PROJECTIONS: tuple[tuple[str, str], ...] = (
    ("equal_earth", "Equal Earth (aires respectées)"),
    ("equirectangular", "Équirectangulaire (plate carrée)"),
    ("mercator", "Mercator (angles respectés)"),
)
MAP_STYLES: tuple[tuple[str, str], ...] = (
    ("continents", "Continents en couleurs"),
    ("political", "Pays (frontières)"),
    ("outline", "Contours seuls"),
    ("satellite", "Image satellite (jour)"),
    ("night", "La Terre de nuit (lumières des villes)"),
)
CONTINENT_CHOICES: tuple[tuple[str, str], ...] = (
    ("", "Aucun"),
    ("Africa", "Afrique"),
    ("Asia", "Asie"),
    ("Europe", "Europe"),
    ("North America", "Amérique du Nord"),
    ("South America", "Amérique du Sud"),
    ("Oceania", "Océanie"),
    ("Antarctica", "Antarctique"),
)
WAVE_MODES: tuple[tuple[str, str], ...] = (
    ("fronts", "Fronts d'onde (effet Doppler, cône de Mach)"),
    ("field", "Champ d'interférences (sources cohérentes)"),
    ("string", "Corde : onde progressive ou stationnaire"),
)
FIELD_DISPLAYS: tuple[tuple[str, str], ...] = (
    ("instant", "Valeur instantanée (crêtes et creux)"),
    ("intensity", "Intensité moyenne (franges)"),
)
RAY_MODES: tuple[tuple[str, str], ...] = (
    ("beam", "Faisceau lumineux"),
    ("wave", "Onde (sinusoïde le long du rayon)"),
    ("packets", "Paquets d'onde qui voyagent"),
    ("photons", "Photons (points lumineux)"),
    ("dashed", "Rayon en pointillés (tracé géométrique)"),
    ("arrows", "Rayon fléché (sens de propagation)"),
)
OPTIC_ELEMENTS: tuple[tuple[str, str], ...] = (
    ("laser", "Laser"),
    ("lamp", "Lampe (source)"),
    ("mirror", "Miroir"),
    ("beam_splitter", "Lame séparatrice (semi-réfléchissante)"),
    ("lens_convex", "Lentille convergente"),
    ("lens_concave", "Lentille divergente"),
    ("double_slit", "Plaque à deux fentes"),
    ("single_slit", "Plaque à une fente"),
    ("screen", "Écran"),
    ("detector", "Détecteur de photons"),
    ("prism", "Prisme"),
    ("polarizer", "Polariseur"),
)
IMPACT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("two_slits", "Deux fentes : interférences"),
    ("one_slit", "Une fente : diffraction"),
    ("which_path", "Chemin mesuré : pas d'interférence"),
    ("uniform", "Uniforme"),
)
PARTICLE_MODES: tuple[tuple[str, str], ...] = (
    ("explosion", "Explosion (éclats projetés)"),
    ("shell", "Coquille de supernova en expansion"),
    ("nebula", "Nébuleuse (reste de supernova)"),
    ("accretion", "Disque d'accrétion (matière en orbite)"),
)
LIGHT_MODES: tuple[tuple[str, str], ...] = (
    ("halo", "Halo lumineux"),
    ("spot", "Projecteur (cône de lumière)"),
    ("darken", "Pénombre : seul un cercle reste éclairé"),
    ("rays", "Rayons (soleil, éclat)"),
)
_TIME = ParamSpec("time_s", "float", 0.0, True, "Temps (s) — animez-le", min=0)

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
                _WRITE,
                _WRITE_STYLE,
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
                _WRITE,
                _WRITE_STYLE,
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
        KindSpec(
            "grid",
            "Grille (plan, transformation, déformation)",
            params=(
                ParamSpec("width", "float", 1600.0, True, "Largeur du cadre", min=10),
                ParamSpec("height", "float", 900.0, True, "Hauteur du cadre", min=10),
                ParamSpec("step", "float", 100.0, True, "Pas de la grille (px par unité)", min=5),
                ParamSpec("progress", "float", 1.0, True, "Tracé de la grille (0 → 1)", min=0, max=1),
                ParamSpec("m_a", "float", 1.0, True, "Matrice a (î en x)", min=-20, max=20),
                ParamSpec("m_b", "float", 0.0, True, "Matrice b (ĵ en x)", min=-20, max=20),
                ParamSpec("m_c", "float", 0.0, True, "Matrice c (î en y)", min=-20, max=20),
                ParamSpec("m_d", "float", 1.0, True, "Matrice d (ĵ en y)", min=-20, max=20),
                ParamSpec("warp", "str", "none", False, "Déformation", choices=GRID_WARPS),
                ParamSpec("warp_amount", "float", 0.0, True, "Intensité de la déformation", min=-3, max=3),
                ParamSpec("warp_radius", "float", 250.0, True, "Rayon de la déformation (px)", min=10),
                ParamSpec("warp_phase", "float", 0.0, True, "Phase de l'onde (tours)"),
                ParamSpec("perspective", "bool", False, False, "Vue en perspective (nappe inclinée)"),
                ParamSpec("tilt_deg", "float", 60.0, True, "Inclinaison de la vue (°)", min=0, max=85),
                ParamSpec("show_axes", "bool", True, False, "Axes"),
                ParamSpec("show_basis", "bool", False, False, "Vecteurs de base î et ĵ"),
                ParamSpec("show_ghost", "bool", True, False, "Grille d'origine en filigrane"),
            ),
            style=(
                ParamSpec("stroke", "color", "#4FC3F7", animatable=True, label="Lignes"),
                ParamSpec("stroke_width", "float", 2.0, animatable=True, label="Épaisseur", min=0),
                ParamSpec("axis_color", "color", "#FFFFFF", animatable=True, label="Axes"),
                ParamSpec("ghost_color", "color", "#FFFFFF30", animatable=True, label="Filigrane"),
                ParamSpec("i_color", "color", "#83C167", animatable=True, label="Vecteur î"),
                ParamSpec("j_color", "color", "#FC6255", animatable=True, label="Vecteur ĵ"),
            ),
        ),
        KindSpec(
            "solid3d",
            "Solide 3D (cube, sphère, pyramide…)",
            params=(
                ParamSpec("shape", "str", "cube", False, "Forme", choices=SOLID_SHAPES),
                ParamSpec("size", "float", 300.0, True, "Taille à l'écran", min=1),
                ParamSpec("size_x", "float", 1.6, True, "Pavé : longueur relative", min=0.05, max=20),
                ParamSpec("size_y", "float", 1.0, True, "Pavé : hauteur relative", min=0.05, max=20),
                ParamSpec("size_z", "float", 0.8, True, "Pavé : profondeur relative", min=0.05, max=20),
                ParamSpec("yaw_deg", "float", 35.0, True, "Rotation horizontale (°)"),
                ParamSpec("pitch_deg", "float", 25.0, True, "Inclinaison (°)"),
                ParamSpec("roll_deg", "float", 0.0, True, "Roulis (°)"),
                ParamSpec("render_mode", "str", "shaded_edges", False, "Rendu", choices=SOLID_MODES),
                ParamSpec("perspective", "float", 0.0, True, "Perspective (0 = aucune)", min=0, max=1),
                # valeurs par défaut = éclairage fixe d'avant la phase 13 (haut-gauche, vers l'avant)
                ParamSpec("light_az_deg", "float", -29.74488129694223, True, "Lumière : direction (°)"),
                ParamSpec(
                    "light_el_deg", "float", 36.65693295448205, True, "Lumière : hauteur (°)", min=-90, max=90
                ),
                ParamSpec("ambient", "float", 0.3, True, "Lumière ambiante", min=0, max=1),
            ),
            style=(
                ParamSpec("fill", "color", "#2677B8", animatable=True, label="Faces"),
                ParamSpec("stroke", "color", "#FFFFFF", animatable=True, label="Arêtes"),
                ParamSpec("stroke_width", "float", 2.5, animatable=True, label="Épaisseur des arêtes", min=0),
            ),
        ),
        KindSpec(
            "celestial",
            "Astre (planète, Lune, Soleil, étoile)",
            params=(
                ParamSpec("body", "str", "earth", False, "Astre", choices=BODY_CHOICES),
                ParamSpec("size", "float", 300.0, True, "Diamètre à l'écran", min=1),
                ParamSpec("spin_deg", "float", 0.0, True, "Rotation sur lui-même (°)"),
                ParamSpec("tilt_deg", "float", 0.0, True, "Inclinaison de l'axe (°)"),
                ParamSpec("pitch_deg", "float", 0.0, True, "Vu depuis (°) : 0 équateur, 90 pôle nord"),
                ParamSpec("lit", "bool", True, False, "Éclairé par une source"),
                ParamSpec(
                    "light_az_deg", "float", 50.0, True, "Lumière : direction (°) — 0 de face, 180 de dos"
                ),
                ParamSpec("light_el_deg", "float", 10.0, True, "Lumière : hauteur (°)", min=-90, max=90),
                ParamSpec("ambient", "float", 0.04, True, "Lumière ambiante (côté nuit)", min=0, max=1),
                ParamSpec("night_lights", "bool", True, False, "Terre : lumières des villes la nuit"),
                ParamSpec("clouds", "float", 0.8, True, "Terre : nuages", min=0, max=1),
                ParamSpec("cloud_shift_deg", "float", 0.0, True, "Terre : dérive des nuages (°)"),
                ParamSpec("atmosphere", "float", 1.0, True, "Atmosphère (liseré)", min=0, max=2),
                ParamSpec("surface", "bool", False, False, "Vénus : surface sous les nuages"),
                ParamSpec("rings", "bool", True, False, "Saturne : anneaux"),
                ParamSpec(
                    "temperature_k", "float", 5772.0, True, "Étoile : température (K)", min=500, max=100000
                ),
                ParamSpec(
                    "limb_darkening", "float", 0.6, True, "Étoile : assombrissement du bord", min=0, max=1
                ),
                ParamSpec("corona", "float", 0.6, True, "Étoile : halo", min=0, max=3),
                ParamSpec("tide_amount", "float", 0.0, True, "Marée (exagérée)", min=0, max=1.5),
                ParamSpec(
                    "tide_angle_deg", "float", 0.0, True, "Marée : direction de l'astre attracteur (°)"
                ),
                ParamSpec("tide_mode", "str", "ocean", False, "Marée : représentation", choices=TIDE_MODES),
                ParamSpec("texture_asset_id", "asset", "", False, "Texture personnelle (image 2:1)"),
            ),
            style=(
                ParamSpec("tint", "color", "#FFFFFF00", animatable=True, label="Teinte"),
                ParamSpec("ocean_color", "color", "#3FA9F5A0", animatable=True, label="Couleur des marées"),
            ),
        ),
        KindSpec(
            "world_map",
            "Carte du monde (planisphère)",
            params=(
                ParamSpec("width", "float", 1600.0, True, "Largeur", min=10),
                ParamSpec("projection", "str", "equal_earth", False, "Projection", choices=PROJECTIONS),
                ParamSpec("map_style", "str", "continents", False, "Style", choices=MAP_STYLES),
                ParamSpec(
                    "highlight", "str", "", False, "Continent mis en valeur", choices=CONTINENT_CHOICES
                ),
                ParamSpec("labels", "bool", False, False, "Noms des continents"),
                ParamSpec("graticule", "bool", True, False, "Méridiens et parallèles"),
                ParamSpec("progress", "float", 1.0, True, "Apparition d'ouest en est (0 → 1)", min=0, max=1),
                ParamSpec(
                    "detail", "str", "50m", False, "Précision", choices=(("50m", "Fine"), ("110m", "Légère"))
                ),
            ),
            style=(
                ParamSpec("ocean_color", "color", "#0E2A47", animatable=True, label="Océans"),
                ParamSpec("land_color", "color", "#D9CBA3", animatable=True, label="Terres"),
                ParamSpec("border_color", "color", "#33415588", animatable=True, label="Frontières"),
                ParamSpec("highlight_color", "color", "#FFD27A", animatable=True, label="Mise en valeur"),
                ParamSpec("graticule_color", "color", "#FFFFFF26", animatable=True, label="Méridiens"),
                ParamSpec("label_color", "color", "#FFFFFF", animatable=True, label="Étiquettes"),
            ),
        ),
        KindSpec(
            "sky",
            "Ciel étoilé (étoiles et constellations réelles)",
            params=(
                ParamSpec("width", "float", 1600.0, True, "Largeur", min=10),
                ParamSpec("height", "float", 900.0, True, "Hauteur", min=10),
                ParamSpec("center_ra_deg", "float", 85.0, True, "Centre : ascension droite (°)"),
                ParamSpec("center_dec_deg", "float", 0.0, True, "Centre : déclinaison (°)", min=-90, max=90),
                ParamSpec("fov_deg", "float", 90.0, True, "Champ de vue (°)", min=1, max=220),
                ParamSpec("field_rotation_deg", "float", 0.0, True, "Rotation du champ (°)"),
                ParamSpec("mag_limit", "float", 5.5, True, "Magnitude limite", min=-2, max=6.5),
                ParamSpec("star_scale", "float", 1.0, True, "Taille des étoiles", min=0.1, max=5),
                ParamSpec("show_lines", "bool", True, False, "Figures des constellations"),
                ParamSpec("show_all_lines", "bool", True, False, "Toutes les constellations"),
                ParamSpec(
                    "highlight", "str", "", False, "Constellation mise en valeur (sigle UAI : Ori, UMa…)"
                ),
                ParamSpec("show_star_names", "bool", True, False, "Noms des étoiles brillantes"),
                ParamSpec(
                    "name_mag_limit", "float", 1.6, False, "Nommer jusqu'à la magnitude", min=-2, max=6
                ),
                ParamSpec("show_constellation_names", "bool", True, False, "Noms des constellations"),
                ParamSpec("label_size", "float", 22.0, True, "Taille des noms", min=4),
                ParamSpec("twinkle", "float", 0.0, True, "Scintillement", min=0, max=1),
                _TIME,
            ),
            style=(
                ParamSpec("fill", "color", "#00000000", animatable=True, label="Fond"),
                ParamSpec("line_color", "color", "#7FB3FF66", animatable=True, label="Figures"),
                ParamSpec("highlight_color", "color", "#FFD27A", animatable=True, label="Mise en valeur"),
                ParamSpec("label_color", "color", "#E8EEF9CC", animatable=True, label="Noms des étoiles"),
                ParamSpec(
                    "constellation_label_color",
                    "color",
                    "#9FC7EE99",
                    animatable=True,
                    label="Noms des constellations",
                ),
                ParamSpec("line_width", "float", 1.6, animatable=True, label="Épaisseur des figures", min=0),
            ),
        ),
        KindSpec(
            "waves",
            "Ondes (Doppler, interférences, corde)",
            params=(
                ParamSpec("mode", "str", "fronts", False, "Type d'onde", choices=WAVE_MODES),
                _TIME,
                ParamSpec("wave_speed", "float", 200.0, True, "Vitesse de l'onde c (px/s)", min=0.001),
                ParamSpec("frequency", "float", 2.0, True, "Fronts : fréquence émise (Hz)", min=0.001),
                ParamSpec("source_speed", "float", 0.0, True, "Fronts : vitesse de la source (px/s)"),
                ParamSpec("direction_deg", "float", 0.0, True, "Fronts : direction de la source (°)"),
                ParamSpec("follow_source", "bool", False, False, "Fronts : la source reste au centre"),
                ParamSpec("max_radius", "float", 900.0, True, "Fronts : portée (px)", min=1),
                ParamSpec("fade", "bool", True, False, "Fronts : s'estompent en s'éloignant"),
                ParamSpec("show_source", "bool", True, False, "Afficher la ou les sources"),
                ParamSpec("source_size", "float", 14.0, True, "Taille de la source", min=1),
                ParamSpec("width", "float", 1200.0, True, "Champ, corde : largeur", min=10),
                ParamSpec("height", "float", 700.0, True, "Champ : hauteur", min=10),
                ParamSpec("wavelength", "float", 60.0, True, "Longueur d'onde (px)", min=2),
                ParamSpec("sources", "int", 2, False, "Champ : nombre de sources", min=1, max=8),
                ParamSpec("separation", "float", 120.0, True, "Champ : écart entre sources (px)", min=0),
                ParamSpec("display", "str", "instant", False, "Champ : affichage", choices=FIELD_DISPLAYS),
                ParamSpec("half_plane", "bool", False, False, "Champ : sources sur le bord gauche (fentes)"),
                ParamSpec("resolution", "float", 0.5, False, "Champ : finesse du calcul", min=0.15, max=1),
                ParamSpec("amplitude", "float", 60.0, True, "Corde : amplitude (px)"),
                ParamSpec("standing", "bool", False, False, "Corde : onde stationnaire"),
                ParamSpec("beads", "int", 0, False, "Corde : perles (0 = aucune)", min=0, max=200),
            ),
            style=(
                ParamSpec("stroke", "color", "#9FC7EE", animatable=True, label="Fronts, corde"),
                ParamSpec("stroke_width", "float", 3.0, animatable=True, label="Épaisseur", min=0),
                ParamSpec("source_color", "color", "#FFD27A", animatable=True, label="Source"),
                ParamSpec("crest_color", "color", "#FFFFFF", animatable=True, label="Champ : crêtes"),
                ParamSpec("fill", "color", "#0B1020", animatable=True, label="Champ : fond"),
                ParamSpec("trough_color", "color", "#2677B8", animatable=True, label="Champ : creux"),
            ),
        ),
        KindSpec(
            "ray",
            "Rayon lumineux (faisceau, onde, photons)",
            params=(
                ParamSpec("points", "points", [[0.0, 0.0], [600.0, 0.0]], False, "Chemin du rayon"),
                ParamSpec("mode", "str", "beam", False, "Représentation", choices=RAY_MODES),
                ParamSpec("progress", "float", 1.0, True, "Propagation (0 → 1)", min=0, max=1),
                ParamSpec(
                    "wavelength_nm",
                    "float",
                    0.0,
                    True,
                    "Longueur d'onde réelle (nm, 0 = couleur du style)",
                    min=0,
                    max=2000,
                ),
                ParamSpec(
                    "wave_length_px", "float", 40.0, True, "Onde : longueur d'onde à l'écran (px)", min=4
                ),
                ParamSpec("amplitude", "float", 14.0, True, "Onde : amplitude (px)"),
                ParamSpec("phase", "float", 0.0, True, "Onde : défilement (périodes)"),
                ParamSpec("photon_pos", "float", 0.0, True, "Photons : position sur le chemin (0 → 1)"),
                ParamSpec("photon_count", "int", 1, False, "Photons : nombre", min=1, max=200),
                ParamSpec("photon_size", "float", 10.0, True, "Photons : taille", min=1),
                ParamSpec("packet_length", "float", 120.0, True, "Paquets : longueur (px)", min=10),
                ParamSpec("path_opacity", "float", 1.0, True, "Photons : visibilité du chemin", min=0, max=1),
            ),
            style=(
                ParamSpec("stroke", "color", "#FF5A4E", animatable=True, label="Couleur"),
                ParamSpec("stroke_width", "float", 4.0, animatable=True, label="Épaisseur", min=0),
            ),
        ),
        KindSpec(
            "optic",
            "Élément d'optique (laser, miroir, lame, fentes…)",
            params=(
                ParamSpec("element", "str", "mirror", False, "Élément", choices=OPTIC_ELEMENTS),
                ParamSpec("size", "float", 120.0, True, "Taille", min=4),
                ParamSpec("active", "float", 0.0, True, "Allumé / déclenché (0 → 1)", min=0, max=1),
                ParamSpec(
                    "slit_width", "float", 0.05, False, "Fentes : largeur relative", min=0.005, max=0.4
                ),
                ParamSpec(
                    "slit_separation", "float", 0.22, False, "Fentes : écart relatif", min=0.01, max=0.9
                ),
            ),
            style=(
                ParamSpec("fill", "color", "#9FC7EE", animatable=True, label="Remplissage"),
                ParamSpec("stroke", "color", "#E8EEF9", animatable=True, label="Contour"),
                ParamSpec("stroke_width", "float", 3.0, animatable=True, label="Épaisseur", min=0),
                ParamSpec("beam_color", "color", "#FF3B30", animatable=True, label="Faisceau, déclenchement"),
            ),
        ),
        KindSpec(
            "impacts",
            "Écran de détection (impacts de photons)",
            params=(
                ParamSpec("width", "float", 220.0, True, "Largeur", min=10),
                ParamSpec("height", "float", 700.0, True, "Hauteur", min=10),
                ParamSpec("vertical", "bool", True, False, "Écran vertical"),
                ParamSpec("pattern", "str", "two_slits", False, "Expérience", choices=IMPACT_PATTERNS),
                ParamSpec("count", "float", 2000.0, True, "Nombre d'impacts affichés", min=0),
                ParamSpec("max_count", "int", 8000, False, "Nombre maximal d'impacts", min=1, max=50000),
                ParamSpec(
                    "fringes", "float", 6.0, False, "Franges brillantes par demi-écran", min=0.1, max=60
                ),
                ParamSpec(
                    "envelope", "float", 0.55, False, "Largeur de la tache de diffraction", min=0.02, max=5
                ),
                ParamSpec("seed", "int", 1, False, "Tirage (graine)", min=0),
                ParamSpec("dot_size", "float", 2.2, True, "Taille des impacts", min=0.5),
                ParamSpec("highlight_last", "bool", True, False, "Dernier impact en surbrillance"),
                ParamSpec("show_curve", "bool", False, False, "Courbe d'intensité théorique"),
                ParamSpec("curve_size", "float", 160.0, True, "Hauteur de la courbe", min=0),
            ),
            style=(
                ParamSpec("fill", "color", "#0A0E16", animatable=True, label="Écran"),
                ParamSpec("stroke", "color", "#5A6575", animatable=True, label="Cadre"),
                ParamSpec("dot_color", "color", "#7CFFB2", animatable=True, label="Impacts"),
                ParamSpec("curve_color", "color", "#FFD27A", animatable=True, label="Courbe"),
            ),
        ),
        KindSpec(
            "particles",
            "Particules (explosion, supernova, nébuleuse, disque)",
            params=(
                ParamSpec("mode", "str", "explosion", False, "Effet", choices=PARTICLE_MODES),
                _TIME,
                ParamSpec("count", "int", 800, False, "Nombre de particules", min=1, max=6000),
                ParamSpec("seed", "int", 1, False, "Tirage (graine)", min=0),
                ParamSpec("radius", "float", 400.0, True, "Rayon (nébuleuse, disque)", min=1),
                ParamSpec("speed", "float", 300.0, True, "Vitesse (px/s)"),
                ParamSpec("size", "float", 4.0, True, "Taille des particules", min=0.3),
                ParamSpec("lifetime", "float", 3.0, True, "Durée de vie (s)", min=0.001),
                ParamSpec("drag", "float", 1.2, True, "Explosion : freinage", min=0),
                ParamSpec("turbulence", "float", 0.3, True, "Turbulence", min=0, max=3),
                ParamSpec("expansion", "float", 0.05, True, "Nébuleuse : expansion (par s)", min=0),
                ParamSpec("tilt_deg", "float", 70.0, True, "Disque : inclinaison (°)", min=0, max=89),
                ParamSpec("inflow", "float", 0.02, True, "Disque : chute vers le centre", min=0, max=1),
                ParamSpec("additive", "bool", True, False, "Lumière additive (brillance)"),
            ),
            style=(
                ParamSpec(
                    "color_a", "color", "#FFFFFF", animatable=True, label="Couleur chaude / intérieure"
                ),
                ParamSpec(
                    "color_b", "color", "#FF7A3D", animatable=True, label="Couleur froide / extérieure"
                ),
            ),
        ),
        KindSpec(
            "black_hole",
            "Trou noir (horizon, disque d'accrétion)",
            params=(
                ParamSpec("size", "float", 160.0, True, "Diamètre de l'horizon", min=2),
                _TIME,
                ParamSpec("inclination_deg", "float", 78.0, True, "Inclinaison du disque (°)", min=0, max=89),
                ParamSpec(
                    "disk_inner", "float", 2.2, True, "Disque : bord intérieur (× horizon)", min=1.2, max=20
                ),
                ParamSpec(
                    "disk_outer", "float", 5.5, True, "Disque : bord extérieur (× horizon)", min=1.4, max=30
                ),
                ParamSpec("spin_speed", "float", 1.0, True, "Vitesse de rotation du disque"),
                ParamSpec("beaming", "float", 0.6, True, "Côté approchant plus brillant", min=0, max=1),
                ParamSpec("lensing", "bool", True, False, "Lentille gravitationnelle"),
                ParamSpec("brightness", "float", 1.0, True, "Luminosité du disque", min=0, max=4),
                ParamSpec("resolution", "float", 0.6, False, "Finesse du calcul", min=0.2, max=1),
            ),
            style=(
                ParamSpec("disk_hot", "color", "#FFF4D6", animatable=False, label="Disque : intérieur"),
                ParamSpec("disk_cool", "color", "#FF7A2E", animatable=False, label="Disque : extérieur"),
            ),
        ),
        KindSpec(
            "light",
            "Lumière (halo, projecteur, pénombre, rayons)",
            params=(
                ParamSpec("mode", "str", "halo", False, "Type de lumière", choices=LIGHT_MODES),
                ParamSpec("radius", "float", 300.0, True, "Portée (px)", min=1),
                ParamSpec("intensity", "float", 1.0, True, "Intensité", min=0, max=4),
                ParamSpec("angle_deg", "float", 0.0, True, "Direction / rotation (°)"),
                ParamSpec("spread_deg", "float", 30.0, True, "Ouverture (°)", min=0.5, max=170),
                ParamSpec("count", "int", 12, False, "Rayons : nombre", min=2, max=72),
                ParamSpec("darkness", "float", 0.75, True, "Pénombre : obscurité", min=0, max=1),
                ParamSpec("softness", "float", 0.35, True, "Pénombre : douceur du bord", min=0.01, max=0.95),
            ),
            style=(
                ParamSpec("fill", "color", "#FFE9B0", animatable=True, label="Couleur de la lumière"),
                ParamSpec("shade_color", "color", "#000000", animatable=True, label="Pénombre : couleur"),
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

# variantes prêtes à poser depuis la Bibliothèque : « type:variante » -> (libellé, paramètres imposés)
OBJECT_VARIANTS: dict[str, tuple[str, dict[str, Any]]] = {
    **{f"solid3d:{shape}": (label, {"shape": shape}) for shape, label in SOLID_SHAPES},
    "grid:plane": ("Repère quadrillé (plan)", {}),
    "grid:transform": ("Grille et vecteurs î, ĵ (algèbre linéaire)", {"show_basis": True}),
    "grid:spacetime": (
        "Espace-temps courbé (nappe)",
        {
            "perspective": True,
            "warp": "gravity",
            "warp_amount": 1.0,
            "warp_radius": 180.0,
            "show_axes": False,
            "height": 1400.0,
            "step": 70.0,
        },
    ),
    "grid:wave": (
        "Onde gravitationnelle (nappe)",
        {
            "perspective": True,
            "warp": "wave",
            "warp_amount": 1.0,
            "warp_radius": 260.0,
            "show_axes": False,
            "height": 1400.0,
            "step": 60.0,
        },
    ),
}


def _astro_variants() -> dict[str, tuple[str, dict[str, Any]]]:
    """Astres du Système solaire (inclinaison réelle de l'axe, NASA) et étoiles connues (Wikidata)."""
    from antares_studio.resources.astro import BODIES, FAMOUS_STARS

    out: dict[str, tuple[str, dict[str, Any]]] = {}
    for body in BODIES.values():
        params: dict[str, Any] = {"body": body.id, "tilt_deg": body.obliquity_deg}
        if body.emissive:
            params |= {"lit": False, "corona": 0.6}
        else:
            params["corona"] = 0.0
        out[f"celestial:{body.id}"] = (body.label, params)
    out["celestial:moon_phase"] = (
        "Lune (phase : premier quartier)",
        {"body": "moon", "corona": 0.0, "light_az_deg": 90.0, "light_el_deg": 0.0, "ambient": 0.03},
    )
    out["celestial:earth_tides"] = (
        "Terre vue du pôle (marées)",
        {"body": "earth", "corona": 0.0, "pitch_deg": 90.0, "lit": False, "tide_amount": 0.25},
    )
    for star in FAMOUS_STARS.values():
        if star.id == "sun":
            continue
        temp = f"{star.temperature_k:,.0f}".replace(",", " ")
        out[f"celestial:star_{star.id}"] = (
            f"{star.label} ({temp} K)",
            {"body": "star", "temperature_k": star.temperature_k, "lit": False, "corona": 0.7},
        )
    return out


def _physics_variants() -> dict[str, tuple[str, dict[str, Any]]]:
    return {
        "world_map:continents": ("Planisphère des continents", {"map_style": "continents", "labels": True}),
        "world_map:political": ("Planisphère des pays", {"map_style": "political"}),
        "world_map:satellite": ("Terre vue de l'espace (planisphère)", {"map_style": "satellite"}),
        "world_map:night": ("La Terre la nuit (planisphère)", {"map_style": "night", "graticule": False}),
        "world_map:outline": ("Contours des continents", {"map_style": "outline"}),
        "sky:whole": ("Ciel étoilé (grand champ)", {"fov_deg": 120.0, "center_dec_deg": 20.0}),
        "sky:orion": (
            "Constellation d'Orion",
            {"center_ra_deg": 84.0, "center_dec_deg": 0.0, "fov_deg": 45.0, "highlight": "Ori"},
        ),
        "sky:ursa_major": (
            "Grande Ourse et étoile Polaire",
            {"center_ra_deg": 170.0, "center_dec_deg": 65.0, "fov_deg": 70.0, "highlight": "UMa"},
        ),
        "sky:cassiopeia": (
            "Cassiopée",
            {"center_ra_deg": 15.0, "center_dec_deg": 60.0, "fov_deg": 40.0, "highlight": "Cas"},
        ),
        "sky:scorpius": (
            "Scorpion et Antarès",
            {"center_ra_deg": 252.0, "center_dec_deg": -30.0, "fov_deg": 45.0, "highlight": "Sco"},
        ),
        "sky:southern_cross": (
            "Croix du Sud",
            {"center_ra_deg": 187.0, "center_dec_deg": -60.0, "fov_deg": 35.0, "highlight": "Cru"},
        ),
        "waves:ripples": ("Ondes circulaires (source immobile)", {"mode": "fronts"}),
        "waves:doppler": (
            "Effet Doppler (source en mouvement)",
            {"mode": "fronts", "wave_speed": 200.0, "source_speed": 100.0},
        ),
        "waves:mach": (
            "Cône de Mach (source supersonique)",
            {"mode": "fronts", "wave_speed": 150.0, "source_speed": 260.0},
        ),
        "waves:young": (
            "Fentes de Young (champ d'onde)",
            {"mode": "field", "half_plane": True, "wavelength": 40.0, "separation": 110.0},
        ),
        "waves:fringes": (
            "Franges d'interférence (intensité)",
            {
                "mode": "field",
                "half_plane": True,
                "display": "intensity",
                "wavelength": 40.0,
                "separation": 110.0,
            },
        ),
        "waves:string": ("Corde : onde progressive", {"mode": "string", "wavelength": 260.0}),
        "waves:standing": (
            "Corde : onde stationnaire",
            {"mode": "string", "standing": True, "wavelength": 400.0, "amplitude": 50.0},
        ),
        "ray:laser": ("Faisceau laser rouge (632,8 nm)", {"mode": "beam", "wavelength_nm": 632.8}),
        "ray:wave": ("Lumière vue comme une onde", {"mode": "wave", "wavelength_nm": 532.0}),
        "ray:packets": ("Paquet d'onde (photon)", {"mode": "packets", "wavelength_nm": 532.0}),
        "ray:photons": ("Photons un par un", {"mode": "photons", "wavelength_nm": 589.0, "photon_count": 3}),
        "ray:geometric": ("Rayon de l'optique géométrique", {"mode": "arrows", "style_stroke": "#FFD27A"}),
        "ray:dashed": ("Rayon prolongé (pointillés)", {"mode": "dashed", "style_stroke": "#FFD27A"}),
        **{f"optic:{el}": (label, {"element": el}) for el, label in OPTIC_ELEMENTS},
        "impacts:two_slits": ("Écran : impacts avec interférences", {"pattern": "two_slits"}),
        "impacts:one_slit": ("Écran : diffraction par une fente", {"pattern": "one_slit"}),
        "impacts:which_path": ("Écran : chemin mesuré (sans interférences)", {"pattern": "which_path"}),
        "particles:explosion": (
            "Explosion",
            {"mode": "explosion", "style_color_a": "#FFF2C0", "style_color_b": "#FF4A1C"},
        ),
        "particles:supernova": (
            "Supernova : coquille en expansion",
            {
                "mode": "shell",
                "count": 1600,
                "speed": 260.0,
                "size": 2.5,
                "lifetime": 8.0,
                "style_color_a": "#E4F0FF",
                "style_color_b": "#4F7BFF",
            },
        ),
        "particles:nebula": (
            "Nébuleuse (reste de supernova)",
            {
                "mode": "nebula",
                "count": 2500,
                "radius": 260.0,
                "size": 4.0,
                "time_s": 5.0,
                "style_color_a": "#5FD3FF",
                "style_color_b": "#FF5A8A",
            },
        ),
        "particles:accretion": (
            "Disque d'accrétion",
            {
                "mode": "accretion",
                "count": 1500,
                "radius": 300.0,
                "size": 2.0,
                "style_color_a": "#FFFFFF",
                "style_color_b": "#FF8A3D",
            },
        ),
        "black_hole:edge": ("Trou noir (disque vu par la tranche)", {}),
        "black_hole:face": ("Trou noir (disque vu de face)", {"inclination_deg": 20.0}),
        "light:halo": ("Halo lumineux", {"mode": "halo"}),
        "light:spot": ("Projecteur", {"mode": "spot", "angle_deg": -60.0, "radius": 600.0}),
        "light:darken": ("Pénombre (mettre un objet en lumière)", {"mode": "darken"}),
        "light:rays": ("Rayons de soleil", {"mode": "rays", "radius": 500.0, "spread_deg": 6.0}),
    }


OBJECT_VARIANTS.update(_astro_variants())
OBJECT_VARIANTS.update(_physics_variants())


def split_style(params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Sépare les clés « style_… » d'une variante (convention de ``new_node``)."""
    plain = {k: v for k, v in params.items() if not k.startswith("style_")}
    style = {k[6:]: v for k, v in params.items() if k.startswith("style_")}
    return plain, style


def resolve_variant(ident: str) -> tuple[str, str, dict[str, Any]]:
    """« solid3d:cube » -> (type, libellé, paramètres imposés) ; un type simple n'impose rien."""
    if ident in OBJECT_VARIANTS:
        label, params = OBJECT_VARIANTS[ident]
        return ident.partition(":")[0], label, dict(params)
    spec = spec_for(ident)
    return spec.kind, spec.label, {}


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

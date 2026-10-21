"""Modèles pédagogiques intégrés (géométrie générée localement, aucune ressource tierce)."""

from __future__ import annotations

from collections.abc import Callable

from antares_studio.domain.kinds import spec_for
from antares_studio.domain.model import Canvas, Node, Project, Scene
from antares_studio.timeline.presets import apply_preset

TemplateBuilder = Callable[[Project, Scene], None]


def new_node(kind: str, name: str, x: float, y: float, **params: object) -> Node:
    spec = spec_for(kind)
    node = Node.create(kind, name, position=[x, y], style=spec.default_style(), params=spec.default_params())
    for k, v in params.items():
        if k.startswith("style_"):
            node.style[k[6:]] = v
        else:
            node.params[k] = v
    return node


def _scale(canvas: Canvas) -> float:
    return min(canvas.width / 1920, canvas.height / 1080)


def build_empty(project: Project, scene: Scene) -> None:
    return None


SCALE_WARNING_TEXT = "Schéma : distances et tailles non à l'échelle"


def scale_warning_node(canvas: Canvas, text: str = SCALE_WARNING_TEXT) -> Node:
    """Encadré d'avertissement d'échelle (SCI-07), placé au-dessus de la bande des sous-titres."""
    k = _scale(canvas)
    node = new_node(
        "callout",
        "Avertissement d'échelle",
        canvas.width / 2,
        canvas.height - 265 * k,  # sous l'image, au-dessus de la bande des sous-titres (20 % inférieurs)
        text=text,
        font_size=28 * k,
        padding=14 * k,
    )
    if len(text) > 70:  # texte long : deux lignes dans 85 % de la largeur, remonté d'autant
        node.params["max_width"] = canvas.width * 0.85
        node.position[1] = canvas.height - 290 * k
    return node


def build_intro(project: Project, scene: Scene) -> None:
    """Introduction : titre du projet et sous-titre, apparition progressive (phase 6, intro/outro)."""
    c = project.canvas
    k = _scale(c)
    cx, cy = c.width / 2, c.height / 2
    title = new_node("text", "Titre", cx, cy - 60 * k, text=project.title, font_size=72 * k, bold=True)
    sub = new_node("text", "Sous-titre", cx, cy + 60 * k, text="Une animation scientifique", font_size=36 * k)
    sub.style["fill"] = "#B0BEC5"
    line = new_node("line", "Trait", cx - 300 * k, cy, end=[600 * k, 0.0])
    for n in (title, sub, line):
        scene.nodes.append(n)
    d = max(1, scene.duration_frames // 4)
    scene.tracks += apply_preset("appear", title, {"duration_frames": d})
    scene.tracks += apply_preset("appear", sub, {"start_frame": d // 2, "duration_frames": d})
    scene.tracks += apply_preset("appear", line, {"start_frame": d // 4, "duration_frames": d})


def build_credits(project: Project, scene: Scene) -> None:
    """Crédits : sources scientifiques, ressources tierces et logiciel, générés depuis le projet."""
    from antares_studio.resources.licenses import credits_lines

    c = project.canvas
    k = _scale(c)
    cx = c.width / 2
    title = new_node("text", "Titre", cx, 120 * k, text="Crédits", font_size=64 * k, bold=True)
    body = new_node(
        "text",
        "Crédits",
        cx,
        c.height / 2 + 20 * k,
        text="\n".join(credits_lines(project)),
        font_size=28 * k,
        align="left",
        max_width=c.width * 0.8,
    )
    body.style["fill"] = "#CFD8DC"
    scene.background = "#05070F"
    for n in (title, body):
        scene.nodes.append(n)
    d = max(1, scene.duration_frames // 5)
    scene.tracks += apply_preset("appear", title, {"duration_frames": d})
    scene.tracks += apply_preset("appear", body, {"start_frame": d // 2, "duration_frames": d})


def build_moon_phases(project: Project, scene: Scene) -> None:
    """Soleil, Terre et Lune en orbite ; légende « non à l'échelle » (parcours P1)."""
    c = project.canvas
    k = _scale(c)
    cx, cy = c.width / 2, c.height / 2
    sun = new_node("circle", "Soleil", cx - 640 * k, cy, radius=140 * k, style_fill="#FFC857")
    rays = new_node(
        "star",
        "Rayons",
        cx - 640 * k,
        cy,
        points_count=12,
        outer_radius=175 * k,
        inner_radius=150 * k,
        style_fill="#FFC85755",
    )
    rays.z_index = -1
    earth = new_node("circle", "Terre", cx + 150 * k, cy, radius=70 * k, style_fill="#2677B8")
    orbit = new_node("orbit_path", "Orbite de la Lune", cx + 150 * k, cy, radius=240 * k)
    orbit.z_index = -1
    moon = new_node("circle", "Lune", cx + 390 * k, cy, radius=22 * k, style_fill="#D9D9D9")
    title = new_node(
        "text",
        "Titre",
        cx,
        110 * k,
        text="Pourquoi la Lune change-t-elle de forme ?",
        font_size=56 * k,
        bold=True,
    )
    legend = scale_warning_node(c)
    for n in (rays, sun, orbit, earth, moon, title, legend):
        scene.nodes.append(n)
    scene.tracks += apply_preset(
        "orbit",
        moon,
        {
            "center_x": cx + 150 * k,
            "center_y": cy,
            "radius": 240 * k,
            "duration_frames": scene.duration_frames,
            "turns": 1,
            "clockwise": False,
            "samples_per_turn": 72,
        },
    )
    scene.tracks += apply_preset("appear", title, {"duration_frames": max(1, scene.duration_frames // 10)})
    scene.tracks += apply_preset("rotate", rays, {"duration_frames": scene.duration_frames, "turns": 0.25})
    project.scientific_metadata.update(
        {
            "representation": "schematic",
            "to_scale": False,
            "notes": "Géométrie Soleil–Terre–Lune simplifiée ; période et distances non respectées.",
            "sources": [
                {"label": "NASA Science — Moon phases", "url": "https://science.nasa.gov/moon/moon-phases/"},
            ],
        }
    )


def build_scale_comparison(project: Project, scene: Scene) -> None:
    """Comparaison d'échelles : flèches et valeurs avec unités (parcours P2)."""
    c = project.canvas
    k = _scale(c)
    cx, cy = c.width / 2, c.height / 2
    title = new_node(
        "text", "Titre", cx, 110 * k, text="Qu'est-ce qu'une année-lumière ?", font_size=56 * k, bold=True
    )
    bar = new_node(
        "rect", "Barre Terre–Soleil", cx, cy - 60 * k, width=300 * k, height=16 * k, style_fill="#4FC3F7"
    )
    arrow = new_node(
        "arrow", "Flèche année-lumière", cx - 700 * k, cy + 120 * k, end=[1400 * k, 0.0], head_size=28 * k
    )
    lab1 = new_node(
        "text", "Valeur 1", cx, cy - 120 * k, text="Terre → Soleil : 1 ua ≈ 1,496 × 10⁸ km", font_size=34 * k
    )
    lab2 = new_node(
        "text",
        "Valeur 2",
        cx,
        cy + 200 * k,
        text="1 année-lumière ≈ 9,461 × 10¹² km ≈ 63 241 ua",
        font_size=34 * k,
    )
    legend = scale_warning_node(c, "Schéma non à l'échelle — constantes : IAU 2012 (ua), CODATA (c)")
    for n in (title, bar, arrow, lab1, lab2, legend):
        scene.nodes.append(n)
    scene.tracks += apply_preset("appear", title, {"duration_frames": 20})
    scene.tracks += apply_preset("appear", lab1, {"start_frame": 20, "duration_frames": 20})
    scene.tracks += apply_preset(
        "translate", arrow, {"start_frame": 40, "duration_frames": 60, "dx": 0, "dy": 0}
    )
    scene.tracks += apply_preset("appear", lab2, {"start_frame": 60, "duration_frames": 20})
    project.scientific_metadata.update(
        {
            "representation": "schematic",
            "to_scale": False,
            "sources": [
                {
                    "label": "IAU 2012 Resolution B2 (unité astronomique = 149 597 870 700 m)",
                    "url": "https://www.iau.org/static/resolutions/IAU2012_English.pdf",
                },
                {
                    "label": "CODATA — vitesse de la lumière c = 299 792 458 m/s",
                    "url": "https://physics.nist.gov/cgi-bin/cuu/Value?c",
                },
            ],
        }
    )


def build_orbit_vectors(project: Project, scene: Scene) -> None:
    """Orbite illustrative avec vecteur vitesse suivant le mobile (parcours P3, version schématique)."""
    c = project.canvas
    k = _scale(c)
    cx, cy = c.width / 2, c.height / 2
    star = new_node("circle", "Étoile", cx, cy, radius=60 * k, style_fill="#FFC857")
    path = new_node("orbit_path", "Trajectoire", cx, cy, radius=230 * k)
    planet = new_node("circle", "Planète", cx + 230 * k, cy, radius=24 * k, style_fill="#2677B8")
    velocity = new_node("arrow", "Vitesse", 0.0, 0.0, end=[0.0, -140 * k], head_size=22 * k)
    velocity.parent_id = planet.id
    velocity.style["stroke"] = "#F2A93B"
    gravity = new_node("arrow", "Gravitation", 0.0, 0.0, end=[-120 * k, 0.0], head_size=22 * k)
    gravity.parent_id = planet.id
    gravity.style["stroke"] = "#EF5350"
    legend = scale_warning_node(
        c, "Orbite circulaire schématique, non à l'échelle — v (orange) tangent, g (rouge) vers l'astre"
    )
    for n in (path, star, planet, velocity, gravity, legend):
        scene.nodes.append(n)
    scene.tracks += apply_preset(
        "orbit",
        planet,
        {
            "center_x": cx,
            "center_y": cy,
            "radius": 230 * k,
            "duration_frames": scene.duration_frames,
            "samples_per_turn": 72,
        },
    )
    # la planète tourne sur elle-même d'un tour : les flèches enfants restent tangente/radiale
    scene.tracks += apply_preset(
        "rotate", planet, {"duration_frames": scene.duration_frames, "turns": -1, "clockwise": True}
    )
    project.scientific_metadata.update({"representation": "schematic", "to_scale": False})


def build_kepler_orbit(project: Project, scene: Scene) -> None:
    """Orbite de Kepler : étoile au foyer, trajectoire elliptique, planète (parcours P3, modélisation)."""
    c = project.canvas
    k = _scale(c)
    cx, cy = c.width / 2, c.height / 2
    a_px, e = 380 * k, 0.6
    star = new_node("circle", "Étoile (foyer)", cx, cy, radius=50 * k, style_fill="#FFC857")
    # l'ellipse est centrée à −a·e du foyer sur l'axe des apsides
    path = new_node(
        "ellipse",
        "Trajectoire",
        cx - a_px * e,
        cy,
        rx=a_px,
        ry=a_px * (1 - e * e) ** 0.5,
        style_fill="#00000000",
        style_stroke="#FFFFFF40",
        style_stroke_width=2 * k,
        style_dash=True,
    )
    path.z_index = -1
    planet = new_node("circle", "Planète", cx + a_px * (1 - e), cy, radius=18 * k, style_fill="#2677B8")
    title = new_node(
        "text",
        "Titre",
        cx,
        100 * k,
        text="Une orbite de Kepler : plus vite près de l'étoile",
        font_size=52 * k,
        bold=True,
    )
    note = scale_warning_node(
        c,
        f"Modélisation à deux corps (Kepler) : e = {e}, a = {a_px:.0f} px à l'écran, périapse à droite — "
        "distances non à l'échelle",
    )
    for n in (path, star, planet, title, note):
        scene.nodes.append(n)
    scene.tracks += apply_preset(
        "kepler",
        planet,
        {
            "focus_x": cx,
            "focus_y": cy,
            "semi_major_px": a_px,
            "eccentricity": e,
            "duration_frames": scene.duration_frames,
            "periods": 1.0,
            "samples_per_period": 120,
        },
    )
    scene.tracks += apply_preset("appear", title, {"duration_frames": max(1, scene.duration_frames // 10)})
    project.scientific_metadata.update(
        {
            "representation": "model",
            "to_scale": False,
            "notes": "Problème à deux corps newtonien ; masse de la planète négligée ; solution analytique "
            "de l'équation de Kepler (Newton–Raphson) ; le temps vidéo est proportionnel au temps physique.",
            "parameters": {
                "eccentricity": e,
                "semi_major_axis_px": a_px,
                "periods": 1.0,
                "method": "analytique",
            },
            "sources": [
                {
                    "label": "JPL Solar System Dynamics — Keplerian elements and Kepler's equation",
                    "url": "https://ssd.jpl.nasa.gov/planets/approx_pos.html",
                },
                {
                    "label": "IAU 2015 B3 — constantes nominales (GM☉, GM⊕)",
                    "url": "https://www.iau.org/static/resolutions/IAU2015_English.pdf",
                },
            ],
        }
    )


TEMPLATES: dict[str, tuple[str, TemplateBuilder]] = {
    "intro": ("Introduction (titre et sous-titre)", build_intro),
    "moon_phases": ("Phases de la Lune (Soleil, Terre, Lune en orbite)", build_moon_phases),
    "scale_comparison": ("Comparaison d'échelles (année-lumière)", build_scale_comparison),
    "orbit_vectors": ("Orbite et vecteurs (vitesse, gravitation)", build_orbit_vectors),
    "kepler_orbit": ("Orbite de Kepler (modélisation à deux corps)", build_kepler_orbit),
    "credits": ("Crédits (sources, ressources, logiciel)", build_credits),
}


def template_labels() -> dict[str, str]:
    return {k: v[0] for k, v in TEMPLATES.items()}


def create_project(title: str, canvas: Canvas, template_id: str = "", duration_s: int = 20) -> Project:
    project = Project.create(title, canvas)
    scene = Scene.create("Scène 1", duration_frames=max(1, int(round(duration_s * float(canvas.fps)))))
    project.scenes.append(scene)
    builder = TEMPLATES.get(template_id, ("", build_empty))[1]
    builder(project, scene)
    return project

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
    legend = new_node(
        "text",
        "Légende",
        cx,
        c.height - 90 * k,
        text="Schéma : distances et tailles non à l'échelle",
        font_size=30 * k,
    )
    legend.style["fill"] = "#B0BEC5"
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
    legend = new_node(
        "text",
        "Source",
        cx,
        c.height - 70 * k,
        text="Constantes : IAU 2012 (ua), CODATA (c)",
        font_size=26 * k,
    )
    legend.style["fill"] = "#B0BEC5"
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
    path = new_node("orbit_path", "Trajectoire", cx, cy, radius=320 * k)
    planet = new_node("circle", "Planète", cx + 320 * k, cy, radius=24 * k, style_fill="#2677B8")
    velocity = new_node("arrow", "Vitesse", 0.0, 0.0, end=[0.0, -140 * k], head_size=22 * k)
    velocity.parent_id = planet.id
    velocity.style["stroke"] = "#F2A93B"
    gravity = new_node("arrow", "Gravitation", 0.0, 0.0, end=[-120 * k, 0.0], head_size=22 * k)
    gravity.parent_id = planet.id
    gravity.style["stroke"] = "#EF5350"
    legend = new_node(
        "text",
        "Légende",
        cx,
        c.height - 80 * k,
        text="Orbite circulaire schématique — v (orange) tangent, g (rouge) vers l'astre",
        font_size=28 * k,
    )
    legend.style["fill"] = "#B0BEC5"
    for n in (path, star, planet, velocity, gravity, legend):
        scene.nodes.append(n)
    scene.tracks += apply_preset(
        "orbit",
        planet,
        {
            "center_x": cx,
            "center_y": cy,
            "radius": 320 * k,
            "duration_frames": scene.duration_frames,
            "samples_per_turn": 72,
        },
    )
    # la planète tourne sur elle-même d'un tour : les flèches enfants restent tangente/radiale
    scene.tracks += apply_preset(
        "rotate", planet, {"duration_frames": scene.duration_frames, "turns": -1, "clockwise": True}
    )
    project.scientific_metadata.update({"representation": "schematic", "to_scale": False})


TEMPLATES: dict[str, tuple[str, TemplateBuilder]] = {
    "moon_phases": ("Phases de la Lune (Soleil, Terre, Lune en orbite)", build_moon_phases),
    "scale_comparison": ("Comparaison d'échelles (année-lumière)", build_scale_comparison),
    "orbit_vectors": ("Orbite et vecteurs (vitesse, gravitation)", build_orbit_vectors),
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

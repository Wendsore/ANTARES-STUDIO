"""Modèles pédagogiques intégrés (géométrie générée localement, aucune ressource tierce)."""

from __future__ import annotations

from collections.abc import Callable

from antares_studio.domain.kinds import spec_for
from antares_studio.domain.model import Canvas, Node, Project, Scene, Track
from antares_studio.science.nbody import Body
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


def add_sources(project: Project, sources: list[dict[str, str]]) -> None:
    """Ajoute des sources aux métadonnées sans écraser celles des autres scènes (doublons ignorés)."""
    existing = project.scientific_metadata.setdefault("sources", [])
    for src in sources:
        if src not in existing:
            existing.append(dict(src))


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
    if len(text) > 70:
        # texte long : replié sur 85 % de la largeur et remonté ; la police de substitution de Windows
        # (DejaVu absente) donne jusqu'à trois lignes, la boîte doit rester au-dessus de la bande (80 %)
        node.params["max_width"] = canvas.width * 0.85
        node.position[1] = canvas.height - 310 * k
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
        }
    )
    add_sources(
        project,
        [
            {"label": "NASA Science — Moon phases", "url": "https://science.nasa.gov/moon/moon-phases/"},
        ],
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
    project.scientific_metadata.update({"representation": "schematic", "to_scale": False})
    add_sources(
        project,
        [
            {
                "label": "IAU 2012 Resolution B2 (unité astronomique = 149 597 870 700 m)",
                "url": "https://www.iau.org/static/resolutions/IAU2012_English.pdf",
            },
            {
                "label": "CODATA — vitesse de la lumière c = 299 792 458 m/s",
                "url": "https://physics.nist.gov/cgi-bin/cuu/Value?c",
            },
        ],
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
    legend = scale_warning_node(c, "Schéma non à l'échelle — v (orange) tangent, g (rouge) vers l'astre")
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
        }
    )
    add_sources(
        project,
        [
            {
                "label": "JPL Solar System Dynamics — Keplerian elements and Kepler's equation",
                "url": "https://ssd.jpl.nasa.gov/planets/approx_pos.html",
            },
            {
                "label": "IAU 2015 B3 — constantes nominales (GM☉, GM⊕)",
                "url": "https://www.iau.org/static/resolutions/IAU2015_English.pdf",
            },
        ],
    )


def _simulation_scene(
    project: Project,
    scene: Scene,
    bodies: list[Body],
    period: float,
    periods: float,
    title: str,
    colors: tuple[str, ...],
    radii: tuple[float, ...],
    notes: str,
    sources: list[dict[str, str]],
) -> None:
    """Scène de simulation à N corps : pistes de position image par image, trajectoires tracées."""
    from antares_studio.domain.model import Track
    from antares_studio.science.nbody import simulate_nbody

    c = project.canvas
    k = _scale(c)
    steps_per_period = 4000
    steps = int(round(steps_per_period * periods))
    result = simulate_nbody(bodies, period / steps_per_period, steps)
    xs = [x for step in result.positions for x, _y in step]
    ys = [y for step in result.positions for _x, y in step]
    # pixels par unité simulée : la figure tient entre le titre et l'encadré (≈ 500 px de haut en 1080p)
    px = min(c.width * 0.8 / ((max(xs) - min(xs)) or 1.0), 460 * k / ((max(ys) - min(ys)) or 1.0))
    cx, cy = c.width / 2, 440 * k
    mid_x, mid_y = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2

    def screen(x: float, y: float) -> tuple[float, float]:
        return cx + (x - mid_x) * px, cy - (y - mid_y) * px  # y physique vers le haut

    dur = scene.duration_frames
    for i, body in enumerate(bodies):
        path = result.track(i)
        trail = [list(screen(*path[int(round(j / 180 * steps))])) for j in range(181)]
        x0, y0 = trail[0]
        trace = new_node(
            "polygon",
            f"Trajectoire {body.name}",
            0.0,
            0.0,
            points=trail,
            closed=False,
            style_fill="#00000000",
            style_stroke=colors[i] + "55",
            style_stroke_width=2 * k,
            style_dash=True,
        )
        trace.z_index = -1
        node = new_node("circle", body.name, x0, y0, radius=radii[i] * k, style_fill=colors[i])
        tx, ty = Track(node.id, "position.x"), Track(node.id, "position.y")
        for f in range(dur + 1):
            sx, sy = screen(*path[int(round(f / dur * steps))])
            tx.set_keyframe(f, sx, "linear")
            ty.set_keyframe(f, sy, "linear")
        scene.nodes += [trace, node]
        scene.tracks += [tx, ty]
    # quantité de mouvement nulle : le centre de masse reste immobile à l'origine
    bx, by = screen(0.0, 0.0)
    scene.nodes.append(new_node("circle", "Centre de masse", bx, by, radius=5 * k, style_fill="#FFFFFFAA"))
    heading = new_node("text", "Titre", cx, 90 * k, text=title, font_size=50 * k, bold=True)
    scene.nodes.append(heading)
    scene.nodes.append(
        scale_warning_node(
            c,
            f"Simulation numérique (Verlet, {steps} pas, G = 1) : écart d'énergie {result.energy_drift:.1e}",
        )
    )
    scene.tracks += apply_preset("appear", heading, {"duration_frames": max(1, dur // 10)})
    project.scientific_metadata.update(
        {
            "representation": "simulation",
            "to_scale": False,
            "notes": notes,
            "parameters": {
                "method": "verlet",
                "G": 1.0,
                "dt": period / steps_per_period,
                "steps": steps,
                "periods": periods,
                "energy_drift": float(f"{result.energy_drift:.3e}"),
            },
        }
    )
    add_sources(project, sources)


def build_three_body(project: Project, scene: Scene) -> None:
    """Chorégraphie en huit : trois masses égales se suivent sur une même courbe (solution périodique)."""
    from antares_studio.science.nbody import FIGURE_EIGHT_PERIOD, figure_eight

    _simulation_scene(
        project,
        scene,
        figure_eight(),
        FIGURE_EIGHT_PERIOD,
        2.0,
        "Trois corps, une seule trajectoire en huit",
        ("#FF8A65", "#4FC3F7", "#AED581"),
        (22.0, 22.0, 22.0),
        "Problème à trois corps newtonien, masses égales, mouvement plan ; solution périodique de "
        "Chenciner et Montgomery (2000), conditions initiales de Simó ; intégration Verlet-vitesse, "
        "deux périodes ; le temps vidéo est proportionnel au temps simulé.",
        [
            {
                "label": "Chenciner & Montgomery (2000), Annals of Mathematics 152, 881–901",
                "url": "https://arxiv.org/abs/math/0011268",
            }
        ],
    )


def build_binary_star(project: Project, scene: Scene) -> None:
    """Étoile double : deux étoiles de masses 2:1 tournent autour de leur centre de masse commun."""
    from antares_studio.science.nbody import binary_star

    bodies, period = binary_star(0.5, 1.0)
    _simulation_scene(
        project,
        scene,
        bodies,
        period,
        2.0,
        "Une étoile double et son centre de masse",
        ("#FFC857", "#FF7043"),
        (40.0, 26.0),
        "Problème à deux corps newtonien, rapport de masses 1/2, orbites circulaires autour du barycentre ; "
        "intégration Verlet-vitesse (contrôle : la solution est connue analytiquement) ; deux périodes.",
        [
            {
                "label": "JPL Solar System Dynamics — two-body problem",
                "url": "https://ssd.jpl.nasa.gov/planets/approx_pos.html",
            }
        ],
    )


def build_chalkboard(project: Project, scene: Scene) -> None:
    """Tableau noir : titre, figure et formule écrits à la craie (théorème de Pythagore)."""
    c = project.canvas
    k = _scale(c)
    cx, cy = c.width / 2, c.height / 2
    scene.background = "#1D2120"
    scene.backdrop = "chalkboard_black"
    chalk = {"style_fx_chalk": 0.6, "write": 0.0, "write_style": "chalk"}
    title = new_node(
        "text",
        "Titre",
        cx,
        130 * k,
        text="Le théorème de Pythagore",
        font_size=64 * k,
        **chalk,
        font_family="Fredericka the Great",
        style_fill="#F4F1E8",
    )
    a, b = 420 * k, 300 * k
    tri = new_node(
        "polygon",
        "Triangle rectangle",
        cx - 420 * k,
        cy + 40 * k,
        points=[[-a / 2, b / 2], [a / 2, b / 2], [-a / 2, -b / 2]],
        style_fill="#00000000",
        style_stroke="#F4F1E8",
        style_stroke_width=5 * k,
        style_fx_chalk=0.6,
    )
    labels = [
        ("Côté a", cx - 420 * k, cy + 40 * k + b / 2 + 40 * k, "a"),
        ("Côté b", cx - 420 * k - a / 2 - 36 * k, cy + 40 * k, "b"),
        ("Côté c", cx - 420 * k + 30 * k, cy + 10 * k, "c"),
    ]
    marks = [
        new_node(
            "text", name, x, y, text=t, font_size=48 * k, font_family="Kalam", style_fill="#9ED4F2", **chalk
        )
        for name, x, y, t in labels
    ]
    formula = new_node(
        "formula",
        "Relation",
        cx + 380 * k,
        cy - 20 * k,
        text="a^{2} + b^{2} = c^{2}",
        font_size=84 * k,
        font_family="Kalam",
        style_fill="#F6E27F",
        **chalk,
    )
    note = new_node(
        "text",
        "Condition",
        cx + 380 * k,
        cy + 120 * k,
        text="dans tout triangle rectangle",
        font_size=40 * k,
        font_family="Kalam",
        style_fill="#F4F1E8",
        **chalk,
    )
    scene.nodes += [title, tri, *marks, formula, note]
    d = scene.duration_frames
    scene.tracks += apply_preset("write", title, {"duration_frames": max(1, d // 6)})
    scene.tracks += apply_preset("appear", tri, {"start_frame": d // 6, "duration_frames": max(1, d // 10)})
    for i, m in enumerate(marks):
        scene.tracks += apply_preset("write", m, {"start_frame": d // 4 + i * d // 30, "duration_frames": 10})
    scene.tracks += apply_preset(
        "write", formula, {"start_frame": d * 2 // 5, "duration_frames": max(1, d // 5)}
    )
    scene.tracks += apply_preset(
        "write", note, {"start_frame": d * 3 // 5, "duration_frames": max(1, d // 6)}
    )


def build_linear_map(project: Project, scene: Scene) -> None:
    """Transformation linéaire d'un plan quadrillé (cisaillement), vecteurs de base î et ĵ."""
    c = project.canvas
    k = _scale(c)
    scene.background = "#0B1020"
    grid = new_node(
        "grid",
        "Plan",
        c.width / 2,
        c.height / 2,
        width=float(c.width),
        height=float(c.height),
        step=110 * k,
        show_basis=True,
        progress=0.0,
    )
    caption = new_node(
        "callout",
        "Matrice",
        c.width / 2,
        80 * k,
        text="Cisaillement : î → (1, 0) ; ĵ → (1, 1)",
        font_size=34 * k,
        padding=14 * k,
    )
    scene.nodes += [grid, caption]
    d = scene.duration_frames
    scene.tracks += apply_preset("trace", grid, {"duration_frames": max(1, d // 4), "easing": "ease_out"})
    scene.tracks += apply_preset(
        "appear", caption, {"start_frame": d // 4, "duration_frames": max(1, d // 10)}
    )
    scene.tracks += apply_preset(
        "linear_map",
        grid,
        {
            "start_frame": d * 2 // 5,
            "duration_frames": max(1, d * 2 // 5),
            "a": 1.0,
            "b": 1.0,
            "c": 0.0,
            "d": 1.0,
        },
    )


def build_curved_spacetime(project: Project, scene: Scene) -> None:
    """Nappe d'espace-temps creusée par une masse (analogie pédagogique de la relativité générale)."""
    import numpy as np

    from antares_studio.rendering.grid import project as project_grid
    from antares_studio.rendering.grid import transform
    from antares_studio.timeline.evaluator import sample_track

    c = project.canvas
    k = _scale(c)
    scene.background = "#05070F"
    scene.backdrop = "starfield"
    gx, gy = c.width / 2, c.height * 0.42  # le creux reste au-dessus de la légende
    grid = new_node(
        "grid",
        "Espace-temps",
        gx,
        gy,
        width=1600 * k,
        height=1400 * k,
        step=70 * k,
        perspective=True,
        tilt_deg=65.0,
        warp="gravity",
        warp_amount=0.0,
        warp_radius=180 * k,
        show_axes=False,
        style_stroke="#4FC3F7",
    )
    sun = new_node("circle", "Masse", gx, gy, radius=46 * k, style_fill="#FFD27A")
    sun.style.update({"fx_glow": 40.0 * k, "fx_glow_color": "#FFB74D", "fx_glow_strength": 1.6})
    caption = scale_warning_node(c, "Analogie : la nappe figure la courbure, pas la géométrie réelle")
    scene.nodes += [grid, sun, caption]
    d = scene.duration_frames
    start, dur = d // 6, max(2, d // 2)
    warp = apply_preset("warp", grid, {"start_frame": start, "duration_frames": dur, "amount": 1.0})
    scene.tracks += warp
    # la masse descend au fond du creux : position calculée par la géométrie même de la grille
    track = Track(sun.id, "position.y")
    for f in range(start, start + dur + 1, max(1, dur // 12)):
        value = sample_track(warp[0], f)
        amount = float(value) if isinstance(value, int | float) else 0.0
        params = {**grid.params, "warp_amount": amount}
        q, z = transform(params, np.zeros((1, 2)))
        depth = float(project_grid(params, q, z)[0][1])
        track.set_keyframe(f, gy + depth - 30 * k * min(1.0, amount), "linear")
    scene.tracks.append(track)
    scene.tracks += apply_preset("appear", caption, {"start_frame": start + dur, "duration_frames": 20})


def build_solids(project: Project, scene: Scene) -> None:
    """Solides 3D de la bibliothèque qui tournent sur eux-mêmes."""
    c = project.canvas
    k = _scale(c)
    scene.background = "#0B1020"
    shapes = [("cube", "#2677B8"), ("pyramid", "#E07A5F"), ("sphere", "#81B29A"), ("icosahedron", "#F2CC8F")]
    title = new_node("text", "Titre", c.width / 2, 140 * k, text="Solides de l'espace", font_size=60 * k)
    scene.nodes.append(title)
    d = scene.duration_frames
    scene.tracks += apply_preset("write", title, {"duration_frames": max(1, d // 6)})
    for i, (shape, color) in enumerate(shapes):
        x = c.width * (i + 1) / (len(shapes) + 1)
        node = new_node(
            "solid3d", shape, x, c.height / 2 + 40 * k, shape=shape, size=280 * k, style_fill=color
        )
        scene.nodes.append(node)
        scene.tracks += apply_preset("appear", node, {"start_frame": i * 8, "duration_frames": 20})
        scene.tracks += apply_preset("spin3d", node, {"duration_frames": d, "turns": 1.0, "tilt_deg": 20.0})


def _orbit_angle_track(
    node_id: str, prop: str, start: int, dur: int, a0: float, turns: float, offset: float = 0.0
) -> Track:
    """Angle (°) qui suit l'orbite du preset « orbit » (sens trigonométrique à l'écran, y vers le bas)."""
    track = Track(node_id, prop)
    n = max(2, min(dur, int(round(72 * abs(turns)))))
    for i in range(n + 1):
        u = i / n
        track.set_keyframe(start + int(round(u * dur)), a0 - 360.0 * turns * u + offset, "linear")
    return track


def build_lunar_phases_real(project: Project, scene: Scene) -> None:
    """Phases de la Lune avec les vrais astres : vue d'en haut (Lune toujours à moitié éclairée par le
    Soleil) et, en médaillon, la Lune vue depuis la Terre, dont la phase suit l'orbite."""
    c = project.canvas
    k = _scale(c)
    scene.background = "#03050C"
    scene.backdrop = "starfield"
    cx, cy = c.width * 0.42, c.height * 0.52
    d = scene.duration_frames
    sun_light = new_node(
        "light", "Lumière du Soleil", -200 * k, cy, mode="halo", radius=900 * k, intensity=0.5
    )
    earth = new_node(
        "celestial",
        "Terre",
        cx,
        cy,
        body="earth",
        size=170 * k,
        corona=0.0,
        pitch_deg=90.0,
        light_az_deg=-90.0,
        light_el_deg=0.0,
    )
    orbit = new_node("orbit_path", "Orbite de la Lune", cx, cy, radius=300 * k)
    orbit.z_index = -1
    moon = new_node(
        "celestial",
        "Lune",
        cx + 300 * k,
        cy,
        body="moon",
        size=60 * k,
        corona=0.0,
        pitch_deg=90.0,
        light_az_deg=-90.0,
        light_el_deg=0.0,
    )
    seen = new_node(
        "celestial",
        "Lune vue de la Terre",
        c.width * 0.82,
        cy,
        body="moon",
        size=260 * k,
        corona=0.0,
        light_el_deg=0.0,
        ambient=0.02,
    )
    label = new_node(
        "text",
        "Légende du médaillon",
        c.width * 0.82,
        cy + 190 * k,
        text="Vue depuis la Terre",
        font_size=34 * k,
    )
    title = new_node(
        "text", "Titre", c.width / 2, 90 * k, text="Les phases de la Lune", font_size=60 * k, bold=True
    )
    sun_note = new_node(
        "text", "Direction du Soleil", 150 * k, cy - 60 * k, text="← lumière du Soleil", font_size=30 * k
    )
    legend = scale_warning_node(c)
    scene.nodes += [sun_light, orbit, earth, moon, seen, label, title, sun_note, legend]
    scene.tracks += apply_preset(
        "orbit",
        moon,
        {
            "center_x": cx,
            "center_y": cy,
            "radius": 300 * k,
            "duration_frames": d,
            "turns": 1,
            "start_angle_deg": 180.0,
            "samples_per_turn": 72,
        },
    )
    # vue depuis la Terre : direction de la lumière = angle de l'orbite (0 : pleine lune, 180 : nouvelle)
    scene.tracks.append(_orbit_angle_track(seen.id, "params.light_az_deg", 0, d, 180.0, 1.0))
    scene.tracks += apply_preset("spin_body", earth, {"duration_frames": d, "turns": 2.0})
    scene.tracks += apply_preset("write", title, {"duration_frames": max(1, d // 10)})
    add_sources(
        project,
        [{"label": "NASA Science — Moon phases", "url": "https://science.nasa.gov/moon/moon-phases/"}],
    )
    project.scientific_metadata.update({"representation": "schematic", "to_scale": False})


def build_doppler(project: Project, scene: Scene) -> None:
    """Effet Doppler : une source en mouvement resserre ses fronts d'onde devant elle."""
    c = project.canvas
    k = _scale(c)
    scene.background = "#0B1020"
    d = scene.duration_frames
    seconds = d / float(c.fps)
    speed_c, speed_v = 220 * k, 110 * k  # v = c/2
    waves = new_node(
        "waves",
        "Fronts d'onde",
        c.width * 0.28,
        c.height * 0.55,
        mode="fronts",
        wave_speed=speed_c,
        frequency=1.6,
        source_speed=speed_v,
        max_radius=1500 * k,
        source_size=16 * k,
        style_stroke_width=3 * k,
    )
    title = new_node(
        "text", "Titre", c.width / 2, 80 * k, text="L'effet Doppler", font_size=60 * k, bold=True
    )
    ahead = new_node(
        "callout",
        "Devant",
        c.width * 0.84,
        c.height * 0.26,
        font_size=30 * k,
        text="Devant : fronts serrés\nfréquence perçue ×2 (aigu)",
    )
    behind = new_node(
        "callout",
        "Derrière",
        c.width * 0.19,
        c.height * 0.26,
        font_size=30 * k,
        text="Derrière : fronts espacés\nfréquence perçue ×2/3 (grave)",
    )
    note = new_node(
        "formula", "Formule", c.width / 2, c.height * 0.88, text="f' = f \\frac{c}{c - v}", font_size=56 * k
    )
    scene.nodes += [waves, title, ahead, behind, note]
    scene.tracks += apply_preset("time_flow", waves, {"duration_frames": d, "seconds": seconds})
    for i, n in enumerate((title, ahead, behind, note)):
        scene.tracks += apply_preset("appear", n, {"start_frame": i * max(1, d // 8), "duration_frames": 20})
    add_sources(
        project,
        [
            {
                "label": "Effet Doppler — source mobile, milieu au repos : f' = f·c/(c − v)",
                "url": "https://fr.wikipedia.org/wiki/Effet_Doppler",
            }
        ],
    )


def build_tides(project: Project, scene: Scene) -> None:
    """Marées : la Lune tourne autour de la Terre (vue du pôle Nord) et entraîne deux bourrelets
    d'eau exagérés, l'un face à elle, l'autre à l'opposé."""
    c = project.canvas
    k = _scale(c)
    scene.background = "#03050C"
    scene.backdrop = "starfield"
    cx, cy = c.width / 2, c.height * 0.52
    d = scene.duration_frames
    earth = new_node(
        "celestial",
        "Terre",
        cx,
        cy,
        body="earth",
        size=260 * k,
        corona=0.0,
        pitch_deg=90.0,
        lit=False,
        tide_amount=0.28,
        atmosphere=0.6,
    )
    orbit = new_node("orbit_path", "Orbite de la Lune", cx, cy, radius=380 * k)
    orbit.z_index = -1
    moon = new_node("celestial", "Lune", cx + 380 * k, cy, body="moon", size=70 * k, corona=0.0, lit=False)
    title = new_node("text", "Titre", cx, 80 * k, text="Les marées", font_size=60 * k, bold=True)
    legend = scale_warning_node(c, "Bourrelets de marée très exagérés (en réalité : environ 1 m)")
    scene.nodes += [orbit, earth, moon, title, legend]
    scene.tracks += apply_preset(
        "orbit",
        moon,
        {
            "center_x": cx,
            "center_y": cy,
            "radius": 380 * k,
            "duration_frames": d,
            "turns": 1,
            "samples_per_turn": 72,
        },
    )
    scene.tracks += apply_preset("tide_follow", earth, {"duration_frames": d, "turns": 1.0})
    scene.tracks += apply_preset("spin_body", earth, {"duration_frames": d, "turns": 3.0})
    scene.tracks += apply_preset("write", title, {"duration_frames": max(1, d // 10)})
    add_sources(
        project,
        [
            {
                "label": "NOAA — Tides and Water Levels",
                "url": "https://oceanservice.noaa.gov/education/tutorial_tides/",
            }
        ],
    )
    project.scientific_metadata.update({"representation": "schematic", "to_scale": False})


def build_supernova(project: Project, scene: Scene) -> None:
    """Vie et mort d'une étoile massive : géante rouge, effondrement, supernova, trou noir."""
    c = project.canvas
    k = _scale(c)
    scene.background = "#020308"
    scene.backdrop = "starfield"
    cx, cy = c.width / 2, c.height / 2
    d = scene.duration_frames
    s1, s2, s3 = int(d * 0.35), int(d * 0.45), int(d * 0.62)  # géante rouge, effondrement, explosion
    star = new_node(
        "celestial", "Étoile", cx, cy, body="star", size=160 * k, temperature_k=9000.0, lit=False, corona=0.7
    )
    size, temp = Track(star.id, "params.size"), Track(star.id, "params.temperature_k")
    for f, s, tk in ((0, 160, 9000), (s1, 460, 3500), (s2, 470, 3400), (s2 + 8, 14, 30000)):
        size.set_keyframe(f, s * k, "ease_in_out" if f < s2 else "ease_in")
        temp.set_keyframe(f, float(tk), "ease_in_out")
    scene.tracks += [size, temp]
    scene.tracks += apply_preset("disappear", star, {"start_frame": s3 - 4, "duration_frames": 6})
    flash = new_node(
        "light", "Éclair", cx, cy, mode="halo", radius=2200 * k, intensity=0.0, style_fill="#E4F0FF"
    )
    fl = Track(flash.id, "params.intensity")
    for f, v in ((s3 - 6, 0.0), (s3, 3.5), (s3 + 30, 0.6), (s3 + 90, 0.0)):
        fl.set_keyframe(f, v, "ease_out")
    scene.tracks.append(fl)
    shell = new_node(
        "particles",
        "Supernova",
        cx,
        cy,
        mode="shell",
        count=1800,
        speed=320 * k,
        size=2.6 * k,
        lifetime=9.0,
        style_color_a="#E4F0FF",
        style_color_b="#4F7BFF",
    )
    shell.opacity = 0.0
    scene.tracks += apply_preset("appear", shell, {"start_frame": s3, "duration_frames": 3})
    scene.tracks += apply_preset(
        "time_flow", shell, {"start_frame": s3, "duration_frames": d - s3, "seconds": (d - s3) / float(c.fps)}
    )
    nebula = new_node(
        "particles",
        "Nébuleuse",
        cx,
        cy,
        mode="nebula",
        count=2500,
        radius=330 * k,
        size=5 * k,
        time_s=5.0,
        style_color_a="#5FD3FF",
        style_color_b="#FF5A8A",
    )
    nebula.opacity = 0.0
    scene.tracks += apply_preset("appear", nebula, {"start_frame": s3 + 40, "duration_frames": 60})
    hole = new_node("black_hole", "Trou noir", cx, cy, size=70 * k, inclination_deg=75.0)
    hole.opacity = 0.0
    scene.tracks += apply_preset("appear", hole, {"start_frame": s3 + 60, "duration_frames": 40})
    scene.tracks += apply_preset(
        "time_flow", hole, {"start_frame": s3, "duration_frames": d - s3, "seconds": 6.0}
    )
    scene.nodes += [nebula, star, shell, flash, hole]
    for i, (f, text) in enumerate(
        (
            (0, "Une étoile massive brûle son hydrogène"),
            (s1 - 30, "Elle gonfle : supergéante rouge"),
            (s2, "Le cœur s'effondre en moins d'une seconde"),
            (s3 + 10, "Supernova !"),
            (s3 + 100, "Il reste un trou noir"),
        )
    ):
        cap = new_node(
            "text",
            f"Étape {i + 1}",
            cx,
            c.height * 0.12,
            text=text,
            font_size=46 * k,
            write_style="typewriter",
        )
        cap.opacity = 0.0
        scene.nodes.append(cap)
        end = [s1 - 30, s2, s3 + 10, s3 + 100, d][i]
        op = Track(cap.id, "opacity")
        for fr, v in (
            (f, 0.0),
            (f + 8, 1.0),
            (max(f + 9, end - 8), 1.0),
            (max(f + 10, end), 0.0 if i < 4 else 1.0),
        ):
            op.set_keyframe(fr, v, "linear")
        scene.tracks.append(op)
    add_sources(
        project,
        [
            {
                "label": "NASA Goddard, Imagine the Universe! — Supernovae",
                "url": "https://imagine.gsfc.nasa.gov/science/objects/supernovae1.html",
            }
        ],
    )
    project.scientific_metadata.update(
        {
            "representation": "schematic",
            "to_scale": False,
            "notes": "Durées très compressées : des millions d'années en quelques secondes.",
        }
    )


def build_double_slit(project: Project, scene: Scene) -> None:
    """Photons envoyés un par un vers deux fentes : les impacts, d'abord dispersés, dessinent peu à peu
    des franges d'interférence (dualité onde-corpuscule)."""
    c = project.canvas
    k = _scale(c)
    scene.background = "#05070F"
    cy = c.height * 0.52
    d = scene.duration_frames
    laser = new_node(
        "optic",
        "Source de photons",
        220 * k,
        cy,
        element="laser",
        size=170 * k,
        active=1.0,
        style_beam_color="#7CFFB2",
    )
    slits = new_node("optic", "Deux fentes", c.width * 0.5, cy, element="double_slit", size=420 * k)
    ray = new_node(
        "ray",
        "Photons",
        0,
        0,
        points=[[320 * k, cy], [c.width * 0.5, cy]],
        mode="photons",
        wavelength_nm=532.0,
        photon_count=4,
        photon_size=7 * k,
    )
    ray.position = [0.0, 0.0]
    screen = new_node(
        "impacts",
        "Écran",
        c.width * 0.8,
        cy,
        width=150 * k,
        height=640 * k,
        count=0.0,
        max_count=8000,
        fringes=5.0,
        show_curve=False,
        dot_size=2.0 * k,
    )
    title = new_node(
        "text", "Titre", c.width / 2, 80 * k, text="Un photon à la fois…", font_size=56 * k, bold=True
    )
    scene.nodes += [laser, ray, slits, screen, title]
    scene.tracks += apply_preset("photon_travel", ray, {"duration_frames": d, "passes": 12.0})
    scene.tracks += apply_preset("impacts_build", screen, {"duration_frames": d, "total": 8000})
    scene.tracks += apply_preset("write", title, {"duration_frames": max(1, d // 10)})
    add_sources(
        project,
        [
            {
                "label": "P. Grangier, G. Roger, A. Aspect, Europhys. Lett. 1, 173 (1986)",
                "url": "https://doi.org/10.1209/0295-5075/1/4/004",
            },
            {
                "label": "A. Tonomura et al., Am. J. Phys. 57, 117 (1989)",
                "url": "https://doi.org/10.1119/1.16104",
            },
        ],
    )


def build_solar_system(project: Project, scene: Scene) -> None:
    """Les huit planètes avec leurs textures réelles, qui tournent sur elles-mêmes (tailles non à
    l'échelle entre géantes et telluriques)."""
    from antares_studio.resources.astro import BODIES

    c = project.canvas
    k = _scale(c)
    scene.background = "#03050C"
    scene.backdrop = "starfield"
    d = scene.duration_frames
    planets = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"]
    for i, pid in enumerate(planets):
        b = BODIES[pid]
        x = c.width * (i + 0.5) / len(planets)
        size = (95 if pid in ("jupiter", "saturn") else 75 if pid in ("uranus", "neptune") else 55) * k * 1.6
        node = new_node(
            "celestial",
            b.label,
            x,
            c.height * 0.5,
            body=pid,
            size=size,
            tilt_deg=b.obliquity_deg,
            corona=0.0,
            light_az_deg=-60.0,
        )
        if pid == "saturn":
            node.params["pitch_deg"] = 18.0
        label = new_node(
            "text", f"Nom {b.label}", x, c.height * 0.5 + 150 * k, text=b.label, font_size=30 * k
        )
        scene.nodes += [node, label]
        scene.tracks += apply_preset("appear", node, {"start_frame": i * 6, "duration_frames": 20})
        turns = max(0.25, min(3.0, 24.0 / abs(b.rotation_h) * 2)) * (1 if b.rotation_h > 0 else -1)
        scene.tracks += apply_preset("spin_body", node, {"duration_frames": d, "turns": turns})
    legend = scale_warning_node(c, "Tailles et distances non à l'échelle ; rotations accélérées")
    scene.nodes.append(legend)
    add_sources(
        project,
        [
            {
                "label": "NASA NSSDCA — Planetary Fact Sheet",
                "url": "https://nssdc.gsfc.nasa.gov/planetary/factsheet/",
            }
        ],
    )
    project.scientific_metadata.update({"representation": "schematic", "to_scale": False})


def build_world_map(project: Project, scene: Scene) -> None:
    """Planisphère (Natural Earth) qui se dessine d'ouest en est, continents nommés."""
    c = project.canvas
    k = _scale(c)
    scene.background = "#081726"
    m = new_node("world_map", "Planisphère", c.width / 2, c.height / 2 + 20 * k, width=1700 * k, labels=True)
    scene.nodes.append(m)
    scene.tracks += apply_preset("trace", m, {"duration_frames": max(2, scene.duration_frames // 3)})


def build_night_sky(project: Project, scene: Scene) -> None:
    """Ciel réel autour d'Orion (Hipparcos) qui défile lentement ; Orion mise en valeur."""
    c = project.canvas
    k = _scale(c)
    scene.background = "#02030A"
    sky = new_node(
        "sky",
        "Ciel d'hiver",
        c.width / 2,
        c.height / 2,
        width=float(c.width),
        height=float(c.height),
        center_ra_deg=70.0,
        center_dec_deg=5.0,
        fov_deg=70.0,
        highlight="Ori",
        label_size=24 * k,
        twinkle=0.3,
    )
    scene.nodes.append(sky)
    ra = Track(sky.id, "params.center_ra_deg")
    ra.set_keyframe(0, 70.0, "ease_in_out")
    ra.set_keyframe(scene.duration_frames, 95.0, "ease_in_out")
    scene.tracks.append(ra)
    scene.tracks += apply_preset(
        "time_flow", sky, {"duration_frames": scene.duration_frames, "seconds": 20.0}
    )


TEMPLATES: dict[str, tuple[str, TemplateBuilder]] = {
    "intro": ("Introduction (titre et sous-titre)", build_intro),
    "moon_phases": ("Phases de la Lune (Soleil, Terre, Lune en orbite)", build_moon_phases),
    "scale_comparison": ("Comparaison d'échelles (année-lumière)", build_scale_comparison),
    "orbit_vectors": ("Orbite et vecteurs (vitesse, gravitation)", build_orbit_vectors),
    "kepler_orbit": ("Orbite de Kepler (modélisation à deux corps)", build_kepler_orbit),
    "three_body": ("Trois corps en huit (simulation numérique)", build_three_body),
    "binary_star": ("Étoile double (simulation numérique)", build_binary_star),
    "chalkboard": ("Tableau noir (écriture à la craie)", build_chalkboard),
    "linear_map": ("Transformation linéaire (grille, vecteurs î et ĵ)", build_linear_map),
    "curved_spacetime": ("Espace-temps courbé par une masse", build_curved_spacetime),
    "solids": ("Solides 3D en rotation", build_solids),
    "lunar_phases_real": ("Phases de la Lune (astres réels, vue depuis la Terre)", build_lunar_phases_real),
    "doppler": ("Effet Doppler (source en mouvement)", build_doppler),
    "tides": ("Marées (Lune en orbite, bourrelets exagérés)", build_tides),
    "supernova": ("Vie et mort d'une étoile (supernova, trou noir)", build_supernova),
    "double_slit": ("Photons et fentes de Young (onde-corpuscule)", build_double_slit),
    "solar_system": ("Les planètes du Système solaire", build_solar_system),
    "world_map": ("Planisphère (continents)", build_world_map),
    "night_sky": ("Ciel étoilé réel (Orion)", build_night_sky),
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

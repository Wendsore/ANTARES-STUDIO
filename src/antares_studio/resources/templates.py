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

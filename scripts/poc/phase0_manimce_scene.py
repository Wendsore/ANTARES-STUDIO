# Phase 0 PoC — Manim Community 0.22.0 (environnement isolé, voir docs/research/2026-10-20-moteurs-rendu-2d.md)
from manim import *

class EarthMoon(Scene):
    def construct(self):
        self.camera.background_color = "#0b1020"
        earth = Circle(radius=0.8, color="#2677B8", fill_opacity=1, stroke_width=0)
        orbit = Circle(radius=2.5, color=WHITE, stroke_opacity=0.25)
        moon = Circle(radius=0.25, color="#D9D9D9", fill_opacity=1, stroke_width=0).move_to(orbit.point_at_angle(0))
        label = Text("Schéma non à l'échelle — Terre et Lune", font_size=28).to_edge(DOWN).to_edge(LEFT)
        arrow = always_redraw(lambda: Arrow(moon.get_center(), moon.get_center() + 0.9 * rotate_vector(normalize(moon.get_center()), PI/2), buff=0, color="#F2A93B"))
        self.add(earth, orbit, moon, arrow)
        self.play(FadeIn(label, run_time=0.5), MoveAlongPath(moon, orbit, run_time=5, rate_func=linear))

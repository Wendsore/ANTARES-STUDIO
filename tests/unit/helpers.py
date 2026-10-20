"""Constructeurs de projets de test (fixtures synthétiques, sans ressource tierce)."""

from __future__ import annotations

from antares_studio.domain.kinds import spec_for
from antares_studio.domain.model import Canvas, Node, Project, Scene


def make_node(kind: str, name: str, **kwargs: object) -> Node:
    spec = spec_for(kind)
    node = Node.create(kind, name, style=spec.default_style(), params=spec.default_params())
    for k, v in kwargs.items():
        setattr(node, k, v)
    return node


def earth_moon_project(duration_frames: int = 300) -> tuple[Project, Scene, Node, Node]:
    project = Project.create("Phases de la Lune", Canvas(1920, 1080, 30, 1))
    scene = Scene.create("Orbite", duration_frames=duration_frames)
    earth = make_node("circle", "Terre", position=[960.0, 540.0])
    earth.params["radius"] = 80.0
    moon = make_node("circle", "Lune", position=[1260.0, 540.0])
    moon.params["radius"] = 25.0
    moon.style["fill"] = "#D9D9D9"
    scene.nodes += [earth, moon]
    project.scenes.append(scene)
    return project, scene, earth, moon

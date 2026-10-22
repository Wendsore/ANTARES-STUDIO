"""Vignettes de la bibliothèque : rendues par le moteur de rendu lui-même, donc fidèles à l'export.

Les formes sont dessinées avec leurs paramètres par défaut ; les modèles sont rendus à 40 % de leur
première scène. Les objets qui dépendent d'une ressource (image, données, séquence) ou dont le rendu
réduit serait illisible (texte, équation) reçoivent une icône.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap

from antares_studio.app import icons
from antares_studio.domain.kinds import spec_for
from antares_studio.domain.model import Canvas, Node, Project, Scene
from antares_studio.rendering.qt_painter import local_bounds, paint_scene_state, render_state_to_image
from antares_studio.resources.templates import TEMPLATES, create_project
from antares_studio.timeline.evaluator import evaluate

RENDERED_KINDS = ("circle", "ellipse", "rect", "polygon", "star", "line", "arrow", "orbit_path")
KIND_ICONS: dict[str, str] = {
    "text": "type",
    "callout": "message-square-text",
    "formula": "sigma",
    "chart": "chart-spline",
    "image": "image",
    "image_sequence": "box",
    "group": "group",
    "camera": "video",
}
PRESET_ICONS: dict[str, str] = {
    "appear": "eye",
    "disappear": "eye-off",
    "translate": "move-right",
    "rotate": "rotate-cw",
    "pulse": "activity",
    "orbit": "orbit",
    "trace": "chart-spline",
    "kepler": "orbit",
}
_kind_cache: dict[tuple[str, int, str], QIcon] = {}
_template_cache: dict[tuple[str, int, int], QPixmap] = {}


def _single_node_project(kind: str) -> tuple[Project, Scene, Node]:
    spec = spec_for(kind)
    node = Node.create(kind, spec.label, style=spec.default_style(), params=spec.default_params())
    if kind == "orbit_path":
        node.style["stroke"] = "#CFD8DC"
        node.style["stroke_width"] = 6.0
    project = Project.create("vignette", Canvas(400, 400, 30, 1))
    scene = Scene.create("vignette", duration_frames=1)
    scene.background = "#00000000"
    scene.nodes.append(node)
    project.scenes.append(scene)
    return project, scene, node


def kind_image(kind: str, size: int = 40) -> QImage:
    """Rendu réel d'un objet ``kind`` avec ses valeurs par défaut, centré et mis à l'échelle."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    if kind not in RENDERED_KINDS:
        return icons.render_svg(KIND_ICONS.get(kind, "square"), size)
    project, scene, node = _single_node_project(kind)
    state = evaluate(project, scene.id, 0)
    bounds = local_bounds(state.nodes[0])
    extent = max(bounds.width(), bounds.height(), 1.0) * 1.1
    # le canevas de 400 unités est rendu dans ``size`` px : l'objet doit couvrir (size - 4) px
    k = (size - 4) * (400 / size) / extent
    node.scale = [k, k]
    if kind in ("line", "arrow", "orbit_path"):  # épaisseur visible (~3 px) une fois réduite
        node.style["stroke_width"] = 3.0 / (k * size / 400)
    if kind == "arrow":
        node.params["head_size"] = 9.0 / (k * size / 400)
    center = bounds.center()
    node.position = [200.0 - center.x() * k, 200.0 - center.y() * k]
    state = evaluate(project, scene.id, 0)
    painter = QPainter(img)
    try:
        paint_scene_state(painter, state, project.canvas, size, size, paint_background=False)
    finally:
        painter.end()
    return img


def kind_icon(kind: str, size: int = 40) -> QIcon:
    from antares_studio.app import theme

    key = (kind, size, theme.active().name)
    cached = _kind_cache.get(key)
    if cached is None:
        cached = QIcon(QPixmap.fromImage(kind_image(kind, size)))
        _kind_cache[key] = cached
    return cached


def preset_icon(preset_id: str) -> QIcon:
    return icons.icon(PRESET_ICONS.get(preset_id, "sparkles"))


def template_pixmap(template_id: str, width: int = 192, height: int = 108) -> QPixmap:
    """Aperçu réel d'un modèle : sa scène rendue à 40 % de sa durée (aucune ressource externe)."""
    key = (template_id, width, height)
    cached = _template_cache.get(key)
    if cached is not None:
        return cached
    if template_id and template_id not in TEMPLATES:
        raise KeyError(template_id)
    project = create_project("Titre de la vidéo", Canvas(1280, 720, 30, 1), template_id, 12)
    scene = project.scenes[0]
    state = evaluate(project, scene.id, int(scene.duration_frames * 0.4))
    img = render_state_to_image(state, project.canvas, width, height)
    pix = QPixmap.fromImage(img)
    _template_cache[key] = pix
    return pix


def clear_cache() -> None:
    _kind_cache.clear()

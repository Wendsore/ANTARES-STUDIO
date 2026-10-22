"""Transitions d'entrée de scène, partagées par l'éditeur et l'export (même image des deux côtés).

Une transition occupe les ``duration_frames`` premières images d'une scène : elle part de la dernière
image de la scène précédente (du noir pour la première scène) et révèle la scène courante. La durée totale
de la vidéo ne change pas.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter

from antares_studio.domain.model import Project
from antares_studio.rendering.qt_painter import AssetResolver, ImageCache, render_state_to_image
from antares_studio.timeline.easing import ease_in_out
from antares_studio.timeline.evaluator import SceneState, evaluate

TRANSITION_LABELS: dict[str, str] = {
    "none": "Aucune (coupe franche)",
    "fade": "Fondu enchaîné",
    "fade_black": "Fondu au noir",
    "slide_left": "Glissement vers la gauche",
    "slide_up": "Glissement vers le haut",
    "wipe": "Volet (de gauche à droite)",
}


def transition_at(project: Project, scene_id: str, frame: int) -> tuple[str, float, str | None] | None:
    """(type, progression u ∈ ]0, 1[, scène précédente ou None) si ``frame`` est dans la transition."""
    scene = project.scene(scene_id)
    tr = scene.transition
    if tr.kind == "none" or tr.duration_frames < 1 or frame >= tr.duration_frames or frame < 0:
        return None
    index = next(i for i, s in enumerate(project.scenes) if s.id == scene_id)
    previous = project.scenes[index - 1].id if index > 0 else None
    return tr.kind, (frame + 1) / (tr.duration_frames + 1), previous


def compose(painter: QPainter, kind: str, u: float, before: QImage, after: QImage, w: int, h: int) -> None:
    """Dessine l'étape ``u`` de la transition ``kind`` entre deux images de même taille."""
    painter.save()
    full = QRectF(0, 0, w, h)
    if kind == "fade":
        painter.drawImage(full, before)
        painter.setOpacity(u)
        painter.drawImage(full, after)
    elif kind == "fade_black":
        painter.fillRect(full, QColor(0, 0, 0))
        if u < 0.5:
            painter.setOpacity(1.0 - 2.0 * u)
            painter.drawImage(full, before)
        else:
            painter.setOpacity(2.0 * u - 1.0)
            painter.drawImage(full, after)
    elif kind in ("slide_left", "slide_up"):
        e = ease_in_out(u)
        if kind == "slide_left":
            painter.drawImage(QRectF(-e * w, 0, w, h), before)
            painter.drawImage(QRectF((1 - e) * w, 0, w, h), after)
        else:
            painter.drawImage(QRectF(0, -e * h, w, h), before)
            painter.drawImage(QRectF(0, (1 - e) * h, w, h), after)
    elif kind == "wipe":
        e = ease_in_out(u)
        painter.drawImage(full, before)
        painter.setClipRect(QRectF(0, 0, e * w, h))
        painter.drawImage(full, after)
    else:
        painter.drawImage(full, after)
    painter.restore()


class FrameRenderer:
    """Rastérise une image d'une scène, transition d'entrée comprise ; garde en cache la dernière image
    de la scène précédente (``token`` : version du projet, pour invalider après une modification)."""

    def __init__(
        self, project: Project, assets: AssetResolver | None = None, cache: ImageCache | None = None
    ):
        self.project = project
        self.assets = assets
        self.cache = cache or ImageCache()
        self._previous: dict[tuple[str | None, int, int, int, bool], QImage] = {}

    def _state_image(self, state: SceneState, w: int, h: int) -> QImage:
        return render_state_to_image(
            state,
            self.project.canvas,
            w,
            h,
            self.assets,
            self.cache,
            subtitle_style=self.project.subtitle_style,
        )

    def previous_image(
        self, scene_id: str | None, w: int, h: int, use_camera: bool = True, token: int = 0
    ) -> QImage:
        key = (scene_id, w, h, token, use_camera)
        img = self._previous.get(key)
        if img is None:
            if scene_id is None:
                img = QImage(w, h, QImage.Format.Format_RGBA8888)
                img.fill(QColor(0, 0, 0))
            else:
                prev = self.project.scene(scene_id)
                img = self._state_image(
                    evaluate(self.project, scene_id, prev.duration_frames - 1, use_camera), w, h
                )
            if len(self._previous) > 8:
                self._previous.clear()
            self._previous[key] = img
        return img

    def render(
        self,
        scene_id: str,
        frame: int,
        w: int,
        h: int,
        use_camera: bool = True,
        state: SceneState | None = None,
        token: int = 0,
    ) -> QImage:
        state = state or evaluate(self.project, scene_id, frame, use_camera)
        current = self._state_image(state, w, h)
        tr = transition_at(self.project, scene_id, state.frame)
        if tr is None:
            return current
        kind, u, previous = tr
        out = QImage(w, h, QImage.Format.Format_RGBA8888)
        out.fill(0)
        painter = QPainter(out)
        try:
            compose(painter, kind, u, self.previous_image(previous, w, h, use_camera, token), current, w, h)
        finally:
            painter.end()
        return out

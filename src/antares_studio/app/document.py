"""Document de travail : pont entre le domaine pur et les widgets Qt (signaux, sélection, frame courante)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from antares_studio.domain.commands import (
    Command,
    SetKeyframe,
    SetProperties,
    SetProperty,
    UndoStack,
)
from antares_studio.domain.model import Node, Project, Scene
from antares_studio.domain.properties import is_animatable
from antares_studio.persistence.paths import UnsafePathError, resolve_under
from antares_studio.persistence.store import ProjectPaths, ProjectStore, resolve_project_root
from antares_studio.timeline.evaluator import SceneState, evaluate


class ProjectDocument(QObject):
    """Projet ouvert dans l'éditeur. Toute modification passe par ``push`` (undo/redo)."""

    changed = Signal()  # modèle modifié (après commande, undo ou redo)
    frameChanged = Signal(int)
    selectionChanged = Signal(list)
    sceneChanged = Signal(str)
    pathChanged = Signal()
    dirtyChanged = Signal(bool)

    def __init__(self, project: Project, root: Path | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self.project = project
        self.paths: ProjectPaths | None = ProjectPaths(resolve_project_root(root)) if root else None
        self.store = ProjectStore()
        self.undo = UndoStack(project)
        self.undo.listeners.append(self._on_stack_changed)
        self.version = 0
        self._frame = 0
        self._selection: list[str] = []
        self._scene_id: str = project.scenes[0].id if project.scenes else ""
        self.auto_key = False
        # éditeur : voir à travers la caméra (comme l'export) ou toute la scène avec le cadre en surimpression
        self.preview_camera = True
        self._state_cache: tuple[int, str, int, bool, SceneState] | None = None
        self._last_dirty = False

    # --- accès -----------------------------------------------------------
    @property
    def scene(self) -> Scene | None:
        return self.project.find_scene(self._scene_id)

    @property
    def scene_id(self) -> str:
        return self._scene_id

    @property
    def frame(self) -> int:
        return self._frame

    @property
    def selection(self) -> list[str]:
        return list(self._selection)

    @property
    def selected_nodes(self) -> list[Node]:
        scene = self.scene
        if scene is None:
            return []
        return [n for n in (scene.find_node(i) for i in self._selection) if n is not None]

    @property
    def is_dirty(self) -> bool:
        return not self.undo.is_clean

    @property
    def title(self) -> str:
        return self.project.title or "Sans titre"

    @property
    def root(self) -> Path | None:
        return self.paths.root if self.paths else None

    def state(self) -> SceneState | None:
        scene = self.scene
        if scene is None:
            return None
        key = (self.version, scene.id, self._frame, self.preview_camera)
        if self._state_cache and self._state_cache[:4] == key:
            return self._state_cache[4]
        st = evaluate(self.project, scene.id, self._frame, use_camera=self.preview_camera)
        self._state_cache = (*key, st)
        return st

    def resolve_asset(self, asset_id: str) -> Path | None:
        asset = self.project.asset(asset_id)
        if asset is None or self.paths is None:
            return None
        try:
            return resolve_under(self.paths.root, asset.path)
        except UnsafePathError:
            return None

    # --- mutations -------------------------------------------------------
    def push(self, cmd: Command, merge: bool = False) -> None:
        self.undo.push(cmd, merge=merge)

    @contextmanager
    def macro(self, label: str) -> Iterator[None]:
        """Regroupe les commandes poussées dans le bloc en une seule étape d'annulation.

        En cas d'exception, les commandes déjà appliquées sont défaites puis l'exception est relancée.
        """
        self.undo.begin_macro(label)
        try:
            yield
        except BaseException:
            self.undo.abort_macro()
            raise
        self.undo.end_macro()

    def set_node_property(self, node_id: str, path: str, value: Any, merge: bool = False) -> None:
        """Modifie une propriété ; pose une image clé si elle est animée ou si « clé auto » est actif."""
        scene = self.scene
        if scene is None:
            return
        node = scene.node(node_id)
        animated = scene.track_for(node_id, path) is not None
        if (animated or self.auto_key) and is_animatable(node, path):
            self.push(SetKeyframe(scene.id, node_id, path, self._frame, value), merge=False)
        else:
            self.push(SetProperty(scene.id, node_id, path, value), merge=merge)

    def set_node_properties(self, node_id: str, values: dict[str, Any], merge: bool = False) -> None:
        scene = self.scene
        if scene is None:
            return
        node = scene.node(node_id)
        keyed = {p: v for p, v in values.items() if scene.track_for(node_id, p) is not None or self.auto_key}
        keyed = {p: v for p, v in keyed.items() if is_animatable(node, p)}
        plain = {p: v for p, v in values.items() if p not in keyed}
        if plain:
            self.push(SetProperties(scene.id, node_id, plain), merge=merge)
        for p, v in keyed.items():
            self.push(SetKeyframe(scene.id, node_id, p, self._frame, v))

    def set_frame(self, frame: int) -> None:
        scene = self.scene
        limit = scene.duration_frames - 1 if scene else 0
        frame = max(0, min(int(frame), max(0, limit)))
        if frame != self._frame:
            self._frame = frame
            self.frameChanged.emit(frame)

    def set_scene(self, scene_id: str) -> None:
        if scene_id != self._scene_id and self.project.find_scene(scene_id) is not None:
            self._scene_id = scene_id
            self._frame = 0
            self._selection = []
            self.sceneChanged.emit(scene_id)
            self.frameChanged.emit(0)
            self.selectionChanged.emit([])

    def set_selection(self, ids: list[str]) -> None:
        scene = self.scene
        valid = [i for i in ids if scene is not None and scene.find_node(i) is not None]
        if valid != self._selection:
            self._selection = valid
            self.selectionChanged.emit(list(valid))

    def _on_stack_changed(self) -> None:
        self.version += 1
        scene = self.scene
        if scene is None and self.project.scenes:
            self._scene_id = self.project.scenes[0].id
            self.sceneChanged.emit(self._scene_id)
        if scene is not None:
            self._selection = [i for i in self._selection if scene.find_node(i) is not None]
            self._frame = max(0, min(self._frame, scene.duration_frames - 1))
        self.changed.emit()
        dirty = self.is_dirty
        if dirty != self._last_dirty:
            self._last_dirty = dirty
            self.dirtyChanged.emit(dirty)

    # --- persistance -----------------------------------------------------
    def save(self, root: Path | None = None) -> Path:
        if root is not None:
            self.paths = (
                self.store.create(root, self.project)
                if not Path(root).exists()
                else ProjectPaths(resolve_project_root(root))
            )
            if Path(self.paths.root).exists() and not self.paths.project_file.exists():
                self.store.create(self.paths.root, self.project)
            self.pathChanged.emit()
        if self.paths is None:
            raise ValueError("aucun emplacement de projet")
        target = self.store.save_atomic(self.project, self.paths.project_file)
        self.undo.mark_clean()
        self._on_stack_changed()
        return target

    def autosave(self) -> Path | None:
        if self.paths is None or not self.is_dirty:
            return None
        return self.store.autosave(self.project, self.paths.root)

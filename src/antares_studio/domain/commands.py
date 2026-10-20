"""Commandes réversibles (undo/redo) sur le modèle de projet. Sans Qt."""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from antares_studio.domain.model import Keyframe, Node, Project, Scene, Track
from antares_studio.domain.properties import get_property, set_property


class Command(Protocol):
    label: str

    def do(self, project: Project) -> None: ...

    def undo(self, project: Project) -> None: ...


@dataclass
class AddNode:
    scene_id: str
    node: Node
    index: int | None = None
    label: str = "Ajouter un objet"

    def do(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        if self.index is None:
            scene.nodes.append(self.node)
        else:
            scene.nodes.insert(self.index, self.node)

    def undo(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        scene.nodes = [n for n in scene.nodes if n.id != self.node.id]


@dataclass
class RemoveNode:
    """Supprime un nœud, ses descendants et leurs pistes ; tout est restauré à l'undo."""

    scene_id: str
    node_id: str
    label: str = "Supprimer l'objet"
    _removed: list[tuple[int, Node]] = field(default_factory=list, repr=False)
    _tracks: list[tuple[int, Track]] = field(default_factory=list, repr=False)

    def do(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        ids = {self.node_id}
        changed = True
        while changed:
            changed = False
            for n in scene.nodes:
                if n.parent_id in ids and n.id not in ids:
                    ids.add(n.id)
                    changed = True
        self._removed = [(i, n) for i, n in enumerate(scene.nodes) if n.id in ids]
        self._tracks = [(i, t) for i, t in enumerate(scene.tracks) if t.target_id in ids]
        scene.nodes = [n for n in scene.nodes if n.id not in ids]
        scene.tracks = [t for t in scene.tracks if t.target_id not in ids]

    def undo(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        for i, n in self._removed:
            scene.nodes.insert(min(i, len(scene.nodes)), n)
        for i, t in self._tracks:
            scene.tracks.insert(min(i, len(scene.tracks)), t)


@dataclass
class SetProperty:
    scene_id: str
    node_id: str
    path: str
    value: Any
    label: str = "Modifier une propriété"
    _old: Any = field(default=None, repr=False)

    def do(self, project: Project) -> None:
        node = project.scene(self.scene_id).node(self.node_id)
        self._old = copy.deepcopy(get_property(node, self.path))
        set_property(node, self.path, copy.deepcopy(self.value))

    def undo(self, project: Project) -> None:
        node = project.scene(self.scene_id).node(self.node_id)
        set_property(node, self.path, copy.deepcopy(self._old))

    def merge_with(self, other: SetProperty) -> bool:
        """Fusionne des modifications successives de la même propriété (glisser continu)."""
        if (self.scene_id, self.node_id, self.path) != (other.scene_id, other.node_id, other.path):
            return False
        self.value = copy.deepcopy(other.value)
        return True


@dataclass
class SetProperties:
    """Modifie plusieurs propriétés d'un nœud en une seule étape d'annulation (glisser, poignées)."""

    scene_id: str
    node_id: str
    values: dict[str, Any]
    label: str = "Modifier l'objet"
    _old: dict[str, Any] = field(default_factory=dict, repr=False)

    def do(self, project: Project) -> None:
        node = project.scene(self.scene_id).node(self.node_id)
        if not self._old:
            self._old = {p: copy.deepcopy(get_property(node, p)) for p in self.values}
        for p, v in self.values.items():
            set_property(node, p, copy.deepcopy(v))

    def undo(self, project: Project) -> None:
        node = project.scene(self.scene_id).node(self.node_id)
        for p, v in self._old.items():
            set_property(node, p, copy.deepcopy(v))

    def merge_with(self, other: SetProperties) -> bool:
        if (self.scene_id, self.node_id) != (other.scene_id, other.node_id):
            return False
        if set(other.values) - set(self.values):
            return False
        self.values.update(copy.deepcopy(other.values))
        return True


@dataclass
class SetKeyframe:
    scene_id: str
    node_id: str
    path: str
    frame: int
    value: Any
    easing: str = "linear"
    label: str = "Poser une image clé"
    _old: Keyframe | None = field(default=None, repr=False)
    _track_created: bool = field(default=False, repr=False)

    def do(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        track = scene.track_for(self.node_id, self.path)
        if track is None:
            track = scene.ensure_track(self.node_id, self.path)
            self._track_created = True
        existing = next((k for k in track.keyframes if k.frame == self.frame), None)
        self._old = copy.deepcopy(existing) if existing else None
        track.set_keyframe(self.frame, copy.deepcopy(self.value), self.easing)

    def undo(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        track = scene.track_for(self.node_id, self.path)
        if track is None:
            return
        track.remove_keyframe(self.frame)
        if self._old is not None:
            track.set_keyframe(self._old.frame, self._old.value, self._old.easing)
        if self._track_created:
            scene.tracks = [t for t in scene.tracks if t is not track]

    def merge_with(self, other: SetKeyframe) -> bool:
        """Fusionne des poses successives de la même clé (glisser continu sur une propriété animée)."""
        if (self.scene_id, self.node_id, self.path, self.frame) != (
            other.scene_id,
            other.node_id,
            other.path,
            other.frame,
        ):
            return False
        self.value = copy.deepcopy(other.value)
        self.easing = other.easing
        return True


@dataclass
class RemoveKeyframe:
    scene_id: str
    node_id: str
    path: str
    frame: int
    label: str = "Supprimer une image clé"
    _old: Keyframe | None = field(default=None, repr=False)

    def do(self, project: Project) -> None:
        track = project.scene(self.scene_id).track_for(self.node_id, self.path)
        if track is None:
            return
        self._old = next((copy.deepcopy(k) for k in track.keyframes if k.frame == self.frame), None)
        track.remove_keyframe(self.frame)

    def undo(self, project: Project) -> None:
        if self._old is None:
            return
        track = project.scene(self.scene_id).ensure_track(self.node_id, self.path)
        track.set_keyframe(self._old.frame, self._old.value, self._old.easing)


@dataclass
class MoveKeyframe:
    scene_id: str
    node_id: str
    path: str
    frame: int
    new_frame: int
    label: str = "Déplacer une image clé"
    _displaced: Keyframe | None = field(default=None, repr=False)

    def do(self, project: Project) -> None:
        track = project.scene(self.scene_id).track_for(self.node_id, self.path)
        if track is None:
            return
        kf = next((k for k in track.keyframes if k.frame == self.frame), None)
        if kf is None:
            return
        self._displaced = next((copy.deepcopy(k) for k in track.keyframes if k.frame == self.new_frame), None)
        track.remove_keyframe(self.new_frame)
        kf.frame = self.new_frame
        track.keyframes.sort(key=lambda k: k.frame)

    def undo(self, project: Project) -> None:
        track = project.scene(self.scene_id).track_for(self.node_id, self.path)
        if track is None:
            return
        kf = next((k for k in track.keyframes if k.frame == self.new_frame), None)
        if kf is not None:
            kf.frame = self.frame
        if self._displaced is not None:
            track.set_keyframe(self._displaced.frame, self._displaced.value, self._displaced.easing)
        track.keyframes.sort(key=lambda k: k.frame)


@dataclass
class RemoveTrack:
    scene_id: str
    node_id: str
    path: str
    label: str = "Supprimer l'animation"
    _old: tuple[int, Track] | None = field(default=None, repr=False)

    def do(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        for i, t in enumerate(scene.tracks):
            if t.target_id == self.node_id and t.property == self.path:
                self._old = (i, t)
                del scene.tracks[i]
                return

    def undo(self, project: Project) -> None:
        if self._old is None:
            return
        scene = project.scene(self.scene_id)
        i, t = self._old
        scene.tracks.insert(min(i, len(scene.tracks)), t)


@dataclass
class ReplaceTracks:
    """Remplace l'ensemble des pistes d'un nœud (utilisé par les presets)."""

    scene_id: str
    node_id: str
    tracks: list[Track]
    label: str = "Appliquer une animation"
    _old: list[Track] = field(default_factory=list, repr=False)

    def do(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        self._old = [t for t in scene.tracks if t.target_id == self.node_id]
        scene.tracks = [t for t in scene.tracks if t.target_id != self.node_id] + copy.deepcopy(self.tracks)

    def undo(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        scene.tracks = [t for t in scene.tracks if t.target_id != self.node_id] + self._old


@dataclass
class ReorderNode:
    scene_id: str
    node_id: str
    new_index: int
    label: str = "Réordonner"
    _old_index: int = field(default=0, repr=False)

    def do(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        self._old_index = next(i for i, n in enumerate(scene.nodes) if n.id == self.node_id)
        node = scene.nodes.pop(self._old_index)
        scene.nodes.insert(max(0, min(self.new_index, len(scene.nodes))), node)

    def undo(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        idx = next(i for i, n in enumerate(scene.nodes) if n.id == self.node_id)
        node = scene.nodes.pop(idx)
        scene.nodes.insert(self._old_index, node)


@dataclass
class SetSceneProperty:
    scene_id: str
    attr: str  # name | duration_frames | background
    value: Any
    label: str = "Modifier la scène"
    _old: Any = field(default=None, repr=False)

    def do(self, project: Project) -> None:
        scene = project.scene(self.scene_id)
        if self.attr not in ("name", "duration_frames", "background"):
            raise KeyError(self.attr)
        self._old = getattr(scene, self.attr)
        setattr(scene, self.attr, self.value)

    def undo(self, project: Project) -> None:
        setattr(project.scene(self.scene_id), self.attr, self._old)


@dataclass
class AddScene:
    scene: Scene
    index: int | None = None
    label: str = "Ajouter une scène"

    def do(self, project: Project) -> None:
        if self.index is None:
            project.scenes.append(self.scene)
        else:
            project.scenes.insert(self.index, self.scene)

    def undo(self, project: Project) -> None:
        project.scenes = [s for s in project.scenes if s.id != self.scene.id]


@dataclass
class RemoveScene:
    scene_id: str
    label: str = "Supprimer la scène"
    _old: tuple[int, Scene] | None = field(default=None, repr=False)

    def do(self, project: Project) -> None:
        for i, s in enumerate(project.scenes):
            if s.id == self.scene_id:
                self._old = (i, s)
                del project.scenes[i]
                return

    def undo(self, project: Project) -> None:
        if self._old is not None:
            i, s = self._old
            project.scenes.insert(min(i, len(project.scenes)), s)


class UndoStack:
    """Pile undo/redo. ``push`` exécute la commande ; ``listener`` est notifié après chaque changement."""

    def __init__(self, project: Project, limit: int = 500):
        self.project = project
        self.limit = limit
        self._undo: list[Command] = []
        self._redo: list[Command] = []
        self.listeners: list[Callable[[], None]] = []
        self.clean_index = 0  # position correspondant à l'état sauvegardé

    def push(self, cmd: Command, merge: bool = False) -> None:
        if merge and self._undo and not self._redo:
            last = self._undo[-1]
            merge_fn = getattr(last, "merge_with", None)
            if type(last) is type(cmd) and merge_fn is not None and merge_fn(cmd):
                cmd.do(self.project)
                self._notify()
                return
        cmd.do(self.project)
        self._undo.append(cmd)
        if len(self._undo) > self.limit:
            del self._undo[0]
            self.clean_index = max(-1, self.clean_index - 1)
        self._redo.clear()
        self._notify()

    def undo(self) -> bool:
        if not self._undo:
            return False
        cmd = self._undo.pop()
        cmd.undo(self.project)
        self._redo.append(cmd)
        self._notify()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        cmd = self._redo.pop()
        cmd.do(self.project)
        self._undo.append(cmd)
        self._notify()
        return True

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_label(self) -> str:
        return self._undo[-1].label if self._undo else ""

    @property
    def redo_label(self) -> str:
        return self._redo[-1].label if self._redo else ""

    def mark_clean(self) -> None:
        self.clean_index = len(self._undo)

    @property
    def is_clean(self) -> bool:
        return self.clean_index == len(self._undo)

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
        self.clean_index = 0
        self._notify()

    def _notify(self) -> None:
        for cb in list(self.listeners):
            cb()

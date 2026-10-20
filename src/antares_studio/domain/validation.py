"""Validation structurelle d'un projet : identifiants, références, cycles, valeurs."""

from __future__ import annotations

import math
from dataclasses import dataclass

from antares_studio.domain.colors import is_color
from antares_studio.domain.ids import is_valid_id
from antares_studio.domain.kinds import KINDS, check_param_value, spec_for
from antares_studio.domain.model import EASINGS, Project, Scene
from antares_studio.domain.properties import check_property_value, is_animatable


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class ProjectValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__("; ".join(str(i) for i in issues))


def validate_project(project: Project) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not is_valid_id(project.project_id):
        issues.append(ValidationIssue("project_id", "identifiant invalide"))
    c = project.canvas
    if c.width <= 0 or c.height <= 0 or c.width > 16384 or c.height > 16384:
        issues.append(ValidationIssue("canvas", "dimensions hors bornes (1..16384)"))
    if c.fps_num <= 0 or c.fps_den <= 0 or c.fps_num / c.fps_den > 240:
        issues.append(ValidationIssue("canvas", "cadence invalide (0 < fps <= 240)"))
    seen_scene: set[str] = set()
    for si, scene in enumerate(project.scenes):
        if scene.id in seen_scene:
            issues.append(ValidationIssue(f"scenes[{si}].id", f"identifiant de scène dupliqué : {scene.id}"))
        seen_scene.add(scene.id)
        issues.extend(validate_scene(scene, prefix=f"scenes[{si}]"))
    seen_asset: set[str] = set()
    for ai, asset in enumerate(project.assets):
        if asset.id in seen_asset:
            issues.append(ValidationIssue(f"assets[{ai}].id", "identifiant de ressource dupliqué"))
        seen_asset.add(asset.id)
        if asset.path.startswith(("/", "\\")) or ".." in asset.path.split("/") or ":" in asset.path:
            issues.append(ValidationIssue(f"assets[{ai}].path", "chemin non relatif ou traversée interdite"))
    return issues


def validate_scene(scene: Scene, prefix: str = "scene") -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not is_valid_id(scene.id):
        issues.append(ValidationIssue(f"{prefix}.id", "identifiant invalide"))
    if scene.duration_frames <= 0 or scene.duration_frames > 10_000_000:
        issues.append(ValidationIssue(f"{prefix}.duration_frames", "durée hors bornes"))
    if not is_color(scene.background):
        issues.append(ValidationIssue(f"{prefix}.background", "couleur invalide"))
    ids: dict[str, int] = {}
    for ni, node in enumerate(scene.nodes):
        p = f"{prefix}.nodes[{ni}]"
        if not is_valid_id(node.id):
            issues.append(ValidationIssue(f"{p}.id", "identifiant invalide"))
        if node.id in ids:
            issues.append(ValidationIssue(f"{p}.id", f"identifiant dupliqué : {node.id}"))
        ids[node.id] = ni
        if node.kind not in KINDS:
            issues.append(ValidationIssue(f"{p}.kind", f"type inconnu : {node.kind}"))
            continue
        for path in ("position.x", "position.y", "scale.x", "scale.y", "rotation_deg", "opacity"):
            try:
                from antares_studio.domain.properties import get_property

                err = check_property_value(node, path, get_property(node, path))
            except (KeyError, IndexError, TypeError):
                err = "valeur absente"
            if err:
                issues.append(ValidationIssue(f"{p}.{path}", err))
        if not isinstance(node.z_index, int) or isinstance(node.z_index, bool):
            issues.append(ValidationIssue(f"{p}.z_index", "entier attendu"))
        spec = spec_for(node.kind)
        for ps in spec.params:
            if ps.name in node.params:
                err = check_param_value(ps, node.params[ps.name])
                if err:
                    issues.append(ValidationIssue(f"{p}.params.{ps.name}", err))
        for ps in spec.style:
            if ps.name in node.style:
                err = check_param_value(ps, node.style[ps.name])
                if err:
                    issues.append(ValidationIssue(f"{p}.style.{ps.name}", err))
    # références parent et cycles
    for ni, node in enumerate(scene.nodes):
        if node.parent_id is not None:
            if node.parent_id not in ids:
                issues.append(
                    ValidationIssue(f"{prefix}.nodes[{ni}].parent_id", f"parent inconnu : {node.parent_id}")
                )
            elif node.parent_id == node.id:
                issues.append(
                    ValidationIssue(
                        f"{prefix}.nodes[{ni}].parent_id", "un nœud ne peut être son propre parent"
                    )
                )
    for cycle in find_parent_cycles(scene):
        issues.append(ValidationIssue(f"{prefix}.nodes", f"cycle de parenté : {' -> '.join(cycle)}"))
    seen_clip: set[str] = set()
    for ci, clip in enumerate(scene.audio):
        cp = f"{prefix}.audio[{ci}]"
        if not is_valid_id(clip.id) or clip.id in seen_clip:
            issues.append(ValidationIssue(f"{cp}.id", "identifiant de clip invalide ou dupliqué"))
        seen_clip.add(clip.id)
        if (
            not isinstance(clip.offset_frames, int)
            or isinstance(clip.offset_frames, bool)
            or clip.offset_frames < 0
        ):
            issues.append(ValidationIssue(f"{cp}.offset_frames", "décalage entier >= 0 attendu"))
        if not is_finite_number(clip.gain) or not 0.0 <= clip.gain <= 4.0:
            issues.append(ValidationIssue(f"{cp}.gain", "gain entre 0 et 4 attendu"))
        if not is_finite_number(clip.in_seconds) or clip.in_seconds < 0:
            issues.append(ValidationIssue(f"{cp}.in_seconds", "début >= 0 attendu"))
        if clip.out_seconds is not None and (
            not is_finite_number(clip.out_seconds) or clip.out_seconds <= clip.in_seconds
        ):
            issues.append(ValidationIssue(f"{cp}.out_seconds", "fin > début attendue"))
        for attr in ("fade_in_seconds", "fade_out_seconds"):
            v = getattr(clip, attr)
            if not is_finite_number(v) or v < 0:
                issues.append(ValidationIssue(f"{cp}.{attr}", "durée de fondu >= 0 attendue"))
    seen_sub: set[str] = set()
    for si2, sub in enumerate(scene.subtitles):
        sp = f"{prefix}.subtitles[{si2}]"
        if not is_valid_id(sub.id) or sub.id in seen_sub:
            issues.append(ValidationIssue(f"{sp}.id", "identifiant de sous-titre invalide ou dupliqué"))
        seen_sub.add(sub.id)
        if sub.start_frame < 0 or sub.end_frame <= sub.start_frame:
            issues.append(ValidationIssue(f"{sp}", "plage de sous-titre invalide (fin > début >= 0)"))
    for ti, track in enumerate(scene.tracks):
        tp = f"{prefix}.tracks[{ti}]"
        if track.target_id not in ids:
            issues.append(ValidationIssue(f"{tp}.target_id", f"cible inconnue : {track.target_id}"))
            continue
        node = scene.nodes[ids[track.target_id]]
        if node.kind not in KINDS:
            continue
        if not is_animatable(node, track.property):
            issues.append(ValidationIssue(f"{tp}.property", f"propriété non animable : {track.property}"))
            continue
        for ki, kf in enumerate(track.keyframes):
            kp = f"{tp}.keyframes[{ki}]"
            if not isinstance(kf.frame, int) or isinstance(kf.frame, bool) or kf.frame < 0:
                issues.append(ValidationIssue(f"{kp}.frame", "frame entière >= 0 attendue"))
            if kf.easing not in EASINGS:
                issues.append(ValidationIssue(f"{kp}.easing", f"interpolation inconnue : {kf.easing}"))
            err = check_property_value(node, track.property, kf.value)
            if err:
                issues.append(ValidationIssue(f"{kp}.value", err))
    return issues


def find_parent_cycles(scene: Scene) -> list[list[str]]:
    parent = {n.id: n.parent_id for n in scene.nodes}
    cycles: list[list[str]] = []
    reported: set[str] = set()
    for start in parent:
        seen: list[str] = []
        cur: str | None = start
        while cur is not None and cur in parent and cur not in seen:
            seen.append(cur)
            cur = parent[cur]
        if cur is not None and cur in seen:
            cycle = seen[seen.index(cur) :] + [cur]
            key = min(cycle)
            if key not in reported:
                reported.add(key)
                cycles.append(cycle)
    return cycles


def assert_valid(project: Project) -> None:
    issues = validate_project(project)
    if issues:
        raise ProjectValidationError(issues)


def is_finite_number(v: object) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)

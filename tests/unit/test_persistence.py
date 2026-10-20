"""MOD-02 … MOD-09, MOD-11, SEC-01, SEC-02 — sérialisation, sauvegarde atomique, autosave, chemins."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from antares_studio.domain.commands import (
    AddNode,
    MoveKeyframe,
    RemoveKeyframe,
    RemoveNode,
    SetKeyframe,
    SetProperty,
    UndoStack,
)
from antares_studio.domain.model import Keyframe, Track
from antares_studio.domain.validation import ProjectValidationError
from antares_studio.persistence import store as store_mod
from antares_studio.persistence.paths import UnsafePathError, normalize_relative, resolve_under
from antares_studio.persistence.schema import ProjectFormatError, project_from_dict, project_to_dict
from antares_studio.persistence.store import ProjectStore
from antares_studio.timeline.evaluator import evaluate
from antares_studio.timeline.presets import apply_preset
from tests.unit.helpers import earth_moon_project, make_node


def test_mod02_roundtrip_is_canonical() -> None:
    project, scene, earth, moon = earth_moon_project()
    scene.tracks += apply_preset("orbit", moon, {"center_x": 960, "center_y": 540, "radius": 300})
    scene.tracks += apply_preset("appear", earth)
    d = project_to_dict(project)
    again = project_from_dict(json.loads(json.dumps(d)))
    assert project_to_dict(again) == d
    assert again == project


def test_mod03_atomic_save_keeps_previous_file_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, scene, earth, moon = earth_moon_project()
    store = ProjectStore()
    paths = store.create(tmp_path / "Film", project)
    original = paths.project_file.read_text(encoding="utf-8")
    project.title = "Modifié"

    def boom(src: str, dst: str) -> None:
        raise OSError("interruption simulée avant remplacement")

    monkeypatch.setattr(store_mod.os, "replace", boom)
    with pytest.raises(OSError):
        store.save_atomic(project, paths.project_file)
    assert paths.project_file.read_text(encoding="utf-8") == original
    assert not list(paths.root.glob(".project-*.tmp"))  # temporaire nettoyé


def test_create_then_load_preserves_everything(tmp_path: Path) -> None:
    project, scene, earth, moon = earth_moon_project()
    scene.tracks += apply_preset(
        "orbit", moon, {"center_x": 960, "center_y": 540, "radius": 300, "duration_frames": 300}
    )
    store = ProjectStore()
    paths = store.create(tmp_path / "Lune", project)
    assert paths.root.name == "Lune.antares"
    for sub in ("assets", "audio", "licenses", "autosaves", "cache", "renders"):
        assert (paths.root / sub).is_dir()
    loaded = store.load(paths.root)
    assert loaded == project
    # TIM-12 : mêmes états aux frames clés après rechargement
    for f in (0, 75, 150, 299):
        assert evaluate(loaded, scene.id, f) == evaluate(project, scene.id, f)
    assert store.load(paths.project_file) == project


def test_mod04_corrupt_project_reports_error_without_touching_file(tmp_path: Path) -> None:
    project, *_ = earth_moon_project()
    store = ProjectStore()
    paths = store.create(tmp_path / "C", project)
    paths.project_file.write_text('{"schema_version": 1, "project_id": 3', encoding="utf-8")
    before = paths.project_file.read_bytes()
    with pytest.raises(ProjectFormatError) as exc:
        store.load(paths.root)
    assert "JSON invalide" in str(exc.value)
    assert paths.project_file.read_bytes() == before


def test_mod10_wrong_types_reported_with_json_path() -> None:
    project, scene, earth, _ = earth_moon_project()
    d = project_to_dict(project)
    d["scenes"][0]["nodes"][0]["position"] = [1, "deux"]
    with pytest.raises(ProjectFormatError) as exc:
        project_from_dict(d)
    assert exc.value.path == "$.scenes[0].nodes[0].position[1]"
    d = project_to_dict(project)
    d["schema_version"] = 99
    with pytest.raises(ProjectFormatError, match="version 99"):
        project_from_dict(d)
    d = project_to_dict(project)
    d["scenes"][0]["tracks"] = [
        {"target_id": earth.id, "property": "opacity", "keyframes": [{"frame": 0, "value": float("inf")}]}
    ]
    with pytest.raises(ProjectFormatError, match="nombre fini"):
        project_from_dict(d)


def test_sec01_no_code_execution_in_project_values(tmp_path: Path) -> None:
    """Un contenu « exécutable » est traité comme simple texte."""
    project, scene, earth, _ = earth_moon_project()
    txt = make_node("text", "t")
    txt.params["text"] = "__import__('os').system('echo pwned')"
    scene.nodes.append(txt)
    store = ProjectStore()
    paths = store.create(tmp_path / "S", project)
    loaded = store.load(paths.root)
    assert loaded.scenes[0].nodes[-1].params["text"] == txt.params["text"]


def test_sec02_asset_paths_rejected_when_leaving_root(tmp_path: Path) -> None:
    root = tmp_path / "P.antares"
    (root / "assets").mkdir(parents=True)
    assert normalize_relative("assets\\img\\a.png") == "assets/img/a.png"
    for bad in ("/etc/passwd", "../x.png", "assets/../../x", "C:\\Windows\\x", "", "assets/\x00"):
        with pytest.raises(UnsafePathError):
            resolve_under(root, bad)
    ok = resolve_under(root, "assets/./terre.png")
    assert ok == (root / "assets" / "terre.png").resolve()
    if os.name != "nt":
        outside = tmp_path / "secret.txt"
        outside.write_text("x")
        (root / "assets" / "lien").symlink_to(outside)
        with pytest.raises(UnsafePathError):
            resolve_under(root, "assets/lien")


def test_mod06_project_folder_is_portable(tmp_path: Path) -> None:
    project, *_ = earth_moon_project()
    project.assets.append(
        __import__("antares_studio.domain.model", fromlist=["Asset"]).Asset(
            id="asset-0123456789ab", path="assets/terre.png", kind="image"
        )
    )
    store = ProjectStore()
    paths = store.create(tmp_path / "A", project)
    raw = paths.project_file.read_text(encoding="utf-8")
    assert str(tmp_path) not in raw
    moved = tmp_path / "ailleurs" / "A.antares"
    moved.parent.mkdir()
    paths.root.rename(moved)
    assert store.load(moved) == project


def test_mod09_autosaves_in_same_clock_tick_never_overwrite(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Régression CI Windows : deux autosaves dans la même milliseconde partageaient le même nom."""
    project, *_ = earth_moon_project()
    store = ProjectStore()
    paths = store.create(tmp_path / "S", project)
    fixed = store_mod.datetime(2026, 10, 21, 12, 0, 0, 123456, tzinfo=store_mod.UTC)

    class FrozenDatetime(store_mod.datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def,override]
            return fixed

    monkeypatch.setattr(store_mod, "datetime", FrozenDatetime)
    project.title = "v1"
    a1 = store.autosave(project, paths.root)
    project.title = "v2"
    a2 = store.autosave(project, paths.root)
    assert a1 != a2 and a1.is_file() and a2.is_file()
    assert store.list_autosaves(paths.root) == [a2, a1]
    found = store.latest_valid_autosave(paths.root)
    assert found is not None and found[1].title == "v2"


def test_mod09_autosave_and_recovery(tmp_path: Path) -> None:
    project, *_ = earth_moon_project()
    store = ProjectStore()
    paths = store.create(tmp_path / "R", project)
    project.title = "v2"
    a1 = store.autosave(project, paths.root)
    project.title = "v3"
    a2 = store.autosave(project, paths.root)
    assert store.list_autosaves(paths.root)[0] == a2
    a2.write_text("corrompu", encoding="utf-8")
    found = store.latest_valid_autosave(paths.root)
    assert found is not None and found[0] == a1 and found[1].title == "v2"
    assert store.load(paths.root).title == "Phases de la Lune"  # fichier principal intact
    for i in range(15):
        project.title = f"v{i}"
        store.autosave(project, paths.root, keep=5)
    assert len(store.list_autosaves(paths.root)) == 5


def test_mod11_unicode_and_spaces_in_paths(tmp_path: Path) -> None:
    project, *_ = earth_moon_project()
    project.title = "Éclipse — été 2026"
    store = ProjectStore()
    paths = store.create(tmp_path / "Dossier avec espaces" / "Éclipse été", project)
    assert paths.root.name == "Éclipse été.antares"
    assert store.load(paths.root).title == project.title


def test_invalid_project_is_not_written(tmp_path: Path) -> None:
    project, scene, earth, _ = earth_moon_project()
    earth.params["radius"] = -1
    with pytest.raises(ProjectValidationError):
        ProjectStore().create(tmp_path / "X", project)


def test_mod08_undo_redo_restores_exact_state() -> None:
    project, scene, earth, moon = earth_moon_project()
    stack = UndoStack(project)
    snapshot0 = project_to_dict(project)
    stack.push(SetProperty(scene.id, earth.id, "position.x", 100.0))
    stack.push(SetKeyframe(scene.id, moon.id, "opacity", 0, 0.0))
    stack.push(SetKeyframe(scene.id, moon.id, "opacity", 30, 1.0, "ease_out"))
    stack.push(MoveKeyframe(scene.id, moon.id, "opacity", 30, 45))
    snapshot_mid = project_to_dict(project)
    stack.push(RemoveKeyframe(scene.id, moon.id, "opacity", 0))
    new = make_node("arrow", "Vitesse", parent_id=moon.id)
    stack.push(AddNode(scene.id, new))
    stack.push(RemoveNode(scene.id, moon.id))
    assert all(n.id not in (moon.id, new.id) for n in scene.nodes)
    assert not scene.tracks_for(moon.id)
    assert stack.undo() and stack.undo() and stack.undo()
    assert project_to_dict(project) == snapshot_mid
    while stack.undo():
        pass
    assert project_to_dict(project) == snapshot0
    while stack.redo():
        pass
    assert all(n.id not in (moon.id, new.id) for n in scene.nodes)


def test_undo_stack_merge_and_clean_state() -> None:
    project, scene, earth, _ = earth_moon_project()
    stack = UndoStack(project)
    stack.push(SetProperty(scene.id, earth.id, "position.x", 10.0))
    stack.push(SetProperty(scene.id, earth.id, "position.x", 20.0), merge=True)
    stack.push(SetProperty(scene.id, earth.id, "position.x", 30.0), merge=True)
    assert earth.position[0] == 30.0
    assert not stack.is_clean  # une commande au-dessus de l'état initial (propre)
    stack.mark_clean()
    assert stack.is_clean
    assert stack.undo()
    assert earth.position[0] == 960.0
    assert not stack.is_clean
    stack.redo()
    assert stack.is_clean


def test_keyframe_commands_restore_track_removal() -> None:
    project, scene, earth, _ = earth_moon_project()
    stack = UndoStack(project)
    stack.push(SetKeyframe(scene.id, earth.id, "opacity", 10, 0.5))
    assert scene.track_for(earth.id, "opacity") is not None
    stack.undo()
    assert scene.track_for(earth.id, "opacity") is None
    scene.tracks.append(Track(earth.id, "opacity", [Keyframe(5, 1.0)]))
    stack.push(SetKeyframe(scene.id, earth.id, "opacity", 5, 0.1))
    stack.undo()
    assert scene.track_for(earth.id, "opacity").keyframes[0].value == 1.0  # type: ignore[union-attr]

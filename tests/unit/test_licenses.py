"""AST-03, AST-06, SCI-07, SCI-08 — provenance des ressources, crédits, avertissement d'échelle, sources."""

from __future__ import annotations

import pytest

from antares_studio.domain.commands import SetAssetLicense, SetProjectMetadata, UndoStack
from antares_studio.domain.model import Asset, AssetLicense, Canvas, Scene
from antares_studio.persistence.schema import project_from_dict, project_to_dict
from antares_studio.rendering.plan import build_render_plan
from antares_studio.rendering.qt_painter import callout_rect, render_state_to_image
from antares_studio.resources.licenses import (
    STATUS_COMPLETE,
    STATUS_MISSING,
    STATUS_NOT_REDISTRIBUTABLE,
    credits_lines,
    inventory,
    license_status,
    provenance_warnings,
)
from antares_studio.resources.templates import TEMPLATES, create_project, scale_warning_node
from antares_studio.timeline.evaluator import evaluate
from tests.unit.helpers import earth_moon_project, make_node


def _project_with_asset(lic: AssetLicense, used: bool = True):  # type: ignore[no-untyped-def]
    project, scene, _earth, _moon = earth_moon_project(60)
    asset = Asset(id="asset-000000000001", path="assets/fond.png", kind="image", sha256="", license=lic)
    project.assets.append(asset)
    if used:
        img = make_node("image", "Fond")
        img.params["asset_id"] = asset.id
        scene.nodes.append(img)
    return project, scene, asset


def test_ast03_asset_without_provenance_is_flagged_and_warned_in_plan() -> None:
    project, scene, asset = _project_with_asset(AssetLicense())
    assert license_status(asset.license) == STATUS_MISSING
    rows = inventory(project)
    assert [r.status for r in rows] == [STATUS_MISSING] and rows[0].used_by == ("Orbite › Fond",)
    warnings = provenance_warnings(project)
    assert len(warnings) == 1 and "sans provenance" in warnings[0] and "fond.png" in warnings[0]
    plan = build_render_plan(project, scene.id, "draft_720p", "/tmp/x.mp4")
    assert any("sans provenance" in w for w in plan.warnings)
    # ressource importée mais inutilisée : pas d'avertissement d'export
    project2, _s, _a = _project_with_asset(AssetLicense(), used=False)
    assert provenance_warnings(project2) == []


def test_ast03_non_redistributable_asset_warns() -> None:
    lic = AssetLicense(author="X", license="proprietary", redistribution_allowed=False)
    project, _scene, asset = _project_with_asset(lic)
    assert license_status(asset.license) == STATUS_NOT_REDISTRIBUTABLE
    assert any("non redistribuable" in w for w in provenance_warnings(project))


def test_ast06_credits_report_is_faithful() -> None:
    lic = AssetLicense(
        author="NASA/JPL-Caltech",
        source_url="https://images.nasa.gov/details/PIA00123",
        license="CC-BY-4.0",
        attribution_required=True,
        redistribution_allowed=True,
        verified_on="2026-10-21",
    )
    project, _scene, asset = _project_with_asset(lic)
    assert license_status(asset.license) == STATUS_COMPLETE
    project.scientific_metadata["sources"] = [
        {"label": "IAU 2012 — unité astronomique", "url": "https://www.iau.org/"}
    ]
    project.scientific_metadata["to_scale"] = False
    lines = credits_lines(project)
    text = "\n".join(lines)
    assert "IAU 2012 — unité astronomique — https://www.iau.org/" in text
    assert "fond.png — NASA/JPL-Caltech — CC BY 4.0 — https://images.nasa.gov/details/PIA00123" in text
    assert "non à l'échelle" in text and "ANTARES Studio" in text and "FFmpeg" in text
    # une ressource sans attribution requise ni auteur n'apparaît pas dans les crédits
    project.assets[0].license = AssetLicense(license="CC0-1.0", redistribution_allowed=True)
    assert "fond.png" not in "\n".join(credits_lines(project))


def test_license_and_metadata_commands_are_undoable_and_persisted() -> None:
    project, _scene, asset = _project_with_asset(AssetLicense())
    stack = UndoStack(project)
    new = AssetLicense(
        author="Moi", license="own-work", redistribution_allowed=True, verified_on="2026-10-21"
    )
    stack.push(SetAssetLicense(asset.id, new))
    stack.push(SetProjectMetadata("sources", [{"label": "Cours", "url": ""}]))
    assert (
        project.assets[0].license.author == "Moi"
        and project.scientific_metadata["sources"][0]["label"] == "Cours"
    )
    roundtrip = project_from_dict(project_to_dict(project))
    assert roundtrip.assets[0].license == new and roundtrip.scientific_metadata["sources"] == [
        {"label": "Cours", "url": ""}
    ]
    stack.undo()
    stack.undo()
    assert project.assets[0].license == AssetLicense() and project.scientific_metadata["sources"] == []
    with pytest.raises(KeyError):
        stack.push(SetAssetLicense("asset-inconnu", new))


@pytest.mark.parametrize("template_id", ["moon_phases", "scale_comparison", "orbit_vectors"])
def test_sci07_templates_carry_a_visible_scale_warning(qapp, template_id: str) -> None:  # type: ignore[no-untyped-def]
    project = create_project("T", Canvas(1920, 1080, 30, 1), template_id, 10)
    assert project.scientific_metadata["to_scale"] is False
    scene = project.scenes[0]
    warnings = [n for n in scene.nodes if n.kind == "callout" and "non à l'échelle" in str(n.params["text"])]
    assert len(warnings) == 1
    node = warnings[0]
    # au-dessus de la bande réservée aux sous-titres (20 % inférieurs)
    assert node.position[1] + callout_rect(node.params).bottom() < 1080 * 0.8
    for frame in (0, scene.duration_frames // 2, scene.duration_frames - 1):
        state = evaluate(project, scene.id, frame)
        st = next(s for s in state.nodes if s.id == node.id)
        assert st.visible and st.opacity == 1.0
        img = render_state_to_image(state, project.canvas, 1920, 1080)
        cx, cy = int(node.position[0]), int(node.position[1])
        box = callout_rect(node.params)
        # bordure orange (anticrénelée) : le pixel le plus rouge autour du bord supérieur
        top = int(cy + box.top())
        border = max((img.pixelColor(cx, y) for y in range(top - 2, top + 3)), key=lambda c: c.red())
        assert border.red() > 150 and border.blue() < 120, border.name()
        whites = sum(
            1
            for x in range(int(cx + box.left()) + 20, int(cx + box.right()) - 20, 4)
            for y in range(int(cy + box.top()) + 8, int(cy + box.bottom()) - 8, 4)
            if img.pixelColor(x, y).lightness() > 220
        )
        assert whites > 30


def test_sci07_scale_warning_node_roundtrip_and_credits_template(qapp) -> None:  # type: ignore[no-untyped-def]
    project = create_project("Crédits", Canvas(1080, 1920, 30, 1), "moon_phases", 10)
    node = scale_warning_node(project.canvas, "Non à l'échelle")
    project.scenes[0].nodes.append(node)
    rt = project_from_dict(project_to_dict(project))
    assert (
        rt.scenes[0].nodes[-1].kind == "callout"
        and rt.scenes[0].nodes[-1].params["text"] == "Non à l'échelle"
    )
    assert "credits" in TEMPLATES and "intro" in TEMPLATES
    project.scientific_metadata["sources"] = [
        {"label": "NASA — Moon", "url": "https://science.nasa.gov/moon/"}
    ]
    cred = create_project("Crédits", Canvas(1920, 1080, 30, 1), "credits", 8)
    cred.scientific_metadata = project.scientific_metadata
    scene = cred.scenes[0]
    scene.nodes.clear()
    scene.tracks.clear()
    TEMPLATES["credits"][1](cred, scene)
    body = next(n for n in scene.nodes if n.name == "Crédits")
    assert "NASA — Moon — https://science.nasa.gov/moon/" in str(body.params["text"])
    assert "ANTARES Studio" in str(body.params["text"])
    assert evaluate(cred, scene.id, scene.duration_frames - 1).nodes


def test_sci08_sources_are_in_metadata_and_manifest_credits() -> None:
    project = create_project("P", Canvas(1920, 1080, 30, 1), "scale_comparison", 5)
    sources = project.scientific_metadata["sources"]
    assert len(sources) == 2 and all(s["url"].startswith("https://") for s in sources)
    assert any("IAU 2012" in line for line in credits_lines(project))


def test_sci08_templates_accumulate_sources_across_scenes() -> None:
    """Régression : chaque modèle ajouté écrasait la liste des sources (le dernier gagnait)."""
    project = create_project("Démo", Canvas(), "moon_phases", 2)
    for template_id in ("scale_comparison", "kepler_orbit", "moon_phases"):
        scene = Scene.create(template_id, 60)
        TEMPLATES[template_id][1](project, scene)
        project.scenes.append(scene)
    labels = [src["label"] for src in project.scientific_metadata["sources"]]
    assert len(labels) == len(set(labels)) == 5  # Lune, IAU au, CODATA c, JPL, IAU GM — sans doublon
    assert any("Moon" in label for label in labels) and any("IAU 2015" in label for label in labels)

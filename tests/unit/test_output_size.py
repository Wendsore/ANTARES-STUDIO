"""Dimensions de sortie : le format du projet est conservé (plus d'image étirée en 9:16 ou 1:1)."""

from __future__ import annotations

import pytest

from antares_studio.domain.model import Canvas
from antares_studio.rendering.plan import PROFILES, build_render_plan, output_size
from antares_studio.resources.templates import create_project


@pytest.mark.parametrize(
    ("canvas", "profile", "expected"),
    [
        (Canvas(1920, 1080), "final_1080p", (1920, 1080)),
        (Canvas(1920, 1080), "draft_720p", (1280, 720)),
        (Canvas(1080, 1920), "final_1080p", (1080, 1920)),
        (Canvas(1080, 1920), "draft_720p", (720, 1280)),
        (Canvas(1080, 1080), "final_1080p", (1080, 1080)),
        (Canvas(1080, 1080), "draft_720p", (720, 720)),
        (Canvas(1000, 1001), "draft_720p", (720, 722)),  # arrondi puis parité (H.264 4:2:0)
    ],
)
def test_output_size_keeps_project_aspect(canvas: Canvas, profile: str, expected: tuple[int, int]) -> None:
    w, h = output_size(PROFILES[profile], canvas)
    assert (w, h) == expected and w % 2 == 0 and h % 2 == 0


def test_render_plan_of_vertical_project_is_vertical_and_not_stretched() -> None:
    project = create_project("Vertical", Canvas(1080, 1920), "intro", 1)
    plan = build_render_plan(project, project.scenes[0].id, "final_1080p", "/tmp/x.mp4")
    assert (plan.width, plan.height) == (1080, 1920)
    assert not any("étirée" in w for w in plan.warnings)

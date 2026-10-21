"""Ligne de commande : --version, --selftest (contrôle d'installation), --export sans interface."""

from __future__ import annotations

from pathlib import Path

import pytest

from antares_studio import __version__
from antares_studio.app.cli import run_cli, run_selftest
from antares_studio.app.main import main
from antares_studio.domain.model import Canvas
from antares_studio.persistence.store import ProjectStore
from antares_studio.rendering import ffmpeg as ff
from antares_studio.resources.templates import create_project

needs_ffmpeg = pytest.mark.skipif(ff.find_ffmpeg() is None, reason="ffmpeg absent")


def test_version_flag_prints_and_exits(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["antares-studio", "--version"]) == 0
    assert capsys.readouterr().out.strip() == f"ANTARES Studio {__version__}"


def test_no_flags_means_gui() -> None:
    assert run_cli([]) is None
    assert run_cli(["projet.antares"]) is None


@pytest.mark.render
def test_selftest_reports_and_succeeds(qapp) -> None:  # type: ignore[no-untyped-def]
    log: list[str] = []
    assert run_selftest(log) == 0
    text = "\n".join(log)
    assert "réouverture OK" in text and "Rendu : image 1280×720 OK" in text and "AUTOTEST : RÉUSSI" in text
    if ff.find_ffmpeg() is not None:
        assert "10 images" in text


@needs_ffmpeg
@pytest.mark.render
def test_export_cli_renders_project(qapp, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    project = create_project("CLI", Canvas(1280, 720, 30, 1), "scale_comparison", 1)
    root = ProjectStore().create(tmp_path / "CLI", project).root
    out = tmp_path / "cli.mp4"
    code = main(["antares-studio", "--export", str(root), str(out), "--profile", "draft_720p"])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert out.is_file() and "export terminé" in captured.out and "30 images" in captured.out
    assert (tmp_path / "cli.credits.txt").is_file()
    assert main(["antares-studio", "--export", str(root), str(out), "--profile", "inexistant"]) == 2

"""Profils de plateforme (cadre imposé), GIF/WebM, lisibilité des sous-titres et contraste du style."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from antares_studio.audio.subtitles import MAX_CPS, check_subtitle_style, check_subtitles, reading_speed
from antares_studio.domain.colors import contrast_ratio, over
from antares_studio.domain.commands import SetProjectSetting
from antares_studio.domain.model import Canvas, Subtitle
from antares_studio.persistence.schema import project_to_dict
from antares_studio.rendering.exporter import DUCKING_FILTER, _build_ffmpeg_command, _concat_args
from antares_studio.rendering.plan import (
    PROFILES,
    AudioClipPlan,
    build_render_plan,
    content_rect,
    output_size,
)
from tests.unit.helpers import earth_moon_project


@pytest.mark.parametrize(
    ("profile", "canvas", "rect"),
    [
        ("youtube_1080p", Canvas(1920, 1080), None),
        ("youtube_1080p", Canvas(1280, 720), None),  # même format : rempli
        ("vertical_1080x1920", Canvas(1920, 1080), (0, 656, 1080, 608)),
        ("square_1080", Canvas(1920, 1080), (0, 236, 1080, 608)),
        ("slides_4_3", Canvas(1080, 1920), (416, 0, 608, 1080)),
        ("draft_720p", Canvas(1080, 1920), None),  # profil d'usage : suit le format du projet
    ],
)
def test_platform_frames_letterbox_without_distortion(profile: str, canvas: Canvas, rect) -> None:  # type: ignore[no-untyped-def]
    prof = PROFILES[profile]
    assert content_rect(prof, canvas) == rect
    if prof.fixed_frame:
        assert output_size(prof, canvas) == (prof.width, prof.height)
    if rect is not None:
        x, y, w, h = rect
        assert abs(w / h - canvas.width / canvas.height) < 0.01  # pas de déformation
        assert x * 2 + w == prof.width and y * 2 + h == prof.height  # centré


def test_gif_plan_reduces_rate_drops_audio_and_keeps_duration() -> None:
    project, scene, *_ = earth_moon_project(duration_frames=31)
    clip = AudioClipPlan("/x.wav", 0)
    plan = build_render_plan(project, scene.id, "gif_480", "a.gif", audio=(clip,), silent_audio=True)
    assert plan.frame_step == 2 and plan.total_frames == 16 and plan.output_fps == Fraction(15)
    assert plan.audio == () and not plan.silent_audio and not plan.profile.has_audio
    assert abs(plan.duration_seconds - 16 / 15) < 1e-9
    cmd = _build_ffmpeg_command(Path("ffmpeg"), plan, Path("o"))
    assert "palettegen=stats_mode=diff" in " ".join(cmd) and cmd[cmd.index("-r") + 1] == "15/1"
    assert _concat_args(plan.profile)[0] == "-filter_complex"
    assert _concat_args(PROFILES["webm_1080p"]) == ["-c", "copy"]
    assert PROFILES["webm_1080p"].suffix == ".webm" and PROFILES["gif_480"].suffix == ".gif"
    project.canvas = Canvas(1920, 1080, 12, 1)
    assert build_render_plan(project, scene.id, "gif_480", "a.gif").frame_step == 1  # déjà ≤ 15 i/s


def test_ducking_filter_only_when_voice_and_music_are_present() -> None:
    from pathlib import Path

    project, scene, *_ = earth_moon_project(duration_frames=30)
    voice = AudioClipPlan("/v.wav", 0)
    music = AudioClipPlan("/m.wav", 0, role="music")
    effect = AudioClipPlan("/e.wav", 0, role="effect")

    def cmd(*clips: AudioClipPlan) -> str:
        plan = build_render_plan(project, scene.id, "draft_720p", "o.mp4", audio=clips)
        return " ".join(_build_ffmpeg_command(Path("ffmpeg"), plan, Path("o")))

    assert DUCKING_FILTER in cmd(voice, music, effect)
    assert "amix=inputs=3" in cmd(voice, music, effect)  # voix + musique atténuée + effet
    assert "sidechaincompress" not in cmd(voice, effect) and "sidechaincompress" not in cmd(music)
    SetProjectSetting("ducking", False).do(project)
    assert "sidechaincompress" not in cmd(voice, music)


def test_project_setting_command_is_undoable_and_default_is_not_saved() -> None:
    project, *_ = earth_moon_project()
    assert "ducking" not in project_to_dict(project)["settings"]
    cmd = SetProjectSetting("ducking", False)
    cmd.do(project)
    assert project_to_dict(project)["settings"]["ducking"] is False
    cmd.undo(project)
    assert "ducking" not in project.settings
    project.settings["ducking"] = False
    back = SetProjectSetting("ducking", None)  # retour au défaut : clé retirée
    back.do(project)
    assert "ducking" not in project.settings
    back.undo(project)
    assert project.settings["ducking"] is False


def test_reading_speed_and_long_display_are_flagged() -> None:
    fps = Fraction(30)
    fast = Subtitle.create(0, 30, "Ce texte est bien trop long pour une seconde")  # 44 car/s
    calm = Subtitle.create(30, 120, "Un rythme confortable.")
    long = Subtitle.create(120, 120 + 8 * 30, "Reste affiché huit secondes.")
    assert reading_speed(fast, fps) > MAX_CPS > reading_speed(calm, fps)
    issues = check_subtitles([fast, calm, long], 600, fps)
    by_index = {(i.index, i.message.split(" ")[0]) for i in issues}
    assert any(i.index == 0 and "caractères" in i.message for i in issues)
    assert any(i.index == 2 and "7 s" in i.message for i in issues)
    assert not any(i.index == 1 for i in issues), by_index


def test_subtitle_style_contrast_checks_the_worst_background() -> None:
    assert check_subtitle_style({"color": "#FFFFFF", "background": "#000000A0"}) == []
    # fond très léger : sur une image blanche, le texte blanc disparaît
    assert check_subtitle_style({"color": "#FFFFFF", "background": "#00000060"})
    # fond transparent : il faut un contour contrasté
    assert check_subtitle_style({"color": "#FFFFFF", "background": "#00000000", "outline_width": 0})
    assert (
        check_subtitle_style(
            {"color": "#FFFFFF", "background": "#00000000", "outline": "#000000", "outline_width": 2}
        )
        == []
    )
    assert contrast_ratio("#FFFFFF", "#000000") == pytest.approx(21.0)
    assert over("#00000080", "#FFFFFF").upper() in ("#7F7F7F", "#808080")

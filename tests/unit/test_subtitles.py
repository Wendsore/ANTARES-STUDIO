"""AUD-06, AUD-07, AUD-08 — sous-titres SRT/VTT, chevauchements, zone sûre, incrustation."""

from __future__ import annotations

from fractions import Fraction

import pytest

from antares_studio.audio.subtitles import (
    SubtitleFormatError,
    check_subtitles,
    format_srt,
    format_vtt,
    parse_subtitles,
)
from antares_studio.domain.model import Subtitle
from antares_studio.persistence.schema import project_from_dict, project_to_dict
from antares_studio.timeline.evaluator import evaluate
from tests.unit.helpers import earth_moon_project

FPS = Fraction(30, 1)

SRT = """1
00:00:01,000 --> 00:00:03,500
Pourquoi la Lune change-t-elle de forme ?

2
00:00:04,000 --> 00:00:06,000
Éclairée par le Soleil — à moitié.
"""

VTT = """WEBVTT

NOTE commentaire ignoré

00:01.000 --> 00:03.500 align:center
Pourquoi la Lune <b>change</b>-t-elle de forme ?

intro
00:00:04.000 --> 00:00:06.000
Éclairée par le Soleil — à moitié.
"""


def test_aud06_parse_srt_and_vtt_utf8_preserved() -> None:
    for text in (SRT, VTT, "﻿" + SRT):
        subs = parse_subtitles(text, FPS)
        assert [s.start_frame for s in subs] == [30, 120]
        assert [s.end_frame for s in subs] == [105, 180]
        assert subs[0].text == "Pourquoi la Lune change-t-elle de forme ?"
        assert subs[1].text == "Éclairée par le Soleil — à moitié."


def test_aud06_format_roundtrip() -> None:
    subs = parse_subtitles(SRT, FPS)
    key = [(s.start_frame, s.end_frame, s.text) for s in subs]
    assert [(s.start_frame, s.end_frame, s.text) for s in parse_subtitles(format_srt(subs, FPS), FPS)] == key
    assert [(s.start_frame, s.end_frame, s.text) for s in parse_subtitles(format_vtt(subs, FPS), FPS)] == key
    assert format_srt(subs, FPS).startswith("1\n00:00:01,000 --> 00:00:03,500\n")
    assert format_vtt(subs, FPS).startswith("WEBVTT\n\n00:00:01.000 --> 00:00:03.500\n")


def test_invalid_subtitle_files_rejected() -> None:
    with pytest.raises(SubtitleFormatError):
        parse_subtitles("1\n00:00:05,000 --> 00:00:02,000\nfin avant début\n", FPS)
    with pytest.raises(SubtitleFormatError):
        parse_subtitles("1\nbonjour\n", FPS)
    with pytest.raises(SubtitleFormatError):
        parse_subtitles("00:00:01,000 -> 00:00:02,000\nflèche invalide\n", FPS)


def test_aud07_overlap_and_quality_diagnostics() -> None:
    subs = [
        Subtitle.create(0, 60, "Un"),
        Subtitle.create(50, 100, "Deux"),
        Subtitle.create(100, 105, "Trop court"),
        Subtitle.create(200, 400, "x" * 90),
        Subtitle.create(250, 300, "   "),
    ]
    issues = check_subtitles(subs, duration_frames=300, fps=FPS)
    msgs = {(i.index, i.message) for i in issues}
    assert (0, "chevauche le sous-titre 2") in msgs
    assert any(i.index == 2 and "0,5 s" in i.message for i in issues)
    assert any(i.index == 3 and "dépasse" in i.message for i in issues)
    assert any(i.index == 3 and "téléphone" in i.message for i in issues)
    assert (4, "texte vide") in msgs
    assert check_subtitles([Subtitle.create(0, 30, "ok")], 300, FPS) == []


def test_subtitle_in_scene_state_and_persistence() -> None:
    project, scene, _, _ = earth_moon_project()
    scene.subtitles = parse_subtitles(SRT, FPS)
    assert evaluate(project, scene.id, 45).subtitle == "Pourquoi la Lune change-t-elle de forme ?"
    assert evaluate(project, scene.id, 110).subtitle is None
    assert evaluate(project, scene.id, 150).subtitle == "Éclairée par le Soleil — à moitié."
    again = project_from_dict(project_to_dict(project))
    assert again.scenes[0].subtitles == scene.subtitles
    # ancien fichier sans champ subtitles/audio : toujours lisible (additif)
    d = project_to_dict(project)
    del d["scenes"][0]["subtitles"]
    del d["scenes"][0]["audio"]
    assert project_from_dict(d).scenes[0].subtitles == []


@pytest.mark.ui
@pytest.mark.parametrize("size", [(1920, 1080), (1080, 1920), (1280, 720)])
def test_aud08_subtitle_rendered_in_safe_zone(qapp, size) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtGui import QImage, QPainter

    from antares_studio.rendering.qt_painter import paint_subtitle

    w, h = size
    img = QImage(w, h, QImage.Format.Format_RGBA8888)
    img.fill(0xFF000000)
    p = QPainter(img)
    rect = paint_subtitle(p, "Schéma : distances et tailles non à l'échelle", w, h, _style())
    p.end()
    # dans la bande inférieure de 20 % et à l'intérieur des marges de 5 %
    assert rect.bottom() <= h * 0.95 + 1 and rect.top() >= h * 0.8 - 1
    assert rect.left() >= w * 0.05 - 1 and rect.right() <= w * 0.95 + 1
    # du texte blanc est présent dans le rectangle (balayage par pas de 3 px ; 2 lignes possibles en 9:16)
    xs = range(int(rect.left()), int(rect.right()), 3)
    ys = range(int(rect.top()), int(rect.bottom()), 3)
    assert any(img.pixelColor(x, y).red() > 200 for y in ys for x in xs)


def _style() -> dict[str, object]:
    from antares_studio.domain.model import DEFAULT_SUBTITLE_STYLE

    return dict(DEFAULT_SUBTITLE_STYLE)

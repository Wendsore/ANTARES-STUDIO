"""Système de design : contrastes WCAG 2.2 des deux thèmes et jetons réaffectés au changement de thème."""

from __future__ import annotations

from dataclasses import fields

import pytest
from PySide6.QtGui import QColor

from antares_studio.app import theme


@pytest.mark.parametrize("palette", theme.THEMES.values(), ids=lambda p: p.name)
def test_every_token_is_a_valid_colour(palette: theme.Palette) -> None:
    names = theme.palette_fields()
    assert len(names) == len(fields(palette)) - 2
    for name in names:
        assert QColor(getattr(palette, name)).isValid(), name


@pytest.mark.parametrize("palette", theme.THEMES.values(), ids=lambda p: p.name)
def test_text_pairs_reach_wcag_aa(palette: theme.Palette) -> None:
    for fg, bg in theme.TEXT_PAIRS:
        ratio = theme.contrast_ratio(getattr(palette, fg), getattr(palette, bg))
        assert ratio >= 4.5, f"{palette.name} : {fg} sur {bg} = {ratio:.2f}:1"


@pytest.mark.parametrize("palette", theme.THEMES.values(), ids=lambda p: p.name)
def test_component_pairs_reach_three_to_one(palette: theme.Palette) -> None:
    for fg, bg in theme.COMPONENT_PAIRS:
        ratio = theme.contrast_ratio(getattr(palette, fg), getattr(palette, bg))
        assert ratio >= 3.0, f"{palette.name} : {fg} sur {bg} = {ratio:.2f}:1"


def test_contrast_ratio_reference_values() -> None:
    assert theme.contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert theme.contrast_ratio("#777777", "#777777") == pytest.approx(1.0)
    assert theme.contrast_ratio("#767676", "#FFFFFF") == pytest.approx(4.54, abs=0.01)  # valeur WebAIM


def test_apply_theme_switches_drawing_tokens(qapp) -> None:  # type: ignore[no-untyped-def]
    try:
        theme.apply_theme(qapp, "clair", 130)
        assert theme.active() is theme.LIGHT and theme.font_scale() == 130
        assert QColor(theme.LIGHT.track) == theme.TRACK_BG
        assert QColor(theme.LIGHT.keyframe) == theme.KEYFRAME
        base = float(qapp.property("antares_base_pt"))
        assert qapp.font().pointSizeF() == pytest.approx(base * 1.3, abs=0.05)
        assert "QPushButton" in qapp.styleSheet()
    finally:
        theme.apply_theme(qapp, "sombre", 100)
    assert QColor(theme.DARK.track) == theme.TRACK_BG and QColor(theme.DARK.keyframe) == theme.KEYFRAME


def test_unknown_theme_and_scale_fall_back_to_defaults(qapp) -> None:  # type: ignore[no-untyped-def]
    try:
        theme.apply_theme(qapp, "inexistant", 7)
        assert theme.active().name == theme.DEFAULT_THEME and theme.font_scale() == 100
    finally:
        theme.apply_theme(qapp, "sombre", 100)

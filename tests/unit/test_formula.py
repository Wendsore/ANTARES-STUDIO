"""Équations : mini-langage analysé sans exécution, rendu local (fraction, racine, indices), bornes."""

from __future__ import annotations

from PySide6.QtGui import QFont

from antares_studio.domain.model import Canvas, Project, Scene
from antares_studio.persistence.schema import project_from_dict, project_to_dict
from antares_studio.rendering.formula_layout import FormulaRenderer, formula_rect
from antares_studio.rendering.qt_painter import render_state_to_image
from antares_studio.science.formula import parse_formula
from antares_studio.timeline.evaluator import evaluate
from tests.unit.helpers import make_node


def test_parser_structures_and_symbols() -> None:
    f = parse_formula(r"F = \frac{G m_{1} m_{2}}{r^{2}}")
    assert f.plain() == "F = (G m_(1) m_(2))/(r^(2))" and f.diagnostics == ()
    assert parse_formula(r"\alpha + \beta \to \infty").plain() == "α + β → ∞"
    assert parse_formula(r"\vec{v} = \sqrt{\frac{G M}{r}}").plain() == "vec(v) = √((G M)/(r))"
    assert parse_formula(r"\text{vitesse} \approx 7,9 \cdot 10^{3}").plain() == "vitesse ≈ 7,9 · 10^(3)"
    assert parse_formula("").plain() == "" and parse_formula(r"\{x\}").plain() == "{x}"
    assert parse_formula(r"a\,b\!c").plain() == "a bc"  # espace fine ; espace négative ignorée


def test_parser_never_raises_and_never_executes() -> None:
    f = parse_formula(r"\input{/etc/passwd} \write18{rm -rf} x = {a + b")
    assert "\\input" in f.plain() and "\\write" in f.plain()
    assert any("inconnue" in d for d in f.diagnostics) and any("non fermée" in d for d in f.diagnostics)
    assert parse_formula("a}b^").diagnostics  # accolade orpheline + exposant sans argument
    assert parse_formula("x^").plain() == "x^()"


def test_layout_fraction_taller_than_inline_and_scripts_smaller(qapp) -> None:  # type: ignore[no-untyped-def]
    r = FormulaRenderer(QFont("DejaVu Sans", 40))
    inline = r.measure(parse_formula("a + b").root)
    frac = r.measure(parse_formula(r"\frac{a}{b}").root)
    sup = r.measure(parse_formula("x^{2}").root)
    plain_x2 = r.measure(parse_formula("x2").root)
    assert frac.height > inline.height * 1.6
    assert sup.width < plain_x2.width and sup.above > inline.above
    sqrt = r.measure(parse_formula(r"\sqrt{x}").root)
    assert sqrt.width > r.measure(parse_formula("x").root).width


def test_formula_node_renders_pixels_and_roundtrips(qapp) -> None:  # type: ignore[no-untyped-def]
    project = Project.create("Eq", Canvas(1280, 720, 30, 1))
    scene = Scene.create("S", duration_frames=10)
    project.scenes.append(scene)
    node = make_node("formula", "Newton", position=[640.0, 360.0])
    node.params["text"] = r"F = \frac{G m_{1} m_{2}}{r^{2}}"
    scene.nodes.append(node)
    assert (
        project_from_dict(project_to_dict(project)).scenes[0].nodes[0].params["text"] == node.params["text"]
    )
    rect = formula_rect(node.params)
    assert rect.width() > 200 and rect.height() > 80
    img = render_state_to_image(evaluate(project, scene.id, 0), project.canvas, 1280, 720)
    whites = sum(
        1
        for x in range(int(640 + rect.left()), int(640 + rect.right()), 3)
        for y in range(int(360 + rect.top()), int(360 + rect.bottom()), 3)
        if img.pixelColor(x, y).lightness() > 200
    )
    assert whites > 100

    # barre de fraction : une ligne horizontale blanche continue (≥ 60 px) juste au-dessus de la ligne de base
    def longest_run(y: int) -> int:
        best = run = 0
        for x in range(int(640 + rect.left()), int(640 + rect.right())):
            run = run + 1 if img.pixelColor(x, y).lightness() > 200 else 0
            best = max(best, run)
        return best

    assert max(longest_run(y) for y in range(360 - 40, 361)) >= 60

"""Projets d'exemple complets : plusieurs scènes, sous-titres, repères, transitions et crédits.

Chaque exemple assemble des modèles intégrés (aucune ressource externe) et montre une vidéo terminée,
prête à exporter. Aucune voix n'est fournie : les sous-titres portent le texte, la narration se fait au
micro (Narration > Enregistrer) ou s'importe. Les sous-titres sont minutés automatiquement pour respecter
les contrôles de lisibilité (vitesse de lecture, durée, longueur).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from antares_studio.domain.model import Canvas, Marker, Project, Scene, SceneTransition, Subtitle
from antares_studio.resources.templates import TEMPLATES

CPS = 12.0  # vitesse de lecture visée (le contrôle avertit au-delà de 17 caractères/s)
MIN_S, MAX_S, GAP_S = 2.0, 6.5, 0.4


@dataclass(frozen=True)
class ExampleScene:
    template: str
    seconds: int
    transition: str = "fade"
    lines: tuple[tuple[str, str], ...] = ()  # (sous-titre, repère éventuel au début de la phrase)


@dataclass(frozen=True)
class Example:
    title: str
    summary: str
    thumbnail: str  # modèle dont la vignette illustre l'exemple
    scenes: tuple[ExampleScene, ...] = field(default_factory=tuple)


EXAMPLES: dict[str, Example] = {
    "phases_lune": Example(
        "Pourquoi la Lune change de forme",
        "Phases de la Lune puis échelle des distances, avec sous-titres et crédits.",
        "moon_phases",
        (
            ExampleScene("intro", 6, "none"),
            ExampleScene(
                "moon_phases",
                24,
                lines=(
                    ("La Lune ne produit pas de lumière : elle renvoie celle du Soleil.", "Lumière"),
                    ("Une moitié de la Lune est toujours éclairée.", ""),
                    ("Selon sa position autour de la Terre, nous voyons plus ou moins de cette moitié.", ""),
                    ("Un cycle complet de phases dure environ 29,5 jours.", "Cycle"),
                    ("Ce schéma n'est pas à l'échelle : la Lune est bien plus loin.", "Échelle"),
                ),
            ),
            ExampleScene(
                "scale_comparison",
                18,
                lines=(
                    ("En astronomie, les distances sont immenses.", ""),
                    ("Une année-lumière est la distance parcourue par la lumière en un an.", "Année-lumière"),
                    ("Elle vaut environ 9 461 milliards de kilomètres.", ""),
                ),
            ),
            ExampleScene("credits", 8, "fade_black"),
        ),
    ),
    "lois_kepler": Example(
        "Les lois de Kepler",
        "Une orbite elliptique commentée par les trois lois, avec sous-titres et crédits.",
        "kepler_orbit",
        (
            ExampleScene("intro", 6, "none"),
            ExampleScene(
                "kepler_orbit",
                26,
                lines=(
                    ("Une planète décrit une ellipse dont l'étoile occupe un foyer.", "1re loi"),
                    ("Elle va plus vite près de l'étoile, plus lentement au loin.", "2e loi"),
                    ("Le rayon étoile-planète balaie des aires égales en des durées égales.", ""),
                    ("Le carré de la période est proportionnel au cube du demi-grand axe.", "3e loi"),
                ),
            ),
            ExampleScene("credits", 8, "fade_black"),
        ),
    ),
    "danse_gravitationnelle": Example(
        "Danse gravitationnelle",
        "Étoile double puis trois corps en huit, calculés par simulation numérique.",
        "three_body",
        (
            ExampleScene("intro", 6, "none"),
            ExampleScene(
                "binary_star",
                20,
                lines=(
                    ("Deux étoiles liées par la gravitation tournent autour de leur centre de masse.", ""),
                    ("La plus massive décrit la plus petite orbite.", "Masses"),
                    ("Chaque trajectoire est calculée pas à pas par simulation numérique.", ""),
                ),
            ),
            ExampleScene(
                "three_body",
                20,
                "slide_left",
                lines=(
                    ("Trois masses égales peuvent se suivre sur une même courbe en huit.", "Huit"),
                    ("Cette solution, trouvée par Moore en 1993, a été démontrée en 2000.", ""),
                    ("Leur centre de masse commun reste immobile.", ""),
                ),
            ),
            ExampleScene("credits", 8, "fade_black"),
        ),
    ),
}


def timed_lines(lines: tuple[tuple[str, str], ...], fps: float) -> list[tuple[int, int]]:
    """Début et fin (exclue) de chaque phrase : durée selon sa longueur, à la suite, 1 s après le début."""
    spans: list[tuple[int, int]] = []
    t = 1.0
    for text, _marker in lines:
        length = min(MAX_S, max(MIN_S, len(text) / CPS))
        spans.append((int(round(t * fps)), int(round((t + length) * fps))))
        t += length + GAP_S
    return spans


def build_example(example_id: str, canvas: Canvas | None = None) -> Project:
    example = EXAMPLES[example_id]
    project = Project.create(example.title, canvas or Canvas())
    fps = float(project.canvas.fps)
    for spec in example.scenes:
        label, builder = TEMPLATES[spec.template]
        spans = timed_lines(spec.lines, fps)
        # la scène dure au moins jusqu'à 1 s après la dernière phrase (aucun sous-titre coupé)
        frames = max(int(round(spec.seconds * fps)), (spans[-1][1] + int(fps)) if spans else 1)
        scene = Scene.create(label.split(" (")[0], duration_frames=frames)
        builder(project, scene)  # les crédits, en dernier, listent les sources de toutes les scènes
        scene.transition = SceneTransition(spec.transition, 15)
        for (text, marker), (start, end) in zip(spec.lines, spans, strict=True):
            scene.subtitles.append(Subtitle.create(start, end, text))
            if marker:
                scene.markers.append(Marker.create(start, marker))
        project.scenes.append(scene)
    return project

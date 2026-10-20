"""Ligne de commande : ``--version``, ``--selftest`` (contrôle d'installation) et ``--export`` sans interface.

Utilisée par le test d'installation propre du binaire empaqueté (phase 9) et pour des exports en lot.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import threading
from pathlib import Path

from antares_studio import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="antares-studio",
        description="ANTARES Studio — vidéos scientifiques 2D sans programmation.",
    )
    parser.add_argument("project", nargs="?", help="dossier .antares à ouvrir")
    parser.add_argument("--version", action="store_true", help="affiche la version et quitte")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="contrôle d'installation sans interface : modèle, sauvegarde, rendu, export si FFmpeg",
    )
    parser.add_argument(
        "--export",
        nargs=2,
        metavar=("PROJET", "SORTIE.mp4"),
        help="exporte la première scène du projet sans ouvrir l'interface",
    )
    parser.add_argument("--profile", default="final_1080p", help="profil d'export (défaut : final_1080p)")
    parser.add_argument("--scene", default="", help="identifiant ou nom de la scène à exporter")
    return parser


def run_selftest(out: list[str] | None = None) -> int:
    """Crée, enregistre, rouvre et rend un projet modèle ; exporte 10 images si FFmpeg est présent."""
    from antares_studio.app.main import create_app

    log = out if out is not None else []
    app = create_app([])
    from antares_studio.app.diagnostics import diagnostics_report
    from antares_studio.domain.model import Canvas
    from antares_studio.persistence.store import ProjectStore
    from antares_studio.rendering import ffmpeg as ff
    from antares_studio.rendering.exporter import export_video
    from antares_studio.rendering.plan import build_render_plan
    from antares_studio.rendering.qt_painter import render_state_to_image
    from antares_studio.resources.templates import create_project
    from antares_studio.timeline.evaluator import evaluate

    log.append(diagnostics_report())
    log.append(f"Plateforme Qt : {app.platformName()}")
    ok = True
    with tempfile.TemporaryDirectory(prefix="antares-selftest-") as tmp:
        project = create_project("Autotest", Canvas(1920, 1080, 30, 1), "moon_phases", 2)
        store = ProjectStore()
        paths = store.create(Path(tmp) / "Autotest", project)
        reloaded = store.load(paths.root)
        if reloaded != project:
            log.append("ÉCHEC : le projet rouvert diffère du projet enregistré")
            ok = False
        else:
            log.append("Projet : création, enregistrement et réouverture OK")
        scene = reloaded.scenes[0]
        state = evaluate(reloaded, scene.id, scene.duration_frames // 2)
        img = render_state_to_image(state, reloaded.canvas, 1280, 720)
        lit = any(img.pixelColor(x, 360).lightness() > 60 for x in range(0, 1280, 16))
        if img.width() != 1280 or not lit:
            log.append("ÉCHEC : rendu 720p vide")
            ok = False
        else:
            log.append("Rendu : image 1280×720 OK")
        ffmpeg = ff.find_ffmpeg()
        if ffmpeg is None:
            log.append("Export : NON TESTÉ (FFmpeg absent)")
        else:
            output = Path(tmp) / "autotest.mp4"
            plan = build_render_plan(reloaded, scene.id, "draft_720p", str(output), end_frame=10)
            try:
                result = export_video(reloaded, plan, cancel=threading.Event())
                log.append(
                    f"Export : {result.probe.width}×{result.probe.height}, {result.probe.nb_frames} images, "
                    f"{result.elapsed_seconds:.1f} s OK"
                )
            except Exception as exc:  # noqa: BLE001 — rapport d'autotest, toute erreur est un échec
                log.append(f"ÉCHEC export : {exc}")
                ok = False
    log.append("AUTOTEST : " + ("RÉUSSI" if ok else "ÉCHEC"))
    if out is None:
        print("\n".join(log))
    return 0 if ok else 1


def run_export(project_path: str, output: str, profile_id: str, scene_ref: str = "") -> int:
    from antares_studio.app.main import create_app
    from antares_studio.persistence.store import ProjectStore, resolve_project_root
    from antares_studio.rendering.exporter import RenderError, audio_plans_for_scene, export_video
    from antares_studio.rendering.plan import PROFILES, build_render_plan

    create_app([])
    if profile_id not in PROFILES:
        print(f"profil inconnu : {profile_id} (choix : {', '.join(PROFILES)})", file=sys.stderr)
        return 2
    root = resolve_project_root(Path(project_path))
    project = ProjectStore().load(root)
    scene = next(
        (s for s in project.scenes if scene_ref and scene_ref in (s.id, s.name)),
        project.scenes[0] if project.scenes else None,
    )
    if scene is None:
        print("le projet ne contient aucune scène", file=sys.stderr)
        return 2

    def resolve(asset_id: str) -> Path | None:
        asset = project.asset(asset_id)
        return (root / asset.path) if asset and (root / asset.path).is_file() else None

    try:
        audio = audio_plans_for_scene(project, scene.id, resolve)
        plan = build_render_plan(project, scene.id, profile_id, str(Path(output).resolve()), audio=audio)
        for w in plan.warnings:
            print(f"avertissement : {w}", file=sys.stderr)
        last = [-1]

        def progress(done: int, total: int) -> None:
            pct = done * 100 // total
            if pct // 10 != last[0]:
                last[0] = pct // 10
                print(f"{pct:3d} % ({done}/{total})", flush=True)

        result = export_video(project, plan, progress=progress, assets=resolve)
    except Exception as exc:  # noqa: BLE001 — sortie CLI : message clair, code de retour 1
        details = getattr(exc, "details", "")
        print(f"échec de l'export : {exc}\n{details}".rstrip(), file=sys.stderr)
        return 1 if isinstance(exc, RenderError) else 3
    probe = result.probe
    print(f"export terminé : {result.output_path} ({probe.nb_frames} images, {result.elapsed_seconds:.1f} s)")
    return 0


def run_cli(argv: list[str]) -> int | None:
    """Traite les options sans interface ; retourne ``None`` si l'interface doit être lancée."""
    args = build_parser().parse_args(argv)
    if args.version:
        print(f"ANTARES Studio {__version__}")
        return 0
    if args.selftest:
        return run_selftest()
    if args.export:
        return run_export(args.export[0], args.export[1], args.profile, args.scene)
    return None

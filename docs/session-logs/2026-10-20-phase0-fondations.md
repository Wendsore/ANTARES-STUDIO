# Session 2026-10-20 — Phase 0 : fondations éprouvées

**Agent :** Claude (Claude Code, session autonome) — **Machine :** `ki`, Debian 13, i5-4310U 2c/4t, 7,6 Go, sans écran, sans GPU — **Branche :** `feat/phase-0-fondations`.

## Faits observés au démarrage

- Dépôt `Wendsore/ANTARES-STUDIO` cloné dans `~/Wendsore-Workspace/repos/` ; 11 commits, uniquement documentaires ; `main` non protégée ; droits `ADMIN` via `gh` ; issue #1 ouverte (lots Phase 0).
- Python 3.13.5, uv, git, gh présents ; FFmpeg absent → installé (`ffmpeg 7.1.5-0+deb13u1`, libx264 disponible) ; Xvfb et libs xcb installés pour les essais OpenGL.

## Commandes exécutées (extrait reproductible)

```bash
uv venv .venv --python 3.13 && uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/python scripts/poc/phase0_qt_renderer.py out.mp4            # 5,05–5,33 s / 150 img 1080p
venv-manimce/bin/manim -qh --fps 30 scripts/poc/phase0_manimce_scene.py EarthMoon   # 8,5–8,7 s
xvfb-run -a venv-manimgl/bin/manimgl scripts/poc/phase0_manimgl_scene.py EarthMoon -w --hd   # 33,8 s
.venv/bin/python -m ruff check src tests && .venv/bin/python -m mypy src
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

## Tests réellement exécutés (Linux, 2026-10-20)

| Suite | Résultat |
|---|---|
| `tests/unit` (37) | PASS |
| `tests/integration/test_export.py` (7, marqueur `render`) | PASS — MP4 1080p 150 images, 720p 30 images, annulation à 50 %, FFmpeg absent |
| `tests/test_documentation.py` (3) | PASS |
| ruff check / format, mypy strict | PASS |
| Windows 11 | **NON TESTÉ** (job GitHub Actions `windows-latest` ajouté ; résultat à lire dans l'onglet Actions) |

## Décisions

- ADR-0001 (moteur), ADR-0002 (schéma/temps). Travail en branche + PR vers `main` ; fusion par l'agent après CI verte, `main` n'étant pas protégée et le propriétaire ayant demandé une synchronisation continue (ordre de mission §3).
- Test TIM-03 : politique « dernière keyframe déclarée gagne » pour une même frame.

## Gate 0

`project → evaluate → export` démontré par `tests/integration/test_export.py::test_ren01_02_12_export_5s_1080p_verified` (ffprobe : h264 1920×1080 30/1, 150 images, 5,000 s ; décodage complet OK). **Gate 0 : PASS (Linux).**

## Prochaine action

Phase 1 : coquille PySide6 (fenêtre, docks, nouveau/ouvrir/enregistrer, autosave, récupération) avec tests `pytest-qt` hors écran.

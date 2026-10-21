"""Adaptateur Blender facultatif (phase 7) : détection et rendu d'une séquence PNG, sans jamais bloquer la 2D.

Blender est un outil externe (GPL) lancé en sous-processus (``blender -b --python script -- args``) ;
il n'est ni embarqué ni requis. Son absence est un état normal signalé dans les diagnostics.
Référence : https://docs.blender.org/manual/en/latest/advanced/command_line/render.html
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path

ENV_BLENDER = "ANTARES_BLENDER"
_SCRIPT = Path(__file__).resolve().parent.parent / "resources" / "blender" / "planete.py"
_SAVED = re.compile(r"^Saved: ")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0


class BlenderError(RuntimeError):
    def __init__(self, message: str, details: str = ""):
        super().__init__(message)
        self.details = details


def find_blender(configured: str | None = None) -> Path | None:
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))
    if os.environ.get(ENV_BLENDER):
        candidates.append(Path(os.environ[ENV_BLENDER]))
    found = shutil.which("blender")
    if found:
        candidates.append(Path(found))
    if sys.platform.startswith("win"):
        for base in (os.environ.get("PROGRAMFILES", r"C:\Program Files"),):
            root = Path(base) / "Blender Foundation"
            if root.is_dir():
                candidates += sorted(root.glob("Blender */blender.exe"), reverse=True)
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    return None


def blender_version(path: Path) -> str:
    try:
        out = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"inconnu ({exc})"
    return (out.stdout.splitlines() or ["inconnu"])[0].strip()


def render_planet_sequence(
    output_dir: Path,
    frames: int,
    width: int = 512,
    height: int = 512,
    turns: float = 1.0,
    color_a: str = "#0D3380",
    color_b: str = "#2E7D32",
    samples: int = 16,
    progress: Callable[[int, int], None] | None = None,
    cancel: threading.Event | None = None,
    blender_path: str | None = None,
    timeout_s: float = 3600,
) -> list[Path]:
    """Rend ``frames`` images PNG ``frame_0001.png`` … dans ``output_dir`` ; retourne les chemins triés."""
    blender = find_blender(blender_path)
    if blender is None:
        raise BlenderError(
            "Blender est introuvable : la planète 3D est indisponible "
            "(les fonctions 2D ne dépendent pas de Blender)."
        )
    if frames < 1 or width < 8 or height < 8:
        raise BlenderError("au moins 1 image et 8 px de côté sont requis")
    if not _SCRIPT.is_file():
        raise BlenderError(f"script de rendu absent : {_SCRIPT}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(blender),
        "-b",
        "--python",
        str(_SCRIPT),
        "--",
        str(output_dir),
        str(frames),
        str(width),
        str(height),
        f"{turns:.6f}",
        color_a,
        color_b,
        str(samples),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        creationflags=_NO_WINDOW,
    )
    done = 0
    log: list[str] = []
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            log.append(line.rstrip())
            if len(log) > 2000:
                del log[:1000]
            if _SAVED.match(line):
                done += 1
                if progress:
                    progress(done, frames)
            if cancel is not None and cancel.is_set():
                proc.kill()
                raise BlenderError("rendu Blender annulé")
        rc = proc.wait(timeout=timeout_s)
    finally:
        if proc.poll() is None:
            proc.kill()
    files = sorted(output_dir.glob("frame_*.png"))
    if rc != 0 or len(files) != frames:
        raise BlenderError(
            f"Blender a échoué (code {rc}, {len(files)}/{frames} images).", "\n".join(log[-40:])
        )
    return files

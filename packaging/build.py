"""Construit le dossier distribuable d'ANTARES Studio avec PyInstaller (phase 9).

Usage : ``python packaging/build.py [--check]`` depuis la racine du dépôt, dans l'environnement du projet
(``pip install pyinstaller`` au préalable). ``--check`` lance ensuite ``--version`` et ``--selftest`` sur le
binaire produit (``QT_QPA_PLATFORM=offscreen`` pour les machines sans écran).

FFmpeg n'est pas téléchargé : déposez ``ffmpeg``/``ffprobe`` (et leur LICENSE) dans ``packaging/ffmpeg/``
pour les livrer dans ``bin/``, sinon l'application cherche FFmpeg sur le PATH ou le chemin configuré.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "ANTARES Studio"
EXE = DIST / ("ANTARES Studio.exe" if sys.platform.startswith("win") else "ANTARES Studio")


def build() -> Path:
    for folder in (ROOT / "build", DIST):
        if folder.is_dir():
            shutil.rmtree(folder)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        str(ROOT / "packaging" / "antares_studio.spec"),
    ]
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)
    if not EXE.is_file():
        raise SystemExit(f"binaire absent : {EXE}")
    size = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"dossier produit : {DIST} ({size / 2**20:.0f} Mo, {sum(1 for _ in DIST.rglob('*'))} fichiers)")
    return EXE


def check(exe: Path) -> None:
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    for args in (["--version"], ["--selftest"]):
        print(f"$ {exe.name} {' '.join(args)}", flush=True)
        proc = subprocess.run([str(exe), *args], env=env, capture_output=True, text=True, timeout=600)
        print(proc.stdout, end="")
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            raise SystemExit(f"échec de {args[0]} (code {proc.returncode})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="exécute --version et --selftest sur le binaire")
    args = parser.parse_args()
    exe = build()
    if args.check:
        check(exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

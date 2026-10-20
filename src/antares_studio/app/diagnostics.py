"""Rapport de diagnostic local (versions, FFmpeg, Qt) sans identifiant ni secret."""

from __future__ import annotations

import platform
import sys

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import qVersion

from antares_studio import __version__
from antares_studio.rendering import ffmpeg as ff


def diagnostics_report(ffmpeg_setting: str = "") -> str:
    lines = [
        f"ANTARES Studio {__version__}",
        f"Système : {platform.system()} {platform.release()} ({platform.machine()})",
        f"Python : {sys.version.split()[0]}",
        f"Qt : {qVersion()} — PySide6 : {pyside_version}",
    ]
    ffmpeg = ff.find_ffmpeg(ffmpeg_setting or None)
    if ffmpeg is None:
        lines.append(
            "FFmpeg : INTROUVABLE — export vidéo indisponible. Installez FFmpeg ou renseignez son chemin."
        )
    else:
        lines.append(f"FFmpeg : {ffmpeg} — {ff.tool_version(ffmpeg)}")
        lines.append(f"  encodeur H.264 (libx264) : {'oui' if ff.has_encoder(ffmpeg, 'libx264') else 'NON'}")
        probe = ff.find_ffprobe(ffmpeg=ffmpeg)
        lines.append(f"ffprobe : {probe if probe else 'INTROUVABLE (vérification des exports impossible)'}")
    return "\n".join(lines)

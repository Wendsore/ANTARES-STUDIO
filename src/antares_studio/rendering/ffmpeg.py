"""Localisation et pilotage de FFmpeg/ffprobe en sous-processus (arguments en liste, jamais de shell)."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

ENV_FFMPEG = "ANTARES_FFMPEG"
ENV_FFPROBE = "ANTARES_FFPROBE"
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


class FFmpegNotFoundError(RuntimeError):
    pass


class FFmpegError(RuntimeError):
    def __init__(self, message: str, stderr: str = "", returncode: int | None = None):
        super().__init__(message)
        self.stderr = stderr
        self.returncode = returncode


def _candidates(name: str, env: str, configured: str | None) -> list[Path]:
    out: list[Path] = []
    if configured:
        out.append(Path(configured))
    if os.environ.get(env):
        out.append(Path(os.environ[env]))
    exe = name + (".exe" if sys.platform.startswith("win") else "")
    # binaire livré avec l'application empaquetée (PyInstaller : dossier de l'exécutable / bin)
    if getattr(sys, "frozen", False):
        out.append(Path(sys.executable).resolve().parent / "bin" / exe)
    found = shutil.which(name)
    if found:
        out.append(Path(found))
    return out


def find_ffmpeg(configured: str | None = None) -> Path | None:
    for c in _candidates("ffmpeg", ENV_FFMPEG, configured):
        if c.is_file() and os.access(c, os.X_OK):
            return c
    return None


def find_ffprobe(configured: str | None = None, ffmpeg: Path | None = None) -> Path | None:
    cands = _candidates("ffprobe", ENV_FFPROBE, configured)
    if ffmpeg is not None:
        sibling = ffmpeg.with_name("ffprobe" + ffmpeg.suffix)
        cands.append(sibling)
    for c in cands:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    return None


def require_ffmpeg(configured: str | None = None) -> Path:
    p = find_ffmpeg(configured)
    if p is None:
        raise FFmpegNotFoundError(
            "FFmpeg est introuvable. Installez-le et ajoutez-le au PATH, ou indiquez son chemin dans "
            "Préférences > Export (variable ANTARES_FFMPEG)."
        )
    return p


def tool_version(path: Path) -> str:
    try:
        out = subprocess.run(
            [str(path), "-version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"inconnu ({exc})"
    first = (out.stdout or out.stderr).splitlines()[:1]
    return first[0].strip() if first else "inconnu"


def has_encoder(ffmpeg: Path, encoder: str) -> bool:
    try:
        out = subprocess.run(
            [str(ffmpeg), "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return any(line.split()[1:2] == [encoder] for line in out.stdout.splitlines() if line.strip())


@dataclass(frozen=True)
class ProbeResult:
    width: int
    height: int
    fps: Fraction
    nb_frames: int
    duration: float
    video_codec: str
    has_audio: bool
    audio_codec: str = ""
    audio_sample_rate: int = 0
    audio_channels: int = 0


def probe(ffprobe: Path, path: Path, require_video: bool = True) -> ProbeResult:
    cmd = [
        str(ffprobe),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        "-count_frames",
        str(path),
    ]
    out = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600, check=False, creationflags=_NO_WINDOW
    )
    if out.returncode != 0:
        raise FFmpegError(f"ffprobe a échoué sur {path.name}", out.stderr, out.returncode)
    data = json.loads(out.stdout or "{}")
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if video is None and audio is not None and not require_video:
        # bande-son seule : dimensions et images à zéro, durée lue sur le flux audio
        return ProbeResult(
            width=0,
            height=0,
            fps=Fraction(0),
            nb_frames=0,
            duration=float(audio.get("duration") or data.get("format", {}).get("duration") or 0.0),
            video_codec="",
            has_audio=True,
            audio_codec=str(audio.get("codec_name", "")),
            audio_sample_rate=int(audio.get("sample_rate", 0)),
            audio_channels=int(audio.get("channels", 0)),
        )
    if video is None:
        raise FFmpegError(f"aucun flux vidéo dans {path.name}", out.stderr)
    num, _, den = str(video.get("r_frame_rate", "0/1")).partition("/")
    fps = Fraction(int(num or 0), int(den or 1)) if int(den or 1) else Fraction(0)
    nb = video.get("nb_read_frames") or video.get("nb_frames") or 0
    duration = float(video.get("duration") or data.get("format", {}).get("duration") or 0.0)
    return ProbeResult(
        width=int(video.get("width", 0)),
        height=int(video.get("height", 0)),
        fps=fps,
        nb_frames=int(nb),
        duration=duration,
        video_codec=str(video.get("codec_name", "")),
        has_audio=audio is not None,
        audio_codec=str(audio.get("codec_name", "")) if audio else "",
        audio_sample_rate=int(audio.get("sample_rate", 0)) if audio else 0,
        audio_channels=int(audio.get("channels", 0)) if audio else 0,
    )


def probe_audio_duration(ffprobe: Path, path: Path) -> float:
    cmd = [str(ffprobe), "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)]
    out = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120, check=False, creationflags=_NO_WINDOW
    )
    if out.returncode != 0:
        raise FFmpegError(f"ffprobe a échoué sur {path.name}", out.stderr, out.returncode)
    data = json.loads(out.stdout or "{}")
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if audio is None:
        raise FFmpegError(f"aucun flux audio dans {path.name}")
    return float(audio.get("duration") or data.get("format", {}).get("duration") or 0.0)


def decode_check(ffmpeg: Path, path: Path, timeout: float = 600) -> bool:
    """Décode entièrement le fichier (``-f null``) ; True si FFmpeg n'a signalé aucune erreur."""
    cmd = [str(ffmpeg), "-v", "error", "-i", str(path), "-f", "null", "-"]
    out = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False, creationflags=_NO_WINDOW
    )
    return out.returncode == 0 and not out.stderr.strip()


class FrameEncoder:
    """Processus ffmpeg lisant des images RGBA brutes sur stdin. Annulable (terminate puis kill)."""

    def __init__(self, cmd: list[str]):
        self.cmd = cmd
        self._proc: subprocess.Popen[bytes] | None = None
        self._stderr: list[bytes] = []
        self._reader: threading.Thread | None = None

    def start(self) -> None:
        self._proc = subprocess.Popen(  # noqa: S603 — arguments en liste, pas de shell
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=_NO_WINDOW,
        )
        assert self._proc.stderr is not None
        stream = self._proc.stderr

        def pump() -> None:
            for line in iter(stream.readline, b""):
                self._stderr.append(line)
                if len(self._stderr) > 2000:
                    del self._stderr[:1000]

        self._reader = threading.Thread(target=pump, name="ffmpeg-stderr", daemon=True)
        self._reader.start()

    def write(self, data: bytes) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        try:
            self._proc.stdin.write(data)
        except (BrokenPipeError, OSError) as exc:
            raise FFmpegError(
                "FFmpeg a interrompu la lecture des images", self.stderr_text(), self._proc.poll()
            ) from exc

    def finish(self, timeout: float = 600) -> int:
        assert self._proc is not None and self._proc.stdin is not None
        with contextlib.suppress(OSError):
            self._proc.stdin.close()
        rc = self._proc.wait(timeout=timeout)
        if self._reader:
            self._reader.join(timeout=5)
        return rc

    def abort(self) -> None:
        if self._proc is None or self._proc.poll() is not None:
            return
        with contextlib.suppress(OSError):
            if self._proc.stdin:
                self._proc.stdin.close()
        self._proc.terminate()
        deadline = time.monotonic() + 5
        while self._proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait(timeout=10)

    def stderr_text(self) -> str:
        return b"".join(self._stderr[-200:]).decode("utf-8", errors="replace")

    @property
    def returncode(self) -> int | None:
        return self._proc.poll() if self._proc else None

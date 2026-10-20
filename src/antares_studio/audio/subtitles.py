"""Sous-titres : lecture/écriture SRT et WebVTT (UTF-8), frames ↔ temps, diagnostic des chevauchements."""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

from antares_studio.domain.model import Subtitle

_TIME_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
_ARROW_RE = re.compile(r"\s*-->\s*")


class SubtitleFormatError(ValueError):
    pass


@dataclass(frozen=True)
class SubtitleIssue:
    index: int
    message: str


def _parse_time(text: str) -> float:
    m = _TIME_RE.fullmatch(text.strip())
    if not m:
        raise SubtitleFormatError(f"horodatage invalide : {text!r}")
    h = int(m.group(1) or 0)
    mnt, sec = int(m.group(2)), int(m.group(3))
    ms = int(m.group(4).ljust(3, "0"))
    return h * 3600 + mnt * 60 + sec + ms / 1000.0


def _format_time(seconds: float, sep: str) -> str:
    seconds = max(0.0, seconds)
    total_ms = int(round(seconds * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def parse_subtitles(text: str, fps: Fraction) -> list[Subtitle]:
    """Lit un contenu SRT ou WebVTT et retourne des sous-titres quantifiés en frames."""
    text = text.lstrip("﻿")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[Subtitle] = []
    i = 0
    if lines and lines[0].strip().upper().startswith("WEBVTT"):
        i = 1
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.upper().startswith(("NOTE", "STYLE", "REGION")) and "-->" not in line:
            if line.upper().startswith(("NOTE", "STYLE", "REGION")):
                i += 1
                while i < len(lines) and lines[i].strip():
                    i += 1
            i += 1
            continue
        if "-->" not in line:
            # numéro de séquence SRT (ou identifiant VTT) : la ligne suivante porte les temps
            i += 1
            if i >= len(lines) or "-->" not in lines[i]:
                raise SubtitleFormatError(f"ligne {i}: horodatage attendu après l'identifiant {line!r}")
            line = lines[i].strip()
        times = _ARROW_RE.split(line, maxsplit=1)
        if len(times) != 2:
            raise SubtitleFormatError(f"ligne {i + 1}: syntaxe « début --> fin » attendue")
        start = _parse_time(times[0])
        end_token = times[1].split()[0] if times[1].split() else ""
        end = _parse_time(end_token)
        i += 1
        body: list[str] = []
        while i < len(lines) and lines[i].strip():
            body.append(lines[i].rstrip())
            i += 1
        content = "\n".join(body)
        content = re.sub(r"</?(b|i|u|c|v|ruby|rt|lang)[^>]*>", "", content)
        if end <= start:
            raise SubtitleFormatError(f"sous-titre {len(out) + 1}: fin avant début")
        sf = int(round(start * float(fps)))
        ef = max(sf + 1, int(round(end * float(fps))))
        out.append(Subtitle.create(sf, ef, content))
    return out


def format_srt(subs: list[Subtitle], fps: Fraction) -> str:
    chunks = []
    for n, s in enumerate(sorted(subs, key=lambda x: (x.start_frame, x.id)), start=1):
        start = _format_time(s.start_frame / float(fps), ",")
        end = _format_time(s.end_frame / float(fps), ",")
        chunks.append(f"{n}\n{start} --> {end}\n{s.text}\n")
    return "\n".join(chunks) + ("\n" if chunks else "")


def format_vtt(subs: list[Subtitle], fps: Fraction) -> str:
    chunks = ["WEBVTT\n"]
    for s in sorted(subs, key=lambda x: (x.start_frame, x.id)):
        start = _format_time(s.start_frame / float(fps), ".")
        end = _format_time(s.end_frame / float(fps), ".")
        chunks.append(f"{start} --> {end}\n{s.text}\n")
    return "\n".join(chunks)


def check_subtitles(subs: list[Subtitle], duration_frames: int, fps: Fraction) -> list[SubtitleIssue]:
    """Diagnostics AUD-07 : chevauchements, durée < 0,5 s, texte vide, dépassement de scène, longueur."""
    issues: list[SubtitleIssue] = []
    ordered = sorted(enumerate(subs), key=lambda p: (p[1].start_frame, p[1].id))
    min_frames = max(1, int(round(0.5 * float(fps))))
    for pos, (idx, s) in enumerate(ordered):
        if not s.text.strip():
            issues.append(SubtitleIssue(idx, "texte vide"))
        if s.end_frame - s.start_frame < min_frames:
            issues.append(SubtitleIssue(idx, "durée inférieure à 0,5 s"))
        if s.end_frame > duration_frames:
            issues.append(SubtitleIssue(idx, "dépasse la fin de la scène"))
        if pos + 1 < len(ordered):
            nidx, nxt = ordered[pos + 1]
            if nxt.start_frame < s.end_frame:
                issues.append(SubtitleIssue(idx, f"chevauche le sous-titre {nidx + 1}"))
        if len(s.text) > 84 or s.text.count("\n") > 1:
            issues.append(SubtitleIssue(idx, "trop long pour un téléphone (max 2 lignes / 84 caractères)"))
    return issues

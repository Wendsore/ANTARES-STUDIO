"""Préférences locales (QSettings) : récents, disposition, FFmpeg, thème, aide. Rien n'est envoyé en ligne."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings

ORG = "Wendsore"
APP = "ANTARES Studio"
MAX_RECENT = 10
SETTINGS_DIR_ENV = "ANTARES_SETTINGS_DIR"


def _open_settings() -> QSettings:
    """Emplacement natif du système, sauf si ``ANTARES_SETTINGS_DIR`` désigne un dossier explicite.

    Le constructeur ``QSettings(organisation, application)`` ignore ``setDefaultFormat`` et ``setPath`` :
    les tests et scripts passent donc par la variable d'environnement, héritée par les sous-processus.
    """
    folder = os.environ.get(SETTINGS_DIR_ENV, "").strip()
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        return QSettings(str(Path(folder) / "antares-studio.ini"), QSettings.Format.IniFormat)
    return QSettings(ORG, APP)


class AppSettings:
    def __init__(self) -> None:
        self._s = _open_settings()

    def file_name(self) -> str:
        return self._s.fileName()

    def recent_projects(self) -> list[Path]:
        raw = self._s.value("recent/projects", [], type=list)
        out: list[Path] = []
        items_raw = raw if isinstance(raw, list) else []
        for item in items_raw:
            p = Path(str(item))
            if p not in out:
                out.append(p)
        return out[:MAX_RECENT]

    def add_recent(self, path: Path) -> None:
        items = [str(path)] + [str(p) for p in self.recent_projects() if p != path]
        self._s.setValue("recent/projects", items[:MAX_RECENT])

    def remove_recent(self, path: Path) -> None:
        self._s.setValue("recent/projects", [str(p) for p in self.recent_projects() if p != path])

    def ffmpeg_path(self) -> str:
        return str(self._s.value("export/ffmpeg_path", "", type=str) or "")

    def set_ffmpeg_path(self, path: str) -> None:
        self._s.setValue("export/ffmpeg_path", path)

    def last_export_profile(self) -> str:
        return str(self._s.value("export/profile", "final_1080p", type=str) or "final_1080p")

    def set_last_export_profile(self, profile_id: str) -> None:
        self._s.setValue("export/profile", profile_id)

    def window_geometry(self) -> QByteArray:
        v = self._s.value("window/geometry", QByteArray(), type=QByteArray)
        return v if isinstance(v, QByteArray) else QByteArray()

    def window_state(self) -> QByteArray:
        v = self._s.value("window/state", QByteArray(), type=QByteArray)
        return v if isinstance(v, QByteArray) else QByteArray()

    def save_window(self, geometry: QByteArray, state: QByteArray) -> None:
        self._s.setValue("window/geometry", geometry)
        self._s.setValue("window/state", state)

    def reset_window(self) -> None:
        self._s.remove("window/geometry")
        self._s.remove("window/state")

    def autosave_interval_s(self) -> int:
        v = self._s.value("edit/autosave_interval_s", 60, type=int)
        return int(v) if isinstance(v, int) and v > 0 else 60

    def favorites(self) -> list[str]:
        """Favoris de la bibliothèque (identifiants « objet:kind », « animation:id », « modèle:id »)."""
        raw = self._s.value("library/favorites", [], type=list)
        return [str(x) for x in raw] if isinstance(raw, list) else []

    def set_favorites(self, ids: list[str]) -> None:
        self._s.setValue("library/favorites", sorted(set(ids)))

    def last_directory(self) -> str:
        return str(self._s.value("files/last_directory", str(Path.home()), type=str) or str(Path.home()))

    def set_last_directory(self, path: str) -> None:
        self._s.setValue("files/last_directory", path)

    # --- apparence et aide (ADR-0005) ------------------------------------------------------------
    def theme(self) -> str:
        return str(self._s.value("ui/theme", "sombre", type=str) or "sombre")

    def set_theme(self, name: str) -> None:
        self._s.setValue("ui/theme", name)

    def font_scale(self) -> int:
        v = self._s.value("ui/font_scale", 100, type=int)
        return int(v) if isinstance(v, int) and 50 <= v <= 200 else 100

    def set_font_scale(self, percent: int) -> None:
        self._s.setValue("ui/font_scale", int(percent))

    def show_welcome(self) -> bool:
        return bool(self._s.value("ui/show_welcome", True, type=bool))

    def set_show_welcome(self, on: bool) -> None:
        self._s.setValue("ui/show_welcome", bool(on))

    def show_tips(self) -> bool:
        return bool(self._s.value("help/show_tips", True, type=bool))

    def set_show_tips(self, on: bool) -> None:
        self._s.setValue("help/show_tips", bool(on))

    def tips_seen(self) -> set[str]:
        raw = self._s.value("help/tips_seen", [], type=list)
        return {str(x) for x in raw} if isinstance(raw, list) else set()

    def mark_tip_seen(self, key: str) -> None:
        self._s.setValue("help/tips_seen", sorted(self.tips_seen() | {key}))

    def reset_tips(self) -> None:
        self._s.setValue("help/tips_seen", [])
        self.set_show_tips(True)

    def tutorials_done(self) -> set[str]:
        raw = self._s.value("help/tutorials_done", [], type=list)
        return {str(x) for x in raw} if isinstance(raw, list) else set()

    def mark_tutorial_done(self, tutorial_id: str) -> None:
        self._s.setValue("help/tutorials_done", sorted(self.tutorials_done() | {tutorial_id}))

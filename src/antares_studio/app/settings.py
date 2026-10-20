"""Préférences locales (QSettings) : récents, disposition, chemin FFmpeg. Aucune donnée envoyée nulle part."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings

ORG = "Wendsore"
APP = "ANTARES Studio"
MAX_RECENT = 10


class AppSettings:
    def __init__(self) -> None:
        self._s = QSettings(ORG, APP)

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

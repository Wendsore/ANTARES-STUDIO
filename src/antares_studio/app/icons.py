"""Icônes de l'interface : SVG Lucide (ISC) embarqués, recolorés à la couleur du thème au chargement.

Hors ligne : aucun fichier n'est téléchargé à l'exécution. Le rendu passe par ``QSvgRenderer`` (module
QtSvg), indépendant du greffon d'images ``qsvg``, ce qui fonctionne aussi dans le paquet PyInstaller.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from antares_studio.app import theme

ICON_DIR = Path(__file__).resolve().parent.parent / "resources" / "icons"
LOGO = "antares-logo"
_cache: dict[tuple[str, str, int], QIcon] = {}


def icon_names() -> list[str]:
    return sorted(p.stem for p in ICON_DIR.glob("*.svg"))


def _svg_bytes(name: str, color: str) -> bytes:
    path = ICON_DIR / f"{name}.svg"
    data = path.read_text(encoding="utf-8")
    if name != LOGO:
        data = data.replace("currentColor", color)
    return data.encode("utf-8")


def render_svg(name: str, size: int, color: str | None = None) -> QImage:
    """Image ARGB de l'icône ``name`` au format ``size`` × ``size`` (transparente si le fichier manque)."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    if not (ICON_DIR / f"{name}.svg").is_file():
        return img
    renderer = QSvgRenderer(QByteArray(_svg_bytes(name, color or theme.active().text)))
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return img


def icon(name: str, color: str | None = None) -> QIcon:
    """Icône multi-résolution (16 à 64 px) ; un état désactivé atténué est fourni pour les actions grisées."""
    col = color or theme.active().text
    key = (name, col, theme.font_scale())
    cached = _cache.get(key)
    if cached is not None:
        return cached
    result = QIcon()
    muted = theme.active().text_muted
    for size in (16, 20, 24, 32, 48, 64):
        result.addPixmap(QPixmap.fromImage(render_svg(name, size, col)), QIcon.Mode.Normal)
        if name != LOGO:
            result.addPixmap(QPixmap.fromImage(render_svg(name, size, muted)), QIcon.Mode.Disabled)
    _cache[key] = result
    return result


def app_icon() -> QIcon:
    return icon(LOGO)


def arrow_files(color: str) -> dict[str, str]:
    """Flèches PNG (haut, bas) pour la feuille de style des champs numériques et listes déroulantes.

    Le CSS de Qt ne sait charger que des fichiers : les PNG sont écrits une fois par couleur dans le
    dossier temporaire de l'utilisateur (aucun greffon d'image requis pour le PNG).
    """
    import tempfile

    folder = Path(tempfile.gettempdir()) / "antares-studio-ui" / color.lstrip("#")
    folder.mkdir(parents=True, exist_ok=True)
    out: dict[str, str] = {}
    for key, name in (("up", "chevron-up"), ("down", "chevron-down")):
        path = folder / f"{key}.png"
        if not path.is_file():
            render_svg(name, 24, color).save(str(path))
        out[key] = path.as_posix()
    return out


def clear_cache() -> None:
    """À appeler après un changement de thème : les icônes seront recolorées au prochain accès."""
    _cache.clear()

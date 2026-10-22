"""Système de design de l'éditeur : jetons de couleur, thèmes sombre et clair, feuille de style globale.

Toutes les couleurs de l'interface viennent d'ici (ADR-0005). Les widgets peints à la main (canevas,
timeline) lisent les constantes de module au moment du dessin (``theme.TRACK_BG``…) : ``apply_theme``
les réaffecte, si bien qu'un changement de thème s'applique sans redémarrage.

Le contenu des scènes (couleurs des objets, fond de scène) n'en dépend jamais : la vidéo exportée est
identique quel que soit le thème de l'éditeur.

Contrastes : chaque couple texte/fond déclaré dans ``TEXT_PAIRS`` respecte le rapport 4,5:1 du critère
WCAG 2.2 1.4.3 ; les composants (bordures de champ, focus) visent 3:1 (critère 1.4.11). Vérifié par
``tests/unit/test_theme.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory


@dataclass(frozen=True)
class Palette:
    name: str
    label: str
    window: str  # fond de la fenêtre, barres de menus et d'outils
    panel: str  # fond des panneaux (docks)
    field: str  # champs de saisie, listes
    raised: str  # boutons
    hover: str  # survol
    border: str  # bordures discrètes (séparateurs)
    control_border: str  # contour des champs et boutons (≥ 3:1 sur ``panel``)
    text: str
    text_muted: str
    accent: str  # couleur de marque (or ANTARES) : bouton principal, onglet actif
    on_accent: str  # texte sur l'accent
    focus: str  # anneau de focus, sélection active
    selection_bg: str
    selection_text: str
    warning: str
    danger: str
    success: str
    # zones peintes à la main
    workspace: str  # autour du canevas
    track: str
    track_alt: str
    ruler: str
    clip: str
    clip_muted: str
    block_text: str  # texte sur un clip ou un bloc de sous-titre
    subtitle_block: str
    keyframe: str  # losanges d'images clés (Timeline, Inspecteur)
    keyframe_selected: str


DARK = Palette(
    name="sombre",
    label="Sombre (recommandé pour le montage)",
    window="#14161D",
    panel="#1B1E27",
    field="#232733",
    raised="#2A2F3D",
    hover="#343A4B",
    border="#2E3343",
    control_border="#6E7890",
    text="#E8ECF2",
    text_muted="#A7B0C0",
    accent="#F2A93B",
    on_accent="#1A1200",
    focus="#4FC3F7",
    selection_bg="#24557A",
    selection_text="#FFFFFF",
    warning="#FFB74D",
    danger="#FF8A80",
    success="#81C784",
    workspace="#0F1117",
    track="#1B1E27",
    track_alt="#212532",
    ruler="#151821",
    clip="#2B6C93",
    clip_muted="#4A5060",
    block_text="#FFFFFF",
    subtitle_block="#7A5512",
    keyframe="#FFD54F",
    keyframe_selected="#FF7043",
)

LIGHT = Palette(
    name="clair",
    label="Clair",
    window="#E9EDF3",
    panel="#F6F8FB",
    field="#FFFFFF",
    raised="#FFFFFF",
    hover="#E1E7EF",
    border="#D3DAE4",
    control_border="#7D889A",
    text="#18202D",
    text_muted="#4F5B6E",
    accent="#B8740F",
    on_accent="#1A1200",
    focus="#0277BD",
    selection_bg="#CDE4F6",
    selection_text="#0B1A2A",
    warning="#8A5300",
    danger="#B3261E",
    success="#2E7D32",
    workspace="#CDD3DC",
    track="#FFFFFF",
    track_alt="#F0F3F7",
    ruler="#E2E7EE",
    clip="#2B6C93",
    clip_muted="#8A93A3",
    block_text="#FFFFFF",
    subtitle_block="#7A5512",
    keyframe="#B26A00",
    keyframe_selected="#C2410C",
)

THEMES: dict[str, Palette] = {p.name: p for p in (DARK, LIGHT)}
DEFAULT_THEME = DARK.name
FONT_SCALES: tuple[int, ...] = (90, 100, 115, 130, 150)

# Couples (texte, fond) qui portent du texte lisible : vérifiés à 4,5:1 minimum.
TEXT_PAIRS: tuple[tuple[str, str], ...] = (
    ("text", "window"),
    ("text", "panel"),
    ("text", "field"),
    ("text", "raised"),
    ("text", "hover"),
    ("text_muted", "panel"),
    ("text_muted", "field"),
    ("text_muted", "window"),
    ("on_accent", "accent"),
    ("selection_text", "selection_bg"),
    ("warning", "panel"),
    ("danger", "panel"),
    ("success", "panel"),
    ("text", "track"),
    ("text", "track_alt"),
    ("text_muted", "track"),
    ("text_muted", "ruler"),
    ("block_text", "clip"),
    ("block_text", "subtitle_block"),
)
# Composants non textuels : 3:1 minimum (contour des champs, focus).
COMPONENT_PAIRS: tuple[tuple[str, str], ...] = (
    ("control_border", "panel"),
    ("control_border", "field"),
    ("focus", "panel"),
    ("accent", "panel"),
    ("keyframe", "track"),
    ("keyframe", "track_alt"),
    ("keyframe", "panel"),
    ("keyframe_selected", "track"),
    ("keyframe_selected", "track_alt"),
    ("keyframe_selected", "panel"),
)


def relative_luminance(color: str) -> float:
    """Luminance relative sRGB (WCAG 2.2, définition « relative luminance »)."""
    c = QColor(color)

    def lin(v: float) -> float:
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(c.redF()) + 0.7152 * lin(c.greenF()) + 0.0722 * lin(c.blueF())


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --- jetons lus au moment du dessin (canevas, timeline) ------------------------------------------
# Couleurs d'outils dessinées par-dessus le contenu de la scène : identiques dans les deux thèmes.
CANVAS_SHADOW = QColor(0, 0, 0, 120)
SELECTION = QColor("#4FC3F7")
SELECTION_FILL = QColor(79, 195, 247, 40)
HANDLE_FILL = QColor("#FFFFFF")
HANDLE_BORDER = QColor("#1E88E5")
ROTATE_HANDLE = QColor("#FFB74D")
GRID = QColor(255, 255, 255, 28)
GRID_MAJOR = QColor(255, 255, 255, 60)
SAFE_ZONE = QColor(255, 193, 7, 110)
RUBBER_BAND = QColor(79, 195, 247, 60)
LOCKED = QColor("#EF5350")
PLAYHEAD = QColor("#FF5252")
# Couleurs qui suivent le thème (réaffectées par ``apply_theme``).
WORKSPACE_BG = QColor(DARK.workspace)
TRACK_BG = QColor(DARK.track)
TRACK_ALT_BG = QColor(DARK.track_alt)
RULER_BG = QColor(DARK.ruler)
CLIP = QColor(DARK.clip)
CLIP_MUTED = QColor(DARK.clip_muted)
BLOCK_TEXT = QColor(DARK.block_text)
SUBTITLE_BLOCK = QColor(DARK.subtitle_block)
OUT_OF_RANGE = QColor(0, 0, 0, 90)
TEXT = QColor(DARK.text)
TEXT_MUTED = QColor(DARK.text_muted)
ACCENT = QColor(DARK.accent)
FOCUS = QColor(DARK.focus)
WARNING = QColor(DARK.warning)
SUCCESS = QColor(DARK.success)
DANGER = QColor(DARK.danger)
KEYFRAME = QColor(DARK.keyframe)
KEYFRAME_SELECTED = QColor(DARK.keyframe_selected)

_active: Palette = DARK
_font_scale: int = 100


def active() -> Palette:
    return _active


def font_scale() -> int:
    return _font_scale


def scaled_pt(points: float) -> float:
    """Taille de police mise à l'échelle choisie par l'utilisateur (accessibilité)."""
    return points * _font_scale / 100


def _set_tokens(p: Palette) -> None:
    g = globals()
    g["WORKSPACE_BG"] = QColor(p.workspace)
    g["TRACK_BG"] = QColor(p.track)
    g["TRACK_ALT_BG"] = QColor(p.track_alt)
    g["RULER_BG"] = QColor(p.ruler)
    g["CLIP"] = QColor(p.clip)
    g["CLIP_MUTED"] = QColor(p.clip_muted)
    g["BLOCK_TEXT"] = QColor(p.block_text)
    g["SUBTITLE_BLOCK"] = QColor(p.subtitle_block)
    g["OUT_OF_RANGE"] = QColor(0, 0, 0, 90) if p is DARK else QColor(24, 32, 45, 40)
    g["TEXT"] = QColor(p.text)
    g["TEXT_MUTED"] = QColor(p.text_muted)
    g["ACCENT"] = QColor(p.accent)
    g["FOCUS"] = QColor(p.focus)
    g["WARNING"] = QColor(p.warning)
    g["SUCCESS"] = QColor(p.success)
    g["DANGER"] = QColor(p.danger)
    g["KEYFRAME"] = QColor(p.keyframe)
    g["KEYFRAME_SELECTED"] = QColor(p.keyframe_selected)


def qpalette(p: Palette) -> QPalette:
    pal = QPalette()
    role = QPalette.ColorRole
    for r, value in (
        (role.Window, p.window),
        (role.WindowText, p.text),
        (role.Base, p.field),
        (role.AlternateBase, p.panel),
        (role.Text, p.text),
        (role.Button, p.raised),
        (role.ButtonText, p.text),
        (role.ToolTipBase, p.raised),
        (role.ToolTipText, p.text),
        (role.Highlight, p.selection_bg),
        (role.HighlightedText, p.selection_text),
        (role.Link, p.focus),
        (role.LinkVisited, p.focus),
        (role.PlaceholderText, p.text_muted),
        (role.BrightText, p.danger),
        (role.Mid, p.border),
        (role.Dark, p.window),
        (role.Light, p.hover),
        (role.Shadow, "#000000"),
    ):
        pal.setColor(r, QColor(value))
    disabled = QColor(p.text_muted)
    disabled.setAlphaF(0.55)
    for r in (role.WindowText, role.Text, role.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, r, disabled)
    return pal


def stylesheet(p: Palette, arrows: dict[str, str] | None = None) -> str:
    """Feuille de style Qt globale.

    Variantes par propriété ``role`` : boutons ``primary`` et ``link`` ; libellés ``hint``, ``warning``,
    ``success``, ``title``, ``subtitle``, ``section`` ; cadres ``card`` et ``banner``.
    """
    return f"""
QMainWindow, QDialog {{ background: {p.window}; }}
QMainWindow::separator {{ background: {p.border}; width: 4px; height: 4px; }}
QMainWindow::separator:hover {{ background: {p.focus}; }}
QDockWidget {{ color: {p.text}; titlebar-close-icon: none; }}
QDockWidget::title {{
    background: {p.window}; padding: 6px 8px; border-bottom: 1px solid {p.border};
    text-align: left; font-weight: 600;
}}
QDockWidget > QWidget {{ background: {p.panel}; }}
QMenuBar {{ background: {p.window}; color: {p.text}; padding: 2px; }}
QMenuBar::item {{ padding: 5px 10px; border-radius: 4px; background: transparent; }}
QMenuBar::item:selected {{ background: {p.hover}; }}
QMenu {{ background: {p.raised}; color: {p.text}; border: 1px solid {p.border}; padding: 4px; }}
QMenu::item {{ padding: 6px 28px 6px 24px; border-radius: 4px; }}
QMenu::item:selected {{ background: {p.selection_bg}; color: {p.selection_text}; }}
QMenu::item:disabled {{ color: {p.text_muted}; }}
QMenu::separator {{ height: 1px; background: {p.border}; margin: 4px 8px; }}
QToolBar {{ background: {p.window}; border: none; border-bottom: 1px solid {p.border}; padding: 3px 6px;
    spacing: 2px; }}
QToolBar::separator {{ background: {p.border}; width: 1px; margin: 4px 6px; }}
QToolButton {{ color: {p.text}; background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 4px 6px; }}
QToolButton:hover {{ background: {p.hover}; border-color: {p.border}; }}
QToolButton:pressed, QToolButton:checked {{ background: {p.selection_bg}; color: {p.selection_text}; }}
QToolButton:disabled {{ color: {p.text_muted}; }}
QPushButton {{ background: {p.raised}; color: {p.text}; border: 1px solid {p.control_border};
    border-radius: 6px; padding: 5px 12px; min-height: 20px; }}
QPushButton:hover {{ background: {p.hover}; }}
QPushButton:pressed {{ background: {p.selection_bg}; color: {p.selection_text}; }}
QPushButton:disabled {{ color: {p.text_muted}; border-color: {p.border}; }}
QPushButton:focus, QToolButton:focus {{ border: 2px solid {p.focus}; }}
QPushButton[role="primary"] {{ background: {p.accent}; color: {p.on_accent}; border: 1px solid {p.accent};
    font-weight: 600; }}
QPushButton[role="primary"]:hover {{ background: {QColor(p.accent).lighter(110).name()}; }}
QPushButton[role="primary"]:focus {{ border: 2px solid {p.focus}; }}
QPushButton[role="link"] {{ background: transparent; border: none; color: {p.focus};
    text-align: left; padding: 2px 4px; }}
QPushButton[role="link"]:hover {{ text-decoration: underline; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {p.field}; color: {p.text}; border: 1px solid {p.control_border}; border-radius: 5px;
    padding: 3px 6px; selection-background-color: {p.selection_bg}; selection-color: {p.selection_text};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus,
QTextEdit:focus {{ border: 2px solid {p.focus}; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ subcontrol-origin: border; width: 18px;
    background: {p.raised}; border-left: 1px solid {p.border}; }}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 5px; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 5px; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {p.hover}; }}
QAbstractSpinBox::up-arrow {{ image: url({(arrows or {}).get("up", "")}); width: 10px; height: 10px; }}
QAbstractSpinBox::down-arrow {{ image: url({(arrows or {}).get("down", "")}); width: 10px; height: 10px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 20px;
    border-left: 1px solid {p.border}; }}
QComboBox::down-arrow {{ image: url({(arrows or {}).get("down", "")}); width: 11px; height: 11px; }}
QComboBox QAbstractItemView {{ background: {p.raised}; color: {p.text}; border: 1px solid {p.border};
    selection-background-color: {p.selection_bg}; selection-color: {p.selection_text}; }}
QListWidget, QTreeWidget, QTreeView, QListView, QTableWidget, QTableView, QTextBrowser {{
    background: {p.field}; color: {p.text}; border: 1px solid {p.border}; border-radius: 6px;
    alternate-background-color: {p.panel}; outline: none;
}}
QListWidget::item, QTreeWidget::item, QTreeView::item {{ padding: 4px 4px; border-radius: 4px; }}
QListWidget::item:hover, QTreeWidget::item:hover, QTreeView::item:hover {{ background: {p.hover}; }}
QListWidget::item:selected, QTreeWidget::item:selected, QTreeView::item:selected,
QTableWidget::item:selected {{ background: {p.selection_bg}; color: {p.selection_text}; }}
QHeaderView::section {{ background: {p.panel}; color: {p.text_muted}; border: none;
    border-bottom: 1px solid {p.border}; padding: 4px 6px; font-weight: 600; }}
QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: 6px; top: -1px; background: {p.panel}; }}
QTabBar::tab {{ background: transparent; color: {p.text_muted}; padding: 6px 8px; border: none;
    border-bottom: 2px solid transparent; }}
QTabBar::tab:hover {{ color: {p.text}; }}
QTabBar::tab:selected {{ color: {p.text}; border-bottom: 2px solid {p.accent}; font-weight: 600; }}
QCheckBox, QRadioButton {{ color: {p.text}; spacing: 6px; }}
QLabel {{ color: {p.text}; }}
QLabel[role="hint"] {{ color: {p.text_muted}; }}
QLabel[role="warning"] {{ color: {p.warning}; }}
QLabel[role="success"] {{ color: {p.success}; }}
QLabel[role="title"] {{ font-size: {scaled_pt(20):.0f}pt; font-weight: 700; }}
QLabel[role="subtitle"] {{ color: {p.text_muted}; font-size: {scaled_pt(11):.0f}pt; }}
QLabel[role="section"] {{ color: {p.text_muted}; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; }}
QFrame[role="card"] {{ background: {p.field}; border: 1px solid {p.border}; border-radius: 10px; }}
QFrame[role="card"]:hover {{ border-color: {p.focus}; }}
QFrame[role="banner"] {{ background: {p.raised}; border: 1px solid {p.accent}; border-radius: 8px; }}
QStatusBar {{ background: {p.window}; color: {p.text_muted}; border-top: 1px solid {p.border}; }}
QStatusBar QLabel {{ color: {p.text_muted}; padding: 0 8px; }}
QToolTip {{ background: {p.raised}; color: {p.text}; border: 1px solid {p.control_border}; padding: 5px;
    border-radius: 4px; }}
QProgressBar {{ background: {p.field}; border: 1px solid {p.border}; border-radius: 5px; text-align: center;
    color: {p.text}; min-height: 16px; }}
QProgressBar::chunk {{ background: {p.accent}; border-radius: 4px; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle {{ background: {p.control_border}; border-radius: 3px; min-height: 24px;
    min-width: 24px; }}
QScrollBar::handle:hover {{ background: {p.text_muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QSplitter::handle {{ background: {p.border}; }}
"""


def apply_theme(app: QApplication, name: str = DEFAULT_THEME, scale: int = 100) -> Palette:
    """Applique le thème ``name`` (``sombre`` | ``clair``) et l'échelle du texte (en %) à l'application."""
    global _active, _font_scale
    p = THEMES.get(name, DARK)
    _active = p
    _font_scale = scale if scale in FONT_SCALES else 100
    fusion = QStyleFactory.create("Fusion")
    if fusion is not None:  # rendu identique sous Windows, macOS et Linux
        app.setStyle(fusion)
    app.setPalette(qpalette(p))
    font = QFont(app.font())
    base = app.property("antares_base_pt")
    if base is None:
        base = font.pointSizeF() if font.pointSizeF() > 0 else 10.0
        app.setProperty("antares_base_pt", base)
    font.setPointSizeF(float(base) * _font_scale / 100)
    app.setFont(font)
    from antares_studio.app.icons import arrow_files  # import local : icons dépend de ce module

    app.setStyleSheet(stylesheet(p, arrow_files(p.text_muted)))
    _set_tokens(p)
    return p


def palette_fields() -> list[str]:
    return [f.name for f in fields(Palette) if f.name not in ("name", "label")]

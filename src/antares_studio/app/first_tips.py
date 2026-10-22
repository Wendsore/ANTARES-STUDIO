"""Astuces de première utilisation : une bulle par panneau, la première fois qu'on y travaille.

La bulle apparaît quand le focus entre pour la première fois dans un panneau (ou le canevas), jamais
pendant un tutoriel. Chaque astuce n'est montrée qu'une fois ; « Ne plus afficher » les coupe toutes,
et **Aide > Réafficher les astuces** les remet.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app.settings import AppSettings

# clé = nom d'objet Qt du panneau (ou du canevas) : (titre, texte)
TIPS: dict[str, tuple[str, str]] = {
    "canvas": (
        "Canevas",
        "Molette : zoom. Bouton du milieu, ou Alt + glisser : déplacer la vue. En déplaçant un objet, des "
        "guides roses montrent les alignements (Ctrl : sans aimant). Flèches : 1 px, Maj + flèches : 10 px.",
    ),
    "dock_library": (
        "Bibliothèque",
        "Double-cliquez sur un élément pour l'ajouter. L'onglet Modèles propose des scènes prêtes (Kepler, "
        "trois corps, étoile double…). La case à gauche d'un élément en fait un favori ; ★ n'affiche que "
        "les favoris.",
    ),
    "dock_layers": (
        "Scènes et objets",
        "L'œil masque un objet, le cadenas le verrouille (il ne se sélectionne plus sur le canevas). "
        "▲ Monter et ▼ Descendre changent l'ordre de dessin ; Ctrl+G groupe la sélection.",
    ),
    "dock_inspector": (
        "Inspecteur",
        "Le losange ◆ pose ou retire une image clé à l'image courante. Avec plusieurs objets sélectionnés, "
        "un champ marqué ≠ a des valeurs différentes : ce que vous saisissez s'applique à tous.",
    ),
    "dock_timeline": (
        "Timeline",
        "Clic droit sur une clé : choisir l'interpolation (dont « Courbe personnalisée… ») ou la supprimer. "
        "M pose un repère à l'image courante ; [ et ] sautent au repère précédent ou suivant.",
    ),
    "dock_narration": (
        "Narration",
        "Importez une voix ou enregistrez-la au micro. Donnez le rôle « Musique » à la musique de fond : "
        "à l'export, elle baisse automatiquement pendant que la voix parle.",
    ),
    "dock_exports": (
        "Exports",
        "Les exports lancés « En arrière-plan » s'enchaînent ici pendant que vous continuez à éditer ; la "
        "vidéo correspond au projet tel qu'il était au moment de l'envoi.",
    ),
}


class TipBubble(QFrame):
    """Bulle d'astuce posée sur la fenêtre (pas de fenêtre séparée : rien ne vole le focus)."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("tip_bubble")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("role", "banner")  # même cadre doré que les bandeaux existants
        self.key = ""
        self.title = QLabel()
        bold = self.title.font()
        bold.setBold(True)
        self.title.setFont(bold)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.never = QCheckBox("Ne plus afficher d'astuces")
        self.ok = QPushButton("Compris")
        self.ok.setProperty("role", "primary")
        self.ok.clicked.connect(self.hide)
        row = QHBoxLayout()
        row.addWidget(self.never)
        row.addStretch(1)
        row.addWidget(self.ok)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.text)
        layout.addLayout(row)
        self.setFixedWidth(360)
        self.hide()

    def show_tip(self, key: str, anchor: QWidget) -> None:
        title, text = TIPS[key]
        self.key = key
        self.title.setText(f"Astuce — {title}")
        self.text.setText(text)
        self.never.setChecked(False)
        self.adjustSize()
        window = self.parentWidget()
        assert window is not None
        top_left = anchor.mapTo(window, QPoint(0, 0))
        x = min(max(8, top_left.x() + 16), window.width() - self.width() - 8)
        y = min(max(8, top_left.y() + 28), window.height() - self.height() - 8)
        self.move(x, y)
        self.show()
        self.raise_()


class TipManager(QObject):
    """Observe le focus de l'application et montre l'astuce du panneau atteint, une seule fois."""

    def __init__(self, window: QWidget, settings: AppSettings, blocked: Callable[[], bool] = lambda: False):
        super().__init__(window)
        self.window = window
        self.settings = settings
        self.blocked = blocked  # vrai pendant un tutoriel
        self.bubble = TipBubble(window)
        self.bubble.never.toggled.connect(lambda on: self.settings.set_show_tips(not on))
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.focusChanged.connect(self._focus_changed)

    def panel_of(self, widget: QWidget | None) -> QWidget | None:
        while widget is not None and widget is not self.window:
            if widget.objectName() in TIPS:
                return widget
            widget = widget.parentWidget()
        return None

    def _focus_changed(self, old: QWidget | None, now: QWidget | None) -> None:
        if old is None:  # focus initial ou retour dans l'application : pas un geste vers un panneau
            return
        panel = self.panel_of(now)
        if panel is not None:
            self.maybe_show(panel.objectName(), panel)

    def maybe_show(self, key: str, anchor: QWidget) -> bool:
        if (
            key not in TIPS
            or not self.settings.show_tips()
            or key in self.settings.tips_seen()
            or self.blocked()
            or self.bubble.isVisible()
        ):
            return False
        self.settings.mark_tip_seen(key)
        self.bubble.show_tip(key, anchor)
        return True

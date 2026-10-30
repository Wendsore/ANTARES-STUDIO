"""Boîtes de dialogue simples : nouveau projet, à propos, diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from antares_studio import __version__
from antares_studio.domain.model import Canvas

RATIOS: dict[str, tuple[int, int]] = {
    "16:9 — paysage (YouTube, TV)": (16, 9),
    "9:16 — vertical (téléphone, Shorts)": (9, 16),
    "1:1 — carré (réseaux sociaux)": (1, 1),
}
RESOLUTIONS: dict[str, int] = {"1080p (Full HD)": 1080, "720p (HD, plus léger)": 720}


@dataclass
class NewProjectChoice:
    title: str
    canvas: Canvas
    template_id: str
    duration_s: int


class NewProjectDialog(QDialog):
    def __init__(self, templates: dict[str, str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Nouveau projet")
        self.setModal(True)
        self._templates = templates
        form = QFormLayout()
        self.title_edit = QLineEdit("Ma vidéo scientifique")
        self.ratio = QComboBox()
        self.ratio.addItems(list(RATIOS))
        self.resolution = QComboBox()
        self.resolution.addItems(list(RESOLUTIONS))
        self.fps = QComboBox()
        self.fps.addItems(["30 images/s (recommandé)", "25 images/s", "24 images/s", "60 images/s"])
        self.duration = QSpinBox()
        self.duration.setRange(1, 3600)
        self.duration.setValue(20)
        self.duration.setSuffix(" s")
        self.template = QComboBox()
        self.template.addItem("Scène vide", "")
        for tid, label in templates.items():
            self.template.addItem(label, tid)
        form.addRow("Titre :", self.title_edit)
        form.addRow("Format :", self.ratio)
        form.addRow("Résolution :", self.resolution)
        form.addRow("Cadence :", self.fps)
        form.addRow("Durée de la première scène :", self.duration)
        form.addRow("Modèle de départ :", self.template)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Créer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def choice(self) -> NewProjectChoice:
        rw, rh = RATIOS[self.ratio.currentText()]
        short = RESOLUTIONS[self.resolution.currentText()]
        if rw >= rh:
            height = short
            width = int(round(short * rw / rh))
        else:
            width = short
            height = int(round(short * rh / rw))
        width += width % 2
        height += height % 2
        fps = int(self.fps.currentText().split()[0])
        return NewProjectChoice(
            title=self.title_edit.text().strip() or "Sans titre",
            canvas=Canvas(width=width, height=height, fps_num=fps, fps_den=1),
            template_id=str(self.template.currentData() or ""),
            duration_s=self.duration.value(),
        )


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("À propos d'ANTARES Studio")
        text = QPlainTextEdit(self)
        text.setReadOnly(True)
        text.setPlainText(
            f"ANTARES Studio — Scientific Animation & Storytelling Studio\nVersion {__version__}\n\n"
            "Logiciel local de création de vidéos scientifiques. Aucune donnée n'est envoyée en ligne.\n\n"
            "Composants tiers :\n"
            "- Qt for Python (PySide6), utilisé sous licence LGPLv3 — https://www.qt.io/licensing\n"
            "  Les bibliothèques Qt sont liées dynamiquement ; leurs sources sont disponibles auprès de\n"
            "  The Qt Company (https://code.qt.io) et sur demande auprès du distributeur d'ANTARES Studio.\n"
            "- FFmpeg (exécutable externe, https://ffmpeg.org) pour l'encodage vidéo ; licence LGPL/GPL\n"
            "  selon le build installé sur votre machine.\n"
            "- NumPy (licence BSD).\n"
            "- Icônes Lucide 1.51.0 (https://lucide.dev), licence ISC ; icônes dérivées de Feather sous\n"
            "  licence MIT. Texte complet : resources/icons/LICENSE-lucide.txt.\n"
            "- Polices d'écriture livrées (Kalam, Caveat, Cabin Sketch, EB Garamond…) : Google Fonts,\n"
            "  licence SIL OFL 1.1 (Apache 2.0 pour Permanent Marker et Special Elite). Textes complets :\n"
            "  resources/fonts/<famille>/.\n"
            "- Données d'exemple des planètes : NASA Planetary Fact Sheet (domaine public).\n"
            "- Textures des astres : Solar System Scope (INOVE), d'après les données NASA, licence\n"
            "  CC BY 4.0 (https://www.solarsystemscope.com/textures/).\n"
            "- Cartes du monde : Natural Earth (domaine public). Étoiles et constellations : d3-celestial\n"
            "  (Olaf Frohn, licence BSD 3 clauses, resources/sky/LICENSE-d3-celestial.txt), catalogue\n"
            "  Hipparcos (ESA). Étoiles connues : Wikidata (CC0). Détail : resources/astro/README.md.\n\n"
            "Licence d'ANTARES Studio : non encore décidée (voir README)."
        )
        layout = QVBoxLayout(self)
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Fermer")
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)
        self.resize(640, 360)


class DiagnosticsDialog(QDialog):
    def __init__(self, report: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Diagnostics")
        text = QPlainTextEdit(self)
        text.setReadOnly(True)
        text.setPlainText(report)
        layout = QVBoxLayout(self)
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Fermer")
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)
        self.resize(640, 420)

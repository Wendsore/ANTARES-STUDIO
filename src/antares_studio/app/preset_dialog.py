"""Dialogue de paramètres d'un preset d'animation (n'expose que les paramètres pertinents)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app.document import ProjectDocument
from antares_studio.domain.model import Node
from antares_studio.timeline.presets import PRESETS


class PresetDialog(QDialog):
    def __init__(self, preset_id: str, document: ProjectDocument, node: Node, parent: QWidget | None = None):
        super().__init__(parent)
        self.spec = PRESETS[preset_id]
        self.document = document
        self.node = node
        self.setWindowTitle(f"Animation : {self.spec.label}")
        self.setModal(True)
        self._editors: dict[str, QWidget] = {}
        layout = QVBoxLayout(self)
        desc = QLabel(self.spec.description)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        form = QFormLayout()
        scene = document.scene
        fps = float(document.project.canvas.fps)
        defaults = self.spec.defaults()
        defaults["start_frame"] = document.frame
        if scene is not None:
            defaults["duration_frames"] = max(
                1, min(scene.duration_frames - document.frame, int(round(5 * fps)))
            )
        if preset_id == "orbit":
            c = document.project.canvas
            defaults["center_x"], defaults["center_y"] = c.width / 2, c.height / 2
            dx, dy = node.position[0] - c.width / 2, node.position[1] - c.height / 2
            r = (dx * dx + dy * dy) ** 0.5
            if r > 1:
                import math

                defaults["radius"] = r
                defaults["start_angle_deg"] = math.degrees(math.atan2(dy, dx))
        for p in self.spec.params:
            editor: QWidget
            if p.type == "int":
                sb = QSpinBox()
                sb.setRange(
                    int(p.min) if p.min is not None else -100000,
                    int(p.max) if p.max is not None else 10_000_000,
                )
                sb.setValue(int(defaults[p.name]))
                editor = sb
            elif p.type == "float":
                dsb = QDoubleSpinBox()
                dsb.setRange(p.min if p.min is not None else -1e6, p.max if p.max is not None else 1e6)
                dsb.setDecimals(2)
                dsb.setValue(float(defaults[p.name]))
                editor = dsb
            elif p.type == "bool":
                cb = QCheckBox()
                cb.setChecked(bool(defaults[p.name]))
                editor = cb
            else:
                combo = QComboBox()
                for ch in p.choices:
                    combo.addItem(
                        {
                            "linear": "Linéaire",
                            "ease_in": "Accélération",
                            "ease_out": "Décélération",
                            "ease_in_out": "Douce",
                        }.get(ch, ch),
                        ch,
                    )
                combo.setCurrentIndex(max(0, combo.findData(defaults[p.name])))
                editor = combo
            self._editors[p.name] = editor
            label = p.label
            if p.name == "duration_frames":
                label += f" (à {fps:g} img/s)"
            form.addRow(label + " :", editor)
        layout.addLayout(form)
        if preset_id == "orbit":
            btn = QPushButton("Utiliser la position actuelle de l'objet comme rayon/phase")
            btn.clicked.connect(self._use_current_position)
            layout.addWidget(btn)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Appliquer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _use_current_position(self) -> None:
        import math

        cx = float(self._editors["center_x"].value())  # type: ignore[attr-defined]
        cy = float(self._editors["center_y"].value())  # type: ignore[attr-defined]
        dx, dy = self.node.position[0] - cx, self.node.position[1] - cy
        self._editors["radius"].setValue(max(0.0, (dx * dx + dy * dy) ** 0.5))  # type: ignore[attr-defined]
        self._editors["start_angle_deg"].setValue(math.degrees(math.atan2(dy, dx)))  # type: ignore[attr-defined]

    def values(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, ed in self._editors.items():
            if isinstance(ed, QSpinBox | QDoubleSpinBox):
                out[name] = ed.value()
            elif isinstance(ed, QCheckBox):
                out[name] = ed.isChecked()
            elif isinstance(ed, QComboBox):
                out[name] = ed.currentData()
        return out

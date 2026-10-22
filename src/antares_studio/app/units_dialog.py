"""Constantes sourcées et conversion d'unités, avec insertion du résultat comme texte dans la scène."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from antares_studio.science.units import (
    CONSTANTS,
    SOURCES,
    UNITS,
    UnitError,
    convert,
    format_number,
    format_quantity,
    units_of,
)

DIMENSION_LABELS = {
    "length": "Longueur",
    "time": "Durée",
    "mass": "Masse",
    "speed": "Vitesse",
    "angle": "Angle",
}


def parse_value(text: str) -> float:
    """Nombre saisi à la française ou à l'anglaise (« 1,5 », « 1.5e8 », « 3 000 ») ; ``UnitError`` sinon."""
    cleaned = text.strip().replace(" ", "").replace(" ", "").replace("×10^", "e").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        raise UnitError(f"nombre illisible : {text!r}") from None


class UnitsDialog(QDialog):
    """« Insérer » produit ``inserted_text`` ; l'appelant crée l'objet Texte (commande annulable)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Constantes et unités")
        self.inserted_text = ""
        self._pending = ""
        self.table = QTableWidget(len(CONSTANTS), 4)
        self.table.setObjectName("units_constants")
        self.table.setHorizontalHeaderLabels(["Grandeur", "Symbole", "Valeur", "Source"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for row, const in enumerate(CONSTANTS):
            source = SOURCES[const.source]
            cells = (
                const.name,
                const.symbol,
                format_quantity(const.value, const.unit, 10),
                source.split(" — ")[0],
            )
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(source)
                self.table.setItem(row, col, item)
        self.table.itemSelectionChanged.connect(self._constant_selected)
        self.value = QLineEdit("1")
        self.value.setObjectName("units_value")
        self.from_unit = QComboBox()
        self.from_unit.setObjectName("units_from")
        for u in UNITS.values():
            self.from_unit.addItem(f"{u.symbol} ({DIMENSION_LABELS[u.dimension].lower()})", u.symbol)
        self.to_unit = QComboBox()
        self.to_unit.setObjectName("units_to")
        self.digits = QSpinBox()
        self.digits.setRange(1, 10)
        self.digits.setValue(4)
        self.result_label = QLabel()
        self.result_label.setObjectName("units_result")
        self.result_label.setProperty("role", "title")
        self.error = QLabel()
        self.error.setProperty("role", "warning")
        self.error.setWordWrap(True)
        line = QHBoxLayout()
        line.addWidget(self.value, 1)
        line.addWidget(self.from_unit)
        line.addWidget(QLabel("→"))
        line.addWidget(self.to_unit)
        form = QFormLayout()
        form.addRow("Valeur :", line)
        form.addRow("Chiffres significatifs :", self.digits)
        form.addRow("Résultat :", self.result_label)
        form.addRow("", self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.insert_btn = buttons.addButton("Insérer dans la scène", QDialogButtonBox.ButtonRole.AcceptRole)
        self.insert_btn.setObjectName("units_insert")
        self.insert_btn.setToolTip("Ajoute le résultat comme objet Texte au centre de la vue")
        buttons.accepted.connect(self._insert)
        buttons.rejected.connect(self.reject)
        hint = QLabel(
            "Constantes exactes ou nominales (SI, CODATA, UAI) ; survolez une ligne pour la référence. "
            "Une conversion entre grandeurs différentes est refusée, jamais approximée."
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "hint")
        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self.table, 1)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.from_unit.currentIndexChanged.connect(self._fill_targets)
        for sig in (self.value.textChanged, self.to_unit.currentIndexChanged, self.digits.valueChanged):
            sig.connect(self._update)
        self.from_unit.setCurrentIndex(self.from_unit.findData("au"))
        self._fill_targets()
        self.to_unit.setCurrentIndex(max(0, self.to_unit.findData("km")))
        self.resize(760, 560)

    def _fill_targets(self) -> None:
        source = UNITS[str(self.from_unit.currentData())]
        current = self.to_unit.currentData()
        self.to_unit.blockSignals(True)
        self.to_unit.clear()
        for symbol in units_of(source.dimension):
            self.to_unit.addItem(symbol, symbol)
        self.to_unit.setCurrentIndex(max(0, self.to_unit.findData(current)))
        self.to_unit.blockSignals(False)
        self._update()

    def _constant_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        const = CONSTANTS[rows[0].row()]
        if const.key in ("au", "ly", "pc"):
            self.value.setText("1")
            self.from_unit.setCurrentIndex(self.from_unit.findData(const.key))
        elif const.key == "c":
            self.value.setText(repr(const.value))
            self.from_unit.setCurrentIndex(self.from_unit.findData("m/s"))
        elif const.key == "yr":
            self.value.setText("1")
            self.from_unit.setCurrentIndex(self.from_unit.findData("yr"))
        else:  # G, GM : pas d'unité convertible ici, la valeur s'insère telle quelle
            self.result_label.setText(format_quantity(const.value, const.unit, self.digits.value()))
            self.error.clear()
            self._pending = f"{const.symbol} = {self.result_label.text()}"
            return
        self._update()

    def converted(self) -> float:
        return convert(
            parse_value(self.value.text()), str(self.from_unit.currentData()), str(self.to_unit.currentData())
        )

    def _update(self) -> None:
        self._pending = ""
        try:
            value = parse_value(self.value.text())
            result = self.converted()
        except UnitError as exc:
            self.result_label.setText("—")
            self.error.setText(str(exc))
            self.insert_btn.setEnabled(False)
            return
        self.error.clear()
        self.insert_btn.setEnabled(True)
        digits = self.digits.value()
        src, dst = str(self.from_unit.currentData()), str(self.to_unit.currentData())
        self.result_label.setText(format_quantity(result, dst, digits))
        self._pending = f"{format_number(value, digits)} {src} = {self.result_label.text()}"

    def text_to_insert(self) -> str:
        return self._pending

    def _insert(self) -> None:
        if self._pending:
            self.inserted_text = self._pending
            self.accept()

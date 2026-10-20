"""Fiches de provenance : licence d'une ressource, inventaire des licences/crédits, sources scientifiques."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app.document import ProjectDocument
from antares_studio.domain.commands import SetAssetLicense, SetProjectMetadata
from antares_studio.domain.model import Asset, AssetLicense
from antares_studio.resources.licenses import (
    LICENSE_CHOICES,
    STATUS_COMPLETE,
    choice_for,
    credits_text,
    inventory,
)


class ProvenanceDialog(QDialog):
    """Fiche auteur / source / licence d'une ressource importée (AST-03, AST-06)."""

    def __init__(self, asset: Asset, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Provenance de la ressource")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        intro = QLabel(
            f"<b>{asset.path}</b><br>Indiquez d'où vient cette ressource : les crédits de la vidéo "
            "et l'inventaire des licences en dépendent. Une fiche incomplète est signalée à l'export."
        )
        intro.setWordWrap(True)
        lay.addWidget(intro)
        form = QFormLayout()
        lay.addLayout(form)
        lic = asset.license
        self.author = QLineEdit(lic.author)
        self.author.setPlaceholderText("Auteur ou organisme (ex. NASA/JPL, votre nom)")
        form.addRow("Auteur :", self.author)
        self.source = QLineEdit(lic.source_url)
        self.source.setPlaceholderText("Adresse ou référence de la source")
        form.addRow("Source :", self.source)
        self.license = QComboBox()
        for c in LICENSE_CHOICES:
            self.license.addItem(c.label, c.id)
        if lic.license and choice_for(lic.license) is None:
            self.license.addItem(lic.license, lic.license)
        idx = self.license.findData(lic.license) if lic.license else 0
        self.license.setCurrentIndex(max(0, idx))
        form.addRow("Licence :", self.license)
        self.attribution = QCheckBox("Attribution requise (apparaît dans les crédits)")
        self.redistribution = QCheckBox("Redistribution autorisée (la vidéo peut être diffusée)")
        form.addRow("", self.attribution)
        form.addRow("", self.redistribution)
        self.license.currentIndexChanged.connect(self._apply_choice_defaults)
        if lic.license:
            self.attribution.setChecked(lic.attribution_required)
            self.redistribution.setChecked(lic.redistribution_allowed)
        else:
            self._apply_choice_defaults()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Enregistrer la fiche")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Plus tard")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _apply_choice_defaults(self) -> None:
        choice = choice_for(str(self.license.currentData()))
        if choice is not None:
            self.attribution.setChecked(choice.attribution_required)
            self.redistribution.setChecked(choice.redistribution_allowed)

    def result_license(self) -> AssetLicense:
        return AssetLicense(
            author=self.author.text().strip(),
            source_url=self.source.text().strip(),
            license=str(self.license.currentData() or ""),
            attribution_required=self.attribution.isChecked(),
            redistribution_allowed=self.redistribution.isChecked(),
            verified_on=datetime.now(UTC).date().isoformat(),
        )


def edit_asset_provenance(document: ProjectDocument, asset: Asset, parent: QWidget | None = None) -> bool:
    """Ouvre la fiche et enregistre la licence (annulable) ; retourne True si la fiche a été enregistrée."""
    dlg = ProvenanceDialog(asset, parent)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return False
    document.push(SetAssetLicense(asset.id, dlg.result_license()))
    return True


class LicenseInventoryDialog(QDialog):
    """Inventaire des ressources du projet (statut, usages) et texte de crédits exportable."""

    COLUMNS = ("Fichier", "Type", "Statut", "Auteur", "Licence", "Utilisée par")

    def __init__(self, document: ProjectDocument, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self.setWindowTitle("Inventaire des licences et crédits")
        self.resize(900, 560)
        lay = QVBoxLayout(self)
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(list(self.COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(lambda _it: self.edit_selected())
        lay.addWidget(QLabel("<b>Ressources importées</b> (double-clic : modifier la fiche)"))
        lay.addWidget(self.table, 2)
        lay.addWidget(QLabel("<b>Crédits générés</b> (écrits dans <code>*.credits.txt</code> à l'export)"))
        self.credits = QPlainTextEdit()
        self.credits.setReadOnly(True)
        lay.addWidget(self.credits, 1)
        row = QHBoxLayout()
        self.btn_edit = QPushButton("Modifier la fiche…")
        self.btn_edit.clicked.connect(self.edit_selected)
        btn_copy = QPushButton("Copier les crédits")
        btn_copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.credits.toPlainText()))
        btn_save = QPushButton("Enregistrer les crédits…")
        btn_save.clicked.connect(self.save_credits)
        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.accept)
        for b in (self.btn_edit, btn_copy, btn_save):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(btn_close)
        lay.addLayout(row)
        document.changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        rows = inventory(self.document.project)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            lic = row.asset.license
            choice = choice_for(lic.license)
            values = (
                row.asset.path,
                row.asset.kind,
                row.status,
                lic.author,
                choice.label if choice else lic.license,
                ", ".join(row.used_by) or "—",
            )
            for c, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setData(Qt.ItemDataRole.UserRole, row.asset.id)
                if c == 2 and row.status != STATUS_COMPLETE:
                    item.setForeground(Qt.GlobalColor.yellow)
                self.table.setItem(r, c, item)
        self.credits.setPlainText(credits_text(self.document.project))
        self.btn_edit.setEnabled(bool(rows))

    def selected_asset(self) -> Asset | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        item = self.table.item(r, 0)
        return self.document.project.asset(str(item.data(Qt.ItemDataRole.UserRole))) if item else None

    def edit_selected(self) -> None:
        asset = self.selected_asset()
        if asset is None and self.table.rowCount():
            self.table.selectRow(0)
            asset = self.selected_asset()
        if asset is not None:
            edit_asset_provenance(self.document, asset, self)

    def save_credits(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer les crédits", "credits.txt", "Texte (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(self.credits.toPlainText())
            except OSError as exc:
                QMessageBox.critical(self, "Enregistrement impossible", str(exc))


class SourcesDialog(QDialog):
    """Sources scientifiques du projet (libellé + adresse), affichées dans les crédits (SCI-08)."""

    def __init__(self, document: ProjectDocument, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self.setWindowTitle("Sources scientifiques")
        self.resize(720, 400)
        lay = QVBoxLayout(self)
        lay.addWidget(
            QLabel(
                "Référencez les sources des constantes, données et modèles utilisés (une ligne par source)."
            )
        )
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Libellé", "Adresse / référence"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table, 1)
        sources = document.project.scientific_metadata.get("sources", [])
        for src in sources if isinstance(sources, list) else []:
            if isinstance(src, dict):
                self._append(str(src.get("label", "")), str(src.get("url", "")))
        row = QHBoxLayout()
        add = QPushButton("Ajouter")
        add.clicked.connect(lambda: self._append("", ""))
        rem = QPushButton("Supprimer")
        rem.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()))
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch(1)
        lay.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _append(self, label: str, url: str) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(label))
        self.table.setItem(r, 1, QTableWidgetItem(url))
        self.table.setCurrentCell(r, 0)

    def sources(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for r in range(self.table.rowCount()):
            label_item, url_item = self.table.item(r, 0), self.table.item(r, 1)
            label = label_item.text().strip() if label_item else ""
            url = url_item.text().strip() if url_item else ""
            if label or url:
                out.append({"label": label, "url": url})
        return out

    def accept(self) -> None:
        new = self.sources()
        if new != self.document.project.scientific_metadata.get("sources", []):
            self.document.push(SetProjectMetadata("sources", new))
        super().accept()

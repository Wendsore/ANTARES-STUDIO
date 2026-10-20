"""AST-05 (favoris déterministes et persistés), inventaire des ressources, métadonnées (SCI-08)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from antares_studio.app.library_dock import FAV_ROLE
from antares_studio.app.main_window import MainWindow
from antares_studio.app.provenance_dialog import LicenseInventoryDialog, ProvenanceDialog, SourcesDialog
from antares_studio.domain.model import AssetLicense
from antares_studio.resources.assets import import_asset

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot):  # type: ignore[no-untyped-def]
    w = MainWindow()
    qtbot.addWidget(w, before_close_func=lambda win: win.document.undo.mark_clean())
    w.resize(1400, 860)
    w.show()
    qtbot.waitExposed(w)
    return w


def _item(lst, fav_id: str):  # type: ignore[no-untyped-def]
    for i in range(lst.count()):
        if lst.item(i).data(FAV_ROLE) == fav_id:
            return lst.item(i)
    raise AssertionError(fav_id)


def test_ast05_favorites_filter_and_persist(window, qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = window.library
    _item(lib.objects, "objet:circle").setCheckState(Qt.CheckState.Checked)
    _item(lib.presets, "animation:orbit").setCheckState(Qt.CheckState.Checked)
    assert lib.favorites() == ["animation:orbit", "objet:circle"]
    assert window.settings.favorites() == ["animation:orbit", "objet:circle"]
    lib.fav_only.setChecked(True)
    assert not _item(lib.objects, "objet:circle").isHidden()
    assert _item(lib.objects, "objet:rect").isHidden()
    assert _item(lib.presets, "animation:appear").isHidden()
    lib.search.setText("cerc")
    assert not _item(lib.objects, "objet:circle").isHidden()
    lib.search.setText("rect")
    assert _item(lib.objects, "objet:circle").isHidden()
    lib.fav_only.setChecked(False)
    lib.search.setText("")
    assert not _item(lib.objects, "objet:rect").isHidden()
    # nouvelle fenêtre : favoris restaurés depuis les préférences
    w2 = MainWindow()
    qtbot.addWidget(w2, before_close_func=lambda win: win.document.undo.mark_clean())
    assert _item(w2.library.objects, "objet:circle").checkState() == Qt.CheckState.Checked
    assert _item(w2.library.objects, "objet:rect").checkState() == Qt.CheckState.Unchecked
    _item(w2.library.objects, "objet:circle").setCheckState(Qt.CheckState.Unchecked)
    assert window.settings.favorites() == ["animation:orbit"]
    w2.close()


def test_provenance_dialog_inventory_and_sources(window, qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    window.document.save(tmp_path / "Prov.antares")
    from PySide6.QtGui import QImage

    src = tmp_path / "fond.png"
    QImage(32, 32, QImage.Format.Format_RGB32).save(str(src))
    asset = import_asset(window.document, src, kind="image")
    qtbot.wait(20)
    assert window.library.assets.topLevelItemCount() == 1
    assert window.library.assets.topLevelItem(0).text(1) == "provenance manquante"
    # fiche de provenance : la licence CC BY coche l'attribution par défaut
    dlg = ProvenanceDialog(asset, window)
    qtbot.addWidget(dlg)
    dlg.author.setText("NASA")
    dlg.source.setText("https://images.nasa.gov/")
    dlg.license.setCurrentIndex(dlg.license.findData("CC-BY-4.0"))
    assert dlg.attribution.isChecked() and dlg.redistribution.isChecked()
    lic = dlg.result_license()
    assert lic == AssetLicense("NASA", "https://images.nasa.gov/", "CC-BY-4.0", True, True, lic.verified_on)
    from antares_studio.domain.commands import SetAssetLicense

    window.document.push(SetAssetLicense(asset.id, lic))
    qtbot.wait(20)
    assert window.library.assets.topLevelItem(0).text(1) == "complète"
    inv = LicenseInventoryDialog(window.document, window)
    qtbot.addWidget(inv)
    assert inv.table.rowCount() == 1 and inv.table.item(0, 3).text() == "NASA"
    assert "fond.png — NASA — CC BY 4.0" in inv.credits.toPlainText()
    # sources scientifiques depuis l'inspecteur (scène sélectionnée) : commande annulable
    window.document.set_selection([])
    qtbot.wait(20)
    assert window.inspector.sources_button.text() == "Sources… (0)"
    sd = SourcesDialog(window.document, window)
    qtbot.addWidget(sd)
    sd._append("CODATA — c", "https://physics.nist.gov/")
    sd.accept()
    assert window.document.project.scientific_metadata["sources"] == [
        {"label": "CODATA — c", "url": "https://physics.nist.gov/"}
    ]
    qtbot.wait(20)
    assert window.inspector.sources_button.text() == "Sources… (1)"
    window.act_undo.trigger()
    assert window.document.project.scientific_metadata["sources"] == []

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def pytest_configure(config):  # type: ignore[no-untyped-def]
    """Isole QSettings dans un dossier temporaire : les tests n'écrivent jamais les préférences réelles."""
    import tempfile

    from PySide6.QtCore import QSettings

    tmp = tempfile.mkdtemp(prefix="antares-qsettings-")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tmp)
    os.environ["ANTARES_TEST_SETTINGS"] = tmp

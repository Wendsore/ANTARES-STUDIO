"""Point d'entrée : ``antares-studio [projet.antares]``, ``--version``, ``--selftest``, ``--export``."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from antares_studio import __version__


def create_app(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("ANTARES Studio")
    app.setOrganizationName("Wendsore")
    app.setApplicationVersion(__version__)
    QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.France))
    return app  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    from antares_studio.app.cli import run_cli

    code = run_cli(argv[1:])
    if code is not None:
        return code
    app = create_app(argv)
    from PySide6.QtCore import QTimer

    from antares_studio.app.incident import install_exception_logger

    install_exception_logger()  # erreurs inattendues gardées pour le rapport d'incident (Aide)
    from antares_studio.app.main_window import MainWindow

    window = MainWindow()
    window.show()
    opened = False
    for arg in argv[1:]:
        p = Path(arg)
        if p.exists():
            opened = window.open_project_path(p)
            break
    if not opened and window.settings.show_welcome():
        QTimer.singleShot(0, window.show_welcome)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

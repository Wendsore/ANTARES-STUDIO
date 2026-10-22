# -*- mode: python ; coding: utf-8 -*-
"""Spécification PyInstaller d'ANTARES Studio (phase 9) — ``python packaging/build.py`` la pilote.

Mode « un dossier » (``--onedir``) : requis pour Qt (plugins, bibliothèques liées dynamiquement,
obligations LGPL : remplacement possible des bibliothèques Qt). Les plugins Qt sont collectés par le
hook PySide6 intégré à PyInstaller ≥ 6 (vérifié avec 6.22.3 ; la page Qt for Python sur PyInstaller
mentionne encore une limitation datée de mars 2021).
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
BUNDLED_FFMPEG = ROOT / "packaging" / "ffmpeg"  # optionnel : ffmpeg(.exe), ffprobe(.exe), LICENSE

datas = [
    (str(ROOT / "packaging" / "THIRD_PARTY_NOTICES.md"), "."),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "CHANGELOG.md"), "."),
]
# Ressources lues comme fichiers à l'exécution : aide (Markdown, images), icônes SVG, exemples, script
# Blender (exécuté par Blender, donc à livrer en .py et pas seulement dans l'archive Python).
datas += collect_data_files("antares_studio", includes=["py.typed", "resources/**/*"], excludes=["**/__pycache__/**"])
# ``collect_data_files`` ignore les .py : le script Blender est ajouté explicitement.
datas.append(
    (str(SRC / "antares_studio" / "resources" / "blender" / "planete.py"), "antares_studio/resources/blender")
)
binaries = []
if BUNDLED_FFMPEG.is_dir():
    for f in BUNDLED_FFMPEG.iterdir():
        if f.is_file():
            (binaries if f.suffix in ("", ".exe", ".dll") else datas).append((str(f), "bin"))

a = Analysis(
    [str(SRC / "antares_studio" / "app" / "main.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=["antares_studio.app.main_window", "antares_studio.app.cli", "PySide6.QtSvg"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtPdf",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "tkinter",
        "matplotlib",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ANTARES Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX a corrompu des binaires Qt par le passé (documentation PyInstaller) ; désactivé
    console=False,  # application fenêtrée ; --selftest/--export écrivent quand même sur stdout si présent
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ANTARES Studio",
)

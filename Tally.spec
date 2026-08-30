# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for Tally.app."""

import os

VERSION = "1.0.0"
ICON = os.path.join("assets", "Tally.icns")

analysis = Analysis(
    ["run_tally.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "watchdog.observers.fsevents",
        "watchdog.observers.polling",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pydoc_data",
        "PIL",
        "numpy",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Tally",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Tally",
)

app = BUNDLE(
    collect,
    name="Tally.app",
    icon=ICON if os.path.exists(ICON) else None,
    bundle_identifier="com.mattmorgan.tally",
    version=VERSION,
    info_plist={
        # A menu bar app: no Dock icon, no application menu.
        "LSUIElement": True,
        "CFBundleName": "Tally",
        "CFBundleDisplayName": "Tally",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "© 2026 Matt Morgan · MIT licence",
        "NSDesktopFolderUsageDescription": (
            "Tally counts the words in documents you choose from your Desktop."
        ),
        "NSDocumentsFolderUsageDescription": (
            "Tally counts the words in documents you choose from your Documents folder."
        ),
        "NSDownloadsFolderUsageDescription": (
            "Tally counts the words in documents you choose from your Downloads folder."
        ),
    },
)

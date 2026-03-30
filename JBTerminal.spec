# -*- mode: python ; coding: utf-8 -*-

import PyQt6
block_cipher = None

# Exclude Anaconda's Qt5 — we only need PyQt6 (Qt6)
_qt5_excludes = [
    'libQt5Core*', 'libQt5Gui*', 'libQt5Widgets*', 'libQt5DBus*',
    'libQt5Network*', 'libQt5Pdf*', 'libQt5PrintSupport*',
    'QtCore', 'QtDBus', 'QtGui', 'QtWidgets',  # Anaconda Qt5 frameworks
]

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('src/theme/neon_theme.qss', 'src/theme'),
    ],
    hiddenimports=[
        'pyte',
        'AppKit',
        'Foundation',
        'objc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide2', 'PySide6'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JBTerminal',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='JBTerminal',
)

app = BUNDLE(
    coll,
    name='JBTerminal.app',
    icon=None,
    bundle_identifier='com.jbterminal.app',
    info_plist={
        'CFBundleName': 'JBTerminal',
        'CFBundleDisplayName': 'JBTerminal',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleLocalizations': ['ko', 'en', 'ja', 'zh_CN'],
        'CFBundleDevelopmentRegion': 'ko',
    },
)

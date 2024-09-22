# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('Blue.ico', '.'), ('menu_helpers.py', '.'), ('table_helpers.py', '.'), ('theme_editor.py', '.'), ('theme_manager.py', '.'), ('opcode_editor.py', '.'), ('themes.json', '.'), ('re1_opcodes.json', '.'), ('re15_opcodes.json', '.'), ('re2_opcodes.json', '.'), ('re3_opcodes.json', '.')],
    hiddenimports=['menu_helpers', 'table_helpers', 'theme_editor', 'theme_manager', 'opcode_editor'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Blue.ico'],
)

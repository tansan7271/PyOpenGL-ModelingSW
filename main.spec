# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PyOpenGL Modeling Application
빌드 명령: pyinstaller main.spec
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),      # 아이콘, 사운드, 텍스처, 스카이돔
        ('datasets', 'datasets'),  # 미로, 아이템 데이터
    ],
    hiddenimports=[
        # PyQt5 멀티미디어
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        # PyOpenGL 관련
        'OpenGL.platform.win32',
        'OpenGL.arrays.numpymodule',
        'OpenGL.arrays.arraydatatype',
        'OpenGL.arrays.ctypesarrays',
        'OpenGL.arrays.ctypesparameters',
        'OpenGL.arrays.ctypespointers',
        'OpenGL.arrays.lists',
        'OpenGL.arrays.numbers',
        'OpenGL.arrays.strings',
        'OpenGL.converters',
        # NumPy
        'numpy',
        'numpy.core._methods',
        'numpy.lib.format',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ModelingApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있으면 여기에 경로 지정 (예: 'assets/app_icon.ico')
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ModelingApp',
)

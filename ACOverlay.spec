# -*- mode: python ; coding: utf-8 -*-
"""
AC Overlay PyInstaller 打包配置
优化版 - 减小EXE体积
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'keyboard',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大型库
        'matplotlib',
        'scipy',
        'pandas',
        'numpy',              # 本项目不需要numpy
        'tkinter',
        'PIL',                # 不需要图像处理
        'pystray',            # 使用Qt自带的托盘
        # 排除PyQt6不需要的模块
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.QtSql',
        'PyQt6.QtTest',
        'PyQt6.QtXml',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtQuickWidgets',
        'PyQt6.QtDesigner',
        'PyQt6.QtHelp',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'PyQt6.QtPdf',
        'PyQt6.QtPdfWidgets',
        'PyQt6.QtPositioning',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtSpatialAudio',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'PyQt6.QtTextToSpeech',
        'PyQt6.Qt3DCore',
        'PyQt6.Qt3DRender',
        'PyQt6.Qt3DInput',
        'PyQt6.Qt3DLogic',
        'PyQt6.Qt3DAnimation',
        'PyQt6.Qt3DExtras',
        'PyQt6.QtBluetooth',
        'PyQt6.QtDBus',
        'PyQt6.QtNfc',
        # 排除其他不需要的标准库
        'unittest',
        'xmlrpc',
        'pydoc',
        'doctest',
        'distutils',
        'lib2to3',
        'test',
        'setuptools',
        'pip',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 移除不需要的二进制文件
a.binaries = [x for x in a.binaries if not any([
    'Qt6WebEngine' in x[0],
    'Qt6Quick' in x[0],
    'Qt6Qml' in x[0],
    'Qt6Pdf' in x[0],
    'Qt6Multimedia' in x[0],
    'Qt6Network' in x[0],
    'Qt6Sql' in x[0],
    'Qt6Svg' in x[0],
    'Qt6Designer' in x[0],
    'Qt6Help' in x[0],
    'Qt6OpenGL' in x[0],
    'Qt6PrintSupport' in x[0],
    'Qt6Test' in x[0],
    'd3dcompiler' in x[0].lower(),      # DirectX编译器
    'opengl32sw' in x[0].lower(),        # 软件OpenGL
    'libcrypto' in x[0].lower(),         # SSL库（不需要网络）
    'libssl' in x[0].lower(),
])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ACOverlay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,               # 移除调试符号
    upx=True,                 # 使用UPX压缩
    upx_exclude=[
        'Qt6Core.dll',        # 这些DLL压缩后可能不稳定
        'Qt6Gui.dll',
        'Qt6Widgets.dll',
        'python*.dll',
    ],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以设置图标 icon='icon.ico'
)

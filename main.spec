# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("qt.conf", ".")] + collect_data_files("certifi"),
    hiddenimports=["qasync", "pymupdf", "sherpa_onnx", "pyaudiowpatch", "win32crypt"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["qt_icu_hook.py"],
    excludes=["tkinter", "matplotlib", "PySide6", "PyQt5", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="VoiceInterviewAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

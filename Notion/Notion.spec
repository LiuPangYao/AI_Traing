# -*- mode: python ; coding: utf-8 -*-
import os, sys
from PyInstaller.utils.hooks import collect_data_files
sys.path.insert(0, os.getcwd())
from personalnote import __version__   # 啟動畫面的預設文字要帶版號

datas = [('assets', 'assets')]
datas += collect_data_files('customtkinter')


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
splash = Splash(
    'assets/splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(140, 116),                 # 文字左下角（圖是 480×180；第二行的位置）
    text_size=11,
    text_color='#6e737d',
    # text_font 不設：Tk 預設字型會自動找系統的中文字型；名字有空格（Microsoft JhengHei UI）會讓啟動畫面的 Tcl 腳本掛掉，整個畫面變成空白 tk 視窗
    text_default='載入中…',
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    splash.binaries,
    [],
    name='Notion',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='build/version_info.txt',
    icon=['assets/icon.ico'],
)

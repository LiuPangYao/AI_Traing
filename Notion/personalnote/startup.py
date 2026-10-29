# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""開機自動啟動。

Windows：在「啟動」資料夾放一個捷徑（shell:startup），不碰登錄檔、不用管理員權限；
捷徑指向 Notion.bat（這樣 bat 裡的設定開機時也會生效）；沒有 bat 就指向程式本身。
Linux：~/.config/autostart/notion.desktop，指向 Notion.sh 或程式本身。
實際建檔的動作在 platform_.py。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from . import platform_


def shortcut_path() -> Path:
    return platform_.autostart_path()


def is_enabled() -> bool:
    return platform_.autostart_enabled()


def launch_target(launcher: Optional[Path]) -> tuple[str, str, str]:
    """回傳 (target, arguments, workdir)。
    有 .bat／.sh 就跑它（Windows 用 cmd 最小化視窗）；否則直接指向 exe 或 python -m personalnote。"""
    if launcher and Path(launcher).is_file():
        bat = Path(launcher).resolve()
        if platform_.IS_WIN:
            return (os.environ.get("ComSpec", "cmd.exe"), f'/c ""{bat}""', str(bat.parent))
        return (str(bat), "", str(bat.parent))
    if getattr(sys, "frozen", False):               # PyInstaller 打包後
        exe = Path(sys.executable).resolve()
        return (str(exe), "", str(exe.parent))
    py = Path(sys.executable)
    if platform_.IS_WIN:
        pyw = py.with_name("pythonw.exe")
        py = pyw if pyw.is_file() else py
    pkg_root = Path(__file__).resolve().parent.parent
    return (str(py), "-m personalnote", str(pkg_root))


def enable(launcher: Optional[Path]) -> Path:
    target, args, workdir = launch_target(launcher)
    return platform_.autostart_enable(target, args, workdir, "Notion 開機啟動")


def disable() -> None:
    platform_.autostart_disable()

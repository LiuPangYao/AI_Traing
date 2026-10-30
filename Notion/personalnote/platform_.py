# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""跟作業系統有關的東西都集中在這裡；其他模組不要直接碰 ctypes、explorer、PowerShell、os.startfile。

Windows 是主要平台（Peter 和同事都用），Linux 是第二平台：能開、能寫、能搜、能匯入匯出；
Linux 沒有的：加密（DPAPI 是 Windows 獨有，crypto.available() 回 False，程式自動存純文字並在設定裡說明）、
拖檔案進視窗（dropfiles 接的是 Windows 訊息）。要補的話在 crypto.py／dropfiles.py 各加 Linux 分支，不用動這裡。

這檔案在 Windows 上實測；Linux 分支寫完沒有機器可跑，第一次在 Linux 跑請先看 log。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
APP_DIR_NAME = "PersonalNote"      # 設定、log 放的資料夾名（沿用舊名，Windows 舊設定才接得上）


# ---- 路徑 ----
def set_ime_font(widget, family: str, size_pt: float) -> bool:
    """Windows 輸入法（注音選字）的組字視窗用 Tk 的字型大小：ImmSetCompositionFont（Peter：選字時字明顯比較小）。
    非 Windows 或沒有輸入法上下文就什麼都不做。"""
    if not IS_WIN:
        return False
    import ctypes
    from ctypes import wintypes
    try:
        hwnd = widget.winfo_id()
        imm = ctypes.windll.imm32
        imm.ImmGetContext.restype = ctypes.c_void_p
        imm.ImmGetContext.argtypes = [wintypes.HWND]
        imm.ImmReleaseContext.argtypes = [wintypes.HWND, ctypes.c_void_p]
        himc = imm.ImmGetContext(hwnd)
        if not himc:
            return False

        class LOGFONTW(ctypes.Structure):
            _fields_ = [("lfHeight", ctypes.c_long), ("lfWidth", ctypes.c_long), ("lfEscapement", ctypes.c_long),
                        ("lfOrientation", ctypes.c_long), ("lfWeight", ctypes.c_long), ("lfItalic", ctypes.c_byte),
                        ("lfUnderline", ctypes.c_byte), ("lfStrikeOut", ctypes.c_byte), ("lfCharSet", ctypes.c_byte),
                        ("lfOutPrecision", ctypes.c_byte), ("lfClipPrecision", ctypes.c_byte), ("lfQuality", ctypes.c_byte),
                        ("lfPitchAndFamily", ctypes.c_byte), ("lfFaceName", ctypes.c_wchar * 32)]
        lf = LOGFONTW()
        dpi = float(widget.winfo_fpixels("1i"))
        lf.lfHeight = -int(round(float(size_pt) * dpi / 72.0))
        lf.lfWeight = 400
        lf.lfCharSet = 1                      # DEFAULT_CHARSET
        lf.lfQuality = 5                      # CLEARTYPE_QUALITY
        lf.lfFaceName = str(family)[:31]
        imm.ImmSetCompositionFontW.argtypes = [ctypes.c_void_p, ctypes.POINTER(LOGFONTW)]
        ok = bool(imm.ImmSetCompositionFontW(himc, ctypes.byref(lf)))
        imm.ImmReleaseContext(hwnd, himc)
        return ok
    except Exception:
        return False


def data_dir() -> Path:
    """log 與救援檔的根：Windows %LOCALAPPDATA%\\PersonalNote（不漫遊，不會被網域同步到伺服器）；Linux ~/.local/state/PersonalNote。"""
    if IS_WIN:
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_DIR_NAME
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / APP_DIR_NAME


def config_dir(base: Optional[Path] = None) -> Path:
    """設定（note_dir.txt）、log、救援檔的根：Windows %APPDATA%\\PersonalNote；Linux ~/.config/PersonalNote。
    base 給測試用（假的 APPDATA）。"""
    if base is not None:
        return Path(base) / APP_DIR_NAME
    if IS_WIN:
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_DIR_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_DIR_NAME


def desktop_dir() -> Path:
    """使用者看得到的「桌面」。Windows 用 SHGetFolderPath（桌面被導到 OneDrive 也抓得到）；
    Linux 看 ~/.config/user-dirs.dirs 的 XDG_DESKTOP_DIR，沒有就 ~/Desktop，再沒有就家目錄。"""
    if IS_WIN:
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0 and buf.value:   # CSIDL_DESKTOPDIRECTORY
                return Path(buf.value)
        except Exception:
            pass
        home = Path(os.environ.get("USERPROFILE", Path.home()))
        return home / "Desktop"
    home = Path.home()
    try:
        for line in (home / ".config" / "user-dirs.dirs").read_text(encoding="utf-8").splitlines():
            if line.startswith("XDG_DESKTOP_DIR="):
                p = Path(os.path.expandvars(line.split("=", 1)[1].strip().strip('"')))
                if p.is_dir():
                    return p
    except OSError:
        pass
    d = home / "Desktop"
    return d if d.is_dir() else home


# ---- 開檔、開資料夾 ----
def open_path(path: str | Path) -> None:
    """用系統預設程式開檔案／網址／資料夾。"""
    if IS_WIN:
        os.startfile(str(path))                      # noqa: S606
    elif IS_MAC:
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_folder(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)
    if IS_WIN:
        subprocess.Popen(["explorer", str(path)])
    else:
        open_path(path)


# ---- 字型 ----
def ui_font_family() -> str:
    """畫面字型。Windows 微軟正黑體；Linux Noto Sans CJK TC（沒裝的話 Tk 會自己退回預設字型，只是中文可能變豆腐）。"""
    return "Microsoft JhengHei UI" if IS_WIN else ("PingFang TC" if IS_MAC else "Noto Sans CJK TC")


def mono_font_family() -> str:
    return "Consolas" if IS_WIN else ("Menlo" if IS_MAC else "DejaVu Sans Mono")


# ---- 視窗圖示 ----
def set_window_icon(win, ico: Path, png: Path) -> None:
    """Windows 吃 .ico（iconbitmap）；Linux／mac 不吃，用 PNG 走 iconphoto。圖要留參考，不然 Tk 會把它收掉。"""
    try:
        if IS_WIN and ico.is_file():
            win.iconbitmap(str(ico))
        elif png.is_file():
            import tkinter as tk
            win._icon_img = tk.PhotoImage(file=str(png))
            win.iconphoto(True, win._icon_img)
    except Exception:
        pass


# ---- 跳一個框（還沒有 Tk 視窗時用）----
def message_box(title: str, text: str, error: bool = False) -> None:
    if IS_WIN:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10 if error else 0x40)
        return
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        (messagebox.showerror if error else messagebox.showinfo)(title, text)
        root.destroy()
    except Exception:
        print(f"{title}: {text}", file=sys.stderr if error else sys.stdout)


# ---- 單一執行個體 ----
_mutex_handle = None
_lock_file = None


def single_instance(window_title: str) -> bool:
    """第二個程式開起來時回 False（Windows 順便把已開的視窗叫到前面）。NOTE_ALLOW_MULTI=1 一律 True（測試用）。"""
    if os.environ.get("NOTE_ALLOW_MULTI") == "1":
        return True
    global _mutex_handle, _lock_file
    if IS_WIN:
        import ctypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)   # use_last_error：錯誤碼不會被中間的呼叫洗掉
        _mutex_handle = k32.CreateMutexW(None, False, "Local\\PersonalNote_single_instance")   # handle 留著到程式結束
        if ctypes.get_last_error() != 183:                      # ERROR_ALREADY_EXISTS
            return True
        u32 = ctypes.windll.user32
        hwnd = u32.FindWindowW("TkTopLevel", window_title)      # 指定 Tk 的視窗類別，檔案總管開著同名資料夾不會撞到
        if hwnd:
            u32.ShowWindow(hwnd, 9)                             # SW_RESTORE：縮小的也叫回來
            u32.SetForegroundWindow(hwnd)
        return False
    # Linux／mac：鎖檔。程式活著就鎖著，第二個鎖不到就退出；當機鎖會自動放掉（flock 跟程序綁在一起）
    try:
        import fcntl
        d = config_dir(); d.mkdir(parents=True, exist_ok=True)
        _lock_file = open(d / "instance.lock", "w")
        fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False
    except Exception:
        return True                                              # 鎖不了就不擋，寧可多開也不要開不了


# ---- 開機啟動 ----
def autostart_path() -> Path:
    if IS_WIN:
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Notion.lnk"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart" / "notion.desktop"


AUTOSTART_SUPPORTED = not IS_WIN     # Windows 不做（Peter 決定：公司機器常擋 PowerShell／COM，讓使用者自己把 Notion.bat 捷徑放進 shell:startup）


def startup_folder() -> Path:
    """Windows 的「啟動」資料夾（shell:startup）；設定面板給使用者一鍵開，自己把 Notion.bat 的捷徑拖進去。"""
    return autostart_path().parent


def autostart_enable(target: str, args: str, workdir: str, description: str) -> Path:
    """Linux：寫 ~/.config/autostart/notion.desktop。Windows 不支援（見 AUTOSTART_SUPPORTED）。"""
    if not AUTOSTART_SUPPORTED:
        raise RuntimeError("Windows 請自己設定：按 Win+R 輸入 shell:startup，把 Notion.bat 的捷徑拖進去。")
    p = autostart_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if False:
        pass
    else:
        exec_line = f'"{target}" {args}'.strip()
        p.write_text("[Desktop Entry]\nType=Application\nName=Notion\n"
                     f"Comment={description}\nExec={exec_line}\nPath={workdir}\nTerminal=false\nX-GNOME-Autostart-enabled=true\n",
                     encoding="utf-8")
    return p


def autostart_disable() -> None:
    p = autostart_path()
    if p.is_file():
        p.unlink()


def autostart_enabled() -> bool:
    return autostart_path().is_file()


def google_drive_dir():
    """Google Drive 桌面版的同步資料夾（有裝才有）：Windows 是某個磁碟機的「My Drive」或家目錄下的 Google Drive；
    Linux／macOS 常見是 ~/Google Drive。找不到回 None（呼叫端讓使用者自己選）。"""
    from pathlib import Path
    home = Path.home()
    cands = [home / "Google Drive" / "My Drive", home / "Google Drive", home / "My Drive", home / "GoogleDrive"]
    if IS_WIN:
        import string
        for letter in string.ascii_uppercase[6:]:            # G: 以後常是 Drive 的虛擬磁碟
            cands.append(Path(f"{letter}:/My Drive"))
            cands.append(Path(f"{letter}:/我的雲端硬碟"))
    for c in cands:
        try:
            if c.is_dir():
                return c
        except OSError:
            continue
    return None

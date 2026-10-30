# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""拖檔案到視窗（只有 Windows）。不裝 tkinterdnd2，直接接 Windows 的 WM_DROPFILES 訊息。

做法：DragAcceptFiles 告訴系統「這個視窗收檔」；用 SetWindowLongPtrW 把視窗的訊息處理函式換成自己的，
收到 WM_DROPFILES 就用 DragQueryFileW 取出檔名放進 _pending，其餘訊息原封不動丟回 Tk 原本的處理函式。
Tk 這邊每 POLL_MS 毫秒（after 排程）來 _pending 拿檔名，再呼叫 on_files。

注意（2026-10-30 真的拖檔就當掉，查出來的）：
- 回呼是在 Tcl 的事件迴圈裡被 Windows 叫的。**裡面連 widget.after 都不能叫**：_tkinter 每次呼叫完會把它記的
  執行緒狀態（tcl_tstate）清掉，回到 Tcl 之後下一個 Python 回呼就 PyEval_RestoreThread(NULL)，程式直接被
  C 執行階段終止（事件檢視器：ucrtbase 0xC0000409），log 與 crash.log 都來不及寫。
  測試用的 simulate_drop 是程序內 SendMessage、不經過事件迴圈，所以以前測不出來；post_drop（PostMessage）才會。
  所以回呼裡只做 ctypes 與 list.append，交給 Tk 的 after 輪詢來處理。
- ctypes 的回呼物件要留著參考（_keep），被回收的話下一個訊息進來程式就直接當掉。
- 以系統管理員身分跑的程式收不到一般檔案總管拖來的檔（Windows 的 UIPI 擋掉），這不是 bug。
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import Callable

WM_DROPFILES = 0x0233
GWLP_WNDPROC = -4
POLL_MS = 100
_keep: dict = {}                      # hwnd → (新 wndproc, 舊 wndproc 位址, on_files)
_pending: dict[int, list[Path]] = {}  # hwnd → 收到、還沒交給 Tk 的檔名

if sys.platform == "win32":
    from ctypes import wintypes
    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM)


def enable(widget, on_files: Callable[[list[Path]], None]) -> bool:
    """讓 widget 所在的視窗收拖進來的檔。成功回 True；非 Windows 或失敗回 False（程式照常跑，只是不能拖）。"""
    if sys.platform != "win32":
        return False
    u32, shell = ctypes.windll.user32, ctypes.windll.shell32
    u32.SetWindowLongPtrW.restype = ctypes.c_void_p
    u32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    u32.CallWindowProcW.restype = ctypes.c_longlong
    u32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
    shell.DragQueryFileW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
    shell.DragQueryFileW.restype = ctypes.c_uint
    shell.DragFinish.argtypes = [ctypes.c_void_p]
    shell.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]

    hwnd = widget.winfo_id()                      # Tk 收滑鼠訊息的那層視窗（不是外框）
    if hwnd in _keep:
        return True

    def proc(h, msg, wp, lp):
        if msg == WM_DROPFILES:                   # 這裡只能 ctypes 與 append，不能碰 Tk（見模組說明）
            paths: list[Path] = []
            try:
                n = shell.DragQueryFileW(wp, 0xFFFFFFFF, None, 0)
                for i in range(n):
                    ln = shell.DragQueryFileW(wp, i, None, 0)
                    buf = ctypes.create_unicode_buffer(ln + 1)
                    shell.DragQueryFileW(wp, i, buf, ln + 1)
                    paths.append(Path(buf.value))
            finally:
                shell.DragFinish(wp)
            if paths:
                _pending.setdefault(h, []).extend(paths)
            return 0
        return u32.CallWindowProcW(_keep[h][1], h, msg, wp, lp)

    cb = WNDPROC(proc)
    old = u32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, ctypes.cast(cb, ctypes.c_void_p).value)
    if not old:
        return False
    _keep[hwnd] = (cb, old, on_files)
    shell.DragAcceptFiles(hwnd, True)

    def poll():
        if not widget.winfo_exists():
            return
        deliver(hwnd)
        widget.after(POLL_MS, poll)

    widget.after(POLL_MS, poll)
    return True


def deliver(hwnd: int) -> bool:
    """把這個視窗收到、還沒處理的檔名交給 on_files。有東西回 True。只能從 Tk 這邊（after、update）呼叫。"""
    paths = _pending.pop(hwnd, None)
    if not paths or hwnd not in _keep:
        return False
    _keep[hwnd][2](paths)
    return True


def _make_hdrop(paths: list[Path]):
    k32 = ctypes.windll.kernel32
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    names = "".join(str(p) + "\0" for p in paths) + "\0"
    data = ctypes.create_unicode_buffer(names, len(names))
    header = 20                                   # DROPFILES：pFiles(4) + pt(8) + fNC(4) + fWide(4)
    size = header + ctypes.sizeof(data)
    h = k32.GlobalAlloc(0x0042, size)             # GMEM_MOVEABLE | GMEM_ZEROINIT
    p = k32.GlobalLock(h)
    ctypes.memmove(p, ctypes.byref(ctypes.c_uint(header)), 4)
    ctypes.memmove(p + 16, ctypes.byref(ctypes.c_int(1)), 4)       # fWide = 1
    ctypes.memmove(p + header, data, ctypes.sizeof(data))
    k32.GlobalUnlock(h)
    return h


def simulate_drop(widget, paths: list[Path]) -> None:
    """測試用：假裝檔案總管把這些檔拖到視窗上（組一個 HDROP 丟 WM_DROPFILES 給它），馬上交給 on_files。"""
    u32 = ctypes.windll.user32
    u32.SendMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    h = _make_hdrop(paths)
    u32.SendMessageW(widget.winfo_id(), WM_DROPFILES, h, None)     # DragFinish 會釋放 h
    deliver(widget.winfo_id())


def post_drop(widget, paths: list[Path]) -> None:
    """測試用，跟真的拖放一樣走訊息佇列（PostMessage）：要 widget.update() 幾次、等過 POLL_MS 之後才會處理。
    2026-10-30 的當機只有這條路會重現，ui_checks 用這個。"""
    u32 = ctypes.windll.user32
    u32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    u32.PostMessageW(widget.winfo_id(), WM_DROPFILES, _make_hdrop(paths), None)

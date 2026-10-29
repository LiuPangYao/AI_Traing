# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""拖檔案到視窗（只有 Windows）。不裝 tkinterdnd2，直接接 Windows 的 WM_DROPFILES 訊息。

做法：DragAcceptFiles 告訴系統「這個視窗收檔」；用 SetWindowLongPtrW 把視窗的訊息處理函式換成自己的，
收到 WM_DROPFILES 就用 DragQueryFileW 取出檔名，其餘訊息原封不動丟回 Tk 原本的處理函式。

注意：
- 回呼是在 Windows 訊息裡被叫的，不要在裡面直接動 Tk；先收齊檔名，用 widget.after(0, …) 排到事件迴圈再處理。
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
_keep: dict = {}          # hwnd → (新 wndproc, 舊 wndproc 位址)

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
        if msg == WM_DROPFILES:
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
                widget.after(0, lambda: on_files(paths))
            return 0
        return u32.CallWindowProcW(_keep[h][1], h, msg, wp, lp)

    cb = WNDPROC(proc)
    old = u32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, ctypes.cast(cb, ctypes.c_void_p).value)
    if not old:
        return False
    _keep[hwnd] = (cb, old)
    shell.DragAcceptFiles(hwnd, True)
    return True


def simulate_drop(widget, paths: list[Path]) -> None:
    """測試用：假裝檔案總管把這些檔拖到視窗上（組一個 HDROP 丟 WM_DROPFILES 給它）。"""
    k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u32.SendMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
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
    u32.SendMessageW(widget.winfo_id(), WM_DROPFILES, h, None)     # DragFinish 會釋放 h

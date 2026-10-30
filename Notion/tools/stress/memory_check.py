# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""記憶體檢查：開真視窗（螢幕外），反覆開筆記、打記號、貼圖、重畫左欄、換語言重畫，量 RSS 有沒有一直長。
用法：python tools/stress/memory_check.py [回合數=150]
判定：暖身（前 20 回）之後到結束，RSS 增加超過 LIMIT_MB 就 FAIL（表示有東西沒放掉）。"""
from __future__ import annotations

import ctypes
import os
import pathlib
import sys
import tempfile
import time
from ctypes import wintypes
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["NOTE_ALLOW_MULTI"] = "1"; os.environ["NOTE_UPDATE_CHECK"] = "0"; os.environ["NOTE_TOUR"] = "0"

LIMIT_MB = 40


class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def rss_mb() -> float:
    k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
    if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
        raise OSError("GetProcessMemoryInfo failed")
    return pmc.WorkingSetSize / 1e6


def main() -> int:
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    from PIL import Image
    from personalnote.config import Settings
    from personalnote.storage import NoteStore, NoteId
    from personalnote.ui.main_window import MainWindow
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="pn_mem_"))
    s = Settings.load(["--note-dir", str(tmp / "n")], env={}, appdata=tmp / "a")
    st = NoteStore(tmp / "n", encrypt=False)
    win = MainWindow(s, st); win.geometry("720x640+3000+3000"); win.update(); time.sleep(0.3); win.update()
    today = date.today()
    text = "# 記憶體 {i}\n==重點== !!紅字!! **粗體** #標籤 https://example.com\n- [ ] 待辦\n```\necho {i}\n```\n" + "字" * 400 + "\n"
    img = Image.new("RGB", (320, 200), (120, 160, 220))
    samples = []
    t0 = time.time()
    for i in range(rounds):
        win.new_note(today); win.editor.set_text(text.format(i=i)); win.editor.flush(); win.update()
        if i % 10 == 0:
            win.paste_image(img); win.editor.flush(); win.update()
        win.open_note(NoteId(today, 1)); win.update()
        win._refresh_sidebar(); win.update()
        if i % 25 == 24:
            win.rebuild_ui(); win.update()
            win.open_settings(); win.update(); win._settings_panel.destroy(); win.update()
        if i in (0, 19) or i % 25 == 24:
            samples.append((i + 1, rss_mb()))
            print(f"回合 {i + 1:4d}  RSS {samples[-1][1]:.1f} MB")
    end = rss_mb(); samples.append((rounds, end))
    warm = next(v for n, v in samples if n >= 20)
    grow = end - warm
    print(f"暖身後 {warm:.1f} MB → 結束 {end:.1f} MB，增加 {grow:.1f} MB，{rounds} 回合，{time.time() - t0:.0f} 秒")
    win.destroy()
    print("MEMORY CHECK:", "PASS" if grow < LIMIT_MB else f"FAIL（超過 {LIMIT_MB} MB）")
    return 0 if grow < LIMIT_MB else 1


if __name__ == "__main__":
    sys.exit(main())

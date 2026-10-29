# -*- coding: utf-8 -*-
# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""大量資料：1500 天 × 2 張、120 張圖、中英文混合。量啟動、切筆記、搜尋、左欄重畫的時間與記憶體。
跑法：python -X utf8 tools/stress/big_data.py [--days 1500]。門檻寫在最後的 CHECK。"""
import argparse, ctypes, pathlib, shutil, sys, tempfile, time
from ctypes import wintypes
from datetime import date, timedelta
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from PIL import Image
from personalnote import applog
applog.setup()          # 跟真的程式一樣寫 log，看門狗倒堆疊才有地方寫
from personalnote.config import Settings
from personalnote.storage import NoteStore, NoteId
from personalnote.ui.main_window import MainWindow

ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=1500); ns = ap.parse_args()


def rss_mb() -> float:
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
    fn = ctypes.windll.psapi.GetProcessMemoryInfo
    fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    fn.restype = wintypes.BOOL
    k32 = ctypes.windll.kernel32
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    ok = fn(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return pmc.WorkingSetSize / 1e6 if ok else -1.0


tmp = pathlib.Path(tempfile.gettempdir()) / "pn_stress_big"
shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
store = NoteStore(tmp, encrypt=True)
today = date.today()
t0 = time.perf_counter()
ZH = "今天開會討論排程參數，權重 15 要不要調到 20。記得問廠商電梯狀態機。"
EN = "Meeting about scheduler weights; consider raising the cost weight from 15 to 20. Ask the vendor about the elevator state machine. Supercalifragilisticexpialidocious_long_identifier_without_spaces_0123456789"
for i in range(ns.days):
    d = today - timedelta(days=i)
    store.save(store.next_id(d), f"# 第 {i} 天 / Day {i}\n{ZH}\n{EN}\n")
    store.save(store.next_id(d), f"second note {i}\n- item\n- 項目\n")
for k in range(120):
    im = Image.new("RGB", (1200 + k, 700), (k % 255, 100, 150)); p = tmp / "attachments" / f"img{k}.png"; im.save(p)
    store.save(NoteId(today - timedelta(days=k), 3), f"# 圖 {k}\n[img{k}.png](attachments/img{k}.png)\n")
gen = time.perf_counter() - t0
print(f"產生 {ns.days*2+120} 張（含 120 張圖）: {gen:.1f} s")

st = Settings.load(["--note-dir", str(tmp)], env={}, appdata=tmp / "ad")
t0 = time.perf_counter(); win = MainWindow(st, store); win.geometry('+3000+3000'); win.update(); startup = time.perf_counter() - t0  # OFFSCREEN：視窗放螢幕外
m0 = rss_mb()
t0 = time.perf_counter()
for i in range(50):
    win.open_note(NoteId(today - timedelta(days=i), 1)); win.update()
switch = (time.perf_counter() - t0) / 50
t0 = time.perf_counter()
for k in range(30):
    win.open_note(NoteId(today - timedelta(days=k), 3)); win.update()
img_switch = (time.perf_counter() - t0) / 30
t0 = time.perf_counter()
for kw in ("電梯", "elevator", "Day 7", "2026-", "沒有這個字"):
    win._on_search(kw); win.update()
search = (time.perf_counter() - t0) / 5
win._on_search("")
t0 = time.perf_counter(); win._refresh_sidebar(); win.update(); refresh = time.perf_counter() - t0
m1 = rss_mb()
# 記憶體：再切 300 次看會不會一直漲
for i in range(300):
    win.open_note(NoteId(today - timedelta(days=i % 120), 3 if i % 3 == 0 else 1))
    if i % 10 == 0: win.update()      # 要 pump 事件，不然看門狗會把測試迴圈當成卡死
win.update(); m2 = rss_mb()
win._on_close()
print(f"啟動 {startup:.2f} s | 切筆記 {switch*1000:.0f} ms | 切有圖的 {img_switch*1000:.0f} ms | 搜尋 {search*1000:.0f} ms | 左欄重畫 {refresh*1000:.0f} ms")
print(f"記憶體 開窗 {m0:.0f} MB → 操作後 {m1:.0f} MB → 再切 300 次 {m2:.0f} MB")
ok = startup < 8 and switch < 0.5 and img_switch < 1.0 and search < 4 and refresh < 0.6 and (m2 - m1) < 150
print("CHECK:", "PASS" if ok else "FAIL（門檻：啟動<8s 切<500ms 圖<1s 搜<4s(第一次要解密全部) 左欄<600ms 300次切換記憶體漲<150MB）")
sys.exit(0 if ok else 1)

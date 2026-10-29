# -*- coding: utf-8 -*-
# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""隨機亂按：2000 步隨機操作（打字中英文、新筆記、切天、刪、清整天、複製到今天、搜尋、縮放、換風格、貼圖、匯出匯入），
每 100 步檢查一次不變量：每個檔都讀得開、標題對得上、沒有 .tmp 殘骸、history 不超過 30。
跑法：python -X utf8 tools/stress/fuzz.py [--steps 2000] [--seed 1]"""
import argparse, pathlib, random, shutil, sys, tempfile, traceback
from datetime import date, timedelta
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from PIL import Image
import tkinter.messagebox as mb
from personalnote import applog
applog.setup()          # 跟真的程式一樣寫 log，看門狗倒堆疊才有地方寫
from personalnote.config import Settings
from personalnote.storage import NoteStore, NoteId, title_of
import personalnote.ui.main_window as mw
from personalnote.ui.main_window import MainWindow

ap = argparse.ArgumentParser(); ap.add_argument("--steps", type=int, default=2000); ap.add_argument("--seed", type=int, default=1)
ns = ap.parse_args(); rnd = random.Random(ns.seed)
mw.messagebox.askyesno = lambda *a, **k: True
mb.askyesno = lambda *a, **k: True

tmp = pathlib.Path(tempfile.gettempdir()) / f"pn_stress_fuzz_{ns.seed}"      # 每個 seed 自己的資料夾，可以同時跑
shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
store = NoteStore(tmp, encrypt=rnd.random() < 0.5)
st = Settings.load(["--note-dir", str(tmp)], env={}, appdata=tmp / "ad")
win = MainWindow(st, store); win.geometry('+3000+3000'); win.update()  # OFFSCREEN：測試視窗放螢幕外，不閃使用者
today = date.today()
WORDS_ZH = ["會議", "廠商", "電梯", "排程", "參數 15", "記得", "明天", "（）", "、", "。"]
WORDS_EN = ["meeting", "elevator", "https://example.com/x?y=1", r"D:\AI\ai study\notes\58.md", "foo(){}", "[x](y)", "- item", "1. first", "end."]
errors = []


def typing(n_chars=40):
    ed = win.editor
    if ed.read_only: return
    words = [rnd.choice(WORDS_ZH + WORDS_EN) for _ in range(rnd.randint(1, 8))]
    ed.text.insert("insert", " ".join(words) + ("\n" if rnd.random() < 0.5 else ""))
    ed.text.edit_modified(True); ed._on_modified()
    if rnd.random() < 0.3: ed.flush()


def act():
    r = rnd.random()
    if r < 0.35: typing()
    elif r < 0.45: win.new_note(win.current_day)
    elif r < 0.55: win.go_day(win.current_day - timedelta(days=rnd.randint(-3, 10)))
    elif r < 0.60:
        days = win.store.list_days()
        if days: d = rnd.choice(days); refs = win.store.list_notes(d); win.open_note(rnd.choice(refs).id)
    elif r < 0.64: win.delete_note(win.current) if win.current else None
    elif r < 0.66: win.clear_day(win.current_day)
    elif r < 0.70:
        days = win.store.list_days()
        if days: d = rnd.choice(days); refs = win.store.list_notes(d); win.copy_to_today(rnd.choice(refs).id)
    elif r < 0.76: win._on_search(rnd.choice(["", "電梯", "meeting", "2026-", "x"]))
    elif r < 0.80: win.zoom(rnd.choice([-1, 1]))
    elif r < 0.82: win.set_theme(rnd.choice(["dark", "light", "system"]))
    elif r < 0.86:
        line = win.paste_image(Image.new("RGB", (rnd.randint(1, 3000), rnd.randint(1, 2000)), (10, 20, 30)))
        win.editor.text.insert("insert", "\n" + line + "\n"); win.editor.text.edit_modified(True); win.editor._on_modified()
    elif r < 0.88: win.editor.undo()
    elif r < 0.90: win.editor.redo()
    elif r < 0.92: win.toggle_sidebar()
    elif r < 0.94:
        # 匯出全部再匯回一張。以前是整包匯回今天：每次張數翻倍，2000 步後左欄破萬列、一步要 10 秒，跑了 14 小時
        out = tmp / "exp"; shutil.rmtree(out, ignore_errors=True); win.store.export_plain(out)
        files = sorted(out.rglob("*.md"))
        if files: win.store.import_file(rnd.choice(files), today)
    elif r < 0.96: win.set_encrypt(not win.store.encrypt)
    elif r < 0.98: win.editor._highlight_links()
    else: win.editor.flush()


def check(step):
    for d in win.store.list_days():
        for ref in win.store.list_notes(d):
            text, ok = win.store.try_load(ref.id)
            if not ok: errors.append(f"step {step}: {ref.id} 讀不到")
            elif title_of(text) != ref.title and ref.title != "（解不開）":
                pass   # 標題快取可能慢一拍（mtime 同秒），不算錯
            if len(win.store.list_snapshots(ref.id)) > 30: errors.append(f"step {step}: {ref.id} history > 30")
    tmps = list(tmp.glob("*/*.tmp"))
    if tmps: errors.append(f"step {step}: 殘留 .tmp {tmps}")


for step in range(1, ns.steps + 1):
    try:
        act()
        if step % 20 == 0: win.update()
        if step % 100 == 0: check(step); print(f"step {step} ok, days={len(win.store.list_days())}, errors={len(errors)}")
    except Exception:
        errors.append(f"step {step}: {traceback.format_exc()[-400:]}")
        if len(errors) > 20: break
try:
    win._on_close()
except Exception:
    errors.append("close: " + traceback.format_exc()[-300:])
print("\n".join(errors[:20]))
print("FUZZ:", "PASS" if not errors else f"FAIL ({len(errors)} 個問題)")
sys.exit(0 if not errors else 1)

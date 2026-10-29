# -*- coding: utf-8 -*-
# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""六個角色在真視窗上走一遍（大學生、研究生、上班族、主管、試務人員、開發人員）。
跑法：python -X utf8 tools/stress/personas.py <報告檔>。會開關視窗幾次，跑的時候別碰滑鼠。
每步是 (名稱, 函式)；例外會被接住寫進報告，最後印 BUGS 數。"""
import sys, os, tempfile, pathlib, shutil, traceback, json
from datetime import date, timedelta
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from personalnote import applog
applog.setup()          # 跟真的程式一樣寫 log，看門狗倒堆疊才有地方寫
from personalnote.config import Settings
from personalnote.storage import NoteStore, NoteId
from personalnote.ui.main_window import MainWindow

OUT = pathlib.Path(sys.argv[1])
report = []
def ok(msg): report.append(("OK", msg))
def bad(msg): report.append(("BUG", msg))
def note(msg): report.append(("NOTE", msg))

def type_into(win, title, body):
    """Simulate a user typing: set title/body then let autosave flush."""
    win.editor.title.delete(0, "end")
    if title: win.editor.title.insert(0, title)
    win.editor._on_title_changed()
    win.editor.text.delete("1.0", "end"); win.editor.text.insert("1.0", body)
    win.editor.text.edit_modified(True); win.editor._on_modified()
    win.update(); win.editor.flush(); win.update()

def run_persona(name, steps):
    tmp = pathlib.Path(tempfile.gettempdir()) / f"pn_persona_{name}"
    shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
    st = Settings.load(["--note-dir", str(tmp), "--theme", "dark"], env={}, appdata=tmp / "appdata")
    store = NoteStore(tmp, encrypt=True)
    win = MainWindow(st, store)
    win.geometry('+3000+3000'); win.update()  # OFFSCREEN：測試視窗放螢幕外
    try:
        for label, fn in steps:
            try:
                fn(win, store, tmp); win.update()
                ok(f"[{name}] {label}")
            except Exception as e:
                bad(f"[{name}] {label}: {e}\n{traceback.format_exc()[-600:]}")
    finally:
        try: win._on_close()
        except Exception as e: bad(f"[{name}] 關閉: {e}")
    return tmp

today = date.today()
def d(n): return today - timedelta(days=n)

# ---------- a. 大學生：課表、作業、社團，很多短筆記、常用清單 ----------
def student_steps():
    def s1(win, store, tmp):
        type_into(win, "", "1. 微積分作業 第 3 章\n2. 英文報告 1000 字\n3. 社團 19:00 練習")
        assert store.list_notes(today)[0].title == "微積分作業 第 3 章", store.list_notes(today)
    def s2(win, store, tmp):
        win.new_note(today); type_into(win, "打工", "週五 18-22 便利商店\n老闆 LINE: https://line.me/ti/p/abc")
        assert len(store.list_notes(today)) == 2
    def s3(win, store, tmp):   # 昨天的待辦抄到今天
        y = d(1); store.save(store.next_id(y), "# 昨天\n1. 借書 還沒做\n2. 問助教")
        win._refresh_sidebar(); win.copy_to_today(NoteId(y, 1))
        assert len(store.list_notes(today)) == 3 and store.load(win.current) .startswith("# 昨天")
    def s4(win, store, tmp):   # 搜尋
        win._on_search("助教"); groups = store.search("助教")
        assert today in groups and d(1) in groups, groups
        win._on_search("")
    def s5(win, store, tmp):   # Enter 接清單：模擬游標在第 1 行尾按 Enter
        win.open_note(NoteId(today, 1)); win.editor.text.mark_set("insert", "1.end"); r = win.editor._on_return()
        assert r == "break" and win.editor.text.get("2.0", "2.end") == "2. ", repr(win.editor.text.get("1.0", "end"))
        win.editor.set_text(store.load(NoteId(today, 1)))  # 還原
    def s6(win, store, tmp):   # 清掉今天其中一張
        win.delete_note(NoteId(today, 2)); assert len(store.list_notes(today)) == 2
        assert list((tmp / ".app" / "trash").iterdir())
    def s7(win, store, tmp):   # Ctrl+滾輪縮放 10 次不超界
        for _ in range(60): win.zoom(1)
        assert win.settings.font_size == 48
        for _ in range(60): win.zoom(-1)
        assert win.settings.font_size == 8
        win.zoom(7)
    return [("清單筆記", s1), ("第二張含網址", s2), ("昨天抄到今天", s3), ("搜尋", s4), ("Enter 接清單", s5), ("刪一張", s6), ("縮放極限", s7)]

# ---------- b. 研究生：長筆記、附件 PDF、論文連結、跨很多天 ----------
def grad_steps():
    def g1(win, store, tmp):
        for i in range(1, 15):
            store.save(store.next_id(d(i)), f"# 實驗 day-{i}\n參數 lr=1e-{i%5} batch={2**(i%6)}\n結果見 D:\\lab\\run{i}.csv")
        win._refresh_sidebar(); assert len(store.list_days()) == 14
    def g2(win, store, tmp):   # 附件
        pdf = tmp / "paper.pdf"; pdf.write_bytes(b"%PDF-1.4 fake")
        win.go_day(today); rel = store.add_attachment(pdf)
        win.editor.insert_at_cursor(f"[paper.pdf]({rel.as_posix()})\n"); win.editor._on_modified(); win.editor.text.edit_modified(True); win.editor._on_modified()
        win.editor.flush(); txt = store.load(win.current)
        assert "[paper.pdf](attachments/paper.pdf)" in txt, txt
        assert store.resolve("attachments/paper.pdf").is_file()
    def g3(win, store, tmp):   # 長文 2000 行
        type_into(win, "長文", "\n".join(f"第 {i} 行 https://arxiv.org/abs/2401.{i:05d}" for i in range(2000)))
        assert len(store.load(win.current)) > 50000
    def g4(win, store, tmp):   # 前一天後一天連續切 30 次
        for _ in range(30): win.go_day(d(1) if win.current_day == today else today)
    def g5(win, store, tmp):   # 匯出純文字
        n = store.export_plain(tmp / "export"); assert n >= 15, n
        assert (tmp / "export" / d(3).isoformat() / "001.md").read_text(encoding="utf-8").startswith("# 實驗")
    def g6(win, store, tmp):   # 關加密再開
        win.set_encrypt(False); assert all(p.suffix == ".md" for p in (tmp / d(2).isoformat()).iterdir())
        win.set_encrypt(True);  assert all(p.suffix == ".note" for p in (tmp / d(2).isoformat()).iterdir())
    return [("14 天資料", g1), ("插 PDF 附件", g2), ("2000 行長文", g3), ("來回切天", g4), ("匯出", g5), ("加密開關", g6)]

# ---------- c. 上班族：每天開機、昨天待辦、會議連結、清掉舊的 ----------
def worker_steps():
    def w1(win, store, tmp):
        type_into(win, "今日待辦", "- 09:30 站立會議 https://teams.microsoft.com/l/meetup-join/xyz\n- 回信給供應商\n- 報帳")
    def w2(win, store, tmp):   # 第二次開機：關掉重開要回到今天
        win._on_close.__func__  # just ensure exists
        state = json.loads((tmp / ".app" / "state.json").read_text(encoding="utf-8")) if (tmp / ".app" / "state.json").exists() else None
        note(f"[上班族] 關閉前 state.json 存在={state is not None}")
    def w3(win, store, tmp):   # 一週後清掉整天
        for i in range(1, 8): store.save(store.next_id(d(i)), f"# {d(i)} 待辦\n- 舊的")
        win._refresh_sidebar(); win.open_note(NoteId(d(7), 1))
        win.clear_day(d(7))     # 會跳確認框？n>0 → askyesno → 在測試裡會卡住
    def w4(win, store, tmp):   # 最上層、主題切換
        win.set_topmost(True); win.set_theme("light"); win.set_theme("system"); win.set_theme("dark"); win.set_topmost(False)
        s = json.loads((tmp / ".app" / "settings.json").read_text(encoding="utf-8")); assert s["theme"] == "dark" and s["topmost"] is False
    def w5(win, store, tmp):   # 側欄收起再開
        win.toggle_sidebar(); win.toggle_sidebar()
    return [("待辦含 Teams 連結", w1), ("狀態檔", w2), ("清掉七天前整天（有確認框）", w3), ("設定切換", w4), ("側欄", w5)]

# ---------- d. 主管：多張同日、換存檔位置到共用槽、搜人名、匯出給秘書 ----------
def manager_steps():
    def m1(win, store, tmp):
        for t in ["與 A 部門會議", "1on1 小王", "預算審查", "供應商拜訪"]:
            win.new_note(today); type_into(win, t, f"{t} 重點：\n1. \n")
        assert len(store.list_notes(today)) == 4, len(store.list_notes(today))   # 一開始那張空白沒打字，不建檔
    def m2(win, store, tmp):   # 換存檔位置（路徑含空格與中文）
        new = tmp / "共用 槽" / "主管筆記"; win.change_note_dir(new)
        assert win.store.root == new and new.is_dir()
        type_into(win, "新位置第一張", "ok"); assert win.store.list_notes(today)
        assert (tmp / "appdata" / "PersonalNote" / "note_dir.txt").exists()   # 要寫進測試的假 APPDATA，不是使用者真的那個
    def m3(win, store, tmp):   # 搜人名
        groups = win.store.search("小王"); note(f"[主管] 搜「小王」在新位置找到 {sum(len(v) for v in groups.values())} 張（舊位置的不會自動搬）")
    def m4(win, store, tmp):   # 按「新筆記」會帶預設標題「筆記N」並建檔；只是翻到空的一天不建檔
        before = len(win.store.list_notes(today)); win.new_note(today); win.editor.flush(); win.go_day(today)
        refs = win.store.list_notes(today)
        assert len(refs) == before + 1 and refs[-1].title == f"筆記{refs[-1].id.seq}", [r.title for r in refs]
        empty_day = d(400); win.go_day(empty_day); win.editor.flush(); win.go_day(today)
        assert not win.store.list_notes(empty_day)
    def m5(win, store, tmp):   # 只有標題沒內文也要存
        win.new_note(today); type_into(win, "只有標題", ""); assert win.store.list_notes(today)[-1].title == "只有標題"
    return [("一天五張", m1), ("換位置（含空格中文）", m2), ("搜人名", m3), ("新筆記預設標題、空天不建檔", m4), ("只有標題", m5)]

# ---------- e. 試務人員：大量截圖、PDF/Word/PPT 位置、網址 ----------
def exam_steps():
    from PIL import Image
    def e1(win, store, tmp):   # 貼 20 張截圖（Ctrl+V 的路徑）
        for k in range(20):
            im = Image.new("RGB", (1600, 900), (k * 10 % 255, 120, 160))
            line = win.paste_image(im)
            assert line and line.startswith("[貼圖_"), line
            win.editor.text.insert("end", line + "\n")
        win.editor.text.edit_modified(True); win.editor._on_modified(); win.update(); win.editor.flush()
        win.editor._highlight_links(); win.update()
        assert len(win.editor._photos) == 20, len(win.editor._photos)
        assert len(list((tmp / "attachments").glob("貼圖_*.png"))) == 20
    def e2(win, store, tmp):   # Office 檔位置（含空格、中文、共用槽）＋網址，全部要能認成連結
        win.new_note(today)
        body = ("名單 \\\\server\\share\\試務 2026\\第二次\\報名名單 final.xlsx\n"
                "簡報 C:\\Users\\Peter.Liu\\Documents\\試務說明會\\簡報 v3.pptx\n"
                "公文 \"D:\\公文 2026\\函 第 123 號.docx\"\n"
                "規章 https://exam.example.gov.tw/rules?year=2026&session=2#section-3\n"
                "PDF [准考證.pdf](attachments/准考證.pdf)\n")
        type_into(win, "試務 10/28", body)
        from personalnote.links import find_links
        targets = [l.target for ln in body.splitlines() for l in find_links(ln)]
        assert targets == ["\\\\server\\share\\試務 2026\\第二次\\報名名單 final.xlsx",
                           "C:\\Users\\Peter.Liu\\Documents\\試務說明會\\簡報 v3.pptx",
                           "D:\\公文 2026\\函 第 123 號.docx",
                           "https://exam.example.gov.tw/rules?year=2026&session=2#section-3",
                           "attachments/准考證.pdf"], targets
    def e3(win, store, tmp):   # 長路徑折疊：有「…」標籤，檔案內容完整
        win.editor._highlight_links(); win.update()
        assert len(win.editor._ell_widgets) >= 1, len(win.editor._ell_widgets)   # 只有網址那行超過 48 字
        assert "報名名單 final.xlsx" in store.load(win.current)
    def e4(win, store, tmp):   # 拖拉縮放寫進 {w=}
        win.open_note(NoteId(today, 1)); win.update(); win.editor._highlight_links(); win.update()
        line = min(win.editor._image_lines)
        win.editor._selected_line = line
        win.editor._image_lines[line] = win.editor._image_lines[line]
        win.editor._pending_w = 240
        win.editor._drag_end(None); win.update(); win.editor.flush()
        assert "{w=240}" in store.load(win.current), store.load(win.current)[:200]
    def e5(win, store, tmp):   # 匯出單張、匯出全部還是純文字（含 {w=} 與連結）
        out = tmp / "out" / "x.md"; store.export_note(win.current, out)
        assert "{w=240}" in out.read_text(encoding="utf-8")
    return [("貼 20 張截圖", e1), ("Office 路徑與網址", e2), ("長路徑折疊", e3), ("拖拉縮放", e4), ("匯出", e5)]

# ---------- f. 開發人員（主要使用者）：指令、程式片段、符號、長路徑、git ----------
def dev_steps():
    CODE = ('# 今天的指令\n'
            'git clone https://github.com/example/robot-demo.git && cd robot-demo\n'
            'python -X utf8 -m unittest discover -s tests -t . | tee "D:\\AI\\ai study\\logs\\unit 2026-10-28.txt"\n'
            'def f(x): return {k: v for k, v in x.items() if v > 0}  # dict comprehension\n'
            'arr[0] = (1, 2); print(f"{arr[0]}") ; foo(){w=1}  <- 這不是圖\n'
            'C:\\Users\\Peter.Liu\\AppData\\Local\\Programs\\Python\\Python312\\python.exe\n'
            '\\\\fileserver\\share\\訓練機\\logs\\run_20260326_164704\\model_best.pt\n'
            'export BATCH=8000; ./run.sh --profile DEMO 2>&1 | grep -v DEBUG\n'
            'ssh user@10.0.0.5 -p 22  # 不要存密碼\n'
            'Tab\tseparated\tvalues\n'
            'trailing spaces   \n'
            '中英混雜 mixed 全形符號：（）「」、，。')
    def d1(win, store, tmp):   # 原樣存、原樣讀（一個字都不能變）
        type_into(win, "指令備忘", CODE)
        saved = store.load(win.current)
        assert saved == "# 指令備忘\n" + CODE, repr(saved[:120])
        win.open_note(store.next_id(d(1))); win.open_note(NoteId(today, 1))
        assert win.editor.text.get("1.0", "end-1c") == CODE
    def d2(win, store, tmp):   # 連結只認該認的：git 網址、python.exe、共用槽；foo(){w=1} 不會被當圖
        from personalnote.links import find_links
        targets = [l.target for ln in CODE.splitlines() for l in find_links(ln)]
        assert "https://github.com/example/robot-demo.git" in targets, targets
        assert r"C:\Users\Peter.Liu\AppData\Local\Programs\Python\Python312\python.exe" in targets, targets
        assert r"\\fileserver\share\訓練機\logs\run_20260326_164704\model_best.pt" in targets, targets
        assert "10.0.0.5" not in "".join(targets)
        win.editor._highlight_links(); win.update()
        assert win.editor._wanted_images() == [], win.editor._wanted_images()
    def d3(win, store, tmp):   # 復原／重做按鈕
        before = win.editor.text.get("1.0", "end-1c")
        win.editor.text.insert("end", "\n多打一行"); win.editor.text.edit_separator()
        win.editor.undo(); win.update()
        assert win.editor.text.get("1.0", "end-1c") == before
        win.editor.redo(); win.update()
        assert win.editor.text.get("1.0", "end-1c").endswith("多打一行")
        win.editor.undo(); win.update()
    def d4(win, store, tmp):   # 圖片極端：超大、超小、拉到最小與最寬、反覆縮放 50 次
        from PIL import Image
        win.new_note(today)
        big = win.paste_image(Image.new("RGB", (8000, 6000), (30, 30, 30)))
        tiny = win.paste_image(Image.new("RGB", (1, 1), (255, 0, 0)))
        small = win.paste_image(Image.new("RGB", (16, 16), (0, 255, 0)))
        win.editor.text.insert("end", big + "\n" + tiny + "\n" + small + "\n")
        win.editor.text.edit_modified(True); win.editor._on_modified(); win.update(); win.editor.flush()
        win.editor._highlight_links(); win.update()
        assert len(win.editor._photos) == 3, len(win.editor._photos)
        maxw = win.editor._max_image_width()
        assert win.editor._image_lines[min(win.editor._image_lines)][1] <= maxw
        import time
        t0 = time.perf_counter()
        for k in range(50):
            ln = min(win.editor._image_lines); win.editor._selected_line = ln
            win.editor._pending_w = 60 if k % 2 else maxw
            win.editor._drag_end(None); win.update()
        dt = time.perf_counter() - t0
        note(f"[開發人員] 8000×6000 圖反覆縮放 50 次共 {dt:.1f} s（每次 {dt/50*1000:.0f} ms）")
        win.editor.flush(); saved = store.load(win.current)
        assert "{w=" in saved
    return [("原樣存讀", d1), ("連結不誤判", d2), ("復原重做", d3), ("圖片極端", d4)]

# clear_day 會開 messagebox；測試時把它換成自動回 True
import tkinter.messagebox as mb
mb.askyesno = lambda *a, **k: True
import personalnote.ui.main_window as mw
mw.messagebox.askyesno = lambda *a, **k: True

for name, steps in [("大學生", student_steps()), ("研究生", grad_steps()), ("上班族", worker_steps()), ("主管", manager_steps()),
                    ("試務人員", exam_steps()), ("開發人員", dev_steps())]:
    run_persona(name, steps)

OUT.write_text("\n".join(f"{k}: {m}" for k, m in report), encoding="utf-8")
print("\n".join(f"{k}: {m.splitlines()[0]}" for k, m in report))
print("BUGS:", sum(1 for k, _ in report if k == "BUG"))

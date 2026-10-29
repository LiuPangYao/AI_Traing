# -*- coding: utf-8 -*-
# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""開真的主視窗（螢幕外）走一遍：標記上色、指令區塊複製、選字套記號、拖檔案進視窗、Big5 匯入。
跑法：python -X utf8 tools/stress/ui_checks.py   （有一項不對就 exit 1）"""
import os, pathlib, shutil, sys, tempfile, time
from datetime import date

os.environ["NOTE_ALLOW_MULTI"] = "1"
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image                                              # noqa: E402
from tkinter import messagebox                                     # noqa: E402
from personalnote import dropfiles                                 # noqa: E402
from personalnote.config import Settings                           # noqa: E402
from personalnote.storage import NoteId, NoteStore                 # noqa: E402
from personalnote.ui.main_window import MainWindow                 # noqa: E402

errors: list[str] = []
def check(cond, msg):
    (print("OK:", msg) if cond else (errors.append(msg), print("FAIL:", msg)))

warned = []
messagebox.showwarning = lambda *a, **k: warned.append(a[1])
tmp = pathlib.Path(tempfile.mkdtemp(prefix="pn_ui_"))
today = date.today()

# ---- 標記 ----
st = NoteStore(tmp / "n1", encrypt=False)
body = ("今天 ==重點== 和 !!警告!! 和 **粗** 和 *斜* 😀 ==表情後==\n```\nssh user@fileserver\nnvidia-smi\n```\n"
        "後面 https://example.com/very/long/path/that/goes/on/and/on/forever/and/ever/x ==連結後==\n```\n沒關的區塊")
st.save(NoteId(today, 1), "# 標記\n" + body)
s = Settings.load(["--note-dir", str(tmp / "n1"), "--font-size", "15"], env={}, appdata=tmp / "a1")
win = MainWindow(s, st); win.geometry("720x640+3000+3000"); win.update(); time.sleep(0.4); win.update()
e = win.editor; t = e.text._textbox
def tagged(tag):
    r = t.tag_ranges(tag); return [t.get(r[i], r[i + 1]) for i in range(0, len(r), 2)]
check(tagged("mark") == ["重點", "表情後", "連結後"], "黃底三處（含 emoji 後、長連結後）")
check(tagged("red") == ["警告"] and tagged("bold") == ["粗"] and tagged("italic") == ["斜"], "紅字／粗體／斜體")
check(len(tagged("code")) == 2 and len(tagged("copybtn")) == 2, "兩個指令區塊、兩個複製按鈕")
check(e.get_text() == "# 標記\n" + body, "上色不改內容")
btns = [w for w in e._ell_widgets if "複製" in str(w.cget("text"))]
btns[0].event_generate("<Button-1>"); win.update()
check(win.clipboard_get() == "ssh user@fileserver\nnvidia-smi", "複製按鈕拿到整段（不含圍欄）")
btns[1].event_generate("<Button-1>"); win.update()
check(win.clipboard_get() == "沒關的區塊", "沒關的區塊也能複製")
t.tag_add("sel", "1.0", "1.2"); e.apply_style("bold"); win.update()
check(t.get("1.0", "1.end").startswith("**今天**"), "選字按粗體包上 **")
t.mark_set("insert", "end"); e.insert_code_block(); win.update()
check(t.get("end-8c", "end-1c") == "``\n\n```", "插空的指令區塊")
e.flush(); check(not e.is_dirty() and not e.last_error, "存檔正常")
win.set_theme("dark"); win.update()
check(t.tag_cget("mark", "background") != "" and t.tag_cget("code", "background") != "", "暗色有顏色")
win.zoom(1); win.update()
check(e._font_bold.cget("size") == e._font.cget("size") == e._font_mono.cget("size"), "縮放三種字型一起變")
t.mark_set("insert", "1.0"); t.event_generate("<Control-h>"); win.update()
check("**今天**" in t.get("1.0", "1.end"), "Ctrl+H 不會變成退格")
win.destroy()

# ---- 拖檔 ----
src = tmp / "來源 資料夾"; src.mkdir()
(src / "會議 記錄.txt").write_bytes("# 會議\r\n- 決議一\r\n".encode("utf-8"))   # write_text 會把 \n 再變 \r\n
(src / "想法.md").write_text("今天的想法 ==重要==", encoding="utf-8-sig")
(src / "空.txt").write_text("", encoding="utf-8")
(src / "big5.txt").write_bytes("中文".encode("cp950"))
(src / "二進位.txt").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00")
Image.new("RGB", (40, 30), (200, 50, 50)).save(src / "截圖 1.png")
(src / "規格.pdf").write_bytes(b"%PDF-1.4 fake")
st = NoteStore(tmp / "n2", encrypt=True)
s = Settings.load(["--note-dir", str(tmp / "n2")], env={}, appdata=tmp / "a2")
win = MainWindow(s, st); win.geometry("720x640+3000+3000"); win.update(); time.sleep(0.3); win.update()
dropfiles.simulate_drop(win, [src / "會議 記錄.txt", src / "想法.md", src / "空.txt", src / "big5.txt", src / "二進位.txt"])
win.update(); win.update()
notes = st.list_notes(today)
check([r.title for r in notes] == ["會議", "想法", "big5"], "txt/md 拖進來變今天三張（空檔跳過、Big5 可讀）")
check(st.load(NoteId(today, 1)) == "# 會議\n- 決議一\n", "CRLF 變 LF")
check(win.current == NoteId(today, 3), "最後一張打開")
check(warned and "二進位.txt" in warned[-1], "二進位檔提示讀不了")
dropfiles.simulate_drop(win, [src / "截圖 1.png", src / "規格.pdf", src])
win.update(); win.update()
txt = win.editor.get_text()
check("\n[截圖 1.png](attachments/截圖 1.png)\n[規格.pdf](attachments/規格.pdf)\n" in txt, "圖與 pdf 變附件連結、各自一行")
check(sorted(p.name for p in (tmp / "n2" / "attachments").iterdir()) == ["截圖 1.png", "規格.pdf"], "附件有複製過去")
check("來源 資料夾" in warned[-1], "資料夾不收並提示")
win.editor.flush(); win.update()
check([l.cget("text") for l in win.sidebar._rows.values()] == ["會議", "想法", "big5"], "左欄三張")
check("第" not in win.day_label.cget("text"), "上方不顯示第幾張")
win.new_note(today); win.update()
check(win.editor.title.get() == "筆記4", "新筆記預設標題「筆記4」")   # 標題欄拿到焦點時內文 FocusOut 會先存一次，所以不檢查 dirty
check(win.editor.title._entry.selection_present(), "預設標題有反白（直接打字就蓋掉）")
win.editor.flush(); win.update()
check([r.title for r in st.list_notes(today)][-1] == "筆記4", "預設標題有存檔、左欄看得到")
win.destroy()
shutil.rmtree(tmp, ignore_errors=True)
print("UI:", "PASS" if not errors else f"FAIL ({len(errors)})")
for m in errors:
    print(" -", m)
sys.exit(0 if not errors else 1)

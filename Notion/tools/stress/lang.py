# -*- coding: utf-8 -*-
# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""中文、英文、混合：純中文、純英文、中英夾雜、英文長字換行、全形半形標點、emoji、BOM、CRLF 匯入；
兩種語言搜尋；標題兩種語言；匯出再匯入一字不差。
跑法：python -X utf8 tools/stress/lang.py"""
import pathlib, shutil, sys, tempfile
from datetime import date
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from personalnote import applog
applog.setup()          # 跟真的程式一樣寫 log，看門狗倒堆疊才有地方寫
from personalnote.config import Settings
from personalnote.storage import NoteStore, NoteId, title_of
from personalnote.ui.main_window import MainWindow

fails = []
def check(cond, msg):
    if not cond: fails.append(msg); print("FAIL:", msg)

tmp = pathlib.Path(tempfile.gettempdir()) / "pn_stress_lang"
shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
store = NoteStore(tmp, encrypt=True)
d = date.today()
SAMPLES = {
    "純中文": "# 今日待辦\n一、早上九點半站立會議，討論電梯狀態機。\n二、下午整理週報，附上讀碼第一課的四個數字。\n三、記得問主管容量重規劃。\n",
    "純英文": "# Daily plan\n1. Stand-up at 09:30, discuss the elevator state machine.\n2. Weekly report in the afternoon; attach the four numbers from lesson one.\n3. Ask manager about the disk re-plan.\nAVeryLongEnglishWordWithoutAnySpacesThatShouldWrapNicelyInsideTheEditorWithoutBreakingAnything0123456789\n",
    "中英夾雜": "# Mixed 混合\nplanner 的 temperature 是 0.3，gamma 0.015 寫死在 .cu 裡；lp_compute 在 planner_cuda.cu:1102。\nSee also: https://example.com/ 與 D:\\AI\\ai study\\notes\\56.md\n",
    "標點與emoji": "# 全形：「」（）、，。；半形: \"\" () , . ;\n😀 emoji 在前面 https://example.com/emoji 後面有連結\ntab\there\n",
}
for name, text in SAMPLES.items():
    nid = store.next_id(d); store.save(nid, text)
    check(store.load(nid) == text, f"{name}: 存讀不一致")
    check(title_of(text) == text.splitlines()[0][2:].strip(), f"{name}: 標題 {title_of(text)!r}")

# CRLF 與 BOM 的匯入
src = tmp / "從 Windows 記事本.txt"; src.write_bytes("\ufeff第一行\r\n第二行 second line\r\n".encode("utf-8"))
nid = store.import_file(src, d)
check(store.load(nid).startswith("# 從 Windows 記事本\n第一行\n第二行"), f"BOM/CRLF 匯入：{store.load(nid)!r}")

# 兩種語言搜尋
check(d in store.search("電梯") and d in store.search("elevator") and d in store.search("ELEVATOR"), "搜尋中/英/大小寫")
check(not store.search("不存在的字串xyz"), "搜不到的字")

# 真視窗：載入每一張，內文一字不差，連結認得
st = Settings.load(["--note-dir", str(tmp)], env={}, appdata=tmp / "ad")
win = MainWindow(st, store); win.geometry("+3000+3000"); win.update()
for ref in store.list_notes(d):
    win.open_note(ref.id); win.update()
    body = win.editor.text.get("1.0", "end-1c")
    full = store.load(ref.id)
    check(win.editor.get_text() == full, f"視窗載入後 get_text 不等於檔案：{ref.title}")
win.editor._highlight_links(); win.update()
# emoji 那張：連結底線位置要在網址上（Tk 的 UTF-16 欄位換算）
emoji_id = [r.id for r in store.list_notes(d) if "全形" in r.title][0]
win.open_note(emoji_id); win.editor._highlight_links(); win.update()
tk_text = win.editor.text._textbox
ranges = tk_text.tag_ranges("link")
tagged = [tk_text.get(ranges[i], ranges[i + 1]) for i in range(0, len(ranges), 2)]
check("https://example.com/emoji" in tagged, f"emoji 行的連結底線範圍：{tagged}")
win._on_close()

# 匯出再匯入一字不差
exp = tmp / "匯出"; store.export_plain(exp)
other = NoteStore(tmp / "other", encrypt=False); other.import_folder(exp)
for a, b in zip(store.list_notes(d), other.list_notes(d)):
    check(store.load(a.id) == other.load(b.id), f"匯出匯入後不一致：{a.title}")

print("LANG:", "PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(0 if not fails else 1)

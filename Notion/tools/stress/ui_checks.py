# -*- coding: utf-8 -*-
# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""開真的主視窗（螢幕外）走一遍：標記上色、指令區塊複製、選字套記號、拖檔案進視窗、Big5 匯入。
跑法：python -X utf8 tools/stress/ui_checks.py   （有一項不對就 exit 1）"""
import os, pathlib, shutil, sys, tempfile, time
from datetime import date

os.environ["NOTE_ALLOW_MULTI"] = "1"
os.environ["NOTE_UPDATE_CHECK"] = "0"   # 測試不連網
os.environ["NOTE_TOUR"] = "0"           # 教學另外測
os.environ["NOTE_ANIM"] = "0"           # 動畫立刻完成，檢查才不用等
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image                                              # noqa: E402
import tkinter as tk
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


def key_on(w, seq):
    """對某個元件模擬按鍵。桌面上別的程式拿走焦點時 Tk 會把按鍵事件丟掉，所以先把焦點要回來。"""
    if win.focus_displayof() is None:
        win.focus_force(); win.update()
    w.focus_set(); w.event_generate(seq); win.update()

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
# 藏記號：游標在第 1 行 → 第 1 行的記號看得到（沒 hide），其他行的記號、圍欄藏起來
e._highlight_links(); win.update()
hidden = tagged("hide")
check(all(int(str(t.tag_ranges("hide")[i]).split(".")[0]) != 1 for i in range(0, len(t.tag_ranges("hide")), 2)), "游標那行（第 1 行）不藏記號")
check("```" in hidden and "**" not in hidden, "其他行的圍欄藏起來、第 1 行的 ** 沒藏")
t.mark_set("insert", "2.0"); e._highlight_links(); win.update()
check("**" in tagged("hide") and "==" in tagged("hide"), "游標移走後第 1 行的記號也藏起來")
# 打勾清單
e.set_text("# 勾\n- [ ] 回信\n- [x] 寄出\n普通行"); win.update(); e._highlight_links(); win.update()
t.mark_set("insert", "3.0"); e._highlight_links(); win.update()           # 游標放在第 3 行，第 1、2 行會有 ☐☑
boxes = [w for w in e._ell_widgets if w.cget("text") in ("☐", "☑")]
check([w.cget("text") for w in boxes] == ["☐", "☑"], "兩行打勾清單各有一個方框（空、勾）")
check(tagged("done") == ["寄出"], "打勾的那行劃掉")
boxes[0].event_generate("<Button-1>"); win.update()
check(t.get("1.0", "1.end") == "- [x] 回信", "點方框 → 文字變 [x]")
check(e.is_dirty(), "點方框算成有改（會存檔）")
boxes = [w for w in e._ell_widgets if w.cget("text") in ("☐", "☑")]
check([w.cget("text") for w in boxes] == ["☑", "☑"], "方框馬上變成勾")
t.mark_set("insert", "3.end"); e.insert_checkbox(); win.update()
check(t.get("3.0", "3.end") == "- [ ] 普通行", "格式列「打勾」在行首加 - [ ] ")
e.insert_checkbox(); win.update()
check(t.get("3.0", "3.end") == "普通行", "再按一次拿掉")
t.mark_set("insert", "1.end"); key_on(t, "<Return>")
check(t.get("2.0", "2.end") == "- [ ] ", "打勾清單按 Enter 接下一個空框")
# 標籤
e.set_text("# 標\n今天 #專案A 看 https://x.y/z#frag 和 issue #42"); win.update(); e._highlight_links(); win.update()
check(tagged("hashtag") == ["#專案A"], "只有 #專案A 是標籤（網址的 #、純數字不算）")
got = []
e._on_tag = lambda s: got.append(s)
bbox = t.bbox("1.4")
t.event_generate("<Control-Button-1>", x=bbox[0] + 2, y=bbox[1] + 2); win.update()
check(got == ["#專案A"], "Ctrl+點標籤送出 #專案A")
# 右鍵「複製成純文字」
e.set_text("# p\n看 **設計** 和 ==重點==\n```\nls\n```"); win.update()
e._copy_plain(t, False); win.update()
check(win.clipboard_get() == "看 設計 和 重點\nls", "複製成純文字去掉記號與圍欄")
# 空筆記提示
e.set_text("# 空\n"); win.update(); e._highlight_links(); win.update()
check(e._hint.winfo_ismapped(), "空筆記顯示提示")
t.insert("1.0", "x"); win.update(); e._highlight_links(); win.update()
check(not e._hint.winfo_ismapped(), "打字後提示消失")
# 已儲存淡出
e._mark_dirty(); e.flush(); win.update()
check(e.status.cget("text").startswith("已儲存"), "存完顯示已儲存")
e.STATUS_FADE_AFTER_MS = 1; e._set_status("已儲存 x", fade=True); win.update(); time.sleep(0.05); win.update()
for _ in range(60):                      # 淡出 400 ms、每幀 16 ms：每次 update 只跑一幀
    time.sleep(0.02); win.update()
check(e.status.cget("text") == "", "已儲存幾秒後淡出")
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
from personalnote.storage import IMPORT_MAX_BYTES
(src / "大檔.txt").write_bytes(b"a" * (IMPORT_MAX_BYTES + 1))
before = win.editor.get_text()
dropfiles.simulate_drop(win, [src / "截圖 1.png", src / "規格.pdf", src, src / "大檔.txt"])
win.update(); win.update()
check(win.editor.get_text() == before and "attachments" not in win.editor.get_text(), "圖、pdf 不收（只收 .md／.txt），內文沒變")
check(len(st.list_notes(today)) == 3, "超過 1 MB 的 .txt 不收")
check(all(n in warned[-1] for n in ("截圖 1.png", "規格.pdf", "來源 資料夾", "大檔.txt")), "不收的檔、資料夾、大檔都列在提示裡")
# 真的拖放走訊息佇列（PostMessage）：以前攔截函式裡叫 widget.after 會讓程式整個被 C 執行階段終止（2026-10-30），現在要活著
n_warn = len(warned)
dropfiles.post_drop(win, [src / "二進位.txt"])
win.update(); time.sleep(0.25); win.update(); win.update()
check(len(warned) == n_warn + 1 and "二進位.txt" in warned[-1], "PostMessage 拖放：程式活著、收到並處理")
win.editor.flush(); win.update()
check([l.cget("text") for n, l in win.sidebar._rows.items() if n.day == today] == ["會議", "想法", "big5"], "左欄今天三張")
from personalnote.storage import TODO_DAY
check(next(iter(win.sidebar._groups)) == TODO_DAY, "待辦事項在左欄最上面")
sel = win.sidebar._rows[win.current]
check(sel.cget("fg") == win.sidebar._accent and win.sidebar._bands[win.current].cget("bg") == win.sidebar._accent, "選中那張：主色字＋左邊色帶")
hdr = win.sidebar._groups[today][3]
check(hdr.cget("text").startswith("●") and hdr.cget("fg") == win.sidebar._accent, "今天的日期列：主色加點")
plus = win.sidebar._groups[today][4]
check(plus.cget("text") == "", "＋ 平常藏著")
plus.event_generate("<Enter>"); win.update()
check(plus.cget("text") == "＋", "滑過日期列 ＋ 出現")

def key(seq):
    """模擬按鍵。Tk 會把按鍵事件轉給有焦點的視窗；桌面上別的程式拿走焦點時事件會被丟掉，所以先要回來。"""
    if win.focus_displayof() is None:
        win.focus_force(); win.update()
    win.event_generate(seq); win.update()

key("<Control-t>")
check(win.current_day == today, "Ctrl+T 回到今天")
# 跨日：假裝昨天畫的左欄，今天的心跳發現日期換了
from datetime import timedelta
yday = today - timedelta(days=1)
st.save(NoteId(yday, 1), "# 昨天\n還在打")
win._refresh_sidebar(); win.go_day(yday); win.update()
win._drawn_today = yday
win._check_day_change(); win.update()
check(win.current_day == today, "跨日：原本看的是（舊的）今天，過午夜自動跳到新的今天")
check(win.sidebar._header_titles.get(today, "").startswith("● ") and not win.sidebar._header_titles.get(yday, "").startswith("● "), "跨日：左欄「● 今天」移到新的一天")
# 左欄放右邊／下面／回左邊（整個視窗重畫）
win.set_sidebar_side("right"); win.update()
check(win.sidebar.grid_info()["column"] == 2 and win._main.grid_info()["column"] == 0, "左欄放右邊：欄位對調")
win.set_sidebar_side("bottom"); win.update(); win.update()
check(win.sidebar.grid_info()["row"] == 2 and win._main.grid_info()["row"] == 0 and win.sidebar.winfo_width() > 600, "左欄放下面：在內文下方、撐滿寬度")
win.set_sidebar_side("left"); win.update()
check(win.sidebar.grid_info()["column"] == 0 and win.state_.sidebar_side == "left", "放回左邊")
# 我的最愛：點筆記列前的星號
from personalnote.storage import FAV_DAY
nid_f = NoteId(today, 2)
win.sidebar._stars[nid_f].event_generate("<Button-1>"); win.update()
check(st.is_favorite(nid_f) and FAV_DAY in win.sidebar._groups and nid_f in win.sidebar._fav_rows, "點星號：加入我的最愛，最上面多一組")
check(win.sidebar._stars[nid_f].cget("text") == "★" and list(win.sidebar._groups)[1] == FAV_DAY, "星號變實心；那組排在待辦事項下面")
win.sidebar._fav_rows[nid_f].event_generate("<Button-1>"); win.update()
check(win.current == nid_f, "點我的最愛裡的那列會開那張")
win.toggle_favorite(nid_f); win.update()
check(not st.is_favorite(nid_f) and FAV_DAY not in win.sidebar._groups and win.sidebar._stars[nid_f].cget("text") == "☆", "再點一次：取消、群組消失、星號變空心")
# 舊版本視窗：先做兩份快照，開視窗、選第二份、還原
nid1 = NoteId(today, 1)
st.SNAPSHOT_MIN_GAP = 0
st.snapshot(nid1, "# 會議\n版本二"); st.save(nid1, "# 會議\n版本二"); st.snapshot(nid1, "# 會議\n版本三"); st.save(nid1, "# 會議\n版本三")
win.open_note(nid1); win.update()
win.show_versions(nid1); win.update()
dlg = win._versions_dialog
vs = dlg._versions_state
check(len(vs["rows"]) == 2, "舊版本視窗列出兩份")
vs["rows"][1].event_generate("<Button-1>"); win.update()
dlg._versions_restore(); win.update(); win.update()
check(win.editor.get_text() == "# 會議\n- 決議一\n", "還原最舊那版（內容回到匯入時）")
check(st.try_load(nid1)[0] == "# 會議\n- 決議一\n", "檔案也換回去了")
check(len(st.list_snapshots(nid1)) == 3 and st.load_snapshot(st.list_snapshots(nid1)[0][1]) == "# 會議\n版本三", "還原前把當時的內容多留了一份")
# 分享：郵件（攔下 open_path 看網址）、Google Drive（指到暫存資料夾）
from personalnote import platform_
opened = []
platform_.open_path = lambda p: opened.append(str(p))
platform_.open_folder = lambda p: opened.append("folder:" + str(p))
win.share_mail(nid1); win.update()
check(opened and opened[-1].startswith("mailto:?subject=") and "%E6%B1%BA%E8%AD%B0%E4%B8%80" in opened[-1], "郵件：mailto 帶主旨與純文字內文")
drive = tmp / "drive"; drive.mkdir()
platform_.google_drive_dir = lambda: drive
win.share_drive(nid1); win.update()
files = sorted(p.name for p in drive.iterdir())
check(files == [f"{today.isoformat()}_001_會議.md"] and (drive / files[0]).read_text(encoding="utf-8").startswith("# 會議"), "Google Drive：存成 .md 到同步資料夾")
check(opened[-1] == "folder:" + str(drive), "存完打開那個資料夾")
check("第" not in win.day_label.cget("text"), "上方不顯示第幾張")
win.new_note(today); win.update()
check(win.editor.title.get() == "筆記4", "新筆記預設標題「筆記4」")   # 標題欄拿到焦點時內文 FocusOut 會先存一次，所以不檢查 dirty
check(win.editor.title._entry.selection_present(), "預設標題有反白（直接打字就蓋掉）")
win.editor.flush(); win.update()
check([r.title for r in st.list_notes(today)][-1] == "筆記4", "預設標題有存檔、左欄看得到")
# 新筆記一律加在今天（看著前一天按也是）；快捷鍵改鍵、撞鍵、還原
from datetime import timedelta as _td
from personalnote import keys as keys_mod
import json as _json
yd = today - _td(days=1)
st.save(NoteId(yd, 1), "# 前一天\n字"); win._refresh_sidebar(); win.go_day(yd); win.update()
key("<Control-n>")
check(win.current.day == today, "看著前一天按 Ctrl+N：新筆記開在今天")
win.set_keys(win.keymap.set("new_note", "Ctrl+Shift+N")); win.update()
win.go_day(yd); win.update(); cur = win.current
key("<Control-n>")
check(win.current == cur, "改鍵後舊的 Ctrl+N 沒作用")
key("<Control-Shift-N>")
check(win.current != cur and win.current.day == today, "新的 Ctrl+Shift+N 有作用")
check(_json.loads(win.settings.settings_path.read_text(encoding="utf-8"))["keys"] == {"new_note": "Ctrl+Shift+N"}, "改的鍵存進 settings.json")
try:
    win.keymap.set("today", "Ctrl+F"); check(False, "撞鍵要被擋")
except keys_mod.Conflict as c:
    check(c.other == "search", "撞鍵被擋，並說是誰在用")
win.set_keys(keys_mod.KeyMap.load()); win.update()
check(win.keymap.overrides() == {} and _json.loads(win.settings.settings_path.read_text(encoding="utf-8"))["keys"] == {}, "全部還原預設")
# 查新版（假的 GitHub 回應）、啟動提醒、設定裡的更新區；第一次開的使用教學
import urllib.error as _ue
from personalnote.state import AppState
fake = lambda: {"tag_name": "v9.9.9", "html_url": "https://github.com/x/releases/tag/v9.9.9",
                "assets": [{"name": "Notion_v9.9.9.zip", "browser_download_url": "https://github.com/LiuPangYao/AI_Traing/releases/download/v9.9.9/Notion_v9.9.9.zip"}]}
def wait_update():
    for _ in range(60):
        win.update(); time.sleep(0.05)
        if win._update["status"] != "checking":
            break
    win.update()
win.start_update_check(force=True, fetch=fake, notify=True); wait_update()
check(win._update["status"] == "ok" and win._update["info"].newer and win._update["info"].version == "9.9.9", "查到新版 9.9.9")
dlgp = getattr(win, "_update_prompt", None)
check(dlgp is not None and dlgp.winfo_exists(), "啟動提醒視窗出現")
dlgp._skip_version(); win.update()
check(win.settings.update_skip == "9.9.9" and not dlgp.winfo_exists(), "「這一版不再提醒」記住 9.9.9")
win._update_prompt = None
win.start_update_check(force=True, fetch=fake, notify=True); wait_update()
check(getattr(win, "_update_prompt", None) is None, "同一版不再跳提醒")
win.open_settings(); win.update(); pnl = win._settings_panel
pnl.show_page("更新"); win.update(); win.update()
check("9.9.9" in pnl._update_lbl.cget("text") and pnl._update_btn.winfo_ismapped(), "設定裡顯示有新版、下載鈕出現")
opened.clear(); pnl._update_btn.invoke(); win.update()
check(bool(opened) and opened[-1].endswith("Notion_v9.9.9.zip"), "下載鈕開 zip 網址")
def fail():
    raise _ue.URLError("no net")
win.start_update_check(force=True, fetch=fail); wait_update()
check(win._update["status"] == "offline" and not pnl._update_btn.winfo_ismapped() and "9.9.9" not in pnl._update_lbl.cget("text"), "沒網路：顯示查不到、沒有下載鈕")
win.set_update_notify(False); win.update()
check(win.settings.update_notify is False and _json.loads(win.settings.settings_path.read_text(encoding="utf-8"))["update_notify"] is False, "關掉啟動提醒會存進 settings.json")
pnl.destroy(); win.update()
check(not win.state_.tour_done, "新資料夾：教學還沒看過")
win.show_tour(); win.update(); tour = win._tour
check(tour is not None and tour.winfo_exists() and tour._page == 0 and "Notion" in tour._title.cget("text"), "教學視窗出現在第 1 頁")
for _ in range(10):
    if not tour.winfo_exists():
        break
    tour._next(); win.update()
check(not tour.winfo_exists() and win.state_.tour_done and AppState.load(win.store.root).tour_done, "按到最後一頁關閉，記住看過了")
# 使用時間：有焦點＋有在動才累加；月曆：格子、換月、點日期；版本紀錄展開／收起
from personalnote import usage as usagelog
now = time.monotonic()
win._last_activity = now; win._last_tick = now - 2
u0 = win.usage.seconds(today)
win._tick_usage(now, focused=True)
check(win.usage.seconds(today) == u0 + 2, "有焦點、有在動：加 2 秒")
win._last_tick = now - 2; win._tick_usage(now, focused=False)
check(win.usage.seconds(today) == u0 + 2, "沒焦點：不加")
win._last_activity = now - usagelog.IDLE_SECONDS - 1; win._last_tick = now - 2; win._tick_usage(now, focused=True)
check(win.usage.seconds(today) == u0 + 2, "太久沒動：不加")
check(win.usage.save(now + 100, force=True) and usagelog.UsageLog(win.store.root).seconds(today) == u0 + 2, "使用時間有寫進 usage.json")
win.show_calendar(); win.update(); cal_dlg = win._calendar; cs = cal_dlg._cal_state
check(today in cs["cells"] and cs["y"] == today.year and cs["m"] == today.month, "月曆開在本月、有今天的格子")
cal_dlg._cal_shift(-1); win.update()
check((cs["y"], cs["m"]) == ((today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)), "◀ 換到上個月")
cal_dlg._cal_shift(1); win.update()
win.go_day(yd); win.update()
cs["cells"][today].event_generate("<Button-1>"); win.update()
check(win.current_day == today, "點月曆的日期跳到那天")
cal_dlg.destroy(); win.update()
win.open_settings(); win.update(); pnl = win._settings_panel; pnl.show_page("更新"); win.update()
pnl._toggle_log(); win.update()
check(pnl._log_box is not None and pnl._log_box.winfo_exists() and len(pnl._log_box.winfo_children()) > 10, "版本紀錄展開，列出各版")
pnl._toggle_log(); win.update()
check(pnl._log_box is None, "版本紀錄收起")
pnl.destroy(); win.update()
# 1.0.7：筆記連結＋返回、範本、未完成清單、Tab 縮排、最近標籤、匯出日期區間
from personalnote import templates as _tpl
nid_a = NoteId(today, 1)
win.sidebar.clear_search(); win.update()
st.save(nid_a, "# 會議\n看 [[想法]] 和 #專案Z #專案Z\n- [ ] 連結測試\n")
win.open_note(nid_a); win.update()
win.jump_to_note("想法"); win.update()
check(win.current == NoteId(today, 2), "[[想法]] 跳到那張")
win.go_back(); win.update()
check(win.current == nid_a, "「返回」回到原本那張")
win.jump_to_note("沒有這張"); win.update()
check(win.current == nid_a, "找不到的連結不會跳")
win.copy_note_link(NoteId(today, 2)); win.update()
check(win.clipboard_get() == "[[想法]]", "複製筆記連結 [[標題]]")
win._refresh_sidebar(); win.update()
tag_lbls = [w.cget("text") for w in win.sidebar._tags.winfo_children()]
check("#專案Z" in tag_lbls, "搜尋框下面列出最近標籤")
tpl_dir = _tpl.ensure_defaults(st.root)
n_before = len(st.list_notes(today))
win.new_from_template(tpl_dir / "週報.md"); win.update()
check(len(st.list_notes(today)) == n_before + 1 and win.editor.title.get().startswith("週報"), "用範本開一張新筆記")
win.show_todo_list(); win.update(); tv = win._todo_view
check(any("連結測試" in it for _n, _t, items in tv._todo_rows for it in items), "未完成清單列出 - [ ] 項目")
tv.destroy(); win.update()
win.open_note(nid_a); win.update()
t = win.editor.text._textbox
t.mark_set("insert", "2.0"); win.editor._on_tab(False); win.update()
check(t.get("2.0", "2.end") == "  - [ ] 連結測試", "清單行 Tab 縮排兩格")
win.editor._on_tab(True); win.update()
check(t.get("2.0", "2.end") == "- [ ] 連結測試", "Shift+Tab 退回")
t.mark_set("insert", "1.0")
check(win.editor._on_tab(False) is None, "不是清單行：Tab 照預設")
# [[ 自動完成：打 [[想 → 清單有「想法」→ Enter 填成 [[想法]]
win.open_note(nid_a); win.update()
t.mark_set("insert", "1.end"); t.insert("insert", "\n再連 [[想"); win.editor._maybe_autocomplete(); win.update()
check(win.editor._ac is not None and any("想法" in it for it in win.editor._ac["items"]), "打 [[ 跳出標題清單（含「想法」）")
idx = next(i for i, it in enumerate(win.editor._ac["items"]) if it == "想法")
win.editor._ac["list"].selection_clear(0, "end"); win.editor._ac["list"].selection_set(idx)
win.editor._ac_choose(); win.update()
check(t.get("2.0", "2.end") == "再連 [[想法]]" and win.editor._ac is None, "Enter 填入 [[想法]] 並關掉清單")
t.insert("insert", " 以及 [["); win.editor._maybe_autocomplete(); win.update()
check(win.editor._ac is not None and len(win.editor._ac["items"]) >= 2, "只打 [[ 列出所有標題")
# 用滑鼠點清單第一項（模擬按下）
class _E: y = 2
lb = win.editor._ac["list"]; first = win.editor._ac["items"][0]
lb.event_generate("<Button-1>", x=5, y=2); win.update()
check(win.editor._ac is None and t.get("2.0", "2.end").endswith("[[" + first + "]]"), "滑鼠點清單也會填入")
# 反向連結、[[日期]]、拖進內文、改標題更新連結
win.open_note(NoteId(today, 2)); win.update()
back = [w.cget("text") for w in win.editor._back.winfo_children() if isinstance(w, tk.Label)]
check(win.editor._back.winfo_ismapped() and "會議" in back, "想法那張下面列出「連到這張的：會議」")
next(w for w in win.editor._back.winfo_children() if isinstance(w, tk.Label) and w.cget("text") == "會議").event_generate("<Button-1>"); win.update()
check(win.current == nid_a, "點反向連結開那張")
win.jump_to_note(yd.isoformat()); win.update()
check(win.current_day == yd, "[[日期]] 跳到那一天")
win.open_note(nid_a); win.update()
tx = win.editor.text._textbox; bb = tx.bbox("1.0")
check(win._drop_note_link(NoteId(today, 2), tx.winfo_rootx() + bb[0] + 2, tx.winfo_rooty() + bb[1] + 2) and tx.get("1.0", "1.end").startswith("[[想法]] "), "拖筆記放進內文：插入 [[想法]]")
check(win._drop_note_link(NoteId(today, 2), 0, 0) is False, "放在內文以外：不插")
win.open_note(NoteId(today, 2)); win.update()
win._save_current("# 想法2\n內容\n"); win.update()
check("[[想法2]]" in st.try_load(nid_a)[0] and "[[想法]]" not in st.try_load(nid_a)[0], "改標題後別張的 [[想法]] 自動變 [[想法2]]")
# 開著的筆記在磁碟上被別的程式改了
win.open_note(nid_a); win.update()
time.sleep(0.05)
NoteStore(st.root, encrypt=st.encrypt).save(nid_a, "# 會議（外面改的）\n外部內容\n")
win._check_current_file(); win.update()
check(win.editor.get_text().startswith("# 會議（外面改的）"), "沒在打字：別的程式改了就自動重新載入")
tx.insert("end", "我在打字"); win.editor._mark_dirty(); time.sleep(0.05)
NoteStore(st.root, encrypt=st.encrypt).save(nid_a, "# 會議（又改）\n再改一次\n")
win._check_current_file()
check("我在打字" in win.editor.get_text() and "被別的程式改了" in win.editor.status.cget("text"), "正在打字：不蓋掉，只提醒")
win.update(); win.editor.flush(); win.update()
check(st.try_load(nid_a)[0].rstrip().endswith("我在打字") and "蓋掉了" in win.editor.status.cget("text"), "存檔後以畫面上的為準，並提醒蓋掉了外面那版")
from personalnote.ui import datepick as _dp
from tkinter import filedialog
picks = iter([yd, today]); _dp.ask_date = lambda *a, **k: next(picks)
out_md = tmp / "range.md"; filedialog.asksaveasfilename = lambda *a, **k: str(out_md)
win.export_range(); win.update()
check(out_md.is_file() and "## 會議" in out_md.read_text(encoding="utf-8"), "匯出日期區間合成一個 .md")
win.destroy()
shutil.rmtree(tmp, ignore_errors=True)
print("UI:", "PASS" if not errors else f"FAIL ({len(errors)})")
for m in errors:
    print(" -", m)
sys.exit(0 if not errors else 1)

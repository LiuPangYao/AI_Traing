# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""主視窗：把 Sidebar、Editor、設定面板接到 NoteStore。

這裡只有「誰呼叫誰」，沒有檔案 I/O 細節（在 storage）、沒有外觀常數（在 theme）。

操作流程（定案）：
- 開啟：回到上次看的那天；那天沒筆記就開今天。今天沒筆記 → 直接給一張空白的，打字才建檔。
- 看之前的：左欄依日期分組（新的在上），點一張就開；◀ ▶ 是前一天／後一天；搜尋框過濾日期和內容。
- 新增：上排 ＋／Ctrl+N 一律加在今天；日期列旁的 ＋ 或右鍵「在這天新增」加在那一天；左下「額外新增」先選日期。
- 刪除：筆記上按右鍵 → 刪除這張；🗑 → 清空目前這張／清掉整天／清掉全部。全部先搬 .app/trash。
- 帶到今天：右鍵 → 複製到今天（前一天沒做完的事抄過來）。
- 存檔：打字停 1.2 秒自動存；切換、關閉一定存。
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from ..i18n import _
from .. import APP_NAME, AUTHOR, __version__, applog, dropfiles, keys, platform_, startup, update
from .. import usage as usagelog
from .. import templates
from ..config import Settings
from ..state import AppState
from ..storage import FAV_DAY, IMPORT_MAX_BYTES, TODO_DAY, TODO_ID, NoteId, NoteRef, NoteStore, title_of, tomorrow, yesterday
from . import theme as T
from .editor import Editor
from .sidebar import Sidebar


class MainWindow(ctk.CTk):
    def __init__(self, settings: Settings, store: NoteStore):
        T.apply_appearance(settings.theme)
        T.clear_icon_cache()
        super().__init__(fg_color=T.MAIN_BG)
        self.settings = settings
        self.store = store
        self.state_ = AppState.load(store.root)
        self.current: Optional[NoteId] = None
        self._search_kw = ""
        self._sidebar_limit = self.SIDEBAR_DAYS

        self.title(APP_NAME)
        _set_icon(self)
        self.minsize(600, 400)              # 再小（左欄開著時）工具列右邊的圖示會被截掉；量過 640 剛好放得下
        self.geometry(self.state_.safe_geometry())
        self.report_callback_exception = self._on_tk_error   # 按鈕裡出錯：記檔＋提示，不要默默吞掉
        self._watchdog = applog.Watchdog(stall_seconds=30)
        self._watchdog.start()
        self.usage = usagelog.UsageLog(store.root)      # 每天用了多久（月曆的熱度圖）
        self._last_activity = time.monotonic()          # 最近一次按鍵／滑鼠
        self._last_tick = self._last_activity
        self._heartbeat()
        self.attributes("-topmost", settings.topmost)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.keymap = keys.KeyMap.load(settings.keys)   # 快捷鍵表：預設疊上設定裡改過的（設定面板可改）
        self._fav_cache: set = set()                    # 有星號的筆記（_refresh_sidebar 每次重算）
        self._back: list = []                           # 「返回」用：之前看過的筆記（最多 50）
        self._build_ui()
        self.bind("<Configure>", self._fit_sidebar, add="+")   # 視窗縮小時左欄跟著讓位（只綁這一次；rebuild_ui 不再綁）
        self._bind_keys()
        for seq in ("<Any-KeyPress>", "<Button>", "<MouseWheel>"):          # 有在動才算「在用」（usage）；綁在主視窗，子元件的事件會傳上來
            self.bind(seq, self._touch_activity, add="+")
        self._update = {"status": "idle", "info": None}     # 查新版的結果（start_update_check）
        if os.environ.get("NOTE_UPDATE_CHECK", "1") != "0":
            self.after(3000, lambda: self.start_update_check(notify=True))   # 開了幾秒再查，不拖慢啟動
        if not self.state_.tour_done and os.environ.get("NOTE_TOUR", "1") != "0":
            self.after(600, self.show_tour)                  # 第一次開：教一次怎麼用，之後不再出現（設定裡可再看）
        self.bind("<FocusIn>", self._on_focus_in)      # 回到視窗時看資料夾有沒有被別的程式動過
        self._last_focus_check = 0.0
        try:                                 # 拖檔案進視窗（見 dropfiles.py）；失敗只記 log，不影響其他功能
            if not dropfiles.enable(self, self._on_drop):
                applog.info("拖檔案功能沒開（不是 Windows 或接不上視窗）")
        except Exception:
            applog.exception("拖檔案功能啟用失敗")
        self._open_initial()                 # 開上次看的那天（沒有就今天）
        if store.newer_format_by:            # 資料是更新版程式寫的：提醒，不要在這版改
            self.after(300, lambda: messagebox.showwarning(
                APP_NAME, _("這些筆記是較新版本（{0}）寫的，這個程式是 {1}。\n").format(store.newer_format_by, __version__)
                          + _("舊版能讀多少讀多少；請更新程式再開，才不會把新格式的東西弄壞。"), parent=self))

    def _build_ui(self) -> None:
        """畫整個視窗的內容（左欄、分隔線、工具列、編輯器）。換語言時 rebuild_ui() 會砍掉重畫一次。"""
        settings = self.settings
        side = self.state_.sidebar_side              # 左欄放哪：left／right／bottom（設定裡改，state.json 記）
        sb_pos, sp_pos, main_pos = self._dock_positions(side)
        for i in range(3):                           # 重畫時上一種擺法的 weight 要先歸零，不然兩欄都會撐開
            self.grid_columnconfigure(i, weight=0); self.grid_rowconfigure(i, weight=0)
        self.grid_columnconfigure(main_pos["column"], weight=1)
        self.grid_rowconfigure(main_pos["row"], weight=1)
        self.sidebar = Sidebar(self, on_select=self.open_note, on_add=self.new_note,
                               on_search=self._on_search, on_note_menu=self.note_menu,
                               on_add_pick=self.new_note_pick, on_reorder=self.reorder_day,
                               on_day_menu=self.day_menu,
                               is_fav=lambda n: n in self._fav_cache, on_star=self.toggle_favorite, on_tag=self.search_tag)
        self.sidebar.grid(**sb_pos)
        if side == "bottom":
            self.sidebar.set_height(self.state_.sidebar_height)
        else:
            self.sidebar.set_width(self.state_.sidebar_width)
        if self._search_kw:                      # 換語言重畫時搜尋還在：框裡的字也要還原，不然清單被濾了卻看不出為什麼
            self.sidebar._search.insert(0, self._search_kw)
        # 左欄和內文之間一條可以拖的分隔線（寬度記在 state.json 的 sidebar_width）
        if side == "bottom":
            self._splitter = tk.Frame(self, height=6, cursor="sb_v_double_arrow", bg=self._splitter_color())
        else:
            self._splitter = tk.Frame(self, width=6, cursor="sb_h_double_arrow", bg=self._splitter_color())
        self._splitter.grid(**sp_pos)
        self._splitter.bind("<B1-Motion>", self._on_splitter_drag)
        self._splitter.bind("<ButtonRelease-1>", lambda _e: self._save_state())
        if not self.state_.sidebar_visible:
            self.sidebar.grid_remove()
            self._splitter.grid_remove()

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(**main_pos, sticky="nsew", padx=(T.PAD, 4) if side == "right" else (4, T.PAD), pady=(6, 3))   # 底邊留少一點，狀態列才會在更下面
        main.grid_rowconfigure(2, weight=1)
        main.grid_columnconfigure(0, weight=1)
        self._main = main
        self._build_topbar(main)
        self.editor = Editor(main, settings.font_family or platform_.ui_font_family(), settings.font_size,
                             on_save=self._save_current, on_zoom=self.zoom,
                             on_open_link=self.open_link,
                             resolve_link=lambda link: self.store.resolve(link),
                             on_paste_image=self.paste_image,
                             format_bar=self.state_.format_bar,
                             on_format_toggle=self._on_format_toggle,
                             on_tag=self.search_tag)
        self.editor.grid(row=2, column=0, sticky="nsew")

    def rebuild_ui(self) -> None:
        """換語言：手上這張先存，砍掉所有元件重畫，再把同一張開回來。設定面板開著就關掉（它也是舊語言畫的）。"""
        self.editor.flush()
        current = self.current
        self.state_ = self.state_.with_(sidebar_width=self.sidebar._width, sidebar_height=self.sidebar._height)   # 重畫用目前的尺寸，不是上次存檔的
        if getattr(self.sidebar, "_search_timer", None) is not None:
            self.sidebar.after_cancel(self.sidebar._search_timer)             # 排程中的搜尋會掛在被砍掉的元件上
        p = getattr(self, "_settings_panel", None)
        if p is not None and p.winfo_exists():
            p.destroy()
        for w in (self.sidebar, self._splitter, self._main):
            w.destroy()
        self._build_ui()
        self._bind_keys()                    # 內文框是新的，鍵要重綁
        if current is not None:
            self.open_note(current)
        else:
            self._refresh_sidebar()

    # ---- 畫面 ----
    def _build_topbar(self, parent) -> None:
        def mk(bar, icon_name, cmd, text="", width=34, plain=True, tip="", **kw):
            """圖示按鈕：圖示由 tools/make_icons.py 畫（assets/icons），找不到圖就顯示 text 的備用字。"""
            style = dict(fg_color="transparent", hover_color=T.ROW_HOVER, text_color=T.TEXT) if plain else {}
            style.update(kw)
            img = T.icon(icon_name, scaling=self._icon_scaling()) if icon_name else None
            btn = ctk.CTkButton(bar, text=text if (img is None or text) else "", image=img, width=width, height=32,
                                corner_radius=8, font=T.ui_font(13), command=cmd, compound="left", **style)
            if tip:
                _tooltip(btn, tip)
            return btn

        # 第一排：日期導覽
        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew")
        nav.grid_columnconfigure(1, weight=1)
        self._nav_prev = mk(nav, "prev", lambda: self.go_day(self._prev_day()), tip=lambda: _("前一天") + f"（{self.keymap.key_of('prev_day')}）")
        self._nav_prev.grid(row=0, column=0)
        self.day_label = ctk.CTkLabel(nav, text="", font=T.ui_font(14, "bold"), text_color=T.TEXT)
        self.day_label.grid(row=0, column=1, sticky="ew")
        self._nav_next = mk(nav, "next", lambda: self.go_day(tomorrow(self.current_day)), tip=lambda: _("後一天") + f"（{self.keymap.key_of('next_day')}）")
        self._nav_next.grid(row=0, column=2)
        mk(nav, "back", self.go_back, text=_("返回"), width=60,
           tip=lambda: _("回上一張筆記") + f"（{self.keymap.key_of('back')}）").grid(row=0, column=3, padx=(8, 0))
        # 語言切換在 ⚙ 設定裡（工具列不放下拉，省位置）
        self._nav = nav
        nav.bind("<Configure>", lambda _e: self._refresh_day_label())   # 視窗變窄就換短一點的寫法

        # 第二排：動作
        act = ctk.CTkFrame(parent, fg_color="transparent")
        act.grid(row=1, column=0, sticky="ew", pady=(6, 8))     # 跟上面日期那排、下面標題框都留白（Peter：功能之間的間距）
        act.grid_columnconfigure(6, weight=1)
        mk(act, "menu", self.toggle_sidebar, tip=lambda: _("收起／展開左欄") + f"（{self.keymap.key_of('sidebar')}）").grid(row=0, column=0, padx=(0, 6))
        mk(act, "today", lambda: self.go_day(date.today()), tip=lambda: _("回到今天") + f"（{self.keymap.key_of('today')}）").grid(row=0, column=1, padx=5)
        mk(act, "cal", self.show_calendar, text=_("月曆"), width=56,
           tip=lambda: _("月曆：哪幾天有筆記、每天用多久") + f"（{self.keymap.key_of('calendar')}）").grid(row=0, column=2, padx=5)
        mk(act, "plus", lambda: self.new_note(date.today()), text=_("新筆記"), width=84, plain=False,
           fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, tip=lambda: _("今天加一張") + f"（{self.keymap.key_of('new_note')}）").grid(row=0, column=3, padx=5)
        mk(act, "tmpl", self.template_menu, text=_("範本 ▾"), width=58,
           tip=_("用範本開一張新筆記（會議紀錄、週報…）")).grid(row=0, column=4, padx=5)
        mk(act, "todo", self.show_todo_list, text=_("未完成"), width=58,
           tip=lambda: _("未完成清單：所有筆記裡還沒打勾的") + f"（{self.keymap.key_of('todo_list')}）").grid(row=0, column=5, padx=5)
        # 復原／重做搬到內文上方的格式列（文字按鈕，箭頭圖示 Peter 說看不懂），這一排才放得下 640 寬
        mk(act, "attach", self.attach_file, tip=_("插入檔案（複製一份到 attachments）")).grid(row=0, column=7, padx=5)
        mk(act, "trash", self.clear_menu, tip=_("清除…")).grid(row=0, column=8, padx=5)
        mk(act, "settings", self.open_settings, tip=_("設定")).grid(row=0, column=9, padx=(6, 0))

    SIDEBAR_DAYS = 45            # 左欄一次畫幾天（幾千張全畫會卡住主迴圈 30 秒）
    SIDEBAR_SEARCH_MAX = 200     # 搜尋結果最多列幾張
    SIDEBAR_MAX_NOTES = 1000     # 左欄一次最多列幾張。Tk 的 grid 一欄最多 10000 列，超過會「row out of bounds」整欄壞掉

    @staticmethod
    def _cap(groups: dict, limit: int) -> tuple[dict, int]:
        """最多留 limit 張；回 (留下的, 沒列出的張數)。"""
        shown, n, hidden = {}, 0, 0
        for d, refs in groups.items():
            take = refs[: max(0, limit - n)]
            if take:
                shown[d] = take
            n += len(take)
            hidden += len(refs) - len(take)
        return shown, hidden

    SEARCH_BUSY_MIN = 300        # 超過這麼多張時搜尋要讀每一張，給個「搜尋中…」

    def _refresh_sidebar(self) -> None:
        self.sidebar.searching = bool(self._search_kw.strip())   # 搜尋結果是過濾過的，左欄不給拖拉排序
        self._fav_cache = set(self.store.favorites())              # 每列畫星號時查這個，不用每列讀一次檔
        if self._search_kw.strip() and self.store.count_notes() > self.SEARCH_BUSY_MIN:
            with self._busy(_("搜尋中")):
                groups = self.store.search(self._search_kw)
        else:
            groups = self.store.search(self._search_kw)
        if self._search_kw.strip():
            shown, hidden = self._cap(groups, self.SIDEBAR_SEARCH_MAX)
            self.sidebar.refresh(shown, self.current, hidden=hidden)
            return
        # 待辦事項永遠在最上面（就算還沒寫也要有那一列可以點）；它不算在「最近幾天」裡
        todo = groups.pop(TODO_DAY, None) or [NoteRef(TODO_ID, _("點這裡寫待辦"))]
        limit = self._sidebar_limit
        days = list(groups.keys())
        shown = {TODO_DAY: todo}
        favs = self.store.favorite_refs()
        if favs:
            shown[FAV_DAY] = favs                   # ★ 我的最愛：待辦事項下面、日期上面
        shown.update({d: groups[d] for d in days[:limit]})
        if self.current and self.current.day in groups and self.current.day not in shown:
            shown[self.current.day] = groups[self.current.day]          # 正在看的那天一定要在
        shown, hidden = self._cap(shown, self.SIDEBAR_MAX_NOTES)
        more = len([d for d in days[limit:] if d not in shown])
        self.sidebar.refresh(shown, self.current, more=more, on_more=self._sidebar_more, hidden=hidden)
        self.sidebar.set_tags(self.store.recent_tags())

    def _on_focus_in(self, _e=None) -> None:
        import time
        now = time.monotonic()
        if now - self._last_focus_check < 5:
            return
        self._last_focus_check = now
        if self.store.refresh_if_changed():
            applog.info("資料夾被外部改動，重掃索引")
            self._refresh_sidebar()

    def _sidebar_more(self) -> None:
        self._sidebar_limit += self.SIDEBAR_DAYS
        self._refresh_sidebar()

    def _refresh_day_label(self) -> None:
        """上方日期：「2026/10/29（四） 今天」，視窗窄就拿掉星期。筆記編號不顯示（Peter：背景記著就好）。
        可用寬度用導覽列減掉兩個箭頭算，不用標籤自己的寬度（文字變長會把標籤撐大，照它算會來回跳）。"""
        if self.current is None:
            return
        d = self.current_day
        tag = _(" 今天") if d == date.today() else ""
        cands = (f"{T.fmt_day(d)}{tag}", f"{T.fmt_day(d, False)}{tag}", T.fmt_day(d, False))
        avail = self._nav.winfo_width() - self._nav_prev.winfo_reqwidth() - self._nav_next.winfo_reqwidth() - 16
        text = cands[-1]
        if avail > 40:
            f = self.day_label.cget("font")
            text = next((c for c in cands if f.measure(c) <= avail), cands[-1])
        else:
            text = cands[0]                      # 還沒排版（寬度 1）：先放完整的
        if self.day_label.cget("text") != text:
            self.day_label.configure(text=text)

    # ---- 開哪張 ----
    @property
    def current_day(self) -> date:
        return self.current.day if self.current else date.today()

    def _open_initial(self) -> None:
        day = self.state_.last_day_or_none() or date.today()
        self.go_day(day if self.store.list_notes(day) else date.today())

    def _prev_day(self) -> date:
        return date.today() if self.current_day == TODO_DAY else yesterday(self.current_day)   # 待辦事項的「前一天」＝今天

    def go_day(self, day: date, pulse: bool = False) -> None:
        """跳到某一天：有筆記開第一張，沒有就給一張新的（不打字不會建檔）。pulse：左欄那列閃一下（月曆、連結跳過來時）。"""
        refs = self.store.list_notes(day)
        self.open_note(refs[0].id if refs else self.store.next_id(day), pulse=pulse)

    def _flush_or_rescue(self) -> None:
        """先存；存不進去（磁碟拔掉、加密失敗）就把手上的字寫成救援檔並提示，呼叫端接著才可以把內容換掉。"""
        self.editor.flush()
        if self.editor.is_dirty() and self.current is not None:
            rescue = self._write_rescue()
            messagebox.showwarning(APP_NAME, _("這張筆記存不進去：{0}\n").format(self.editor.last_error)
                                   + _("已另存救援檔：{0}").format(rescue), parent=self)

    def open_note(self, nid: NoteId, pulse: bool = False) -> None:
        if self.current is not None and self.current != nid and not getattr(self, "_going_back", False):
            self._back.append(self.current)        # 「返回」用
            del self._back[:-50]
        if self.current is not None:
            self._flush_or_rescue()                # 同一張重開也要：存不進去時先寫救援檔，不讓磁碟上的舊版蓋掉畫面上的字
        else:
            self.editor.flush()
        self.current = nid
        text, ok = self.store.try_load(nid)
        self.editor.set_text(text, read_only=not ok)   # 解不開的只能看，不會被存檔蓋掉
        applog.info("開啟 %s-%03d 可讀=%s 長度=%d", nid.day, nid.seq, ok, len(text))
        if pulse:
            self.after(0, lambda: self.sidebar.pulse(nid))     # 左欄畫好之後再閃（anim.APPEAR）
        self._refresh_day_label()
        if self.sidebar.has(nid):
            self.sidebar.set_selected(nid)            # 已經在左欄：只換選取，不整欄重畫
        else:
            self._refresh_sidebar()
        self.editor.focus()
        self._save_state()                   # 記住看到哪一天；直接關機也不會丟

    def new_note(self, day: date) -> None:
        """按「新筆記」：開下一個編號，標題預設「筆記N」（N 跟編號一樣，背景記著、畫面不顯示），反白等你改。"""
        if day == TODO_DAY:                      # 待辦事項只有一張：在它上面按「新筆記」就加到今天
            day = date.today()
        self.editor.flush()
        nid = self.store.next_id(day)
        self.open_note(nid)
        self.editor.set_default_title(_("筆記{0}").format(nid.seq))

    def reorder_day(self, day: date, seqs: list[int]) -> None:
        """左欄長按拖拉放開：記住這一天的顯示順序（只改顯示，檔名與編號不動）。"""
        self.editor.flush()
        self.store.set_order(day, seqs)
        applog.info("排序 %s → %s", day, seqs)
        self._refresh_sidebar()

    def new_note_pick(self) -> None:
        """左下「額外新增」：跳月曆選一天，再在那天開新筆記（補以前的紀錄用）。"""
        from . import datepick
        d = datepick.ask_date(self, self.current_day, quiet=_quiet_dialog)
        if d is not None:
            self.new_note(d)

    def _save_current(self, text: str) -> None:
        if self.current is None:
            return
        is_new = not self.store.path_for(self.current).is_file()   # 第一次存：左欄還沒有它，存完要整欄重畫
        try:
            self.store.snapshot(self.current, text)  # 存之前留一份版本（內容有變才留）
        except Exception:
            applog.exception("快照失敗（不影響存檔）")   # history 寫不進去不能擋正式存檔
        self.store.save(self.current, text)
        applog.info("存檔 %s-%03d 長度=%d", self.current.day, self.current.seq, len(text))
        # 左欄：這張已經在清單裡就只改它的字（每 1.2 秒重畫整欄太重）；是新的一張才整欄重畫。
        # 檔案到這裡已經存好了，左欄畫壞不能算存檔失敗（不然編輯器每 1.2 秒重試一次，愈試愈慢）
        try:
            if not self.sidebar.set_title(self.current, title_of(text)) and is_new:
                self._refresh_sidebar()          # 不是新的卻不在左欄＝被搜尋濾掉或超過上限：不重畫（會卡 1 秒）
                self.sidebar.pulse(self.current) # 新的一列剛出現：閃一下
        except Exception:
            applog.exception("左欄更新失敗（檔案已存好）")

    def _on_search(self, kw: str) -> None:
        self._search_kw = kw
        self._refresh_sidebar()

    def search_tag(self, tag: str) -> None:
        """Ctrl+點內文的 #標籤：左欄搜尋框填入那個標籤。再點一次（已經在搜同一個）就清掉。"""
        if not self.state_.sidebar_visible:
            self.toggle_sidebar()
        self.sidebar.set_search("" if self._search_kw.strip() == tag else tag)

    def focus_search(self) -> None:
        if not self.state_.sidebar_visible:
            self.toggle_sidebar()
        self.sidebar.focus_search()

    # ---- 右鍵選單（日期列）----
    def day_menu(self, day: date, x: int, y: int) -> None:
        m = tk.Menu(self, tearoff=0, font=(T.UI_FONT_FAMILY, 10))
        m.add_command(label=_("在這天新增"), command=lambda: self.new_note(day))
        m.add_command(label=_("匯出這一天（合成一個 .md）…"), command=lambda: self.export_day(day))
        m.add_separator()
        m.add_command(label=_("清掉 {0} 整天").format(T.fmt_day(day, False)), command=lambda: self.clear_day(day))
        m.tk_popup(x, y)

    def export_day(self, day: date) -> None:
        self.editor.flush()
        if not self.store.list_notes(day):
            messagebox.showwarning(APP_NAME, _("這一天沒有筆記。"), parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, title=_("匯出這一天"), initialfile=f"{day.isoformat()}.md",
                                            defaultextension=".md", filetypes=[(_("純文字"), "*.md *.txt")])
        if path:
            n = self.store.export_day(day, Path(path))
            self.editor._set_status(_("已匯出 {0} 張").format(n), fade=True)

    # ---- 右鍵選單（筆記列）----
    def note_menu(self, nid: NoteId, x: int, y: int) -> None:
        m = tk.Menu(self, tearoff=0, font=(T.UI_FONT_FAMILY, 10))
        m.add_command(label=_("開啟"), command=lambda: self.open_note(nid))
        m.add_command(label=_("複製到今天"), command=lambda: self.copy_to_today(nid))
        m.add_command(label=_("匯出這張…"), command=lambda: self.export_note(nid))
        m.add_command(label=_("舊版本…"), command=lambda: self.show_versions(nid))
        m.add_command(label=_("取消我的最愛") if self.store.is_favorite(nid) else _("加入我的最愛"),
                      command=lambda: self.toggle_favorite(nid))
        m.add_command(label=_("複製筆記連結 [[標題]]"), command=lambda: self.copy_note_link(nid))
        share = tk.Menu(m, tearoff=0, font=(T.UI_FONT_FAMILY, 10))
        share.add_command(label=_("用郵件寄出（開郵件程式）"), command=lambda: self.share_mail(nid))
        share.add_command(label=_("複製到 Google Drive 資料夾"), command=lambda: self.share_drive(nid))
        m.add_cascade(label=_("分享"), menu=share)
        m.add_separator()
        m.add_command(label=_("刪除這張"), command=lambda: self.delete_note(nid))
        m.add_command(label=_("清掉 {0} 整天").format(T.fmt_day(nid.day, False)), command=lambda: self.clear_day(nid.day))
        m.tk_popup(x, y)

    def show_versions(self, nid: NoteId) -> None:
        """右鍵「舊版本…」：列出這張的快照（每次內容有變且隔 10 分鐘以上就留一份），可以看、可以還原。"""
        from . import versions
        self.editor.flush()
        versions.show(self, self.store, nid, on_restore=self.restore_version, quiet=_quiet_dialog)

    def restore_version(self, nid: NoteId, path: Path) -> None:
        text = self.store.load_snapshot(path)
        self.editor.flush()
        self.store.snapshot(nid, text, force=True)      # 現在的內容先留一份，還原錯了還能再還回來
        self.store.save(nid, text)
        applog.info("還原舊版 %s-%03d ← %s", nid.day, nid.seq, path.name)
        if nid == self.current:
            self.editor.set_text(text)
        else:
            self.open_note(nid)
        self._refresh_sidebar()
        self.editor._set_status(_("已還原舊版本"), fade=True)

    def _share_text(self, nid: NoteId):
        self.editor.flush()
        text, ok = self.store.try_load(nid)
        if not ok or not text.strip():
            messagebox.showwarning(APP_NAME, _("這張是空的或解不開，沒有東西可以分享。"), parent=self)
            return None
        return text

    SHARE_MAIL_MAX = 1800        # mailto 網址太長有些郵件程式會吃不下；超過就只帶前面一段並提醒用匯出

    def share_mail(self, nid: NoteId) -> None:
        """開系統預設的郵件程式，主旨＝標題、內文＝去掉記號的純文字（mailto 不能帶附件）。"""
        text = self._share_text(nid)
        if text is None:
            return
        from urllib.parse import quote
        from .. import markup
        subject = title_of(text) or T.fmt_day(nid.day, False)
        body = markup.plain(text.split("\n", 1)[1] if "\n" in text else "")
        cut = len(body) > self.SHARE_MAIL_MAX
        if cut:
            body = body[: self.SHARE_MAIL_MAX] + "\n…"
        url = f"mailto:?subject={quote(subject)}&body={quote(body.replace(chr(10), chr(13) + chr(10)))}"
        platform_.open_path(url)
        if cut:
            messagebox.showinfo(APP_NAME, _("筆記太長，郵件只帶了前面一段。完整的請用「匯出這張」存成檔案再附加。"), parent=self)

    def share_drive(self, nid: NoteId) -> None:
        """存一份 .md 到 Google Drive 桌面版的同步資料夾（找得到就直接存，找不到就讓你選資料夾）。"""
        text = self._share_text(nid)
        if text is None:
            return
        import re as _re
        folder = platform_.google_drive_dir()
        if folder is None:
            chosen = filedialog.askdirectory(parent=self, title=_("找不到 Google Drive 資料夾，請自己選（或任何要同步的資料夾）"))
            if not chosen:
                return
            folder = Path(chosen)
        safe = _re.sub(r'[\\/:*?"<>|]', "_", title_of(text))
        dest = folder / f"{nid.day.isoformat()}_{nid.seq:03d}_{safe}.md"
        self.store.export_note(nid, dest)
        self.editor._set_status(_("已存到 {0}").format(folder.name), fade=True)
        platform_.open_folder(folder)

    def copy_to_today(self, nid: NoteId) -> None:
        self.editor.flush()                  # 先把手上這張存掉，next_id 才不會跟它撞號
        text, ok = self.store.try_load(nid)
        if not ok or not text.strip():
            messagebox.showwarning(APP_NAME, _("這張解不開或是空的，沒有東西可以複製。"), parent=self)
            return
        today = date.today()
        new = self.store.next_id(today)
        self.store.save(new, text)
        self.open_note(new)

    def delete_note(self, nid: NoteId) -> None:
        title = next((r.title for r in self.store.list_notes(nid.day) if r.id == nid), "")
        if not messagebox.askyesno(APP_NAME, _("刪除「{0}」？（會先搬到垃圾桶，設定裡可以還原）").format(title), parent=self):
            return
        self.sidebar.animate_remove(nid, lambda: self._delete_now(nid))   # 列先收合，再真的刪（anim.REMOVE）

    def _delete_now(self, nid: NoteId) -> None:
        if nid == self.current:
            self.editor.set_text("")
        self.store.delete(nid)
        self._refresh_sidebar()
        if nid == self.current:
            self.go_day(nid.day)

    def restore_last_deleted(self) -> None:
        """設定面板「還原上一次刪除」：把垃圾桶裡最新的那張搬回它原本的日期（編號被佔走就接在最後）。"""
        nid = self.store.restore_last_deleted()
        if nid is None:
            messagebox.showinfo(APP_NAME, _("垃圾桶是空的。"), parent=self)
            return
        self._refresh_sidebar()
        self.open_note(nid)

    # ---- 清除（都搬到 .app/trash，不是真的刪）----
    def clear_menu(self) -> None:
        dlg = ctk.CTkToplevel(self)
        dlg.title(_("清除"))
        dlg.attributes("-topmost", True)
        _quiet_dialog(dlg)
        ctk.CTkLabel(dlg, text=_("清掉的東西會先搬到 .app/trash，不會直接消失。"),
                     font=T.ui_font(12), text_color=T.TEXT_MUTED).pack(padx=16, pady=(14, 8))

        def row(text, cmd, danger=False):
            ctk.CTkButton(dlg, text=text, font=T.ui_font(13), height=34, corner_radius=8,
                          fg_color=T.DANGER if danger else None,
                          command=lambda: (dlg.destroy(), cmd())).pack(fill="x", padx=16, pady=4)

        row(_("清空目前這張"), self.clear_current)
        row(_("清掉 {0} 整天").format(T.fmt_day(self.current_day, False)), lambda: self.clear_day(self.current_day))
        row(_("清掉全部筆記"), self.clear_all, danger=True)
        ctk.CTkButton(dlg, text=_("取消"), fg_color="transparent", text_color=T.TEXT_MUTED,
                      hover_color=T.ROW_HOVER, command=dlg.destroy).pack(pady=(4, 12))
        T.center_over(dlg, self)                 # 按鈕都放好了才知道多大，最後再置中

    def clear_current(self) -> None:
        if self.current is None:
            return
        nid = self.current
        self.sidebar.animate_remove(nid, lambda: self._delete_now(nid))   # 先重畫左欄：接著開的那張編號可能跟刪掉的一樣

    def clear_day(self, day: date) -> None:
        n = len(self.store.list_notes(day))
        if n and not messagebox.askyesno(APP_NAME, _("清掉 {0} 的 {1} 張筆記？").format(T.fmt_day(day, False), n), parent=self):
            return
        if self.current_day != day:
            self._flush_or_rescue()          # 清的是別天：手上這張還沒存的字先存起來；存不進去就寫救援檔
        self.editor.set_text("")
        self.store.delete_day(day)
        self._refresh_sidebar()
        self.go_day(day)

    def clear_all(self) -> None:
        n = self.store.count_notes()
        if n and not messagebox.askyesno(APP_NAME, _("清掉全部 {0} 張筆記？（附件保留）").format(n), parent=self):
            return
        self.editor.set_text("")             # 全清，手上這張也不用存
        with self._busy(_("清除中")) as progress:
            self.store.delete_all(progress)
        self._refresh_sidebar()
        self.go_day(date.today())

    # ---- 會花時間的動作：畫面上給個「處理中… 120／3120」，不然使用者以為卡住 ----
    from contextlib import contextmanager

    @contextmanager
    def _busy(self, what: str):
        """用法：with self._busy("加密中") as progress: store.set_encrypt(on, progress)
        progress(做了幾個, 總共幾個) 由 store 在迴圈裡呼叫；這裡每 0.1 秒更新一次字並讓畫面重畫。
        動作是在主執行緒同步做的（store 不是執行緒安全的），所以沒有動畫，只有進度字和等待游標。"""
        import time
        box = ctk.CTkFrame(self, corner_radius=T.RADIUS, fg_color=T.SIDEBAR_BG, border_width=1, border_color=T.ACCENT)
        lbl = ctk.CTkLabel(box, text=f"{what}…", font=T.ui_font(13, "bold"), text_color=T.TEXT)
        lbl.pack(padx=28, pady=16)
        box.place(relx=0.5, rely=0.5, anchor="center")
        self.configure(cursor="watch")
        self.update_idletasks()
        last = [0.0]

        def progress(done: int, total: int) -> None:
            now = time.monotonic()
            if now - last[0] < 0.1:
                return
            last[0] = now
            lbl.configure(text=_("{0}… {1}／{2}").format(what, done, total) if total else f"{what}… {done}")
            self.update_idletasks()
        try:
            yield progress
        finally:
            box.destroy()
            self.configure(cursor="")

    # ---- 附件與連結 ----
    def attach_file(self) -> None:
        if self.editor.read_only:
            messagebox.showwarning(APP_NAME, _("這張是唯讀的（解不開或較新版本），不能插入附件。"), parent=self)
            return
        path = filedialog.askopenfilename(parent=self, title=_("插入檔案連結（會複製一份到 attachments）"))
        if not path:
            return
        rel = self.store.add_attachment(Path(path))
        self.editor.insert_own_line(f"[{Path(path).name}]({rel.as_posix()})\n")

    TEXT_EXT = (".md", ".txt")
    ATTACH_MAX_BYTES = 50_000_000     # 拖進來的檔超過這個大小先問一下（複製是同步的，太大會等）

    def _on_drop(self, paths: list[Path]) -> None:
        """拖檔案進視窗：只收 .md／.txt（IMPORT_MAX_BYTES 以內），匯成「今天」的筆記（最後一張打開）。
        其他檔（pdf、word、圖）不收——要放附件請用 📎 或 Ctrl+V 貼圖。讀不了、太大、不是文字檔、資料夾都列出來提示。"""
        self.editor.flush()
        last, bad = None, []
        for p in paths:
            if not p.is_file() or p.suffix.lower() not in self.TEXT_EXT:
                bad.append(p.name)
                continue
            try:
                nid = self.store.import_file(p, date.today())
                if nid is not None:
                    last = nid
            except (UnicodeDecodeError, OSError):
                applog.exception("拖進來的檔讀不了 %s", p)
                bad.append(p.name)
        applog.info("拖進 %d 個檔，匯入筆記=%s 跳過=%d", len(paths), last, len(bad))
        if last is not None:
            self._refresh_sidebar()
            self.open_note(last)
        if bad:
            messagebox.showwarning(APP_NAME, _("只收 .md／.txt 文字檔（{0} MB 以內）；這些沒收進來：\n").format(IMPORT_MAX_BYTES // (1024 * 1024))
                                   + "\n".join(bad), parent=self)

    def paste_image(self, img) -> Optional[str]:
        """剪貼簿的圖（截圖）→ 存成 attachments/貼圖_時間.png，回要插進筆記的那行。"""
        try:
            rel = self.store.add_image(img)
        except Exception as e:
            applog.exception("貼圖存檔失敗")
            messagebox.showerror(APP_NAME, _("截圖存不進去：{0}").format(e), parent=self)
            return None
        applog.info("貼圖 %s", rel)
        return f"[{rel.name}]({rel.as_posix()})"

    EXEC_EXT = {".exe", ".bat", ".cmd", ".ps1", ".lnk", ".vbs", ".js", ".msi", ".scr", ".com",
                ".hta", ".pif", ".reg", ".url", ".wsf", ".wsh", ".vbe", ".jse", ".cpl", ".inf", ".appref-ms",
                ".py", ".pyw", ".jar", ".psm1", ".ps1xml", ".msc", ".scf", ".iso", ".img"}   # 開之前會先問（QA 審查補齊）

    def open_link(self, link: str) -> None:
        if link.startswith("note:"):               # [[標題]]：跳到另一張
            self.jump_to_note(link[5:])
            return
        from .. import platform_
        p = self.store.resolve(link)
        if p.exists():
            if p.suffix.lower() in self.EXEC_EXT and not messagebox.askyesno(
                    APP_NAME, _("這是可以執行的檔案：{0}\n確定要執行？").format(p), parent=self):
                return                              # 筆記可能是別人匯入的，Ctrl+點 不能什麼都直接跑（PM 審查）
            platform_.open_path(p)
        elif link.startswith(("http://", "https://")):
            platform_.open_path(link)
        else:
            messagebox.showwarning(APP_NAME, _("找不到：{0}").format(p), parent=self)

    # ---- 匯入／匯出（純文字 .md）----
    def export_note(self, nid: Optional[NoteId] = None) -> None:
        nid = nid or self.current
        if nid is None:
            return
        self.editor.flush()
        text, ok = self.store.try_load(nid)
        if not ok or not text.strip():
            messagebox.showwarning(APP_NAME, _("這張是空的或解不開，沒有東西可以匯出。"), parent=self)
            return
        import re as _re
        safe = _re.sub(r'[\/:*?"<>|]', "_", title_of(text))        # 檔名不能有這些（「會議 10:30」這種標題很常見）
        default = f"{nid.day.isoformat()}_{nid.seq:03d}_{safe}.md"
        path = filedialog.asksaveasfilename(parent=self, title=_("匯出這張筆記"), initialfile=default,
                                            defaultextension=".md", filetypes=[(_("純文字"), "*.md *.txt")])
        if path:
            self.store.export_note(nid, Path(path))

    def export_all(self) -> None:
        chosen = filedialog.askdirectory(parent=self, title=_("全部筆記要匯出到哪個資料夾（純文字）"))
        if not chosen:
            return
        self.editor.flush()
        with self._busy(_("匯出中")) as progress:
            n = self.store.export_plain(Path(chosen), progress)
        messagebox.showinfo(APP_NAME, _("已匯出 {0} 張筆記到\n{1}").format(n, chosen), parent=self)

    def import_files(self) -> None:
        """挑一個或多個 .md / .txt，匯進目前這一天。"""
        paths = filedialog.askopenfilenames(parent=self, title=_("匯入筆記檔（可多選）"),
                                            filetypes=[(_("純文字"), "*.md *.txt"), (_("全部"), "*.*")])
        if not paths:
            return
        self.editor.flush()
        day = self.current_day
        last = None
        for p in paths:
            try:
                nid = self.store.import_file(Path(p), day)
            except UnicodeDecodeError:
                messagebox.showwarning(APP_NAME, _("不是 UTF-8 純文字，跳過：{0}").format(p), parent=self)
                continue
            except OSError as e:                     # 太大（storage.TooBig）或讀不了
                messagebox.showwarning(APP_NAME, _("沒收進來（超過 {0} MB 或讀不了）：{1}\n{2}").format(IMPORT_MAX_BYTES // (1024 * 1024), p, e), parent=self)
                continue
            last = nid or last
        self._refresh_sidebar()
        if last:
            self.open_note(last)

    def import_folder(self) -> None:
        """匯入「匯出全部」產生的資料夾（日期資料夾各回各的日期）。"""
        chosen = filedialog.askdirectory(parent=self, title=_("要匯入的資料夾（匯出全部產生的那種）"))
        if not chosen:
            return
        self.editor.flush()
        with self._busy(_("匯入中")) as progress:
            done, skipped = self.store.import_folder(Path(chosen), progress=progress)
        self._refresh_sidebar()
        msg = _("匯入 {0} 張。").format(done)
        if skipped:
            msg += _("\n另有 {0} 張 .note 是別台電腦加密的，解不開，已跳過。").format(skipped)
        messagebox.showinfo(APP_NAME, msg, parent=self)

    # ---- 外觀與設定 ----
    def zoom(self, delta: int) -> None:
        size = max(T.MIN_FONT, min(T.MAX_FONT, self.settings.font_size + delta))
        if size == self.settings.font_size:
            return
        self.settings = self.settings.with_(font_size=size)
        self.editor.set_font_size(size)
        self.settings.save()

    def toggle_sidebar(self) -> None:
        visible = not self.sidebar.winfo_ismapped()
        if visible:
            self.sidebar.grid(); self._splitter.grid()
        else:
            self.sidebar.grid_remove(); self._splitter.grid_remove()
        self.state_ = self.state_.with_(sidebar_visible=visible)
        self._save_state()

    def _splitter_color(self) -> str:
        return T.SIDEBAR_BG[1] if ctk.get_appearance_mode() == "Dark" else T.SIDEBAR_BG[0]

    def _fit_sidebar(self, e=None) -> None:
        """左欄最寬 = 視窗寬 − 330（工具列那排至少要這麼寬）；放下面時寬＝視窗寬、最高 = 視窗高 − 300。
        還原上次尺寸、視窗縮小都經過這裡。"""
        if e is not None and e.widget is not self:
            return
        if self.state_.sidebar_side == "bottom":
            self.sidebar.set_width(self.winfo_width(), clamp=False)       # 列標題的「…」照實際寬算
            room = self.winfo_height() - 300
            if room > T.SIDEBAR_MIN_H and self.sidebar._height > room:
                self.sidebar.set_height(room)
            return
        room = self.winfo_width() - 330
        if room > T.SIDEBAR_MIN and self.sidebar._width > room:
            self.sidebar.set_width(room)

    def _on_splitter_drag(self, e) -> None:
        """拖分隔線：左欄寬（放下面時是高）跟著滑鼠。範圍 theme.SIDEBAR_MIN～MAX／SIDEBAR_MIN_H～MAX_H。"""
        side = self.state_.sidebar_side
        if side == "bottom":
            h = min(self.winfo_rooty() + self.winfo_height() - e.y_root, self.winfo_height() - 300)
            self.sidebar.set_height(h)
            self.state_ = self.state_.with_(sidebar_height=self.sidebar._height)
            return
        if side == "right":
            w = self.winfo_rootx() + self.winfo_width() - e.x_root
        else:
            w = e.x_root - self.winfo_rootx()
        self.sidebar.set_width(min(w, self.winfo_width() - 330))   # 內文那邊至少留 330 給工具列
        self.state_ = self.state_.with_(sidebar_width=self.sidebar._width)

    def _on_format_toggle(self, visible: bool) -> None:
        self.state_ = self.state_.with_(format_bar=visible)
        self._save_state()

    def _save_state(self) -> None:
        """隨手存狀態（Windows 直接關機時不會走 _on_close，所以不能只靠關閉時存）。"""
        try:
            self.state_ = self.state_.with_(geometry=self.geometry(), last_day=self.current_day.isoformat(),
                                            sidebar_width=self.sidebar._width, sidebar_height=self.sidebar._height)
            self.state_.save(self.store.root)
        except Exception:
            pass

    def set_theme(self, theme: str) -> None:
        self.settings = self.settings.with_(theme=theme)
        ctk.set_appearance_mode(theme)
        self.editor.refresh_theme()
        self._refresh_sidebar()              # 左欄列是 tk.Label，顏色要重算
        self._splitter.configure(bg=self._splitter_color())
        self.settings.save()

    def set_language(self, lang: str) -> None:
        """畫面語言：記進設定、載入翻譯表、整個視窗重畫（在設定面板裡切）。"""
        if lang == self.settings.lang:
            return
        from .. import i18n
        self.settings = self.settings.with_(lang=lang)
        self.settings.save()
        i18n.set_language(lang)
        applog.info("換語言 → %s", lang)
        self.store.invalidate_caches()     # 左欄快取裡有翻譯過的「（解不開）」「（空白）」，要重算
        panel_open = getattr(self, "_settings_panel", None) is not None and self._settings_panel.winfo_exists()
        self.rebuild_ui()
        if panel_open:
            self.open_settings()            # 使用者是在面板裡切的：面板用新語言重開，不要突然不見

    def _bind_keys(self) -> None:
        """照 keymap 綁視窗層的快捷鍵（新筆記、今天、搜尋、左欄、前後一天、縮放）；內文框的交給 editor.bind_keys。改鍵時先解掉舊的。"""
        for seq, fid in getattr(self, "_key_seqs", ()):
            tk.Misc.unbind(self, seq, fid)             # 帶 funcid 才會刪掉 Tcl 命令（CTk 的 unbind 不接受）
        self._key_seqs = []
        actions = {
            "new_note": lambda _e: self.new_note(date.today()),
            "today": lambda _e: self.go_day(date.today()),
            "search": lambda _e: self.focus_search(),
            "sidebar": lambda _e: self.toggle_sidebar(),
            "prev_day": lambda _e: self.go_day(self._prev_day()),
            "next_day": lambda _e: self.go_day(tomorrow(self.current_day)),
            "zoom_in": lambda _e: self.zoom(1),
            "zoom_out": lambda _e: self.zoom(-1),
            "calendar": lambda _e: self.show_calendar(),
            "todo_list": lambda _e: self.show_todo_list(),
            "back": lambda _e: self.go_back(),
        }
        for action, fn in actions.items():
            for seq in keys.sequences(self.keymap.key_of(action)):
                self._key_seqs.append((seq, self.bind(seq, fn)))
        self.editor.bind_keys(self.keymap)

    def set_keys(self, km: keys.KeyMap) -> None:
        """改快捷鍵：記進設定（只存跟預設不同的）、重綁視窗與內文框的鍵。工具列提示是函式，會自己讀新的鍵，不用重畫。"""
        self.keymap = km
        self.settings = self.settings.with_(keys=km.overrides())
        self.settings.save()
        self._bind_keys()
        applog.info("快捷鍵 → %s", km.overrides() or "預設")

    def set_sidebar_side(self, side: str) -> None:
        """左欄放左／右／下：記進 state.json，整個視窗重畫（設定面板開著就重開）。"""
        if side not in ("left", "right", "bottom") or side == self.state_.sidebar_side:
            return
        self.state_ = self.state_.with_(sidebar_side=side, sidebar_visible=True)
        self._save_state()
        applog.info("左欄位置 → %s", side)
        panel_open = getattr(self, "_settings_panel", None) is not None and self._settings_panel.winfo_exists()
        self.rebuild_ui()
        if panel_open:
            self.open_settings()

    def _icon_scaling(self) -> float:
        """螢幕縮放（125%／150%）：圖示要縮到這個倍數的像素才不會糊或鋸齒。"""
        try:
            return float(ctk.ScalingTracker.get_window_scaling(self))
        except Exception:
            return 1.0

    @staticmethod
    def _dock_positions(side: str):
        """左欄、分隔線、內文在 grid 裡的位置（row／column／sticky）。left：欄 0,1,2；right：欄 2,1,0；bottom：列 2,1,0。"""
        if side == "right":
            return dict(row=0, column=2, sticky="nse"), dict(row=0, column=1, sticky="ns"), dict(row=0, column=0)
        if side == "bottom":
            return dict(row=2, column=0, sticky="sew"), dict(row=1, column=0, sticky="ew"), dict(row=0, column=0)
        return dict(row=0, column=0, sticky="nsw"), dict(row=0, column=1, sticky="ns"), dict(row=0, column=2)

    def toggle_favorite(self, nid: NoteId) -> None:
        """左欄星號（或右鍵）：加入／取消我的最愛；最上面「★ 我的最愛」那組跟著出現／消失。"""
        on = not self.store.is_favorite(nid)
        self.store.set_favorite(nid, on)
        applog.info("我的最愛 %s %s", "加入" if on else "取消", nid)
        self._refresh_sidebar()

    # ---- 查新版、啟動提醒、使用教學 ----
    def start_update_check(self, force: bool = False, fetch=None, notify: bool = False) -> None:
        """背景執行緒去 GitHub 看有沒有新版（執行緒裡不碰 Tk；結果用 after 輪詢拿回來）。
        notify：查到比現在新、開關開著、而且不是「這一版不再提醒」的那版，就跳提醒。fetch 給測試用。"""
        if self._update["status"] == "checking":
            return
        if self._update["status"] != "idle" and not force:
            return
        self._update = {"status": "checking", "info": None}
        p = getattr(self, "_settings_panel", None)
        if p is not None and p.winfo_exists():
            p.refresh_update()
        box: dict = {}
        fetch_fn = fetch or update.fetch

        def work():
            box["r"] = update.check(__version__, fetch_fn)

        threading.Thread(target=work, daemon=True, name="update-check").start()

        def poll():
            if "r" not in box:
                self.after(300, poll)
                return
            status, info = box["r"]
            self._update = {"status": status, "info": info}
            applog.info("查新版：%s %s", status, info)
            panel = getattr(self, "_settings_panel", None)
            if panel is not None and panel.winfo_exists():
                panel.refresh_update()
            if (notify and info is not None and info.newer and self.settings.update_notify
                    and info.version != self.settings.update_skip):
                self._update_prompt = UpdatePrompt(self, info)

        self.after(300, poll)

    def set_update_notify(self, on: bool) -> None:
        self.settings = self.settings.with_(update_notify=on)
        self.settings.save()

    def show_tour(self) -> None:
        """使用教學（第一次開自動跳；設定裡「再看一次」）。"""
        t = getattr(self, "_tour", None)
        if t is not None and t.winfo_exists():
            t.lift(); t.focus_force()
            return
        self._tour = TourDialog(self)

    # ---- 筆記之間跳來跳去 ----
    def jump_to_note(self, ref: str) -> None:
        """[[標題]] 或 [[2026-10-29/003]]：找到就開（open_note 會把現在這張記進「返回」）。"""
        nid = self.store.find_note(ref)
        if nid is None:
            self.editor._set_status(_("找不到筆記「{0}」").format(ref), fade=True)
            return
        self.open_note(nid, pulse=True)

    def go_back(self) -> None:
        """回上一張看過的筆記（連結跳過去、月曆點日期之後用）。"""
        while self._back:
            nid = self._back.pop()
            if nid == self.current or not (self.store.exists(nid) or nid == TODO_ID):
                continue
            self._going_back = True
            try:
                self.open_note(nid, pulse=True)
            finally:
                self._going_back = False
            return
        self.editor._set_status(_("沒有上一張了"), fade=True)

    def copy_note_link(self, nid: NoteId) -> None:
        ref = next((r for r in self.store.list_notes(nid.day) if r.id == nid), None)
        title = (ref.title if ref else "").strip()
        link = f"[[{title}]]" if title and not title.startswith("（") else f"[[{nid.day.isoformat()}/{nid.seq:03d}]]"
        self.clipboard_clear(); self.clipboard_append(link)
        self.editor._set_status(_("已複製 {0}，貼到別張筆記裡，Ctrl+點就會跳過來").format(link), fade=True)

    # ---- 範本、未完成清單、匯出區間 ----
    def template_menu(self) -> None:
        """「新筆記」旁的 ▾：列出 .app/templates 的 .md，選一個就用它開一張今天的筆記。"""
        d = templates.ensure_defaults(self.store.root)
        m = tk.Menu(self, tearoff=0)
        for p in templates.list_templates(self.store.root):
            m.add_command(label=p.stem, command=lambda pp=p: self.new_from_template(pp))
        m.add_separator()
        m.add_command(label=_("開啟範本資料夾（可自己加 .md）"), command=lambda: platform_.open_folder(d))
        try:
            m.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            m.grab_release()

    def new_from_template(self, path: Path) -> None:
        text = templates.render(path, date.today())
        if not text.strip():
            return
        self.editor.flush()
        nid = self.store.import_text(date.today(), text)
        self._refresh_sidebar()
        self.open_note(nid)
        applog.info("用範本開新筆記 %s → %s", path.name, nid)

    def show_todo_list(self) -> None:
        """工具列「未完成」／Ctrl+L：所有筆記裡還沒打勾的 - [ ] 列成一頁。只開一個。"""
        t = getattr(self, "_todo_view", None)
        if t is not None and t.winfo_exists():
            t.lift(); t.focus_force()
            return
        from . import todo_view
        todo_view.show(self, self.store, on_open=lambda n: self.open_note(n, pulse=True), quiet=_quiet_dialog)

    def export_range(self) -> None:
        """設定 → 存檔 →「匯出日期區間…」：選起訖日，合成一個 .md（週報、交接用）。"""
        from . import datepick
        today = date.today()
        d1 = datepick.ask_date(self, today - timedelta(days=6), quiet=_quiet_dialog)
        if d1 is None:
            return
        d2 = datepick.ask_date(self, today, quiet=_quiet_dialog)
        if d2 is None:
            return
        if d1 > d2:
            d1, d2 = d2, d1
        path = filedialog.asksaveasfilename(parent=self, title=_("匯出日期區間"), initialfile=f"{d1.isoformat()}_{d2.isoformat()}.md",
                                            defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if not path:
            return
        self.editor.flush()
        n = self.store.export_range(d1, d2, Path(path))
        self.editor._set_status(_("已匯出 {0} 張到 {1}").format(n, path), fade=True)

    def set_topmost(self, on: bool) -> None:
        self.settings = self.settings.with_(topmost=on)
        self.attributes("-topmost", on)
        self.settings.save()

    def change_note_dir(self, new_dir: Path) -> None:
        """換存檔位置：舊的不搬（使用者自己決定），新資料夾不存在就建。"""
        self.editor.flush()
        self._save_state()
        try:
            new_store = NoteStore(new_dir, encrypt=self.settings.encrypt)   # 先確定開得起來，再記位置
        except OSError as e:
            applog.exception("換存檔位置失敗 %s", new_dir)
            messagebox.showerror(APP_NAME, _("這個位置用不了：{0}\n{1}").format(new_dir, e), parent=self)
            return
        self.settings = self.settings.with_(note_dir=new_dir)
        self.settings.save_note_dir()
        self.store = new_store
        self.usage = usagelog.UsageLog(new_dir)
        self.state_ = AppState.load(new_dir)
        self.current = None
        applog.info("換存檔位置 → %s", new_dir)
        self.go_day(date.today())

    def set_encrypt(self, on: bool) -> None:
        """切換加密：現有筆記全部改寫成新格式，並記進設定。"""
        self.editor.flush()
        with self._busy(_("加密中") if on else _("解密中")) as progress:
            self.store.set_encrypt(on, progress)
        self.settings = self.settings.with_(encrypt=on)
        self.settings.save()
        self._refresh_sidebar()

    def open_settings(self) -> None:
        """設定面板只開一個：已經開著就拉到前面，不再疊第二個。"""
        p = getattr(self, "_settings_panel", None)
        if p is not None and p.winfo_exists():
            p.deiconify(); p.lift(); p.focus_force()
            return
        self._settings_panel = SettingsPanel(self)

    # ---- 錯誤 ----
    def _on_tk_error(self, exc, val, tb) -> None:
        """tkinter 回呼裡沒接到的例外：寫到 <note_dir>/.app/error.log，畫面跳一個提示。"""
        import traceback
        applog.error_with_tb("tkinter 回呼例外", (exc, val, tb))
        text = "".join(traceback.format_exception(exc, val, tb))
        try:
            log = self.store.root / ".app" / "error.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as f:
                f.write(f"\n==== {datetime.now():%Y-%m-%d %H:%M:%S}\n{text}")
        except Exception:
            pass
        messagebox.showerror(APP_NAME, _("程式出錯了（已記在 .app/error.log）：\n{0}").format(val), parent=self)

    # ---- 關閉 ----
    def _on_close(self) -> None:
        self.editor.flush()
        if self.editor.is_dirty():          # 存不進去（磁碟拔掉、權限）：寫救援檔，不讓字消失
            rescue = self._write_rescue()
            if not messagebox.askyesno(APP_NAME, _("這張筆記存不進去：{0}\n").format(self.editor.last_error)
                                       + _("已另存救援檔：{0}\n\n仍要關閉？").format(rescue), parent=self):
                return
        self._save_state()
        self.usage.save(time.monotonic(), force=True)
        self._watchdog.stop()
        applog.info("關閉視窗")
        self.destroy()

    def _write_rescue(self) -> Path:
        """存不進去的字另外寫一份。加密開著就用同一種加密寫 .note（不然救援檔變明文，等於繞過加密）；
        加密失敗才退回明文 .md。"""
        from .. import crypto
        d = applog.log_dir().parent / "rescue"
        d.mkdir(parents=True, exist_ok=True)
        stem = d / f"{datetime.now():%Y%m%d_%H%M%S}_{self.current_day.isoformat()}"
        text = self.editor.get_text()
        try:
            if self.store.encrypt:
                p = stem.with_suffix(".note")
                p.write_bytes(crypto.encrypt_text(text))
            else:
                raise crypto.CryptoError("plain")
        except Exception:
            p = stem.with_suffix(".md")
            p.write_text(text, encoding="utf-8")
        applog.warning("寫救援檔 %s", p)
        return p

    def _heartbeat(self) -> None:
        """每 2 秒告訴看門狗主迴圈還活著，順便看日期換了沒、累加使用時間。"""
        self._watchdog.ping()
        self._check_day_change()
        self._tick_usage(time.monotonic())
        self.after(2000, self._heartbeat)

    def _touch_activity(self, _e=None) -> None:
        self._last_activity = time.monotonic()

    def _tick_usage(self, now: float, focused: Optional[bool] = None) -> None:
        """視窗有焦點、而且 IDLE_SECONDS 內有動作，才把這段時間算到今天；每 30 秒寫一次檔。focused 給測試用。"""
        if focused is None:
            try:
                focused = self.focus_displayof() is not None
            except tk.TclError:
                focused = False
        if focused and now - self._last_activity < usagelog.IDLE_SECONDS:
            self.usage.add(date.today(), now - self._last_tick)
        self._last_tick = now
        self.usage.save(now)

    def show_calendar(self) -> None:
        """工具列「月曆」／Ctrl+M：這個月哪幾天有筆記、每天用多久；點日期跳過去。只開一個。"""
        c = getattr(self, "_calendar", None)
        if c is not None and c.winfo_exists():
            c.lift(); c.focus_force()
            return
        from . import calendar as cal
        cal.show(self, self.store, self.usage, on_pick=lambda d: self.go_day(d, pulse=True), quiet=_quiet_dialog)

    def _check_day_change(self) -> None:
        """程式常常整晚開著：過了午夜，左欄的「● 今天」還停在昨天，按「新筆記」就會加到昨天。
        日期一換就重畫左欄與上方日期；原本看的就是（舊的）今天，順便跳到新的今天。"""
        today = date.today()
        drawn = getattr(self, "_drawn_today", None)
        if drawn is None:
            self._drawn_today = today
            return
        if today == drawn:
            return
        self._drawn_today = today
        was_on_today = self.current_day == drawn
        self._refresh_sidebar()
        if was_on_today:
            self.go_day(today)
        else:
            self._refresh_day_label()


_tooltip = T.tooltip             # 小提示：跟格式列同一套（theme.tooltip）


def _quiet_dialog(dlg: ctk.CTkToplevel) -> None:
    """讓 CTkToplevel 開的時候不要閃好幾下。
    customtkinter 開 Toplevel 會「藏起來→換標題列顏色→再顯示」一次；呼叫它的 resizable() 又會在 10 ms 後再做一次，
    200 ms 後還會把圖示換成它自己的。所以：resizable 直接用 tk 的（不觸發重畫），圖示現在就設（設過它就不會再蓋）。"""
    tk.Toplevel.resizable(dlg, False, False)
    _set_icon(dlg)


def _set_icon(win) -> None:
    """視窗左上角與工作列的圖示。打包後圖示在 PyInstaller 的暫存目錄（sys._MEIPASS）。Windows 用 .ico，其他用 .png。"""
    import sys
    from .. import platform_
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent)) / "assets"
    if win.winfo_exists():
        platform_.set_window_icon(win, base / "icon.ico", base / "icon.png")


class UpdatePrompt(ctk.CTkToplevel):
    """啟動時發現有新版的提醒：下載／這一版不再提醒／稍後；勾「以後都不提醒」等於關掉設定裡的開關。"""

    def __init__(self, win: MainWindow, info):
        super().__init__(win)
        self.win, self.info = win, info
        self.title(_("有新版"))
        self.attributes("-topmost", True)
        _quiet_dialog(self)
        ctk.CTkLabel(self, text=_("{0} 有新版 {1}（你現在是 {2}）。").format(APP_NAME, info.version, __version__),
                     font=T.ui_font(13, "bold")).pack(padx=20, pady=(16, 4), anchor="w")
        ctk.CTkLabel(self, text=_("下載後把 Notion.exe 換掉就好，筆記和設定都不會動。"), font=T.ui_font(12),
                     text_color=T.TEXT_MUTED, wraplength=400, justify="left").pack(padx=20, pady=(0, 10), anchor="w")
        self._never = ctk.CTkCheckBox(self, text=_("以後都不提醒（設定 → 更新 可以再打開）"), font=T.ui_font(11))
        self._never.pack(padx=20, pady=(0, 10), anchor="w")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(row, text=_("下載新版"), font=T.ui_font(12), width=110, fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                      command=self._download).pack(side="right", padx=(8, 0))
        ctk.CTkButton(row, text=_("這一版不再提醒"), font=T.ui_font(12), width=130, fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, command=self._skip_version).pack(side="right", padx=(8, 0))
        ctk.CTkButton(row, text=_("稍後再說"), font=T.ui_font(12), width=80, fg_color="transparent", text_color=T.TEXT_MUTED,
                      hover_color=T.ROW_HOVER, command=self._later).pack(side="left")
        self.protocol("WM_DELETE_WINDOW", self._later)
        T.center_over(self, win)

    def _close(self) -> None:
        if self._never.get():
            self.win.set_update_notify(False)
        self.destroy()

    def _download(self) -> None:
        platform_.open_path(update.safe_url(self.info.url))
        self._close()

    def _skip_version(self) -> None:
        self.win.settings = self.win.settings.with_(update_skip=self.info.version)
        self.win.settings.save()
        self._close()

    def _later(self) -> None:
        self._close()


class TourDialog(ctk.CTkToplevel):
    """第一次開程式的使用教學：五頁、看一次就好（state.json 的 tour_done）；設定 → 更新 裡可以再看。
    一頁＝左邊一個大圖示、右邊標題加三句重點、底下進度點（Peter 2026-10-30：一段字很呆板）。
    文字顯示時才 _()，tools/check_strings.py 會把 PAGES 列進翻譯表。"""

    PAGES = (
        ("✎", "歡迎使用 {0}", ("筆記照日期放在左欄，一天可以很多張",
                               "「＋ 新筆記」或 Ctrl+N 在今天加一張，第一行就是標題",
                               "停下來 1 秒多就自動存，不用按儲存")),
        ("✦", "記號會自動上色", ("==重點==、!!紅字!!、**粗體**、*斜體*",
                                 "三個反引號包起來是指令區塊，右上角可一鍵複製",
                                 "游標離開那行，記號就藏起來；格式列的按鈕也能加")),
        ("▣", "圖與檔案", ("Ctrl+V 直接貼截圖，角落把手可以拉大小",
                           ".md／.txt 拖進視窗就變成今天的筆記",
                           "其他檔用 📎 放附件連結，Ctrl+點連結會打開")),
        ("☆", "找與整理", ("Ctrl+F 搜尋日期或內容",
                           "標題前的 ☆ 點一下加入「我的最愛」",
                           "行首打 - [ ] 就是打勾清單；左欄、日期、內文都有右鍵選單")),
        ("⚙", "設定在右上角", ("語言、字體、左欄放哪邊、快捷鍵（可以自己改）",
                               "換電腦前先 設定 → 存檔 → 匯出全部（筆記綁這台的 Windows 帳號）",
                               "這個教學在 設定 → 說明 可以再看一次")),
    )

    def __init__(self, win: MainWindow):
        super().__init__(win)
        self.win = win
        self._page = 0
        self.title(_("使用教學"))
        self.attributes("-topmost", True)
        _quiet_dialog(self)
        card = ctk.CTkFrame(self, fg_color="transparent")
        card.pack(fill="both", expand=True, padx=20, pady=(18, 6))
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(1, weight=1)
        self._glyph = ctk.CTkLabel(card, text="", font=ctk.CTkFont(family=T.UI_FONT_FAMILY, size=46), text_color=T.ACCENT, width=72)
        self._glyph.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 18))
        self._title = ctk.CTkLabel(card, text="", font=T.ui_font(16, "bold"), anchor="w")
        self._title.grid(row=0, column=1, sticky="w")
        self._lines = ctk.CTkFrame(card, fg_color="transparent")
        self._lines.grid(row=1, column=1, sticky="nsew", pady=(8, 0))
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(0, 16))
        self._dots = ctk.CTkLabel(bottom, text="", font=T.ui_font(14), text_color=T.ACCENT)
        self._dots.pack(side="left")
        self._next_btn = ctk.CTkButton(bottom, text="", font=T.ui_font(12), width=96, fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                                       command=self._next)
        self._next_btn.pack(side="right", padx=(8, 0))
        ctk.CTkButton(bottom, text=_("跳過"), font=T.ui_font(12), width=70, fg_color="transparent", text_color=T.TEXT_MUTED,
                      hover_color=T.ROW_HOVER, command=self._finish).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self._finish)
        self._render()
        T.center_over(self, win, 540, 290)

    def _render(self) -> None:
        glyph, title, bullets = self.PAGES[self._page]
        self._glyph.configure(text=glyph)
        self._title.configure(text=_(title).format(APP_NAME))
        for w in self._lines.winfo_children():
            w.destroy()
        for b in bullets:
            ctk.CTkLabel(self._lines, text="•  " + _(b), font=T.ui_font(12), anchor="w", justify="left", wraplength=400).pack(
                fill="x", anchor="w", pady=2)
        n = len(self.PAGES)
        self._dots.configure(text="  ".join("●" if i == self._page else "○" for i in range(n)))
        self._next_btn.configure(text=_("完成") if self._page == n - 1 else _("下一步"))

    def _next(self) -> None:
        if self._page >= len(self.PAGES) - 1:
            self._finish()
            return
        self._page += 1
        self._render()

    def _finish(self) -> None:
        self.win.state_ = self.win.state_.with_(tour_done=True)
        self.win._save_state()
        self.destroy()


class SettingsPanel(ctk.CTkToplevel):
    """設定面板。每個控制項直接呼叫 MainWindow 的 set_xxx，不自己存檔。

    項目：外觀（一般／跟隨系統／暗黑模式）、字體大小、最上層、開機啟動、
         加密、存檔位置（開啟／更改）、匯出純文字、垃圾桶、版本。
    """

    _THEME_KEYS = {"light": "一般", "system": "跟隨系統", "dark": "暗黑模式"}
    _SIDE_KEYS = {"left": "左邊", "right": "右邊", "bottom": "下面"}     # 左欄位置；顯示時 _()

    @property
    def THEME_LABELS(self) -> dict:
        return {k: _(v) for k, v in self._THEME_KEYS.items()}       # 開面板時才翻，換語言後才會是新的

    PAGES = (("外觀", "◐"), ("存檔", "▤"), ("快捷鍵", "⌘"), ("更新", "↻"), ("說明", "？"), ("紀錄", "≡"))   # (頁名, 導覽圖示)；頁名顯示時 _()
    TABS = tuple(n for n, _g in PAGES)             # check_strings 用（頁名要翻譯）

    def __init__(self, win: MainWindow):
        super().__init__(win)
        self.win = win
        self.title(_("設定"))
        self.attributes("-topmost", True)
        _quiet_dialog(self)                          # 不閃：見 _quiet_dialog 的說明
        self._capturing = None
        self._key_btns: dict = {}
        # 版面（Peter 2026-10-30：分頁那版還是呆板）：左邊導覽列（圖示＋頁名），右邊一張張圓角卡片，每個項目一列、列間細線
        root = ctk.CTkFrame(self, fg_color=T.PANEL_BG, corner_radius=0)
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)
        self._nav = ctk.CTkFrame(root, width=172, corner_radius=0, fg_color=T.SIDEBAR_BG)
        self._nav.grid(row=0, column=0, sticky="nsw")
        self._nav.grid_propagate(False)
        ctk.CTkLabel(self._nav, text=_("設定"), font=T.ui_font(17, "bold"), anchor="w").pack(fill="x", padx=20, pady=(20, 12))
        self._nav_btns: dict = {}
        for name, glyph in self.PAGES:
            b = ctk.CTkButton(self._nav, text=f"{glyph}   {_(name)}", font=T.ui_font(13), anchor="w", height=36, corner_radius=T.RADIUS,
                              fg_color="transparent", hover_color=T.ROW_HOVER, text_color=T.TEXT, command=lambda n=name: self.show_page(n))
            b.pack(fill="x", padx=10, pady=2)
            self._nav_btns[name] = b
        ctk.CTkLabel(self._nav, text=f"{APP_NAME} {__version__}", font=T.ui_font(10), text_color=T.TEXT_MUTED).pack(side="bottom", pady=14)
        self._content = ctk.CTkFrame(root, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)
        self._pages: dict = {}
        self._outers: dict = {}
        for name, _glyph in self.PAGES:
            outer = ctk.CTkFrame(self._content, fg_color="transparent")
            outer.grid(row=0, column=0, sticky="nsew")           # 全部疊在同一格，show_page 把要的那頁拉到最上面
            page = ctk.CTkScrollableFrame(outer, fg_color="transparent")
            page.pack(fill="both", expand=True, padx=(20, 12), pady=(8, 8))
            page.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(page, text=_(name), font=T.ui_font(19, "bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=2, pady=(8, 12))
            self._pages[name] = page
            self._outers[name] = outer
        self._build_appearance(win)
        self._build_files(win)
        self._build_keys_page()
        self._build_update(win)
        self._build_logs(win)
        self.show_page("外觀")
        self.update_idletasks()
        T.center_over(self, win, 820, 560)

    def show_page(self, name: str) -> None:
        """切到某一頁：導覽列那顆亮起，右邊那頁拉到最上面。"""
        for n, b in self._nav_btns.items():
            on = n == name
            b.configure(fg_color=T.ACCENT if on else "transparent", text_color=T.ON_ACCENT if on else T.TEXT,
                        hover_color=T.ACCENT_HOVER if on else T.ROW_HOVER)
        self._outers[name].tkraise()
        self._current_page = name

    def _page(self, name: str) -> None:
        """之後的 _section（開一張卡）、_row、_full 都放到這一頁。"""
        self._cur_page = self._pages[name]
        self.body = self._cur_page
        self._r = 1                                   # 第 0 列是頁標題
        self._page_r = 1

    # ---- 外觀 ----
    def _build_appearance(self, win: MainWindow) -> None:
        self._page("外觀")
        locked = [k for k in ("NOTE_THEME", "NOTE_FONT", "NOTE_FONT_SIZE", "NOTE_TOPMOST", "NOTE_ENCRYPT", "NOTE_LANG", "NOTE_DIR")
                  if os.environ.get(k, "").strip()]
        if locked:                                   # Notion.bat 有填值：那幾項這裡改了下次用 bat 開會被蓋回去
            ctk.CTkLabel(self.body, text=_("Notion.bat 裡有填：") + "、".join(locked) + _("。這幾項以 .bat 為準，這裡改了下次用 .bat 開會被蓋回去；要在這裡改就把 .bat 裡那行留空。"),
                         font=T.ui_font(11), text_color=T.DANGER, wraplength=540, justify="left").grid(
                row=self._r, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 8)); self._r += 1

        self._section(_("外觀"))
        label_to_key = {v: k for k, v in self.THEME_LABELS.items()}
        seg = ctk.CTkSegmentedButton(self.body, values=list(self.THEME_LABELS.values()), font=T.ui_font(12),
                                     command=lambda lbl: win.set_theme(label_to_key[lbl]))
        seg.set(self.THEME_LABELS[win.settings.theme])
        self._row(_("風格"), seg)

        from .. import i18n
        names = i18n.langs()
        name_to_code = {v: k for k, v in names.items()}
        lang_seg = ctk.CTkSegmentedButton(self.body, values=list(names.values()), font=T.ui_font(12),
                                          command=lambda name: win.set_language(name_to_code[name]))
        lang_seg.set(names.get(win.settings.lang, names.get(i18n.DEFAULT, i18n.ZH_TW_NAME)))
        self._row(_("語言"), lang_seg)

        side_names = {k: _(v) for k, v in self._SIDE_KEYS.items()}
        side_seg = ctk.CTkSegmentedButton(self.body, values=list(side_names.values()), font=T.ui_font(12),
                                          command=lambda name: win.set_sidebar_side({v: k for k, v in side_names.items()}[name]))
        side_seg.set(side_names[win.state_.sidebar_side])
        self._row(_("筆記列（左欄）放哪邊"), side_seg)

        box = ctk.CTkFrame(self.body, fg_color="transparent")
        self.size_lbl = ctk.CTkLabel(box, text=str(win.settings.font_size), width=30, font=T.ui_font(12))
        ctk.CTkButton(box, text=_("－"), width=30, command=lambda: self._zoom(-1)).pack(side="left")
        self.size_lbl.pack(side="left", padx=4)
        ctk.CTkButton(box, text=_("＋"), width=30, command=lambda: self._zoom(1)).pack(side="left")
        self._row(_("字體大小（Ctrl+滾輪也可）"), box)

        top = ctk.CTkSwitch(self.body, text="", width=48, command=lambda: win.set_topmost(bool(top.get())))
        top.select() if win.settings.topmost else top.deselect()
        self._row(_("視窗永遠在最上層"), top, last=True)

    # ---- 存檔 ----
    def _build_files(self, win: MainWindow) -> None:
        self._page("存檔")
        self._section(_("你的資料與隱私"))
        for line in (_("筆記只存在這台電腦的資料夾裡，不經過任何雲端、不用帳號，程式也不收集任何東西。"),
                     _("唯一會連網的是「更新」分頁：啟動時讀一次 GitHub 上的版本號（可以關掉）。")):
            self._note("•  " + line)
        self._end_card()

        self._section(_("啟動與安全"))
        if platform_.AUTOSTART_SUPPORTED:        # Linux：程式幫你寫 autostart
            self.startup_sw = ctk.CTkSwitch(self.body, text="", width=48, command=self._toggle_startup)
            self.startup_sw.select() if startup.is_enabled() else self.startup_sw.deselect()
            self._row(_("開機自動啟動"), self.startup_sw)
        else:                                    # Windows：讓使用者自己放捷徑（公司機器常擋 PowerShell／COM，程式不代勞）
            btn = ctk.CTkButton(self.body, text=_("開啟啟動資料夾"), font=T.ui_font(11), width=150, height=26, fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, command=lambda: platform_.open_folder(platform_.startup_folder()))
            self._row(_("開機自動啟動"), btn)
            self._note(_("把 Notion.bat 的捷徑放進 Windows 的「啟動」資料夾就會開機自動開（上面的按鈕會開那個資料夾）。"))
        self.enc_sw = ctk.CTkSwitch(self.body, text="", width=48, command=self._toggle_encrypt)
        self.enc_sw.select() if win.store.encrypt else self.enc_sw.deselect()
        self._row(_("加密存檔（綁這個 Windows 帳號；換電腦前先匯出）"), self.enc_sw)
        self._note(_("加密＝用你登入的這個 Windows 帳號把檔案鎖住（DPAPI）：別人拷走檔案打不開，換帳號或換電腦也打不開，所以換電腦前先「匯出全部」成純文字。關掉加密就是普通的 .md 文字檔。"))
        from .. import crypto
        if not crypto.available():          # Linux／mac：DPAPI 沒有，筆記是純文字
            self.enc_sw.deselect(); self.enc_sw.configure(state="disabled")
            self._note(_("這個作業系統沒有加密功能，筆記是純文字檔。"))
        self._end_card()

        self._section(_("存檔位置"))
        self.dir_lbl = ctk.CTkLabel(self.body, text=str(win.store.root), font=T.ui_font(11),
                                    text_color=T.TEXT_MUTED, wraplength=520, justify="left", anchor="w")
        self._full(self.dir_lbl, pady=(0, 4))
        btns = ctk.CTkFrame(self.body, fg_color="transparent")
        ctk.CTkButton(btns, text=_("開啟資料夾"), font=T.ui_font(12), width=96,
                      command=lambda: platform_.open_folder(win.store.root)).pack(side="left")
        ctk.CTkButton(btns, text=_("更改位置…"), font=T.ui_font(12), width=96, fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, command=self._pick_dir).pack(side="left", padx=6)
        ctk.CTkButton(btns, text=_("垃圾桶"), font=T.ui_font(12), width=70, fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG,
                      command=lambda: platform_.open_folder(win.store.root / ".app" / "trash")).pack(side="left", padx=6)
        ctk.CTkButton(btns, text=_("還原上一次刪除"), font=T.ui_font(12), width=150, fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, command=win.restore_last_deleted).pack(side="left")
        self._full(btns)
        self._full(ctk.CTkButton(self.body, text=_("範本資料夾（新筆記 ▾ 用的 .md）"), font=T.ui_font(12), width=240,
                                 fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG,
                                 command=lambda: platform_.open_folder(templates.ensure_defaults(win.store.root))), pady=(0, 4))
        self._end_card()

        self._section(_("匯入／匯出（純文字 .md）"))
        io_row = ctk.CTkFrame(self.body, fg_color="transparent")
        for text, cmd in ((_("匯出這張…"), win.export_note), (_("匯出全部…"), win.export_all),
                          (_("匯入檔案…"), win.import_files), (_("匯入資料夾…"), win.import_folder)):
            ctk.CTkButton(io_row, text=text, font=T.ui_font(12), width=118, fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, command=cmd).pack(side="left", padx=(0, 6))
        self._full(io_row)
        self._full(ctk.CTkButton(self.body, text=_("匯出日期區間…（合成一個 .md，週報用）"), font=T.ui_font(12), width=260,
                                 fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, command=win.export_range), pady=(0, 4))
        self._note(_("匯入的筆記接在那一天後面編號，不會蓋掉既有的；換電腦前先「匯出全部」。"))
        self._end_card()

    # ---- 快捷鍵 ----
    def _build_keys_page(self) -> None:
        self._page("快捷鍵")
        self._section(_("快捷鍵"))
        self._build_keys_table().grid(row=self._r, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 6)); self._r += 1
        self._end_card()

    # ---- 更新 ----
    def _build_update(self, win: MainWindow) -> None:
        self._page("更新")
        self._section(_("更新"))
        upd_row = ctk.CTkFrame(self.body, fg_color="transparent")
        self._update_lbl = ctk.CTkLabel(upd_row, text="", font=T.ui_font(12), anchor="w", justify="left", wraplength=360)
        self._update_lbl.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(upd_row, text=_("重新檢查"), font=T.ui_font(11), width=84, height=26, fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, command=lambda: win.start_update_check(force=True)).pack(side="right", padx=(8, 0))
        self._update_btn = ctk.CTkButton(upd_row, text=_("下載新版"), font=T.ui_font(11), width=90, height=26,
                                         fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, command=self._download_update)
        self._full(upd_row, pady=(2, 6))
        upd_row.grid_configure(sticky="ew")
        self._divider()
        self._notify_sw = ctk.CTkSwitch(self.body, text="", width=48, command=lambda: win.set_update_notify(bool(self._notify_sw.get())))
        (self._notify_sw.select if win.settings.update_notify else self._notify_sw.deselect)()
        self._row(_("啟動時有新版就提醒我"), self._notify_sw)
        for line in (_("① 程式開啟幾秒後讀一次 GitHub 上的版本號（只讀，不傳任何東西出去）"),
                     _("② 比你的新就跳提醒；或在這裡按「重新檢查」"),
                     _("③ 按「下載新版」開瀏覽器拿 zip"),
                     _("④ 關掉 Notion，把 zip 裡的 Notion.exe 蓋掉原本的，再開"),
                     _("筆記和設定都在資料夾裡，換 exe 不會動到。")):
            self._note(line)
        self._end_card()

        self._page("說明")                            # 教學、關於、版本紀錄放自己一頁（找教學的人不會去「更新」找）
        self._section(_("說明"))
        btn = ctk.CTkButton(self.body, text=_("再看一次使用教學"), font=T.ui_font(11), width=150, height=26, fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, command=win.show_tour)
        self._row(_("使用教學"), btn, last=True)

        self._section(_("關於"))
        import sys as _sys
        about = _("{0} {1}\n用 Python {2} 寫的（畫面：tkinter ＋ customtkinter；打包：PyInstaller）\n開發：{3}").format(
            APP_NAME, __version__, f"{_sys.version_info.major}.{_sys.version_info.minor}", AUTHOR)
        self._note(about, muted=False)
        self._end_card()

        self._section(_("版本紀錄"))
        self._log_card = self.body
        self._log_box = None
        self._log_btn = ctk.CTkButton(self.body, text="▸ " + _("每一版改了什麼（1.0.0 → {0}）").format(__version__), font=T.ui_font(12),
                                      anchor="w", fg_color="transparent", hover_color=T.ROW_HOVER, text_color=T.TEXT, command=self._toggle_log)
        self._full(self._log_btn, pady=(0, 6))
        self._log_row = self._r; self._r += 1
        self._end_card()
        self.refresh_update()                        # 不在這裡自動查：連網只在啟動那次（可用 NOTE_UPDATE_CHECK=0 關）或按「重新檢查」

    # ---- 紀錄 ----
    def _build_logs(self, win: MainWindow) -> None:
        self._page("紀錄")
        self._section(_("紀錄與當機檔（回報問題時把這些一起給）"))
        log_dir = applog.log_dir()
        rescue_dir = log_dir.parent / "rescue"
        items = ((_("程式紀錄 personalnote.log、卡死堆疊 crash.log"), log_dir),
                 (_("關閉時存不進去的字（救援檔）"), rescue_dir),
                 (_("筆記的舊版本 history／垃圾桶 trash／畫面錯誤 error.log"), win.store.root / ".app"))
        for i, (what, where) in enumerate(items):
            row = ctk.CTkFrame(self.body, fg_color="transparent")
            ctk.CTkLabel(row, text=f"{what}\n{where}", font=T.ui_font(11), text_color=T.TEXT_MUTED,
                         justify="left", anchor="w", wraplength=440).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text=_("開啟"), font=T.ui_font(11), width=56, height=26, fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG,
                          command=lambda d=where: platform_.open_folder(d)).pack(side="right", padx=(8, 0))
            self._full(row, pady=6)
            row.grid_configure(sticky="ew")
            if i < len(items) - 1:
                self._divider()
        self._end_card()

    def _toggle_log(self) -> None:
        """版本紀錄：點一下展開（每版一段），再點收起。預設收起，表很長。"""
        if self._log_box is not None and self._log_box.winfo_exists():
            self._log_box.destroy(); self._log_box = None
            self._log_btn.configure(text="▸ " + _("每一版改了什麼（1.0.0 → {0}）").format(__version__))
            return
        from .. import changelog, i18n
        box = ctk.CTkFrame(self._log_card, fg_color="transparent")
        for ver, items in changelog.entries(i18n.current()):
            ctk.CTkLabel(box, text=ver, font=T.ui_font(12, "bold"), anchor="w").pack(fill="x", pady=(6, 0))
            for it in items:
                ctk.CTkLabel(box, text="•  " + it, font=T.ui_font(11), text_color=T.TEXT_MUTED, wraplength=500,
                             justify="left", anchor="w").pack(fill="x", padx=(6, 0))
        box.grid(row=self._log_row, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))
        self._log_box = box
        self._log_btn.configure(text="▾ " + _("每一版改了什麼（1.0.0 → {0}）").format(__version__))

    # ---- 更新狀態 ----
    def refresh_update(self) -> None:
        """照主視窗查到的結果更新文字；有新版才顯示「下載新版」。"""
        st, info = self.win._update["status"], self.win._update["info"]
        newer = st == "ok" and info is not None and info.newer
        if st == "checking":
            text = _("正在查 GitHub 有沒有新版…")
        elif newer:
            text = _("有新版 {0}（你現在是 {1}）").format(info.version, __version__)
        elif st == "ok":
            text = _("已是最新（{0}）").format(__version__)
        elif st == "no_release":
            text = _("GitHub 上還沒有發布的版本（你現在是 {0}）").format(__version__)
        elif st == "offline":
            text = _("查不到（沒網路，或被防火牆擋住）")
        else:
            text = _("還沒查（啟動時關掉了，或還沒到時間）；按「重新檢查」才會連網")
        self._update_lbl.configure(text=text)
        if newer:
            self._update_btn.pack(side="right", padx=(8, 0))
        else:
            self._update_btn.pack_forget()

    def _download_update(self) -> None:
        info = self.win._update["info"]
        if info is not None:
            platform_.open_path(update.safe_url(info.url))

    # ---- 快捷鍵表（點鍵改）----
    def _build_keys_table(self) -> ctk.CTkFrame:
        """兩欄：左邊是鍵（可改的是按鈕，點了再按組合鍵；滑鼠那些是字，不能改），右邊是功能。"""
        box = ctk.CTkFrame(self.body, fg_color="transparent")
        box.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(box, text=_("點左邊的鍵，再按你要的組合鍵（要帶 Ctrl 或 Alt；F1～F12 可以單獨用），Esc 取消。兩個功能不能用同一組。"),
                     font=T.ui_font(11), text_color=T.TEXT_MUTED, wraplength=520, justify="left").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self._key_btns = {}
        r = 1
        for action, _default, desc in keys.ACTIONS:
            b = ctk.CTkButton(box, text=self.win.keymap.key_of(action), width=150, height=26, font=T.ui_font(11, "bold"),
                              fg_color=T.KEYCAP_BG, hover_color=T.KEYCAP_HOVER, text_color=T.TEXT, anchor="w",
                              command=lambda a=action: self._capture_key(a))
            b.grid(row=r, column=0, sticky="w", padx=(0, 14), pady=1)
            ctk.CTkLabel(box, text=_(desc), font=T.ui_font(11), text_color=T.TEXT_MUTED, anchor="w", justify="left", wraplength=340).grid(
                row=r, column=1, sticky="w", pady=1)
            self._key_btns[action] = b
            r += 1
        ctk.CTkButton(box, text=_("全部還原預設"), width=150, height=26, font=T.ui_font(11), fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, command=self._reset_keys).grid(
            row=r, column=0, sticky="w", pady=(4, 6))
        self._key_status = ctk.CTkLabel(box, text="", font=T.ui_font(11), text_color=T.TEXT_MUTED, anchor="w", justify="left", wraplength=380)
        self._key_status.grid(row=r, column=1, sticky="w", pady=(4, 6))
        r += 1
        for key, what in keys.GESTURES:                   # 滑鼠、Enter：不能改，只列出來
            ctk.CTkLabel(box, text=_(key), font=T.ui_font(11, "bold"), anchor="w").grid(row=r, column=0, sticky="w", padx=(0, 14), pady=1)
            ctk.CTkLabel(box, text=_(what), font=T.ui_font(11), text_color=T.TEXT_MUTED, anchor="w", justify="left", wraplength=340).grid(
                row=r, column=1, sticky="w", pady=1)
            r += 1
        return box

    def _capture_key(self, action: str) -> None:
        """點了某個鍵的按鈕：等使用者按下一組鍵（面板接 KeyPress）。"""
        self._cancel_capture()
        self._capturing = action
        self._key_btns[action].configure(text=_("請按組合鍵…"), fg_color=T.ACCENT, text_color=T.ON_ACCENT)
        self._key_status.configure(text=_("等你按鍵（Esc 取消）"))
        self.focus_set()
        self._capture_bind = self.bind("<KeyPress>", self._on_capture_key)

    def _cancel_capture(self) -> None:
        a = getattr(self, "_capturing", None)
        if a is None:
            return
        self._capturing = None
        try:
            self.unbind("<KeyPress>", self._capture_bind)
        except Exception:
            pass
        if a in self._key_btns and self._key_btns[a].winfo_exists():
            self._key_btns[a].configure(text=self.win.keymap.key_of(a), fg_color=T.KEYCAP_BG, text_color=T.TEXT)

    def _on_capture_key(self, e):
        action = self._capturing
        if action is None:
            return None
        if e.keysym == "Escape":
            self._cancel_capture()
            self._key_status.configure(text=_("沒有改"))
            return "break"
        name = keys.from_event(e)
        if name is None:
            if e.keysym not in keys.MODIFIER_KEYSYMS:     # 只按了 Ctrl／Shift 就繼續等
                self._key_status.configure(text=_(keys.MSG_UNSUPPORTED))
            return "break"
        try:
            km = self.win.keymap.set(action, name)
        except keys.Conflict as c:
            self._key_status.configure(text=_("「{0}」已經被「{1}」用了，換一組").format(c.name, _(c.desc)))
            return "break"
        except ValueError as err:
            self._key_status.configure(text=_(str(err)))
            return "break"
        self._cancel_capture()
        self.win.set_keys(km)
        self._key_btns[action].configure(text=name)
        self._key_status.configure(text=_("「{0}」改成 {1}").format(_(km.desc_of(action)), name))
        return "break"

    def _reset_keys(self) -> None:
        self._cancel_capture()
        self.win.set_keys(keys.KeyMap.load())
        for a, b in self._key_btns.items():
            b.configure(text=self.win.keymap.key_of(a))
        self._key_status.configure(text=_("全部回到預設"))

    # ---- 排版小工具 ----
    def _section(self, text: str) -> None:
        """開一張新卡（圓角、比底色亮一階），上面一行粗體小標；之後的 _row／_full／_note 都放進這張卡。"""
        if self.body is self._cur_page:              # 卡之前直接放在頁上的東西（例如 .bat 警告）
            self._page_r = self._r
        card = ctk.CTkFrame(self._cur_page, fg_color=T.CARD_BG, corner_radius=10)
        card.grid(row=self._page_r, column=0, sticky="ew", padx=2, pady=(0, 14)); self._page_r += 1
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text=text, font=T.ui_font(12, "bold"), anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 6))
        self.body = card
        self._r = 1

    def _end_card(self) -> None:
        """卡的底部留一點空。"""
        if self.body is not self._cur_page:
            self.body.grid_rowconfigure(self._r, minsize=10); self._r += 1

    def _divider(self) -> None:
        ctk.CTkFrame(self.body, height=1, fg_color=T.DIVIDER).grid(row=self._r, column=0, columnspan=2, sticky="ew", padx=16); self._r += 1

    def _row(self, label: str, widget, last: bool = False) -> None:
        """一列：左邊字、右邊控制項；列與列之間一條細線（last=True 是卡裡最後一列，下面不畫線、直接收卡）。"""
        ctk.CTkLabel(self.body, text=label, font=T.ui_font(12), anchor="w", justify="left", wraplength=320).grid(
            row=self._r, column=0, sticky="w", padx=16, pady=9)
        widget.grid(row=self._r, column=1, sticky="e", padx=16, pady=9); self._r += 1
        if last:
            self._end_card()
        else:
            self._divider()

    def _full(self, widget, pady=6) -> None:
        widget.grid(row=self._r, column=0, columnspan=2, sticky="w", padx=16, pady=pady); self._r += 1

    def _note(self, text: str, muted: bool = True) -> None:
        """卡裡的一段說明字（灰、可換行）。"""
        ctk.CTkLabel(self.body, text=text, font=T.ui_font(11), text_color=T.TEXT_MUTED if muted else T.TEXT,
                     wraplength=520, justify="left", anchor="w").grid(row=self._r, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 6)); self._r += 1

    # ---- 動作 ----
    def _zoom(self, d: int) -> None:
        self.win.zoom(d)
        self.size_lbl.configure(text=str(self.win.settings.font_size))

    def _pick_dir(self) -> None:
        chosen = filedialog.askdirectory(parent=self, title=_("筆記要存在哪個資料夾"),
                                         initialdir=str(self.win.store.root))
        if not chosen:
            return
        if os.environ.get("NOTE_DIR", "").strip():
            messagebox.showwarning(APP_NAME, _("Notion.bat 裡的 NOTE_DIR 有設值，下次用 .bat 開會以它為準。\n")
                                   + _("要長期改位置，請把 .bat 裡的 NOTE_DIR 改掉或留空。"), parent=self)
        self.win.change_note_dir(Path(chosen))
        self.dir_lbl.configure(text=str(self.win.store.root))

    def _toggle_encrypt(self) -> None:
        on = bool(self.enc_sw.get())
        if not on and not messagebox.askyesno(APP_NAME, _("關掉加密後，硬碟拔走就能直接讀到內容。確定？"), parent=self):
            self.enc_sw.select()
            return
        self.win.set_encrypt(on)

    def _toggle_startup(self) -> None:
        try:
            if self.startup_sw.get():
                startup.enable(self.win.settings.launcher)
            else:
                startup.disable()
        except Exception as e:  # PowerShell 不在或被擋
            messagebox.showerror(APP_NAME, _("開機啟動設定失敗：{0}").format(e), parent=self)
            self.startup_sw.deselect()

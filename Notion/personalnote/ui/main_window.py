# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""主視窗：把 Sidebar、Editor、設定面板接到 NoteStore。

這裡只有「誰呼叫誰」，沒有檔案 I/O 細節（在 storage）、沒有外觀常數（在 theme）。

操作流程（定案）：
- 開啟：回到上次看的那天；那天沒筆記就開今天。今天沒筆記 → 直接給一張空白的，打字才建檔。
- 看之前的：左欄依日期分組（新的在上），點一張就開；◀ ▶ 是前一天／後一天；搜尋框過濾日期和內容。
- 新增：上排 ＋、Ctrl+N、或日期列旁的 ＋（在那一天底下加）。
- 刪除：筆記上按右鍵 → 刪除這張；🗑 → 清空目前這張／清掉整天／清掉全部。全部先搬 .app/trash。
- 帶到今天：右鍵 → 複製到今天（前一天沒做完的事抄過來）。
- 存檔：打字停 1.2 秒自動存；切換、關閉一定存。
"""
from __future__ import annotations

import os
import subprocess
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from ..i18n import _
from .. import APP_NAME, AUTHOR, __version__, applog, dropfiles, platform_, startup
from ..config import Settings
from ..state import AppState
from ..storage import NoteId, NoteStore, title_of, tomorrow, yesterday
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
        self._heartbeat()
        self.attributes("-topmost", settings.topmost)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

        self.bind("<Control-n>", lambda _e: self.new_note(self.current_day))
        self.bind("<Control-backslash>", lambda _e: self.toggle_sidebar())   # Ctrl+B 讓給粗體
        for seq in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):      # 一般鍵盤的 + 要 Shift，Ctrl+= 送的是 equal
            self.bind(seq, lambda _e: self.zoom(1))
        for seq in ("<Control-minus>", "<Control-KP_Subtract>"):
            self.bind(seq, lambda _e: self.zoom(-1))
        self.bind("<Control-Prior>", lambda _e: self.go_day(yesterday(self.current_day)))
        self.bind("<Control-Next>", lambda _e: self.go_day(tomorrow(self.current_day)))
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
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = Sidebar(self, on_select=self.open_note, on_add=self.new_note,
                               on_search=self._on_search, on_note_menu=self.note_menu,
                               on_add_pick=self.new_note_pick)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.set_width(self.state_.sidebar_width)
        if self._search_kw:                      # 換語言重畫時搜尋還在：框裡的字也要還原，不然清單被濾了卻看不出為什麼
            self.sidebar._search.insert(0, self._search_kw)
        self.bind("<Configure>", self._fit_sidebar, add="+")   # 視窗縮小時左欄跟著讓位，不然工具列被擠出去
        # 左欄和內文之間一條可以拖的分隔線（寬度記在 state.json 的 sidebar_width）
        self._splitter = tk.Frame(self, width=6, cursor="sb_h_double_arrow", bg=self._splitter_color())
        self._splitter.grid(row=0, column=1, sticky="ns")
        self._splitter.bind("<B1-Motion>", self._on_splitter_drag)
        self._splitter.bind("<ButtonRelease-1>", lambda _e: self._save_state())
        if not self.state_.sidebar_visible:
            self.sidebar.grid_remove()
            self._splitter.grid_remove()

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=2, sticky="nsew", padx=(4, T.PAD), pady=(6, 3))   # 底邊留少一點，狀態列才會在更下面
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
                             on_format_toggle=self._on_format_toggle)
        self.editor.grid(row=2, column=0, sticky="nsew")

    def rebuild_ui(self) -> None:
        """換語言：手上這張先存，砍掉所有元件重畫，再把同一張開回來。設定面板開著就關掉（它也是舊語言畫的）。"""
        self.editor.flush()
        current = self.current
        self.state_ = self.state_.with_(sidebar_width=self.sidebar._width)   # 重畫用目前的寬，不是上次存檔的
        if getattr(self.sidebar, "_search_timer", None) is not None:
            self.sidebar.after_cancel(self.sidebar._search_timer)             # 排程中的搜尋會掛在被砍掉的元件上
        p = getattr(self, "_settings_panel", None)
        if p is not None and p.winfo_exists():
            p.destroy()
        for w in (self.sidebar, self._splitter, self._main):
            w.destroy()
        self._build_ui()
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
            img = T.icon(icon_name) if icon_name else None
            btn = ctk.CTkButton(bar, text=text if (img is None or text) else "", image=img, width=width, height=32,
                                corner_radius=8, font=T.ui_font(13), command=cmd, compound="left", **style)
            if tip:
                _tooltip(btn, tip)
            return btn

        # 第一排：日期導覽
        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew")
        nav.grid_columnconfigure(1, weight=1)
        self._nav_prev = mk(nav, "prev", lambda: self.go_day(yesterday(self.current_day)), tip=_("前一天（Ctrl+PgUp）"))
        self._nav_prev.grid(row=0, column=0)
        self.day_label = ctk.CTkLabel(nav, text="", font=T.ui_font(14, "bold"), text_color=T.TEXT)
        self.day_label.grid(row=0, column=1, sticky="ew")
        self._nav_next = mk(nav, "next", lambda: self.go_day(tomorrow(self.current_day)), tip=_("後一天（Ctrl+PgDn）"))
        self._nav_next.grid(row=0, column=2)
        # 語言下拉（Peter：最前面就要有 EN／繁中／简中／日本語，選了畫面直接換）
        from .. import i18n
        names = i18n.langs()                           # {代碼: 顯示名}，由翻譯表的欄位決定，程式裡不寫死
        name_to_code = {v: k for k, v in names.items()}
        self._lang_menu = ctk.CTkOptionMenu(nav, values=list(names.values()), width=78, height=28,
                                            font=T.ui_font(12), dropdown_font=T.ui_font(12), corner_radius=8,
                                            fg_color=T.ROW_HOVER, button_color=T.ROW_HOVER, text_color=T.TEXT,
                                            command=lambda s: self.set_language(name_to_code[s]))
        self._lang_menu.set(names.get(self.settings.lang, names.get(i18n.DEFAULT, i18n.ZH_TW_NAME)))
        self._lang_menu.grid(row=0, column=3, padx=(6, 0))
        _tooltip(self._lang_menu, _("語言"))
        self._nav = nav
        nav.bind("<Configure>", lambda _e: self._refresh_day_label())   # 視窗變窄就換短一點的寫法

        # 第二排：動作
        act = ctk.CTkFrame(parent, fg_color="transparent")
        act.grid(row=1, column=0, sticky="ew", pady=(2, 6))
        act.grid_columnconfigure(3, weight=1)
        mk(act, "menu", self.toggle_sidebar, tip=_("收起／展開左欄（Ctrl+\\）")).grid(row=0, column=0, padx=(0, 2))
        mk(act, "today", lambda: self.go_day(date.today()), text=_("今天"), width=64, tip=_("回到今天")).grid(row=0, column=1, padx=2)
        mk(act, "plus", lambda: self.new_note(self.current_day), text=_("新筆記"), width=92, plain=False,
           fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, tip=_("在這一天加一張（Ctrl+N）")).grid(row=0, column=2, padx=2)
        # 復原／重做搬到內文上方的格式列（文字按鈕，箭頭圖示 Peter 說看不懂），這一排才放得下 640 寬
        mk(act, "attach", self.attach_file, tip=_("插入檔案（複製一份到 attachments）")).grid(row=0, column=5, padx=2)
        mk(act, "trash", self.clear_menu, tip=_("清除…")).grid(row=0, column=6, padx=2)
        mk(act, "settings", self.open_settings, tip=_("設定")).grid(row=0, column=7, padx=(2, 0))

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
        if self._search_kw.strip() and self.store.count_notes() > self.SEARCH_BUSY_MIN:
            with self._busy(_("搜尋中")):
                groups = self.store.search(self._search_kw)
        else:
            groups = self.store.search(self._search_kw)
        if self._search_kw.strip():
            shown, hidden = self._cap(groups, self.SIDEBAR_SEARCH_MAX)
            self.sidebar.refresh(shown, self.current, hidden=hidden)
            return
        limit = self._sidebar_limit
        days = list(groups.keys())
        shown = {d: groups[d] for d in days[:limit]}
        if self.current and self.current.day in groups and self.current.day not in shown:
            shown[self.current.day] = groups[self.current.day]          # 正在看的那天一定要在
        shown, hidden = self._cap(shown, self.SIDEBAR_MAX_NOTES)
        more = len([d for d in days[limit:] if d not in shown])
        self.sidebar.refresh(shown, self.current, more=more, on_more=self._sidebar_more, hidden=hidden)

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

    def go_day(self, day: date) -> None:
        """跳到某一天：有筆記開第一張，沒有就給一張新的（不打字不會建檔）。"""
        refs = self.store.list_notes(day)
        self.open_note(refs[0].id if refs else self.store.next_id(day))

    def _flush_or_rescue(self) -> None:
        """先存；存不進去（磁碟拔掉、加密失敗）就把手上的字寫成救援檔並提示，呼叫端接著才可以把內容換掉。"""
        self.editor.flush()
        if self.editor.is_dirty() and self.current is not None:
            rescue = self._write_rescue()
            messagebox.showwarning(APP_NAME, _("這張筆記存不進去：{0}\n").format(self.editor.last_error)
                                   + _("已另存救援檔：{0}").format(rescue), parent=self)

    def open_note(self, nid: NoteId) -> None:
        if self.current is not None and self.current != nid:
            self._flush_or_rescue()
        else:
            self.editor.flush()
        self.current = nid
        text, ok = self.store.try_load(nid)
        self.editor.set_text(text, read_only=not ok)   # 解不開的只能看，不會被存檔蓋掉
        applog.info("開啟 %s-%03d 可讀=%s 長度=%d", nid.day, nid.seq, ok, len(text))
        self._refresh_day_label()
        if self.sidebar.has(nid):
            self.sidebar.set_selected(nid)            # 已經在左欄：只換選取，不整欄重畫
        else:
            self._refresh_sidebar()
        self.editor.focus()
        self._save_state()                   # 記住看到哪一天；直接關機也不會丟

    def new_note(self, day: date) -> None:
        """按「新筆記」：開下一個編號，標題預設「筆記N」（N 跟編號一樣，背景記著、畫面不顯示），反白等你改。"""
        self.editor.flush()
        nid = self.store.next_id(day)
        self.open_note(nid)
        self.editor.set_default_title(_("筆記{0}").format(nid.seq))

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
        self.store.snapshot(self.current, text)      # 存之前留一份版本（內容有變才留）
        self.store.save(self.current, text)
        applog.info("存檔 %s-%03d 長度=%d", self.current.day, self.current.seq, len(text))
        # 左欄：這張已經在清單裡就只改它的字（每 1.2 秒重畫整欄太重）；是新的一張才整欄重畫。
        # 檔案到這裡已經存好了，左欄畫壞不能算存檔失敗（不然編輯器每 1.2 秒重試一次，愈試愈慢）
        try:
            if not self.sidebar.set_title(self.current, title_of(text)) and is_new:
                self._refresh_sidebar()          # 不是新的卻不在左欄＝被搜尋濾掉或超過上限：不重畫（會卡 1 秒）
        except Exception:
            applog.exception("左欄更新失敗（檔案已存好）")

    def _on_search(self, kw: str) -> None:
        self._search_kw = kw
        self._refresh_sidebar()

    # ---- 右鍵選單（筆記列）----
    def note_menu(self, nid: NoteId, x: int, y: int) -> None:
        m = tk.Menu(self, tearoff=0, font=(T.UI_FONT_FAMILY, 10))
        m.add_command(label=_("開啟"), command=lambda: self.open_note(nid))
        m.add_command(label=_("複製到今天"), command=lambda: self.copy_to_today(nid))
        m.add_command(label=_("匯出這張…"), command=lambda: self.export_note(nid))
        m.add_separator()
        m.add_command(label=_("刪除這張"), command=lambda: self.delete_note(nid))
        m.add_command(label=_("清掉 {0} 整天").format(T.fmt_day(nid.day, False)), command=lambda: self.clear_day(nid.day))
        m.tk_popup(x, y)

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
        dlg.geometry(f"+{self.winfo_rootx() + 80}+{self.winfo_rooty() + 80}")
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

    def clear_current(self) -> None:
        if self.current is None:
            return
        self.editor.set_text("")
        self.store.delete(self.current)
        self._refresh_sidebar()              # 先重畫左欄：接著開的那張編號可能跟刪掉的一樣，不重畫會留舊列
        self.go_day(self.current.day)

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
        """拖檔案進視窗：.md／.txt 匯成「今天」的筆記（最後一張打開）；其他檔（截圖、pdf、word）複製到
        attachments 並在游標處插一個連結，跟按 📎 一樣。讀不了的檔跳過並提示。"""
        self.editor.flush()
        last, bad = None, []
        if self.editor.read_only and any(p.suffix.lower() not in self.TEXT_EXT for p in paths):
            messagebox.showwarning(APP_NAME, _("這張是唯讀的（解不開或較新版本），附件沒有插入；先開別張再拖。"), parent=self)
            paths = [p for p in paths if p.suffix.lower() in self.TEXT_EXT]
        for p in paths:
            try:
                if p.suffix.lower() in self.TEXT_EXT:
                    nid = self.store.import_file(p, date.today())
                    if nid is not None:
                        last = nid
                elif p.is_file():
                    rel = self.store.add_attachment(p)
                    self.editor.insert_own_line(f"[{p.name}]({rel.as_posix()})\n")
                else:
                    bad.append(p.name)           # 資料夾不收
            except (UnicodeDecodeError, OSError):
                applog.exception("拖進來的檔讀不了 %s", p)
                bad.append(p.name)
        applog.info("拖進 %d 個檔，匯入筆記=%s 跳過=%d", len(paths), last, len(bad))
        if last is not None:
            self._refresh_sidebar()
            self.open_note(last)
        if bad:
            messagebox.showwarning(APP_NAME, _("這些沒收進來（不是 UTF-8 文字檔或是資料夾）：\n") + "\n".join(bad), parent=self)

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

    EXEC_EXT = {".exe", ".bat", ".cmd", ".ps1", ".lnk", ".vbs", ".js", ".msi", ".scr", ".com"}

    def open_link(self, link: str) -> None:
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
        """左欄最寬 = 視窗寬 − 330（工具列那排至少要這麼寬）。還原上次寬度、視窗縮小都經過這裡。"""
        if e is not None and e.widget is not self:
            return
        room = self.winfo_width() - 330
        if room > T.SIDEBAR_MIN and self.sidebar._width > room:
            self.sidebar.set_width(room)

    def _on_splitter_drag(self, e) -> None:
        """拖分隔線：左欄寬 = 滑鼠在視窗裡的 x（左欄從 0 開始）。範圍 theme.SIDEBAR_MIN～MAX。"""
        w = min(e.x_root - self.winfo_rootx(), self.winfo_width() - 330)   # 右邊至少留 330 給工具列
        self.sidebar.set_width(w)
        self.state_ = self.state_.with_(sidebar_width=self.sidebar._width)

    def _on_format_toggle(self, visible: bool) -> None:
        self.state_ = self.state_.with_(format_bar=visible)
        self._save_state()

    def _save_state(self) -> None:
        """隨手存狀態（Windows 直接關機時不會走 _on_close，所以不能只靠關閉時存）。"""
        try:
            self.state_ = self.state_.with_(geometry=self.geometry(), last_day=self.current_day.isoformat(),
                                            sidebar_width=self.sidebar._width)
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
        """畫面語言：記進設定、載入翻譯表、整個視窗重畫（工具列下拉或設定面板都走這裡）。"""
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
        """每 2 秒告訴看門狗主迴圈還活著。"""
        self._watchdog.ping()
        self.after(2000, self._heartbeat)


def _tooltip(widget, text: str, delay_ms: int = 600) -> None:
    """滑鼠停在按鈕上 0.6 秒顯示說明。"""
    state = {"after": None, "tip": None}

    def show():
        state["after"] = None
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        tk.Label(tip, text=text, font=(T.UI_FONT_FAMILY, 10), bg="#333843", fg="#ffffff", padx=8, pady=4).pack()
        tip.geometry(f"+{widget.winfo_rootx()}+{widget.winfo_rooty() + widget.winfo_height() + 4}")
        state["tip"] = tip

    def enter(_e):
        state["after"] = widget.after(delay_ms, show)

    def leave(_e):
        if state["after"]:
            widget.after_cancel(state["after"]); state["after"] = None
        if state["tip"]:
            state["tip"].destroy(); state["tip"] = None

    widget.bind("<Enter>", enter, add="+")
    widget.bind("<Leave>", leave, add="+")
    widget.bind("<ButtonPress>", leave, add="+")


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


class SettingsPanel(ctk.CTkToplevel):
    """設定面板。每個控制項直接呼叫 MainWindow 的 set_xxx，不自己存檔。

    項目：外觀（一般／跟隨系統／暗黑模式）、字體大小、最上層、開機啟動、
         加密、存檔位置（開啟／更改）、匯出純文字、垃圾桶、版本。
    """

    _THEME_KEYS = {"light": "一般", "system": "跟隨系統", "dark": "暗黑模式"}

    @property
    def THEME_LABELS(self) -> dict:
        return {k: _(v) for k, v in self._THEME_KEYS.items()}       # 開面板時才翻，換語言後才會是新的

    def __init__(self, win: MainWindow):
        super().__init__(win)
        self.win = win
        self.title(_("設定"))
        self.attributes("-topmost", True)
        _quiet_dialog(self)                          # 不閃：見 _quiet_dialog 的說明
        self.geometry(f"+{win.winfo_rootx() + 40}+{win.winfo_rooty() + 60}")
        # 內容放在可捲動的框裡：螢幕矮（筆電 768）時面板比螢幕高，不捲就看不到底下的按鈕
        self.body = ctk.CTkScrollableFrame(self, width=560, fg_color="transparent")   # 英文字串比中文長，430 會切到按鈕
        self.body.pack(fill="both", expand=True)
        self.body.grid_columnconfigure(1, weight=1)
        pad = dict(padx=16, pady=6)
        self._r = 0

        locked = [k for k in ("NOTE_THEME", "NOTE_FONT", "NOTE_FONT_SIZE", "NOTE_TOPMOST", "NOTE_ENCRYPT", "NOTE_LANG", "NOTE_DIR")
                  if os.environ.get(k, "").strip()]
        if locked:                                   # Notion.bat 有填值：那幾項這裡改了下次用 bat 開會被蓋回去
            ctk.CTkLabel(self.body, text=_("Notion.bat 裡有填：") + "、".join(locked) + _("。這幾項以 .bat 為準，這裡改了下次用 .bat 開會被蓋回去；要在這裡改就把 .bat 裡那行留空。"),
                         font=T.ui_font(11), text_color=T.DANGER, wraplength=520, justify="left").grid(
                row=self._r, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 0)); self._r += 1

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

        box = ctk.CTkFrame(self.body, fg_color="transparent")
        self.size_lbl = ctk.CTkLabel(box, text=str(win.settings.font_size), width=30, font=T.ui_font(12))
        ctk.CTkButton(box, text=_("－"), width=30, command=lambda: self._zoom(-1)).pack(side="left")
        self.size_lbl.pack(side="left", padx=4)
        ctk.CTkButton(box, text=_("＋"), width=30, command=lambda: self._zoom(1)).pack(side="left")
        self._row(_("字體大小（Ctrl+滾輪也可）"), box)

        top = ctk.CTkSwitch(self.body, text=_("視窗永遠在最上層"), font=T.ui_font(12),
                            command=lambda: win.set_topmost(bool(top.get())))
        top.select() if win.settings.topmost else top.deselect()
        self._full(top)

        self._section(_("啟動與安全"))
        if platform_.AUTOSTART_SUPPORTED:        # Linux：程式幫你寫 autostart
            self.startup_sw = ctk.CTkSwitch(self.body, text=_("開機自動啟動"), font=T.ui_font(12), command=self._toggle_startup)
            self.startup_sw.select() if startup.is_enabled() else self.startup_sw.deselect()
            self._full(self.startup_sw)
        else:                                    # Windows：讓使用者自己放捷徑（公司機器常擋 PowerShell／COM，程式不代勞）
            row = ctk.CTkFrame(self.body, fg_color="transparent")
            ctk.CTkLabel(row, text=_("開機自動啟動：把 Notion.bat 的捷徑放進 Windows 的「啟動」資料夾（右邊按鈕會開那個資料夾）。"),
                         font=T.ui_font(11), text_color=T.TEXT_MUTED, justify="left", anchor="w", wraplength=380).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text=_("開啟啟動資料夾"), font=T.ui_font(11), width=150, height=24, fg_color="transparent",
                          border_width=1, text_color=T.TEXT,
                          command=lambda: platform_.open_folder(platform_.startup_folder())).pack(side="right", padx=(8, 0))
            self._full(row, pady=2)
            row.grid_configure(sticky="ew")

        self.enc_sw = ctk.CTkSwitch(self.body, text=_("加密存檔（綁這個 Windows 帳號；換電腦前先匯出）"),
                                    font=T.ui_font(12), command=self._toggle_encrypt)
        self.enc_sw.select() if win.store.encrypt else self.enc_sw.deselect()
        self._full(self.enc_sw)
        from .. import crypto
        if not crypto.available():          # Linux／mac：DPAPI 沒有，筆記是純文字
            self.enc_sw.deselect(); self.enc_sw.configure(state="disabled")
            ctk.CTkLabel(self.body, text=_("這個作業系統沒有加密功能，筆記是純文字檔。"), font=T.ui_font(11),
                         text_color=T.TEXT_MUTED).grid(row=self._r, column=0, columnspan=2, sticky="w", padx=16); self._r += 1

        self._section(_("存檔位置"))
        self.dir_lbl = ctk.CTkLabel(self.body, text=str(win.store.root), font=T.ui_font(11),
                                    text_color=T.TEXT_MUTED, wraplength=520, justify="left", anchor="w")
        self._full(self.dir_lbl, pady=(0, 2))
        btns = ctk.CTkFrame(self.body, fg_color="transparent")
        ctk.CTkButton(btns, text=_("開啟資料夾"), font=T.ui_font(12), width=96,
                      command=lambda: platform_.open_folder(win.store.root)).pack(side="left")
        ctk.CTkButton(btns, text=_("更改位置…"), font=T.ui_font(12), width=96, fg_color="transparent",
                      border_width=1, text_color=T.TEXT, command=self._pick_dir).pack(side="left", padx=6)
        ctk.CTkButton(btns, text=_("垃圾桶"), font=T.ui_font(12), width=70, fg_color="transparent",
                      border_width=1, text_color=T.TEXT,
                      command=lambda: platform_.open_folder(win.store.root / ".app" / "trash")).pack(side="left", padx=6)
        ctk.CTkButton(btns, text=_("還原上一次刪除"), font=T.ui_font(12), width=150, fg_color="transparent",
                      border_width=1, text_color=T.TEXT, command=win.restore_last_deleted).pack(side="left")
        self._full(btns)

        self._section(_("匯入／匯出（純文字 .md）"))
        io_row = ctk.CTkFrame(self.body, fg_color="transparent")
        for text, cmd in ((_("匯出這張…"), win.export_note), (_("匯出全部…"), win.export_all),
                          (_("匯入檔案…"), win.import_files), (_("匯入資料夾…"), win.import_folder)):
            ctk.CTkButton(io_row, text=text, font=T.ui_font(12), width=118, fg_color="transparent",
                          border_width=1, text_color=T.TEXT, command=cmd).pack(side="left", padx=(0, 6))
        self._full(io_row)
        ctk.CTkLabel(self.body, text=_("匯入的筆記接在那一天後面編號，不會蓋掉既有的；換電腦前先「匯出全部」。"),
                     font=T.ui_font(11), text_color=T.TEXT_MUTED, wraplength=520, justify="left").grid(
            row=self._r, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 4)); self._r += 1

        self._section(_("快捷鍵"))
        self._shortcut_table()

        self._section(_("紀錄與當機檔（回報問題時把這些一起給）"))
        log_dir = applog.log_dir()
        rescue_dir = log_dir.parent / "rescue"
        for what, where in ((_("程式紀錄 personalnote.log、卡死堆疊 crash.log"), log_dir),
                            (_("關閉時存不進去的字（救援檔）"), rescue_dir),
                            (_("筆記的舊版本 history／垃圾桶 trash／畫面錯誤 error.log"), win.store.root / ".app")):
            row = ctk.CTkFrame(self.body, fg_color="transparent")
            ctk.CTkLabel(row, text=f"{what}\n{where}", font=T.ui_font(11), text_color=T.TEXT_MUTED,
                         justify="left", anchor="w", wraplength=460).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text=_("開啟"), font=T.ui_font(11), width=50, height=24, fg_color="transparent",
                          border_width=1, text_color=T.TEXT,
                          command=lambda d=where: platform_.open_folder(d)).pack(side="right", padx=(8, 0))
            self._full(row, pady=2)
            row.grid_configure(sticky="ew")

        ctk.CTkLabel(self.body, text=_("{0} {1}   開發：{2}").format(APP_NAME, __version__, AUTHOR), font=T.ui_font(11),
                     text_color=T.TEXT_MUTED).grid(row=self._r, column=0, columnspan=2, sticky="e", padx=16, pady=(8, 12))
        self.update_idletasks()
        inner = self.body.winfo_reqheight()          # 內容實際要的高度（body 是放內容的那個框）
        self.body.configure(height=min(inner, self.winfo_screenheight() - 140))   # 放得下就不出現捲軸

    SHORTCUTS = (
        ("Ctrl+N", "新筆記"),
        ("Ctrl+S", "立刻存（平常停 1.2 秒就自動存）"),
        ("Ctrl+\\", "收起／展開左欄"),
        ("Ctrl+H / Ctrl+Shift+H", "選取的字標黃底 ==重點== ／ 紅字 !!警告!!"),
        ("Ctrl+B / Ctrl+I", "選取的字 **粗體** ／ *斜體*"),
        ("Ctrl+Shift+C", "插一段 ``` 指令區塊（右上角可一鍵複製）"),
        ("Ctrl+PgUp / PgDn", "前一天／後一天"),
        ("Ctrl+滾輪、Ctrl+±", "字體放大縮小"),
        ("Ctrl+V", "貼截圖（剪貼簿是圖就存成附件）"),
        ("Ctrl+點連結", "開網址或檔案路徑"),
        ("行首 1. 或 - 後 Enter", "自動接下一項，空項再 Enter 結束"),
        ("筆記列按右鍵", "開啟、複製到今天、匯出、刪除、清整天"),
        ("拖檔案進視窗", ".md／.txt 匯成今天的筆記；其他檔變附件連結"),
    )

    def _shortcut_table(self) -> None:
        """兩欄表格：按鍵｜功能。要加快捷鍵改 SHORTCUTS 就好。"""
        tbl = ctk.CTkFrame(self.body, fg_color="transparent")
        tbl.grid_columnconfigure(1, weight=1)
        for i, (key, what) in enumerate(self.SHORTCUTS):
            ctk.CTkLabel(tbl, text=_(key), font=T.ui_font(11, "bold"), anchor="w").grid(
                row=i, column=0, sticky="w", padx=(0, 14), pady=1)
            ctk.CTkLabel(tbl, text=_(what), font=T.ui_font(11), text_color=T.TEXT_MUTED, anchor="w", justify="left", wraplength=340).grid(
                row=i, column=1, sticky="w", pady=1)
        tbl.grid(row=self._r, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 4)); self._r += 1

    # ---- 排版小工具 ----
    def _section(self, text: str) -> None:
        ctk.CTkLabel(self.body, text=text, font=T.ui_font(12, "bold")).grid(
            row=self._r, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 2)); self._r += 1

    def _row(self, label: str, widget) -> None:
        ctk.CTkLabel(self.body, text=label, font=T.ui_font(12)).grid(row=self._r, column=0, sticky="w", padx=16, pady=4)
        widget.grid(row=self._r, column=1, sticky="e", padx=16, pady=4); self._r += 1

    def _full(self, widget, pady=4) -> None:
        widget.grid(row=self._r, column=0, columnspan=2, sticky="w", padx=16, pady=pady); self._r += 1

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

# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""左欄：搜尋框 + 依日期分組的筆記清單。

只負責「畫出來」和「回報點了哪個」，不碰檔案。
主視窗呼叫 refresh(groups, selected) 重畫。回呼：
    on_select(NoteId)         點了一張筆記
    on_add(day)               點日期列右邊的 ＋
    on_search(keyword)        搜尋框內容變了（停 250 ms 才送）
    on_note_menu(NoteId, x, y) 在筆記上按右鍵（主視窗決定選單內容）

清單列用 tk.Label 不用 CTkButton：一顆 CTkButton 要畫 10 ms，45 天約 100 列就 1 秒；tk.Label 不到 1 ms。
顏色自己依目前深淺色挑（theme 的 (淺, 深) 一對），主視窗換風格時會呼叫 refresh 重畫。
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from datetime import date
from typing import Callable, Optional

import customtkinter as ctk

from ..i18n import _
from .. import imefix
from ..storage import NoteId, NoteRef
from . import theme as T


def _c(pair) -> str:
    """theme 的 (淺色, 深色) → 目前要用的那個。"""
    if isinstance(pair, str):
        return pair
    return pair[1] if ctk.get_appearance_mode() == "Dark" else pair[0]


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_select: Callable[[NoteId], None],
                 on_add: Callable[[date], None], on_search: Callable[[str], None],
                 on_note_menu: Callable[[NoteId, int, int], None],
                 on_add_pick: Optional[Callable[[], None]] = None,
                 on_reorder: Optional[Callable[[date, list[int]], None]] = None):
        """on_add_pick：左下「額外新增」按鈕（主視窗跳月曆選日期再開新筆記）。"""
        super().__init__(master, width=T.SIDEBAR_WIDTH, corner_radius=0, fg_color=T.SIDEBAR_BG)
        self._row_font = tkfont.Font(family=T.UI_FONT_FAMILY, size=11)   # 量標題寬度用，跟列的字型一樣
        self._header_font = tkfont.Font(family=T.UI_FONT_FAMILY, size=10, weight="bold")
        self._width = T.SIDEBAR_WIDTH
        self._row_max_px = self._width - 62              # 列的可用寬：左欄寬減掉兩邊留白（14+4）、字的內距（10+10）、框、捲軸（量過剛好）
        self._titles: dict[NoteId, str] = {}             # 每列的完整標題（寬度改了要重算「…」）
        self._header_titles: dict[date, str] = {}        # 每天標題列的完整字（英文 2026/10/29 (Thu) Today 較長，窄的時候要「…」）
        self.grid_propagate(False)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._on_select = on_select
        self._on_add = on_add
        self._on_search = on_search
        self._on_note_menu = on_note_menu
        self._on_reorder = on_reorder
        self.searching = False                   # 主視窗設：目前清單是搜尋結果（過濾過，不給拖拉排序）
        self._press_job = None                   # 長按計時器
        self._drag: Optional[dict] = None        # 拖拉中：{"day", "nid", "lbl", "start"}
        self._selected: Optional[NoteId] = None
        self._rows: dict[NoteId, tk.Label] = {}
        self._groups: dict[date, list] = {}      # 日期 → [框, 標題列, 箭頭, 日期字, ＋, 筆記列…]（上色、摺疊用）
        self._collapsed: set[date] = set()       # 摺起來的日期

        self._search = ctk.CTkEntry(self, placeholder_text=_("🔍 搜尋日期或內容"), font=T.ui_font(12),
                                    height=30, corner_radius=T.RADIUS)
        self._search.grid(row=0, column=0, sticky="ew", padx=8, pady=(T.PAD, 6))
        self._search_timer = None
        self._search.bind("<KeyRelease>", self._search_debounced)   # 停 250 ms 才搜，打字不卡
        self._search.bind("<Escape>", lambda _e: self.clear_search())
        imefix.bind(self._search._entry)

        if on_add_pick is not None:              # 左下角：先選日期再新增（例如回頭補五月的紀錄）
            ctk.CTkButton(self, text=_("＋ 額外新增"), font=T.ui_font(12), height=30, corner_radius=T.RADIUS,
                          fg_color="transparent", border_width=1, text_color=T.TEXT, hover_color=T.ROW_HOVER,
                          command=on_add_pick).grid(row=2, column=0, sticky="ew", padx=8, pady=(4, T.PAD))

        self._list = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._list.grid(row=1, column=0, sticky="nsew", padx=(2, 0))
        self._list.grid_columnconfigure(0, weight=1)
        self._empty = ctk.CTkLabel(self._list, text=_("還沒有筆記\n按右邊的 ＋ 開第一張"), font=T.ui_font(12),
                                   text_color=T.TEXT_MUTED, justify="center")

    # ---- 外部呼叫 ----
    def refresh(self, groups: dict[date, list[NoteRef]], selected: Optional[NoteId],
                more: int = 0, on_more: Optional[Callable[[], None]] = None, hidden: int = 0) -> None:
        """重畫清單。groups 已經由主視窗切好（只畫最近幾天、最多幾張）；
        more > 0 就在最底下放「顯示更多（還有 N 天）」；hidden > 0 就提示「還有 N 張沒列出」。"""
        for w in self._list.winfo_children():
            if w is not self._empty:
                w.destroy()
        self._empty.grid_forget()
        self._rows.clear()
        self._titles.clear()
        self._selected = selected
        if not groups:
            self._empty.grid(row=0, column=0, pady=30)
            return
        self._bg = _c(T.SIDEBAR_BG)
        self._fg = _c(T.TEXT)
        self._hover = _c(T.ROW_HOVER)
        self._accent = _c(T.ACCENT)
        self._muted = _c(T.TEXT_MUTED)
        self._header = _c(T.DAY_HEADER)
        self._day_bg = _c(T.DAY_ACTIVE_BG)
        self._groups.clear()
        row = 0
        for day, refs in groups.items():
            # 一天一個框：框的底色就是「這一天」的底色（選中那天深灰，其他跟左欄一樣），摺疊就是把筆記列藏起來
            box = tk.Frame(self._list, bg=self._bg)
            box.grid(row=row, column=0, sticky="ew", pady=(4, 2))
            box.grid_columnconfigure(0, weight=1)
            row += 1
            widgets = [box] + self._day_header(box, day, len(refs))
            for r, ref in enumerate(refs, start=1):
                widgets.append(self._note_row(box, ref, r))
            self._groups[day] = widgets
            if day in self._collapsed:
                self._apply_collapse(day)
        if hidden > 0:
            tk.Label(self._list, text=_("還有 {0} 張沒列出，用搜尋找").format(hidden), bg=self._bg, fg=self._muted,
                     font=(T.UI_FONT_FAMILY, 10), pady=6).grid(row=row, column=0, sticky="ew", padx=10)
            row += 1
        if more > 0 and on_more is not None:
            lbl = tk.Label(self._list, text=_("顯示更多（還有 {0} 天）").format(more), bg=self._bg, fg=self._muted,
                           font=(T.UI_FONT_FAMILY, 10), cursor="hand2", pady=8)
            lbl.grid(row=row, column=0, sticky="ew", padx=10, pady=(8, 10))
            lbl.bind("<Button-1>", lambda _e: on_more())
        self.set_selected(selected)

    def set_selected(self, nid: Optional[NoteId]) -> None:
        """選中某張：那張藍色；它那一天整組深灰（跟其他天區分）；那天摺著的話自動展開。"""
        if self._selected in self._rows:
            self._paint(self._rows[self._selected], False)
        self._selected = nid
        if nid is not None and nid.day in self._collapsed and nid.day in self._groups:
            self._collapsed.discard(nid.day)
            self._apply_collapse(nid.day)
        for day in self._groups:
            self._paint_day(day)
        if nid in self._rows:
            self._paint(self._rows[nid], True)

    def set_width(self, width: int) -> None:
        """主視窗拖分隔線時呼叫：改寬度，並照新寬度重算每列標題的「…」。"""
        width = max(T.SIDEBAR_MIN, min(T.SIDEBAR_MAX, int(width)))
        if width == self._width:
            return
        self._width = width
        self._row_max_px = width - 62
        self.configure(width=width)
        for nid, lbl in self._rows.items():
            text = self._elide(self._titles.get(nid, lbl.cget("text")))
            if lbl.cget("text") != text:
                lbl.configure(text=text)
        for day, widgets in self._groups.items():        # 日期標題列也重算
            title = widgets[3]
            text = self._elide_header(self._header_titles.get(day, title.cget("text")))
            if title.cget("text") != text:
                title.configure(text=text)

    # ---- 長按拖拉排序（同一天裡上下移動）----
    LONG_PRESS_MS = 350

    def _day_labels(self, day: date) -> list:
        """這一天的筆記列（照目前畫面上的順序）。groups[day] = [框, 標題列, 箭頭, 日期字, ＋, 筆記列…]。"""
        return list(self._groups.get(day, [])[5:])

    def _press(self, e, nid: NoteId, lbl) -> None:
        self._on_select(nid)                     # 點一下照常開筆記
        self._cancel_press()
        if self._on_reorder is None or self.searching or self._search.get().strip():
            return                               # 搜尋中清單是過濾過的，不給排
        self._press_job = self.after(self.LONG_PRESS_MS, lambda: self._start_drag(nid, lbl))

    def _cancel_press(self) -> None:
        if self._press_job is not None:
            self.after_cancel(self._press_job)
            self._press_job = None

    def _start_drag(self, nid: NoteId, lbl) -> None:
        self._press_job = None
        if not lbl.winfo_exists() or len(self._day_labels(nid.day)) < 2:
            return
        self._drag = {"day": nid.day, "nid": nid, "lbl": lbl,
                      "start": [w for w in self._day_labels(nid.day)]}
        lbl.configure(cursor="fleur", relief="raised", bd=1)

    def _drag_motion(self, e) -> None:
        if self._drag is None:
            return
        labels = self._day_labels(self._drag["day"])
        me = self._drag["lbl"]
        others = [w for w in labels if w is not me]
        pos = sum(1 for w in others if e.y_root > w.winfo_rooty() + w.winfo_height() / 2)   # 游標在幾列的中線以下
        new = others[:pos] + [me] + others[pos:]
        if new != labels:                        # 畫面上即時換位置
            for r, w in enumerate(new, start=1):
                w.grid_configure(row=r)
            self._groups[self._drag["day"]] = self._groups[self._drag["day"]][:5] + new

    def _release(self, _e=None) -> None:
        self._cancel_press()
        if self._drag is None:
            return
        d, self._drag = self._drag, None
        d["lbl"].configure(cursor="hand2", relief="flat", bd=0)
        labels = self._day_labels(d["day"])
        if labels != d["start"] and self._on_reorder is not None:
            seq_of = {w: n.seq for n, w in self._rows.items()}
            self._on_reorder(d["day"], [seq_of[w] for w in labels if w in seq_of])

    def toggle_day(self, day: date) -> None:
        """點日期標題：摺疊／展開那一天的筆記列。摺疊狀態只記在這個視窗裡（重開就全展開）。"""
        if day in self._collapsed:
            self._collapsed.discard(day)
        else:
            self._collapsed.add(day)
        if day in self._groups:
            self._apply_collapse(day)

    def has(self, nid: NoteId) -> bool:
        return nid in self._rows

    def set_title(self, nid: NoteId, title: str) -> bool:
        """只改一列的字。這張不在清單裡（新的、或被搜尋濾掉）回 False，呼叫端再整欄重畫。"""
        lbl = self._rows.get(nid)
        if lbl is None:
            return False
        self._titles[nid] = title
        title = self._elide(title)
        if lbl.cget("text") != title:
            lbl.configure(text=title)
        return True

    def clear_search(self) -> None:
        self._search.delete(0, "end")
        self._on_search("")

    def _search_debounced(self, _e=None) -> None:
        if self._search_timer is not None:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(250, lambda: (setattr(self, "_search_timer", None),
                                                      self._on_search(self._search.get())))

    # ---- 內部 ----
    def _day_bg_of(self, day: date) -> str:
        """這一天的底色：選中的那張在這一天 → 深灰，否則跟左欄一樣。"""
        return self._day_bg if (self._selected is not None and self._selected.day == day) else self._bg

    def _paint(self, lbl: tk.Label, selected: bool) -> None:
        nid = next((n for n, w in self._rows.items() if w is lbl), None)
        bg = self._accent if selected else self._day_bg_of(nid.day) if nid else self._bg
        lbl.configure(bg=bg, fg="#ffffff" if selected else self._fg)

    def _paint_day(self, day: date) -> None:
        bg = self._day_bg_of(day)
        for w in self._groups.get(day, ()):
            if w is self._rows.get(self._selected):
                continue                             # 選中那張維持藍色
            w.configure(bg=bg)

    def _apply_collapse(self, day: date) -> None:
        widgets = self._groups.get(day)
        if not widgets:
            return
        box, bar, arrow = widgets[0], widgets[1], widgets[2]
        folded = day in self._collapsed
        arrow.configure(text="▸" if folded else "▾")
        for w in widgets[1:]:
            if w.master is box and w is not bar:     # 筆記列（直接掛在框裡的，標題列以外）
                w.grid_remove() if folded else w.grid()

    def _day_header(self, box: tk.Frame, day: date, n: int) -> list:
        """日期標題列：▾ 2026/10/29（四） 今天 … ＋。點日期（或箭頭）摺疊／展開，點 ＋ 在這天加一張。
        回傳建出來的 widget（框、箭頭、字、＋），給上色用。"""
        bar = tk.Frame(box, bg=self._bg)
        bar.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        bar.grid_columnconfigure(1, weight=1)
        from ..storage import TODO_DAY
        is_todo = day == TODO_DAY
        label = T.fmt_day(day)
        if day == date.today():
            label += _(" 今天")
        self._header_titles[day] = label
        arrow = tk.Label(bar, text="▾", bg=self._bg, fg=self._muted, font=(T.UI_FONT_FAMILY, 9), cursor="hand2", padx=2)
        arrow.grid(row=0, column=0, sticky="w")
        title = tk.Label(bar, text=self._elide_header(label), bg=self._bg,
                         fg=_c(T.DANGER) if is_todo else self._header,          # 待辦事項：紅字
                         font=(T.UI_FONT_FAMILY, 10, "bold"), anchor="w", cursor="hand2")
        title.grid(row=0, column=1, sticky="w")
        for w in (arrow, title, bar):
            w.bind("<Button-1>", lambda _e, d=day: self.toggle_day(d))
        plus = tk.Label(bar, text="" if is_todo else _("＋"), bg=self._bg, fg=self._muted, font=(T.UI_FONT_FAMILY, 11),
                        cursor="arrow" if is_todo else "hand2", padx=6)   # 待辦事項只有一張，不給新增
        plus.grid(row=0, column=2, sticky="e", padx=(0, 4))
        if not is_todo:
            plus.bind("<Button-1>", lambda _e, d=day: self._on_add(d))
        plus.bind("<Enter>", lambda _e, w=plus: w.configure(fg=self._fg))
        plus.bind("<Leave>", lambda _e, w=plus: w.configure(fg=self._muted))
        return [bar, arrow, title, plus]

    def _elide_header(self, text: str) -> str:
        """日期標題列可用寬 = 左欄寬 − 箭頭(16) − ＋(32) − 捲軸與留白(24)。"""
        return self._elide(text, self._header_font, self._width - 72)

    def _elide(self, text: str, font=None, max_px: Optional[int] = None) -> str:
        """標題太長就切掉尾巴加「…」（tk.Label 不會自己省略，只會硬切）。"""
        font = font or self._row_font
        max_px = self._row_max_px if max_px is None else max_px
        if font.measure(text) <= max_px:
            return text
        lo, hi = 0, len(text)
        while lo < hi:                           # 二分找最長放得下的前綴
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + "…") <= max_px:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + "…"

    def _note_row(self, box: tk.Frame, ref: NoteRef, row: int) -> tk.Label:
        lbl = tk.Label(box, text=self._elide(ref.title), bg=self._bg, fg=self._fg, font=(T.UI_FONT_FAMILY, 11),
                       anchor="w", padx=10, pady=5, cursor="hand2")
        lbl.grid(row=row, column=0, sticky="ew", padx=(14, 4), pady=1)
        lbl.bind("<Button-1>", lambda e, n=ref.id, w=lbl: self._press(e, n, w))
        lbl.bind("<B1-Motion>", self._drag_motion)
        lbl.bind("<ButtonRelease-1>", self._release)
        lbl.bind("<Button-3>", lambda e, n=ref.id: self._on_note_menu(n, e.x_root, e.y_root))
        lbl.bind("<Enter>", lambda _e, w=lbl, n=ref.id: w.configure(bg=self._hover) if n != self._selected else None)
        lbl.bind("<Leave>", lambda _e, w=lbl, n=ref.id: w.configure(bg=self._day_bg_of(n.day)) if n != self._selected else None)
        self._rows[ref.id] = lbl
        self._titles[ref.id] = ref.title
        return lbl

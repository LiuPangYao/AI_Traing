# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""小月曆：挑一個日期（左欄「額外新增」用）。

ask_date(parent, initial, quiet) → date 或 None（取消）。
畫面：◀ 2026 年 5 月 ▶，上面一排 一～日，底下 6 排日子；今天藍框、initial 那天深灰；點日子就回傳。
quiet：主視窗的 _quiet_dialog（讓 CTkToplevel 不閃、設圖示）；沒給也能用。
"""
from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date
from typing import Callable, Optional

import customtkinter as ctk

from ..i18n import _
from . import theme as T

WEEKDAYS = ("一", "二", "三", "四", "五", "六", "日")     # 顯示時才 _()：import 的時候語言還沒設


def ask_date(parent, initial: Optional[date] = None, quiet: Optional[Callable] = None) -> Optional[date]:
    initial = initial or date.today()
    dlg = ctk.CTkToplevel(parent)
    dlg.title(_("選日期"))
    dlg.attributes("-topmost", True)
    if quiet:
        quiet(dlg)
    else:
        tk.Toplevel.resizable(dlg, False, False)
    dlg.geometry(f"+{parent.winfo_rootx() + 60}+{parent.winfo_rooty() + 120}")
    dlg.grab_set()                                    # 選完才能回主視窗
    result: list[Optional[date]] = [None]
    state = {"y": initial.year, "m": initial.month}
    bg = T.MAIN_BG[1] if ctk.get_appearance_mode() == "Dark" else T.MAIN_BG[0]
    fg = T.TEXT[1] if ctk.get_appearance_mode() == "Dark" else T.TEXT[0]
    muted = T.TEXT_MUTED[1] if ctk.get_appearance_mode() == "Dark" else T.TEXT_MUTED[0]
    accent = T.ACCENT[1] if ctk.get_appearance_mode() == "Dark" else T.ACCENT[0]
    active = T.DAY_ACTIVE_BG[1] if ctk.get_appearance_mode() == "Dark" else T.DAY_ACTIVE_BG[0]
    hover = T.ROW_HOVER[1] if ctk.get_appearance_mode() == "Dark" else T.ROW_HOVER[0]

    head = ctk.CTkFrame(dlg, fg_color="transparent")
    head.pack(fill="x", padx=12, pady=(12, 4))
    title = ctk.CTkLabel(head, text="", font=T.ui_font(13, "bold"))

    def nav(dy: int, dm: int) -> None:
        m = state["m"] + dm
        y = state["y"] + dy + (m - 1) // 12
        state["y"], state["m"] = y, (m - 1) % 12 + 1
        draw()

    for text, cmd, side in (("«", lambda: nav(-1, 0), "left"), ("‹", lambda: nav(0, -1), "left"),
                            ("›", lambda: nav(0, 1), "right"), ("»", lambda: nav(1, 0), "right")):
        ctk.CTkButton(head, text=text, width=28, height=26, font=T.ui_font(13), fg_color="transparent",
                      hover_color=T.ROW_HOVER, text_color=T.TEXT, command=cmd).pack(side=side)
    title.pack(side="left", expand=True)

    grid = tk.Frame(dlg, bg=bg)
    grid.pack(padx=12, pady=(0, 6))
    for c, w in enumerate(WEEKDAYS):
        tk.Label(grid, text=_(w),bg=bg, fg=muted, font=(T.UI_FONT_FAMILY, 9), width=3).grid(row=0, column=c, pady=(0, 2))
    cells: list[tk.Label] = []

    def pick(d: date) -> None:
        result[0] = d
        dlg.destroy()

    def draw() -> None:
        for c in cells:
            c.destroy()
        cells.clear()
        title.configure(text=_("{0} 年 {1} 月").format(state['y'], state['m']))
        for r, week in enumerate(calendar.monthcalendar(state["y"], state["m"]), start=1):
            for c, day in enumerate(week):
                if day == 0:
                    lbl = tk.Label(grid, text="", bg=bg, width=3)
                else:
                    d = date(state["y"], state["m"], day)
                    is_today, is_init = d == date.today(), d == initial
                    lbl = tk.Label(grid, text=str(day), width=3, pady=3, cursor="hand2",
                                   font=(T.UI_FONT_FAMILY, 10, "bold" if is_today else "normal"),
                                   bg=active if is_init else bg, fg=accent if is_today else fg,
                                   highlightthickness=1 if is_today else 0, highlightbackground=accent)
                    lbl.bind("<Button-1>", lambda _e, d=d: pick(d))
                    lbl.bind("<Enter>", lambda _e, w=lbl: w.configure(bg=hover))
                    lbl.bind("<Leave>", lambda _e, w=lbl, b=(active if is_init else bg): w.configure(bg=b))
                lbl.grid(row=r, column=c, padx=1, pady=1)
                cells.append(lbl)

    foot = ctk.CTkFrame(dlg, fg_color="transparent")
    foot.pack(fill="x", padx=12, pady=(0, 10))
    ctk.CTkButton(foot, text=_("今天"), width=60, height=26, font=T.ui_font(12), fg_color="transparent",
                  border_width=1, text_color=T.TEXT, command=lambda: pick(date.today())).pack(side="left")
    ctk.CTkButton(foot, text=_("取消"), width=60, height=26, font=T.ui_font(12), fg_color="transparent",
                  text_color=T.TEXT_MUTED, hover_color=T.ROW_HOVER, command=dlg.destroy).pack(side="right")
    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    draw()
    dlg.wait_window()
    return result[0]

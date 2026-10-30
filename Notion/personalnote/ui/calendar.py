# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""月曆：這個月哪幾天有筆記、每天用了多久（顏色越深用越久）。點日期跳到那天（視窗留著，可以繼續翻）；◀ ▶ 換月，「今天」回本月。
資料：筆記張數從 NoteStore，使用秒數從 usage.UsageLog。只畫，不碰檔案。"""
from __future__ import annotations

import calendar as _cal
import tkinter as tk
from datetime import date
from typing import Callable, Optional

import customtkinter as ctk

from ..i18n import _
from ..usage import UsageLog, fmt_duration
from ..storage import NoteStore
from . import theme as T

LEVELS_LIGHT = ("#ffffff", "#dbe7fd", "#b7cffb", "#86aff7", "#4f8cff")   # 用 0／<10／<30／<60／≥60 分
LEVELS_DARK = ("#2b2f38", "#2f3f5e", "#355084", "#3b64ad", "#4f8cff")


def level(seconds: int) -> int:
    m = int(seconds) // 60
    return 0 if m <= 0 else 1 if m < 10 else 2 if m < 30 else 3 if m < 60 else 4


def show(parent, store: NoteStore, usage: UsageLog, on_pick: Callable[[date], None],
         quiet: Optional[Callable] = None, year: Optional[int] = None, month: Optional[int] = None):
    today = date.today()
    dlg = ctk.CTkToplevel(parent)
    dlg.title(_("月曆"))
    dlg.attributes("-topmost", True)
    if quiet:
        quiet(dlg)
    else:
        tk.Toplevel.resizable(dlg, False, False)
    dark = ctk.get_appearance_mode() == "Dark"
    pick = lambda pair: pair[1] if dark else pair[0]
    accent, text_c, muted_c = pick(T.ACCENT), pick(T.TEXT), pick(T.TEXT_MUTED)
    state = {"y": year or today.year, "m": month or today.month, "cells": {}}

    head = ctk.CTkFrame(dlg, fg_color="transparent")
    head.pack(fill="x", padx=16, pady=(14, 6))
    title = ctk.CTkLabel(head, text="", font=T.ui_font(15, "bold"))
    soft = dict(fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, font=T.ui_font(12), height=28)
    ctk.CTkButton(head, text="◀", width=36, command=lambda: shift(-1), **soft).pack(side="left")
    title.pack(side="left", expand=True)
    ctk.CTkButton(head, text="▶", width=36, command=lambda: shift(1), **soft).pack(side="right")
    ctk.CTkButton(head, text=_("今天"), width=64, command=lambda: goto(today.year, today.month), **soft).pack(side="right", padx=(0, 8))

    week = ctk.CTkFrame(dlg, fg_color="transparent")
    week.pack(fill="x", padx=16)
    for i, w in enumerate(T.WEEKDAY_ZH):
        week.grid_columnconfigure(i, weight=1, uniform="d")
        ctk.CTkLabel(week, text=_(w), font=T.ui_font(11), text_color=T.TEXT_MUTED).grid(row=0, column=i, pady=(2, 2))
    grid = ctk.CTkFrame(dlg, fg_color="transparent")
    grid.pack(fill="both", expand=True, padx=16)
    for c in range(7):
        grid.grid_columnconfigure(c, weight=1, uniform="d")
    foot = ctk.CTkLabel(dlg, text="", font=T.ui_font(11), text_color=T.TEXT_MUTED, wraplength=560, justify="left", anchor="w")
    foot.pack(fill="x", padx=16, pady=(8, 14))

    def render() -> None:
        for w in grid.winfo_children():
            w.destroy()
        y, m = state["y"], state["m"]
        title.configure(text=f"{y} / {m:02d}")
        counts = {d: len(store.list_notes(d)) for d in store.list_days() if d.year == y and d.month == m}
        secs = usage.month(y, m)
        levels = LEVELS_DARK if dark else LEVELS_LIGHT
        state["cells"] = {}
        for r, days in enumerate(_cal.Calendar(firstweekday=0).monthdayscalendar(y, m)):   # 週一開頭，跟 WEEKDAY_ZH 一樣
            grid.grid_rowconfigure(r, minsize=58, weight=1)
            for c, dnum in enumerate(days):
                if dnum == 0:
                    continue
                d = date(y, m, dnum)
                n, s = counts.get(d, 0), secs.get(d, 0)
                lv = level(s)
                bg = levels[lv]
                fg = "#ffffff" if lv >= 3 else text_c
                sub_fg = "#e8eefc" if lv >= 3 else muted_c
                cell = tk.Frame(grid, bg=bg, cursor="hand2", highlightthickness=2 if d == today else 0,
                                highlightbackground=accent, highlightcolor=accent)
                cell.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                tk.Label(cell, text=str(dnum), bg=bg, fg=fg, font=(T.UI_FONT_FAMILY, 11, "bold" if d == today else "normal"),
                         anchor="nw").pack(anchor="nw", padx=6, pady=(3, 0))
                parts = []
                if n:
                    parts.append(_("{0} 張").format(n))
                if s >= 60:
                    parts.append(fmt_duration(s, _))
                tk.Label(cell, text="\n".join(parts), bg=bg, fg=sub_fg, font=(T.UI_FONT_FAMILY, 9), anchor="sw",
                         justify="left").pack(anchor="sw", padx=6, pady=(0, 3), fill="x")
                for w in (cell, *cell.winfo_children()):
                    w.bind("<Button-1>", lambda _e, dd=d: on_pick(dd))
                state["cells"][d] = cell
        total = sum(secs.values())
        text = _("這個月：{0} 天有筆記、{1} 張；用了 {2}").format(len(counts), sum(counts.values()), fmt_duration(total, _))
        if secs:
            text += "；" + _("平均每個有用的日子 {0}").format(fmt_duration(total // len(secs), _))
        foot.configure(text=text)

    def goto(y: int, m: int) -> None:
        state["y"], state["m"] = y, m
        render()

    def shift(k: int) -> None:
        m, y = state["m"] + k, state["y"]
        if m < 1:
            m, y = 12, y - 1
        if m > 12:
            m, y = 1, y + 1
        goto(y, m)

    dlg.bind("<Left>", lambda _e: shift(-1))
    dlg.bind("<Right>", lambda _e: shift(1))
    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    render()
    T.center_over(dlg, parent, 620, 500)
    dlg._cal_state = state                 # ui_checks 用
    dlg._cal_shift = shift
    parent._calendar = dlg
    return dlg

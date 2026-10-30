# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""未完成清單：掃最近 DAYS 天所有筆記裡的「- [ ] 」行，列成一頁（每張筆記一段：日期＋標題，下面是它的未完成項目）。
點項目開那張筆記；「複製成文字」把整份複製到剪貼簿（週報、交接用）。只讀，不改筆記。"""
from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from typing import Callable, Optional

import customtkinter as ctk

from ..i18n import _
from ..listing import CHECK_RE
from ..storage import NoteId, NoteStore, TODO_DAY
from . import theme as T

DAYS = 180
MAX_ITEMS = 400


def collect(store: NoteStore, days: int = DAYS, today: Optional[date] = None) -> list[tuple[NoteId, str, list[str]]]:
    """[(編號, 標題, [未完成項目…])]，新的日期在前；待辦事項那張也算（排最前）。"""
    today = today or date.today()
    since = today - timedelta(days=days)
    out = []
    total = 0
    for d in store.list_days():
        if d != TODO_DAY and d < since:
            continue
        for ref in store.list_notes(d):
            text, ok = store.try_load(ref.id)
            if not ok:
                continue
            items = []
            for line in text.split("\n"):
                m = CHECK_RE.match(line)
                if m and m.group(2) == " ":
                    items.append(m.group(3).strip())
            if items:
                out.append((ref.id, ref.title, items))
                total += len(items)
                if total >= MAX_ITEMS:
                    return out
    return out


def as_text(rows: list[tuple[NoteId, str, list[str]]]) -> str:
    parts = []
    for nid, title, items in rows:
        head = _("待辦事項") if nid.day == TODO_DAY else f"{nid.day.month:02d}/{nid.day.day:02d} {title}".rstrip()
        parts.append(head + "\n" + "\n".join(f"- [ ] {it}" for it in items))
    return "\n\n".join(parts) + ("\n" if parts else "")


def show(parent, store: NoteStore, on_open: Callable[[NoteId], None], quiet: Optional[Callable] = None):
    dlg = ctk.CTkToplevel(parent)
    dlg.title(_("未完成清單"))
    dlg.attributes("-topmost", True)
    if quiet:
        quiet(dlg)
    else:
        tk.Toplevel.resizable(dlg, False, False)
    rows = collect(store)
    n_items = sum(len(items) for _n, _t, items in rows)
    head = ctk.CTkFrame(dlg, fg_color="transparent")
    head.pack(fill="x", padx=16, pady=(14, 4))
    ctk.CTkLabel(head, text=_("未完成清單（最近 {0} 天，{1} 項）").format(DAYS, n_items), font=T.ui_font(14, "bold")).pack(side="left")
    soft = dict(fg_color=T.BTN_SOFT_BG, hover_color=T.BTN_SOFT_HOVER, text_color=T.BTN_SOFT_FG, font=T.ui_font(12), height=28)

    def copy_all():
        dlg.clipboard_clear(); dlg.clipboard_append(as_text(rows))
        status.configure(text=_("已複製到剪貼簿"))
    ctk.CTkButton(head, text=_("複製成文字"), width=100, command=copy_all, **soft).pack(side="right")
    body = ctk.CTkScrollableFrame(dlg, fg_color="transparent", width=560, height=400)
    body.pack(fill="both", expand=True, padx=12, pady=(0, 4))
    dark = ctk.get_appearance_mode() == "Dark"
    muted = T.TEXT_MUTED[1] if dark else T.TEXT_MUTED[0]
    items_widgets = []
    if not rows:
        ctk.CTkLabel(body, text=_("沒有未完成的項目。行首打「- [ ] 」就會出現在這裡。"), font=T.ui_font(12), text_color=T.TEXT_MUTED).pack(pady=30)
    for nid, title, items in rows:
        head_txt = _("待辦事項") if nid.day == TODO_DAY else f"{nid.day.month:02d}/{nid.day.day:02d}  {title}"
        h = ctk.CTkLabel(body, text=head_txt, font=T.ui_font(12, "bold"), anchor="w", cursor="hand2")
        h.pack(fill="x", pady=(8, 2))
        h.bind("<Button-1>", lambda _e, n=nid: on_open(n))
        for it in items:
            lbl = ctk.CTkLabel(body, text="☐  " + it, font=T.ui_font(12), text_color=T.TEXT_MUTED, anchor="w", justify="left",
                               wraplength=520, cursor="hand2")
            lbl.pack(fill="x", padx=(14, 0))
            lbl.bind("<Button-1>", lambda _e, n=nid: on_open(n))
            lbl.bind("<Enter>", lambda e: e.widget.configure(text_color=T.TEXT))
            lbl.bind("<Leave>", lambda e: e.widget.configure(text_color=muted))
            items_widgets.append(lbl)
    status = ctk.CTkLabel(dlg, text=_("點項目會開那張筆記；打勾要在筆記裡打。"), font=T.ui_font(11), text_color=T.TEXT_MUTED)
    status.pack(padx=16, pady=(0, 12), anchor="w")
    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    T.center_over(dlg, parent, 600, 520)
    dlg._todo_rows = rows                  # ui_checks 用
    dlg._todo_items = items_widgets
    parent._todo_view = dlg
    return dlg

# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""「舊版本…」視窗：左邊列這張筆記的快照（時間、第一行），右邊預覽，按「還原這一版」就換回去。

快照是 storage.snapshot() 在每次存檔前留的（內容有變、距上一份 10 分鐘以上），最多 30 份。
還原前主視窗會先把現在的內容也留一份（force），所以還原錯了可以再還回來。
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk

from ..i18n import _
from ..storage import NoteId, NoteStore, title_of
from . import theme as T


def show(parent, store: NoteStore, nid: NoteId, on_restore: Callable[[NoteId, Path], None],
         quiet: Optional[Callable] = None) -> None:
    snaps = store.list_snapshots(nid)
    dlg = ctk.CTkToplevel(parent)
    dlg.title(_("舊版本"))
    dlg.attributes("-topmost", True)
    if quiet:
        quiet(dlg)
    else:
        tk.Toplevel.resizable(dlg, False, False)
    T.center_over(dlg, parent, 720, 440)
    dlg.grab_set()
    dlg.grid_columnconfigure(1, weight=1)
    dlg.grid_rowconfigure(1, weight=1)
    dark = ctk.get_appearance_mode() == "Dark"
    bg, fg, muted, accent, sel = (T.MAIN_BG[dark], T.TEXT[dark], T.TEXT_MUTED[dark], T.ACCENT[dark], T.ROW_SELECTED_BG[dark])

    ctk.CTkLabel(dlg, text=_("{0} 的舊版本（{1} 份）").format(title_of(store.try_load(nid)[0]) or T.fmt_day(nid.day, False), len(snaps)),
                 font=T.ui_font(13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 4))
    lst = ctk.CTkScrollableFrame(dlg, width=220, fg_color=T.SIDEBAR_BG, corner_radius=T.RADIUS)
    lst.grid(row=1, column=0, sticky="nsw", padx=(12, 6), pady=4)
    preview = ctk.CTkTextbox(dlg, font=T.ui_font(12), wrap="word", corner_radius=T.RADIUS, fg_color=T.EDITOR_BG,
                             border_width=1, border_color=T.EDITOR_BORDER)
    preview.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=4)
    state = {"path": None, "rows": []}

    def pick(i: int) -> None:
        when, path = snaps[i]
        state["path"] = path
        for k, row in enumerate(state["rows"]):
            row.configure(bg=sel if k == i else T.SIDEBAR_BG[dark], fg=accent if k == i else fg)
        preview.configure(state="normal")
        preview.delete("1.0", "end")
        try:
            preview.insert("1.0", store.load_snapshot(path))
        except Exception as e:                               # 解不開（別台電腦的快照）
            preview.insert("1.0", _("這一版解不開：{0}").format(e))
        preview.configure(state="disabled")
        restore_btn.configure(state="normal")

    if not snaps:
        tk.Label(lst, text=_("還沒有舊版本。\n內容有變且隔 10 分鐘以上存檔時會自動留一份。"), bg=T.SIDEBAR_BG[dark], fg=muted,
                 font=(T.UI_FONT_FAMILY, 10), justify="left", wraplength=200).pack(anchor="w", padx=8, pady=8)
    for i, (when, path) in enumerate(snaps):
        try:
            first = (store.load_snapshot(path).split("\n", 1)[0] or "").lstrip("# ")[:24]
        except Exception:
            first = _("（解不開）")
        row = tk.Label(lst, text=f"{when:%Y/%m/%d %H:%M}\n{first}", bg=T.SIDEBAR_BG[dark], fg=fg, justify="left",
                       font=(T.UI_FONT_FAMILY, 10), anchor="w", padx=8, pady=4, cursor="hand2")
        row.pack(fill="x", padx=4, pady=1)
        row.bind("<Button-1>", lambda _e, i=i: pick(i))
        state["rows"].append(row)

    foot = ctk.CTkFrame(dlg, fg_color="transparent")
    foot.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 12))
    ctk.CTkLabel(foot, text=_("還原會把現在的內容也留成一份舊版本，可以再還回來。"), font=T.ui_font(10),
                 text_color=T.TEXT_MUTED).pack(side="left")

    def do_restore() -> None:
        if state["path"] is None:
            return
        on_restore(nid, Path(state["path"]))
        dlg.destroy()

    ctk.CTkButton(foot, text=_("取消"), width=70, height=28, font=T.ui_font(12), fg_color="transparent",
                  text_color=T.TEXT_MUTED, hover_color=T.ROW_HOVER, command=dlg.destroy).pack(side="right")
    restore_btn = ctk.CTkButton(foot, text=_("還原這一版"), width=100, height=28, font=T.ui_font(12),
                                fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, state="disabled", command=do_restore)
    restore_btn.pack(side="right", padx=(0, 8))
    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    if snaps:
        pick(0)
    dlg._versions_state = state                              # ui_checks 用
    dlg._versions_restore = do_restore
    parent._versions_dialog = dlg

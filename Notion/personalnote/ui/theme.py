# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""外觀常數。要換顏色、間距、字型，改這裡就好。顏色是 (淺色, 深色) 一對。"""
from __future__ import annotations

import customtkinter as ctk

ACCENT = ("#4f5bd5", "#8b93ff")   # 主色：選中的筆記、按鈕、連結（靛藍，比純藍柔和；Peter 2026-10-30 要一套好一點的配色）
ACCENT_HOVER = ("#3f49b8", "#7a82f0")
SIDEBAR_BG = ("#f0eee9", "#1f2026")   # 左欄：暖灰（紙張感）
MAIN_BG = ("#f7f6f2", "#17181c")   # 視窗底：暖白，比內文框暗一點點，白框才看得出來
EDITOR_BG = ("#ffffff", "#24262c")   # 可以打字的地方：純白
EDITOR_BORDER = ("#d9d6cf", "#3a3d46")   # 標題欄、內文框的細邊
TEXT = ("#1c1b19", "#e8e6e3")   # 近黑（不用純黑，長時間看比較不刺）
TEXT_MUTED = ("#7a776f", "#9b9a95")
ROW_HOVER = ("#e6e3dc", "#2c2e35")
DAY_HEADER = ("#3f3e3a", "#c5c4bf")
DAY_ACTIVE_BG = ("#e8e5dd", "#2a2c33")   # 左欄：選中那張所在的那一天整組的底色
ROW_SELECTED_BG = ("#dde0f7", "#33375a")   # 左欄：選中那張的淡靛藍底（左邊再加一條主色色帶）
DANGER = ("#d9534f", "#e06c66")
CARD_BG = ("#ffffff", "#2a2c33")   # 設定面板的卡片
DIVIDER = ("#e8e5de", "#3a3d46")      # 卡片裡列與列之間的細線
PANEL_BG = ("#f3f1ec", "#1c1d22")   # 設定面板右邊的底
BTN_SOFT_BG = ("#e9ebfa", "#343a5e")   # 次要按鈕：淡靛藍底、靛藍字
BTN_SOFT_HOVER = ("#dbdff7", "#3f4670")
BTN_SOFT_FG = ("#4149c0", "#aab0ff")
KEYCAP_BG = ("#efede8", "#3a3d46")   # 快捷鍵表的鍵帽
KEYCAP_HOVER = ("#e3e0d9", "#464a55")

PAD = 10
RADIUS = 6                   # 圓角小一點：CTk 畫圓角是用反鋸齒的圓，半徑大四個角看起來糊糊的（Peter 反映）
SIDEBAR_WIDTH = 240          # 預設寬；要放得下英文的「2026/10/29 (Thu) Today」加「＋」（中文較短）
SIDEBAR_MIN, SIDEBAR_MAX = 180, 480   # 拖分隔線能拖到的範圍（再窄日期標題會被切）
SIDEBAR_HEIGHT = 220         # 左欄放下面時的預設高
SIDEBAR_MIN_H, SIDEBAR_MAX_H = 120, 600   # 放下面時拖分隔線能拖到的範圍
MIN_FONT, MAX_FONT = 8, 48

from .. import platform_

UI_FONT_FAMILY = platform_.ui_font_family()      # Windows 微軟正黑體；Linux Noto Sans CJK TC


def ui_font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=UI_FONT_FAMILY, size=size, weight=weight)


_ICON_CACHE: dict = {}


def clear_icon_cache() -> None:
    """CTkImage 綁在建立它時的 Tk 根視窗上；主視窗重新建立（測試會）就要清掉，不然會「image doesn't exist」。"""
    _ICON_CACHE.clear()


def icon(name: str, size: int = 18, scaling: float = 1.0):
    """工具列圖示：assets/icons/<name>_light.png 與 _dark.png（tools/make_icons.py 畫的 128 px）。
    先用 LANCZOS 縮到實際像素（size × 螢幕縮放），再交給 CTkImage——讓它自己縮會有鋸齒（Peter 2026-10-30）。
    找不到檔就回 None，按鈕退回顯示文字。打包後圖示在 sys._MEIPASS/assets。"""
    key = (name, size, round(float(scaling), 2))
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    import sys
    from pathlib import Path
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent)) / "assets" / "icons"
    try:
        from PIL import Image
        px = max(1, int(round(size * float(scaling))))
        light = Image.open(base / f"{name}_light.png").convert("RGBA").resize((px, px), Image.LANCZOS)
        dark = Image.open(base / f"{name}_dark.png").convert("RGBA").resize((px, px), Image.LANCZOS)
        img = ctk.CTkImage(light_image=light, dark_image=dark, size=(size, size))
    except Exception:
        img = None
    _ICON_CACHE[key] = img
    return img


def apply_appearance(theme: str) -> None:
    ctk.set_appearance_mode(theme)          # "dark" / "light" / "system"
    ctk.set_default_color_theme("blue")


WEEKDAY_ZH = ("一", "二", "三", "四", "五", "六", "日")


def fmt_day(d, with_weekday: bool = True) -> str:
    """畫面上的日期：台灣習慣 2026/10/28（三）；英文版翻譯表裡寫成 2026/10/28 (Wed)。
    資料夾名稱另外用 ISO（2026-10-28）才好排序。"""
    from ..i18n import _
    from ..storage import TODO_DAY
    if d == TODO_DAY:
        return _("待辦事項")
    s = f"{d.year}/{d.month:02d}/{d.day:02d}"
    return _("{0}（{1}）").format(s, _(WEEKDAY_ZH[d.weekday()])) if with_weekday else s


LINK_COLOR = ("#3b49c9", "#9aa3ff")


def center_over(dlg, parent, width: int = 0, height: int = 0) -> None:
    """跳出視窗（設定、清除、舊版本）放在主視窗正中央，不用每次自己拖。
    沒給大小就先排版、拿內容需要的大小；主視窗整個在主螢幕裡時，順便夾住不讓跳出視窗超出螢幕
    （主視窗在第二螢幕時座標可能是負的或超過主螢幕寬，那就不夾，照中央放）。"""
    dlg.update_idletasks()
    w = width or dlg.winfo_reqwidth()
    h = height or dlg.winfo_reqheight()
    px, py, pw, ph = parent.winfo_rootx(), parent.winfo_rooty(), parent.winfo_width(), parent.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2 - 16                 # 標題列不算在 rooty 裡，往上補一點才是視覺上的正中央
    sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
    if 0 <= px and px + pw <= sw:
        x = max(0, min(x, sw - w))
    if 0 <= py and py + ph <= sh:
        y = max(0, min(y, sh - h - 48))         # 底下留工作列
    dlg.geometry(f"{w}x{h}+{x}+{y}" if width else f"+{x}+{y}")


def tooltip(widget, text: str, delay_ms: int = 600) -> None:
    """滑鼠停 0.6 秒出現的小提示（工具列、格式列按鈕都用這套）。"""
    import tkinter as tk
    state = {"win": None, "job": None}

    def show():
        state["job"] = None
        if state["win"] is not None or not widget.winfo_exists():
            return
        w = tk.Toplevel(widget)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        tk.Label(w, text=text() if callable(text) else text,          # 可以給函式：快捷鍵改了提示跟著變
                 font=(UI_FONT_FAMILY, 10), bg="#333843", fg="#ffffff", padx=8, pady=4).pack()
        w.geometry(f"+{widget.winfo_rootx()}+{widget.winfo_rooty() + widget.winfo_height() + 4}")
        state["win"] = w

    def hide(_e=None):
        if state["job"] is not None:
            widget.after_cancel(state["job"]); state["job"] = None
        if state["win"] is not None:
            state["win"].destroy(); state["win"] = None

    def arm(*_):                                   # *_：CTk 有些地方會不帶 event 呼叫綁定的函式
        if state["job"] is None and widget.winfo_exists():
            state["job"] = widget.after(delay_ms, show)

    widget.bind("<Enter>", arm, add="+")
    widget.bind("<Leave>", hide, add="+")
    widget.bind("<ButtonPress>", hide, add="+")

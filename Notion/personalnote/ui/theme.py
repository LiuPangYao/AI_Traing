# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""外觀常數。要換顏色、間距、字型，改這裡就好。顏色是 (淺色, 深色) 一對。"""
from __future__ import annotations

import customtkinter as ctk

ACCENT = ("#2f6fed", "#4f8cff")          # 主色：選中的筆記、按鈕
ACCENT_HOVER = ("#245bd0", "#3b78f0")
SIDEBAR_BG = ("#f1f3f7", "#1b1d22")
MAIN_BG = ("#ffffff", "#15161a")
EDITOR_BG = ("#eef1f6", "#262a33")       # 可以打字的地方：要跟外框明顯不同（Peter：不然不知道哪裡能輸入）
EDITOR_BORDER = ("#c9cfda", "#3a3f4b")   # 標題欄、內文框的細邊
TEXT = ("#1f2328", "#e6e6e6")
TEXT_MUTED = ("#6b7280", "#9aa0a6")
ROW_HOVER = ("#e4e8f0", "#2a2d35")
DAY_HEADER = ("#374151", "#c7cbd1")
DAY_ACTIVE_BG = ("#e4e8f0", "#272a32")   # 左欄：選中那張所在的那一天整組的底色（比左欄深一階就好，選中那張另外有色帶）
ROW_SELECTED_BG = ("#d6e2fb", "#2b3a5c") # 左欄：選中那張的淡底（左邊再加一條主色色帶，不整條塗藍）
DANGER = ("#d9534f", "#e06c66")

PAD = 10
RADIUS = 6                   # 圓角小一點：CTk 畫圓角是用反鋸齒的圓，半徑大四個角看起來糊糊的（Peter 反映）
SIDEBAR_WIDTH = 240          # 預設寬；要放得下英文的「2026/10/29 (Thu) Today」加「＋」（中文較短）
SIDEBAR_MIN, SIDEBAR_MAX = 180, 480   # 拖分隔線能拖到的範圍（再窄日期標題會被切）
MIN_FONT, MAX_FONT = 8, 48

from .. import platform_

UI_FONT_FAMILY = platform_.ui_font_family()      # Windows 微軟正黑體；Linux Noto Sans CJK TC


def ui_font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=UI_FONT_FAMILY, size=size, weight=weight)


_ICON_CACHE: dict = {}


def clear_icon_cache() -> None:
    """CTkImage 綁在建立它時的 Tk 根視窗上；主視窗重新建立（測試會）就要清掉，不然會「image doesn't exist」。"""
    _ICON_CACHE.clear()


def icon(name: str, size: int = 18):
    """工具列圖示：assets/icons/<name>_light.png 與 _dark.png（tools/make_icons.py 畫的）。
    找不到檔就回 None，按鈕退回顯示文字。打包後圖示在 sys._MEIPASS/assets。"""
    key = (name, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    import sys
    from pathlib import Path
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent)) / "assets" / "icons"
    try:
        from PIL import Image
        img = ctk.CTkImage(light_image=Image.open(base / f"{name}_light.png"),
                           dark_image=Image.open(base / f"{name}_dark.png"), size=(size, size))
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


LINK_COLOR = ("#1a5fd0", "#7fb0ff")

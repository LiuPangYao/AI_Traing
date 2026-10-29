# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""修 tkinter 接微軟注音時吃掉標點的問題。

症狀（2026-10-28 用診斷視窗抓到）：中文模式按「.」，Windows 交給 tkinter 的事件是
    keysym='Delete' char='.' keycode=46
鍵碼 46 剛好是 VK_DELETE，也剛好是「.」的 ASCII 碼。tkinter 看鍵碼認成 Delete，
文字框就去刪下一個字，而不是打出「.」。英文模式走正常路徑（keycode=110，keysym='period'），沒事。
同理「,」(44=VK_PRINT)、「-」(45=VK_INSERT)、「/」(47=VK_HELP) 等都可能中獎。
實測過的只有「.」（2026-10-28，Peter 的微軟注音）；其餘鍵名是依鍵碼表推的，還沒逐一實測。
再遇到打不出的符號：用 scratch 的診斷視窗（記 keysym/char/keycode）看一次，把 keysym 補進 CONTROL_KEYSYMS。

做法：在 KeyPress 時，如果事件帶著一個可印出的字元、但 keysym 卻是控制鍵名，就自己把字元插進去，
並擋掉 tkinter 的預設動作。判斷邏輯在 fixed_char()（純函式，可測試）；bind() 掛到 Text 或 Entry 上。
"""
from __future__ import annotations

from typing import Optional

# tkinter 會把這些鍵碼撞名的事件誤認成的 keysym
CONTROL_KEYSYMS = frozenset({
    "Delete", "Insert", "Print", "Help", "Select", "Execute", "Clear", "Pause", "Cancel",
    "Escape", "Home", "End", "Prior", "Next", "Left", "Right", "Up", "Down", "Menu", "Snapshot",
})


def fixed_char(keysym: str, char: str) -> Optional[str]:
    """該事件其實是「輸入法送來的一個字」時，回傳要插入的字；否則 None（照 tkinter 預設）。"""
    if len(char) != 1 or not char.isprintable() or char == " ":
        return None
    if keysym in CONTROL_KEYSYMS:
        return char
    return None


def bind(widget) -> None:
    """掛到 tk.Text / tk.Entry（或 customtkinter 包起來的那個內層）。"""
    def on_key(e):
        ch = fixed_char(e.keysym, e.char)
        if ch is None:
            return None
        try:                                       # 有選取範圍時，正常打字會取代選取：這裡也要
            widget.delete("sel.first", "sel.last")
        except Exception:
            pass
        widget.insert("insert", ch)
        return "break"
    widget.bind("<KeyPress>", on_key, add="+")

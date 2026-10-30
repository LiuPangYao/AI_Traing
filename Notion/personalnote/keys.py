# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""快捷鍵：哪些功能可以改鍵、預設是什麼、「Ctrl+Shift+H」這種寫法怎麼變成 tk 的 <Control-Shift-H>。

規則（設定面板改鍵時檢查，load 讀設定檔時也用同一套）：
- 一定要帶 Ctrl 或 Alt；只有 F1～F12 可以單獨用。
- 系統的 Ctrl+C／V／X／Z／Y／A 不能拿來用（複製貼上還原要照常）。
- 兩個功能不能用同一組鍵。
使用者改過的存在 settings.json 的 keys（{功能代號: 鍵}），沒改的用預設；設定檔裡壞掉的那筆直接退回預設，程式照常開。
畫面上的字（功能說明、錯誤訊息）顯示時才 _()，所以 tools/check_strings.py 會把 ACTIONS／GESTURES／MESSAGES 列進翻譯表。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Optional

# (功能代號, 預設鍵, 功能說明)
ACTIONS: tuple[tuple[str, str, str], ...] = (
    ("new_note", "Ctrl+N", "新筆記（加在今天）"),
    ("today", "Ctrl+T", "回到今天"),
    ("search", "Ctrl+F", "跳到搜尋框"),
    ("save", "Ctrl+S", "立刻存（平常停 1.2 秒就自動存）"),
    ("sidebar", "Ctrl+\\", "收起／展開左欄"),
    ("mark", "Ctrl+H", "選取的字標黃底 ==重點=="),
    ("red", "Ctrl+Shift+H", "選取的字變紅字 !!警告!!"),
    ("bold", "Ctrl+B", "選取的字 **粗體**"),
    ("italic", "Ctrl+I", "選取的字 *斜體*"),
    ("code", "Ctrl+Shift+C", "插一段 ``` 指令區塊（右上角可一鍵複製）"),
    ("prev_day", "Ctrl+PgUp", "前一天"),
    ("next_day", "Ctrl+PgDn", "後一天"),
    ("zoom_in", "Ctrl+=", "字體放大（Ctrl+滾輪也可）"),
    ("zoom_out", "Ctrl+-", "字體縮小"),
)
# 滑鼠、Enter 這些不是「組合鍵」，不能改，只列給人看
GESTURES: tuple[tuple[str, str], ...] = (
    ("Ctrl+滾輪", "字體放大縮小"),
    ("Ctrl+V", "貼截圖（剪貼簿是圖就存成附件）"),
    ("Ctrl+點連結", "開網址或檔案路徑"),
    ("Ctrl+點 #標籤", "左欄搜尋這個標籤（再點一次清掉）"),
    ("行首 1. 或 - 後 Enter", "自動接下一項，空項再 Enter 結束"),
    ("格式列「打勾」", "這行變 - [ ] 清單；點方框打勾，完成的會劃掉"),
    ("內文按右鍵", "剪下、複製、貼上、全選、複製成純文字（去掉記號）"),
    ("筆記列按右鍵", "開啟、複製到今天、匯出、舊版本（還原）、分享（郵件／Google Drive）、刪除、清整天"),
    ("日期列按右鍵", "在這天新增、整天合成一個 .md 匯出、清整天"),
    ("拖檔案進視窗", ".md／.txt（1 MB 以內）匯成今天的筆記；其他檔不收，附件用 📎 或 Ctrl+V 貼圖"),
    ("長按筆記列再拖", "同一天裡上下調整順序（搜尋中不能排）"),
    ("筆記列前的 ☆", "點一下加入我的最愛，最上面會多一組「★ 我的最愛」；再點一次取消"),
)
RESERVED = {"Ctrl+C", "Ctrl+V", "Ctrl+X", "Ctrl+Z", "Ctrl+Y", "Ctrl+A"}

# parse() 會丟出的訊息（畫面顯示時 _()）
MSG_FORMAT = "格式看不懂（例：Ctrl+Shift+N）"
MSG_NO_KEY = "要有一個主鍵"
MSG_NEED_MOD = "要帶 Ctrl 或 Alt（F1～F12 可以單獨用）"
MSG_RESERVED = "這組是系統的複製／貼上／還原，不能拿來用"
MSG_UNSUPPORTED = "不支援這個鍵"
MESSAGES = (MSG_FORMAT, MSG_NO_KEY, MSG_NEED_MOD, MSG_RESERVED, MSG_UNSUPPORTED)

# 鍵名 → tk keysym（一個鍵名可能對應好幾個 keysym：主鍵盤與數字鍵盤的 + -、Enter）
_KEYSYMS: dict[str, tuple[str, ...]] = {
    "=": ("equal", "plus", "KP_Add"), "-": ("minus", "KP_Subtract"), "\\": ("backslash",),
    "[": ("bracketleft",), "]": ("bracketright",), ";": ("semicolon",), "'": ("apostrophe",),
    ",": ("comma",), ".": ("period",), "/": ("slash",), "`": ("grave",),
    "PgUp": ("Prior",), "PgDn": ("Next",), "Home": ("Home",), "End": ("End",),
    "Ins": ("Insert",), "Del": ("Delete",), "Space": ("space",), "Tab": ("Tab",),
    "Enter": ("Return", "KP_Enter"), "Up": ("Up",), "Down": ("Down",), "Left": ("Left",), "Right": ("Right",),
}
for _i in range(1, 13):
    _KEYSYMS[f"F{_i}"] = (f"F{_i}",)
for _c in "0123456789":
    _KEYSYMS[_c] = (_c, f"KP_{_c}")
_NAME_OF_KEYSYM: dict[str, str] = {ks: name for name, syms in _KEYSYMS.items() for ks in syms}
_NAME_LOWER: dict[str, str] = {name.lower(): name for name in _KEYSYMS}
_MODS = ("Ctrl", "Alt", "Shift")                    # 顯示順序固定，Ctrl+Shift+H 與 Shift+Ctrl+H 才會算同一組
_MOD_SEQ = {"Ctrl": "Control-", "Alt": "Alt-", "Shift": "Shift-"}
MODIFIER_KEYSYMS = {"Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Caps_Lock", "Num_Lock",
                    "Win_L", "Win_R", "Meta_L", "Meta_R", "Super_L", "Super_R", "ISO_Level3_Shift"}
ALT_MASK = 0x20000 if sys.platform == "win32" else 0x8      # tk event.state 的 Alt 位元：Windows 與 X11 不一樣


class Conflict(ValueError):
    """這組鍵已經被別的功能用了。other = 那個功能的代號，desc = 它的說明（顯示時 _()）。"""

    def __init__(self, name: str, other: str, desc: str):
        super().__init__(f"{name} already used by {other}")
        self.name, self.other, self.desc = name, other, desc


def _canon_key(p: str) -> str:
    if len(p) == 1 and p.isalpha():
        return p.upper()
    if p in _KEYSYMS:
        return p
    if p.lower() in _NAME_LOWER:
        return _NAME_LOWER[p.lower()]
    raise ValueError(MSG_UNSUPPORTED)


def parse(text: str) -> str:
    """把「ctrl + shift + h」整理成標準寫法「Ctrl+Shift+H」；不合規則就 ValueError（訊息在 MESSAGES 裡）。"""
    raw = str(text).replace(" ", "")
    parts = [p for p in raw.split("+") if p != ""]
    if raw.endswith("+") and raw != "+":          # 「Ctrl++」這種：最後那個 + 不支援（請用 =）
        raise ValueError(MSG_UNSUPPORTED)
    mods: set[str] = set()
    key: Optional[str] = None
    for p in parts:
        low = p.lower()
        if low in ("ctrl", "control"):
            mods.add("Ctrl")
        elif low == "alt":
            mods.add("Alt")
        elif low == "shift":
            mods.add("Shift")
        elif key is None:
            key = _canon_key(p)
        else:
            raise ValueError(MSG_FORMAT)
    if key is None:
        raise ValueError(MSG_NO_KEY)
    if not (mods & {"Ctrl", "Alt"}) and not (key.startswith("F") and key[1:].isdigit()):
        raise ValueError(MSG_NEED_MOD)
    name = "+".join([m for m in _MODS if m in mods] + [key])
    if name in RESERVED:
        raise ValueError(MSG_RESERVED)
    return name


def sequences(name: str) -> list[str]:
    """「Ctrl+Shift+H」→ ['<Control-Shift-h>', '<Control-Shift-H>']。
    字母綁大小寫兩種（Caps Lock 開著 tk 送大寫）；Ctrl+H 與 Ctrl+Shift+H 同時綁時 tk 會挑修飾鍵較多、較符合的那個。"""
    parts = name.split("+")
    key, mods = parts[-1], parts[:-1]
    prefix = "".join(_MOD_SEQ[m] for m in mods)
    syms = (key.lower(), key.upper()) if (len(key) == 1 and key.isalpha()) else _KEYSYMS[key]
    return [f"<{prefix}{s}>" for s in syms]


def from_event(event) -> Optional[str]:
    """設定面板「按一下你要的組合鍵」：tk 的 KeyPress 事件 → 鍵名（還沒驗證，交給 KeyMap.set）。
    只按了 Ctrl／Shift 這種修飾鍵，或不支援的鍵，回 None。"""
    ks = event.keysym
    if ks in MODIFIER_KEYSYMS:
        return None
    if len(ks) == 1 and ks.isalpha():
        key = ks.upper()
    elif ks in _NAME_OF_KEYSYM:
        key = _NAME_OF_KEYSYM[ks]
    else:
        return None
    mods = []
    if event.state & 4:
        mods.append("Ctrl")
    if event.state & ALT_MASK:
        mods.append("Alt")
    if event.state & 1:
        mods.append("Shift")
    return "+".join(mods + [key])


_DEFAULTS = {a: k for a, k, _d in ACTIONS}
_DESC = {a: d for a, _k, d in ACTIONS}


@dataclass(frozen=True)
class KeyMap:
    keys: dict[str, str] = field(default_factory=lambda: dict(_DEFAULTS))   # 功能代號 → 鍵（含預設）

    @classmethod
    def load(cls, overrides: Optional[dict] = None) -> "KeyMap":
        """預設疊上使用者改過的。格式錯的丟掉；兩個功能撞同一組鍵時，改過的那個退回預設（對調兩組鍵是合法的）。"""
        keys = dict(_DEFAULTS)
        changed: dict[str, str] = {}
        for a, k in (overrides or {}).items():
            if a not in keys:
                continue
            try:
                changed[a] = parse(k)
            except ValueError:
                continue
        keys.update(changed)
        for _ in range(len(keys) + 1):
            seen: dict[str, str] = {}
            dup = None
            for a, k in keys.items():
                if k in seen:
                    dup = a if a in changed else seen[k]
                    break
                seen[k] = a
            if dup is None:
                break
            keys[dup] = _DEFAULTS[dup]
            changed.pop(dup, None)
        return cls(keys)

    def key_of(self, action: str) -> str:
        return self.keys[action]

    def desc_of(self, action: str) -> str:
        return _DESC[action]

    def conflict(self, name: str, action: str) -> Optional[str]:
        """name 已經被哪個功能（action 以外）用了；沒有回 None。"""
        for a, k in self.keys.items():
            if k == name and a != action:
                return a
        return None

    def set(self, action: str, text: str) -> "KeyMap":
        """換一組鍵，回新的 KeyMap。格式不對 ValueError；撞到別的功能 Conflict。"""
        name = parse(text)
        other = self.conflict(name, action)
        if other is not None:
            raise Conflict(name, other, _DESC[other])
        new = dict(self.keys)
        new[action] = name
        return KeyMap(new)

    def overrides(self) -> dict[str, str]:
        """跟預設不同的那幾個（存進 settings.json 的就是這些）。"""
        return {a: k for a, k in self.keys.items() if k != _DEFAULTS[a]}

    def table(self) -> list[tuple[str, str]]:
        """給設定面板與使用說明的兩欄表：(鍵, 功能)，可改的在前、不能改的手勢在後。"""
        return [(self.keys[a], d) for a, _k, d in ACTIONS] + list(GESTURES)

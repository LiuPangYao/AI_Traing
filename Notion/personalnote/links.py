# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""筆記文字裡的連結：找出來（畫底線用）、判斷游標點到哪一個（開啟用）。

純文字處理，不碰 UI，所以可以單元測試。認三種：
1. 網址      https://... http://... www....
2. Windows 路徑  C:\\...  D:\\...
3. 附件寫法  [名稱](attachments/xxx.pdf)   → 目標是括號裡的路徑
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]\"']+")
# Windows 路徑兩種寫法：
#  1. 用引號包起來 "D:\AI\ai study\notes\58.md"（路徑有空格最保險）
#  2. 不加引號：允許中間有單一空格，但必須以「.副檔名」結尾才知道在哪裡停，例如 D:\AI\ai study\notes\58.md
#     純資料夾路徑（沒副檔名）遇到空格就停。
#  3. 網路共用槽 \\server\share\試務 2026\名單.xlsx 規則同上。
_START = r'(?:[A-Za-z]:\\|\\\\)'
_SEG = r'[^\s"<>|()\[\],，。、]+'              # 路徑的一段（不含空白、引號、中文標點）
WINPATH_QUOTED_RE = re.compile(r'"(' + _START + r'[^"<>|]+)"')
WINPATH_RE = re.compile(
    _START + _SEG + '(?: ' + _SEG + ')*?' + r'\.[A-Za-z0-9]{1,6}(?=$|[\s,;:!?)\]。，、])'   # 有副檔名：可含單一空格
    + '|' + _START + _SEG)                                                                 # 沒副檔名：空格就停
ATTACH_RE = re.compile(r"\[[^\]]*\]\(([^()]+)\)(?:\{w=\d+\})?")   # 後面可接 {w=400}：圖片顯示寬度
NOTE_RE = re.compile(r"\[\[([^\[\]\n]{1,80})\]\]")      # [[標題]] 或 [[2026-10-29/003]]：連到另一張筆記（目標寫成 note:…）
_TRAIL = ".,;:!?"


@dataclass(frozen=True)
class Link:
    start: int      # 在該行的字元位置（含）
    end: int        # （不含）
    target: str     # 要開的東西：網址或路徑


def find_links(line: str) -> list[Link]:
    """一行裡所有連結，照出現順序。附件寫法整個 [..](..) 都算連結範圍。"""
    out: list[Link] = []
    taken: list[tuple[int, int]] = []

    for m in NOTE_RE.finditer(line):
        out.append(Link(m.start(), m.end(), "note:" + m.group(1).strip()))
        taken.append((m.start(), m.end()))

    for m in ATTACH_RE.finditer(line):
        if any(a <= m.start() < b for a, b in taken):
            continue
        out.append(Link(m.start(), m.end(), m.group(1).strip()))
        taken.append((m.start(), m.end()))

    for m in WINPATH_QUOTED_RE.finditer(line):
        if any(a <= m.start() < b for a, b in taken):
            continue
        out.append(Link(m.start(), m.end(), m.group(1)))
        taken.append((m.start(), m.end()))

    for rx in (URL_RE, WINPATH_RE):
        for m in rx.finditer(line):
            if any(a <= m.start() < b for a, b in taken):
                continue
            s = m.group(0).rstrip(_TRAIL)
            target = "https://" + s if s.startswith("www.") else s
            out.append(Link(m.start(), m.start() + len(s), target))
            taken.append((m.start(), m.start() + len(s)))

    return sorted(out, key=lambda l: l.start)


def link_at(line: str, col: int) -> Optional[str]:
    """游標在第 col 個字元時點到的連結目標；沒有就 None。"""
    for l in find_links(line):
        if l.start <= col <= l.end:
            return l.target
    return None

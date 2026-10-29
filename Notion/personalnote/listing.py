# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""清單自動接續：行首是「1. 」「- 」「• 」「* 」時，按 Enter 自動補下一個標記。

純文字處理，不碰 UI，可以單元測試。
    next_marker("1. 買牛奶")  -> "2. "
    next_marker("  - 子項")    -> "  - "
    next_marker("3. ")         -> ""      （只有標記沒內容 = 想結束清單，呼叫端把這行清掉）
    next_marker("普通文字")    -> None    （不是清單）
"""
from __future__ import annotations

import re
from typing import Optional

NUMBERED_RE = re.compile(r"^(\s*)(\d+)(?:([.)])\s+|(、)\s*)(.*)$")   # 「1. 」「1) 」要空格；「1、」可不用
BULLET_RE = re.compile(r"^(\s*)([-•*])\s+(.*)$")


def next_marker(line: str) -> Optional[str]:
    m = NUMBERED_RE.match(line)
    if m:
        indent, num, sep_ascii, sep_zh, rest = m.groups()
        if rest.strip() == "":
            return ""
        return f"{indent}{int(num) + 1}{sep_zh}" if sep_zh else f"{indent}{int(num) + 1}{sep_ascii} "
    m = BULLET_RE.match(line)
    if m:
        indent, mark, rest = m.groups()
        return "" if rest.strip() == "" else f"{indent}{mark} "
    return None

# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""行內記號與指令區塊。檔案裡存的就是這些記號（純文字，匯出的 .md 照樣看得懂），畫面上照記號上色，記號本身淡灰。

| 打法          | 畫面                  | kind   |
| ==重點==      | 黃底                  | mark   |
| !!警告!!      | 紅字                  | red    |
| **粗體**      | 粗體                  | bold   |
| *斜體*        | 斜體                  | italic |
| ``` … ```     | 等寬灰底＋「複製」按鈕 | code_blocks() |

規則：記號裡面不能是空的、頭尾不能是空白（「* 項目 * 另一項」不會被當斜體）；``` 區塊裡的字不套行內記號。
要加一種記號：MARKERS 加一列、INLINE_RE 加一個分支（順序要在比它短的記號前面）、editor.py 的 STYLE_TAGS 加顏色。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MARKERS = {"mark": "==", "red": "!!", "bold": "**", "italic": "*"}
KINDS = ("mark", "red", "bold", "italic")                       # 跟 INLINE_RE 的分支順序一致
def _inner(ch: str) -> str:
    """記號裡面的字：至少一個字、頭尾不是空白、不含記號字元本身（不然「==a== x ==b==」會黏成一段）。"""
    return r"([^%s\s](?:[^%s]*?[^%s\s])?)" % (ch, ch, ch)


INLINE_RE = re.compile(
    r"(==)" + _inner("=") + r"=="
    r"|(!!)" + _inner("!") + r"!!"
    r"|(\*\*)" + _inner("*") + r"\*\*"
    r"|(\*)" + _inner("*") + r"\*"
)
FENCE = "```"


@dataclass(frozen=True)
class Span:
    kind: str
    start: int          # 整段含記號的起點（Python 字元位置，editor 再換成 tk 的欄位）
    end: int
    inner_start: int    # 要上色的字
    inner_end: int


def inline_spans(line: str) -> list[Span]:
    out = []
    for m in INLINE_RE.finditer(line):
        for k, kind in enumerate(KINDS):
            g = 2 * k + 1                                        # 第 k 個分支的（記號, 內容）群組
            if m.group(g) is not None:
                out.append(Span(kind, m.start(), m.end(), m.start(g + 1), m.end(g + 1)))
                break
    return out


def code_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """回每個 ``` 區塊的 (開頭行, 結尾行)，0-based；沒關的區塊算到最後一行。"""
    out, open_at = [], None
    for i, l in enumerate(lines):
        if l.strip().startswith(FENCE):
            if open_at is None:
                open_at = i
            else:
                out.append((open_at, i))
                open_at = None
    if open_at is not None:
        out.append((open_at, len(lines) - 1))
    return out


def parse(text: str) -> tuple[list[tuple[int, int]], dict[int, list[Span]]]:
    """整份內文 → (指令區塊, {行號: 行內記號})，行號 0-based。區塊裡的行不找行內記號。"""
    lines = text.split("\n")
    blocks = code_blocks(lines)
    skip = set()
    for a, b in blocks:
        skip.update(range(a, b + 1))
    spans = {}
    for i, l in enumerate(lines):
        if i in skip or not any(ch in l for ch in "=!*"):
            continue
        s = inline_spans(l)
        if s:
            spans[i] = s
    return blocks, spans


def is_fence(line: str) -> bool:
    return line.strip().startswith(FENCE)


def block_text(lines: list[str], a: int, b: int) -> str:
    """指令區塊的內容（不含圍欄），給「複製」按鈕用。沒關的區塊最後一行是內容，不是圍欄。"""
    end = b if (b > a and is_fence(lines[b])) else b + 1
    return "\n".join(lines[a + 1:end])

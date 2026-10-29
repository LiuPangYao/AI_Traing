# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""行內記號與指令區塊。檔案裡存的就是這些記號（純文字，匯出的 .md 照樣看得懂），畫面上照記號上色，記號本身淡灰。

| 打法          | 畫面                  | kind   |
| ==重點==      | 黃底                  | mark   |
| !!警告!!      | 紅字                  | red    |
| **粗體**      | 粗體                  | bold   |
| *斜體*        | 斜體                  | italic |
| ``` … ```     | 等寬灰底＋「複製」按鈕 | code_blocks() |
| - [ ] 事項    | 方框，點一下打勾      | checkbox()    |
| - [x] 事項    | 打勾、字劃掉          | checkbox()    |
| #標籤         | 主色字，Ctrl+點＝搜尋 | tags()        |

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
CHECK_RE = re.compile(r"^(\s*)- \[( |x|X)\] ")                    # 打勾清單：「- [ ] 」「- [x] 」（GitHub 寫法）
# #標籤：# 前面不能黏著字母／數字／#／路徑符號（網址的 #anchor、「issue #42」的純數字不算）
TAG_RE = re.compile(r"(?<![\w#/.&=])#([A-Za-z_\u3040-\u30ff\u4e00-\u9fff][\w\u3040-\u30ff\u4e00-\u9fff-]{0,29})")
ATTACH_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^()]+)\)(?:\{w=\d+\})?")


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


def checkbox(line: str):
    """打勾清單那一行 → (記號起點, 記號終點, 打勾了嗎)；不是就 None。記號＝「- [ ] 」六個字（縮排不算）。"""
    m = CHECK_RE.match(line)
    if not m:
        return None
    return m.end(1), m.end(), m.group(2).lower() == "x"


def toggle_checkbox(line: str) -> str:
    """「- [ ] 」↔「- [x] 」；不是打勾清單就原樣回。"""
    m = CHECK_RE.match(line)
    if not m:
        return line
    new = " " if m.group(2).lower() == "x" else "x"
    return line[:m.start(2)] + new + line[m.end(2):]


def tags(line: str) -> list[tuple[int, int]]:
    """一行裡的 #標籤：(起點含 #, 終點)。"""
    return [(m.start(), m.end()) for m in TAG_RE.finditer(line)]


def plain(text: str) -> str:
    """去掉記號的純文字（右鍵「複製成純文字」）：==x== → x、**x** → x、[名稱](路徑) → 名稱、``` 圍欄行拿掉。
    打勾清單與 #標籤照原樣留著（本來就看得懂）。"""
    lines = text.split("\n")
    blocks = code_blocks(lines)
    skip = set()
    fences = set()
    for a, b in blocks:
        skip.update(range(a, b + 1))
        fences.add(a)
        if b > a and is_fence(lines[b]):
            fences.add(b)
    out = []
    for i, l in enumerate(lines):
        if i in fences:
            continue
        if i not in skip:
            l = ATTACH_LINK_RE.sub(lambda m: m.group(1) or m.group(2), l)
            l = INLINE_RE.sub(lambda m: next(g for g in m.groups()[1::2] if g is not None), l)
        out.append(l)
    return "\n".join(out)

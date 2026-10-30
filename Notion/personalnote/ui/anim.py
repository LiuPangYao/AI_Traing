# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""動畫只有這一套（Peter 2026-10-30：動畫要有條理）。Tk 沒有動畫系統，全部用 after 一幀一幀畫。

規則：
- 時間：出現／跳到 APPEAR 240 ms（主色淡到底色的「脈動」）、消失 REMOVE 120 ms（列先收合再移除）、狀態字 FADE 400 ms（淡出）。
- 曲線：ease-out（先快後慢），每幀 FRAME 16 ms（約 60 fps）。
- 只在「一件事發生」時動（新增、刪除、跳到某張、存檔提示），整欄重畫、換語言、換主題不動。
- 任何地方要動畫一律呼叫這裡的函式；NOTE_ANIM=0（測試、慢機器）就全部立刻完成。
"""
from __future__ import annotations

import os
from typing import Callable, Optional

APPEAR = 240
REMOVE = 120
FADE = 400
FRAME = 16


def enabled() -> bool:
    return os.environ.get("NOTE_ANIM", "1") != "0"


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) * (1 - t)


def blend(c1: str, c2: str, t: float) -> str:
    """兩個 #rrggbb 之間取 t（0＝c1，1＝c2）。"""
    t = max(0.0, min(1.0, t))
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def fade_bg(widgets, c_from: str, c_to: str, ms: int = APPEAR, done: Optional[Callable] = None) -> None:
    """一組 tk 元件的 bg 從 c_from 淡到 c_to（元件被砍掉就停）。"""
    widgets = [w for w in widgets if w is not None]
    if not widgets:
        if done:
            done()
        return
    host = widgets[0]
    if not enabled():
        _set_bg(widgets, c_to)
        if done:
            done()
        return
    steps = max(1, ms // FRAME)

    def frame(i: int) -> None:
        if not host.winfo_exists():
            return
        _set_bg(widgets, blend(c_from, c_to, ease_out(i / steps)))
        if i < steps:
            host.after(FRAME, lambda: frame(i + 1))
        elif done:
            done()
    frame(0)


def _set_bg(widgets, color: str) -> None:
    for w in widgets:
        try:
            if w.winfo_exists():
                w.configure(bg=color)
        except Exception:
            pass


def collapse(frame, done: Callable, ms: int = REMOVE) -> None:
    """一列從現在的高度收合到 0，再呼叫 done（通常是真的刪掉並重畫）。"""
    try:
        alive = frame.winfo_exists()
    except Exception:
        alive = False
    if not alive or not enabled():
        done()
        return
    h0 = max(1, frame.winfo_height())
    frame.grid_propagate(False)
    steps = max(1, ms // FRAME)

    def step(i: int) -> None:
        if not frame.winfo_exists():
            done()
            return
        h = max(1, round(h0 * (1 - ease_out(i / steps))))
        frame.configure(height=h)
        if i < steps:
            frame.after(FRAME, lambda: step(i + 1))
        else:
            done()
    step(0)


def fade_fg(widget, c_from: str, c_to: str, ms: int = FADE, done: Optional[Callable] = None,
            cancel_box: Optional[dict] = None) -> None:
    """文字顏色淡出（狀態字用）。cancel_box["job"] 會放 after id，呼叫端可取消。"""
    if not enabled():
        try:
            widget.configure(fg=c_to)
        except Exception:
            pass
        if done:
            done()
        return
    steps = max(1, ms // FRAME)

    def frame(i: int) -> None:
        if not widget.winfo_exists():
            return
        try:
            widget.configure(fg=blend(c_from, c_to, ease_out(i / steps)))
        except Exception:
            return
        if i < steps:
            job = widget.after(FRAME, lambda: frame(i + 1))
            if cancel_box is not None:
                cancel_box["job"] = job
        else:
            if cancel_box is not None:
                cancel_box["job"] = None
            if done:
                done()
    frame(0)

# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""每天用了多久（月曆的熱度圖用）。

怎麼算：主視窗有鍵盤焦點、而且最近 IDLE_SECONDS 內有按鍵或滑鼠動作，才算「在用」；主視窗的心跳（2 秒）每次把經過的秒數
加到今天（跨午夜就算到新的一天）。離開座位、切到別的程式、視窗沒焦點都不算。
存哪裡：<筆記資料夾>/.app/usage.json，{"YYYY-MM-DD": 秒}，每 SAVE_EVERY 秒寫一次、關閉時一定寫。
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from .config import APP_SUBDIR

IDLE_SECONDS = 60          # 多久沒動就不算在用
SAVE_EVERY = 30            # 幾秒寫一次檔
MAX_TICK = 10              # 一次心跳最多算幾秒（睡眠、休眠醒來的大段空白不算）


def fmt_duration(seconds: int, _=None) -> str:
    """秒 → 「1 小時 5 分」／「42 分」／「不到 1 分」。_ 給翻譯函式（顯示時才翻）。"""
    _ = _ or (lambda s: s)
    m = int(seconds) // 60
    if m <= 0:
        return _("不到 1 分")
    h, m = divmod(m, 60)
    return _("{0} 小時 {1} 分").format(h, m) if h else _("{0} 分").format(m)


class UsageLog:
    def __init__(self, root: Path):
        self.path = Path(root) / APP_SUBDIR / "usage.json"
        self._data: dict[str, int] = {}
        self._dirty = False
        self._last_save = 0.0
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}
        except (OSError, ValueError):
            data = {}
        if isinstance(data, dict):
            for k, v in data.items():
                try:
                    date.fromisoformat(str(k)); self._data[str(k)] = max(0, int(v))
                except (ValueError, TypeError):
                    continue

    def seconds(self, day: date) -> int:
        return self._data.get(day.isoformat(), 0)

    def add(self, day: date, seconds: float) -> None:
        s = int(min(max(seconds, 0), MAX_TICK))
        if s <= 0:
            return
        self._data[day.isoformat()] = self.seconds(day) + s
        self._dirty = True

    def save(self, now: float, force: bool = False) -> bool:
        """now 給 time.monotonic()；沒改過、或離上次寫不到 SAVE_EVERY 秒就不寫。寫失敗不丟例外（下次再試）。"""
        if not self._dirty or (not force and now - self._last_save < SAVE_EVERY):
            return False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
        except OSError:
            return False
        self._dirty = False
        self._last_save = now
        return True

    def month(self, year: int, mon: int) -> dict[date, int]:
        """這個月每天的秒數（只列有用過的天）。"""
        out = {}
        for k, v in self._data.items():
            d = date.fromisoformat(k)
            if d.year == year and d.month == mon and v > 0:
                out[d] = v
        return out

    def total_days(self) -> int:
        return sum(1 for v in self._data.values() if v > 0)

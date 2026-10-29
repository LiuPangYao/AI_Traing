# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""程式自己記的狀態（不是設定、不是筆記）：視窗大小位置、側欄寬度、上次看的日期。

存在 <note_dir>/.app/state.json。壞掉或不存在就用預設，不會讓程式開不起來。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Any, Optional

from .config import APP_SUBDIR

STATE_FILE = "state.json"


@dataclass(frozen=True)
class AppState:
    geometry: str = "720x640+240+120"   # tkinter 格式 WxH+X+Y；便利貼大小，不是全螢幕（太窄工具列圖示、日期標題會被截）
    sidebar_visible: bool = True
    sidebar_width: int = 220            # 左欄寬度（拖分隔線改的；範圍見 theme.SIDEBAR_MIN／MAX）
    format_bar: bool = False            # 內文上方的格式列（重點／紅字／粗體…）展開著嗎；預設收起來，不常用
    last_day: Optional[str] = None      # ISO 日期字串

    @classmethod
    def load(cls, note_dir: Path) -> "AppState":
        path = note_dir / APP_SUBDIR / STATE_FILE
        if not path.is_file():
            return cls()
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return replace(cls(), **known)

    def save(self, note_dir: Path) -> None:
        path = note_dir / APP_SUBDIR / STATE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    def with_(self, **kw: Any) -> "AppState":
        return replace(self, **kw)

    def last_day_or_none(self):
        """state.json 壞掉或日期格式不對就當沒有。"""
        from datetime import date
        try:
            return date.fromisoformat(self.last_day) if self.last_day else None
        except (TypeError, ValueError):
            return None

    def safe_geometry(self) -> str:
        """視窗位置若跑到所有螢幕之外（例如拔掉外接螢幕），改回預設位置，不然視窗會看不到。"""
        import re
        m = re.match(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$", self.geometry)
        if not m:
            return AppState.geometry
        w, h, x, y = (int(v) for v in m.groups())
        vx, vy, vw, vh = _virtual_screen()
        if x < vx - w + 60 or y < vy or x > vx + vw - 60 or y > vy + vh - 60:
            return f"{w}x{h}+240+120"
        return self.geometry


def _virtual_screen() -> tuple[int, int, int, int]:
    """所有螢幕合起來的範圍 (x, y, 寬, 高)。非 Windows 給一個很大的範圍。"""
    try:
        import ctypes
        m = ctypes.windll.user32.GetSystemMetrics
        return m(76), m(77), m(78), m(79)     # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CX/CYVIRTUALSCREEN
    except Exception:
        return -100000, -100000, 200000, 200000

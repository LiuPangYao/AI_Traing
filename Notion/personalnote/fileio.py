# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""小檔案的原子寫入：先寫 .tmp、fsync、再改名蓋過去。中途斷電只會留下 .tmp，正式檔永遠完整。
settings.json、state.json、format.json、favorites.json、usage.json、note_dir.txt 都走這裡（QA 審查：以前用 write_text，會留半截 JSON）。"""
from __future__ import annotations

import os
from pathlib import Path


def atomic_write_bytes(p: Path, data: bytes) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


def atomic_write_text(p: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(p, text.encode(encoding))

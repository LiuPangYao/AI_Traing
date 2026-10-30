# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""範本：<筆記資料夾>/.app/templates/*.md。「新筆記 ▾」列出這裡的檔，選一個就用它的內容開一張新筆記。
第一次用（資料夾不存在或是空的）會放四個預設範本（中英各兩個）；使用者可以改、刪、加自己的。
範本裡的 {date} 會換成當天日期（2026/10/30）。"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .config import APP_SUBDIR

TEMPLATE_DIR = "templates"

DEFAULTS = {
    "會議紀錄.md": "# 會議紀錄 {date}\n\n- 時間：\n- 出席：\n- 主題：\n\n## 討論\n- \n\n## 決議\n- \n\n## 待辦（負責人／期限）\n- [ ] \n",
    "週報.md": "# 週報 {date}\n\n## 本週完成\n- \n\n## 進行中\n- [ ] \n\n## 下週計畫\n- [ ] \n\n## 問題／需要協助\n- \n",
    "Meeting notes.md": "# Meeting notes {date}\n\n- Time:\n- Attendees:\n- Topic:\n\n## Discussion\n- \n\n## Decisions\n- \n\n## Action items (owner / due)\n- [ ] \n",
    "Weekly report.md": "# Weekly report {date}\n\n## Done this week\n- \n\n## In progress\n- [ ] \n\n## Next week\n- [ ] \n\n## Issues / help needed\n- \n",
}


def template_dir(root: Path) -> Path:
    return Path(root) / APP_SUBDIR / TEMPLATE_DIR


def ensure_defaults(root: Path) -> Path:
    """資料夾不存在或是空的就放預設範本。回資料夾路徑。"""
    d = template_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    if not any(d.glob("*.md")):
        for name, text in DEFAULTS.items():
            (d / name).write_text(text, encoding="utf-8", newline="\n")
    return d


def list_templates(root: Path) -> list[Path]:
    d = template_dir(root)
    return sorted(d.glob("*.md"), key=lambda p: p.name.lower()) if d.is_dir() else []


def render(path: Path, day: date) -> str:
    """讀範本、換掉 {date}。讀不了回空字串（呼叫端當沒有範本）。"""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return ""
    return text.replace("{date}", f"{day.year}/{day.month:02d}/{day.day:02d}")

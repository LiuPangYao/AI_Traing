# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""把原始碼複製一份到公開的 GitHub repo 資料夾（只放程式與架構，不放筆記、打包產物、研發紀錄）。

跑法：python tools/sync_public_copy.py [目的資料夾]   預設 D:\\AI\\github_note\\AI_Traing\\Notion
- 跳過：build/ dist/ release/ __pycache__/ old_desktop/ *.spec build.log 研發紀錄.md
- 目的資料夾裡多出來的檔會刪掉（讓它跟原始碼一致）
- README 最上面加一段「公開版說明」（這份只是架構分享、不是公司資訊、請勿直接改這份副本）
- 複製前掃一遍有沒有公司／專案字眼（SENSITIVE），有就不複製並列出來
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\AI\github_note\AI_Traing\Notion")
SKIP_DIRS = {"build", "dist", "release", "__pycache__", ".pytest_cache", "old_desktop"}
SKIP_FILES = {"build.log", "PersonalNote.spec", "Notion.spec", "研發紀錄.md"}
SENSITIVE = re.compile(r"亞洲光學|亞光|aoci|ao-AI-Training|10\.7\.0\.|192\.168\.|OpenProject|清大|NTHU|MPPI|AO_AMR|ao_amr", re.I)
NOTICE = """> **公開版說明（Public copy notice）**
> 這份是 Notion（本機便利貼工具）的**架構與程式碼分享**，由企劃／PM 角度整理；不含任何公司資訊、專案資料或使用者筆記。
> 這個副本只供參考，**請勿直接在這裡修改**：原始碼在維護者的本機維護，改好後整份同步過來（tools/sync_public_copy.py）。
> This folder shares the architecture and source of a local sticky-notes tool for reference only. It contains no company data.
> Do not edit this copy directly; changes are made upstream and synced here.

"""


def wanted(p: Path) -> bool:
    rel = p.relative_to(ROOT)
    return not (any(part in SKIP_DIRS for part in rel.parts) or p.name in SKIP_FILES)


def main() -> int:
    files = [p for p in ROOT.rglob("*") if p.is_file() and wanted(p)]
    hits = []
    for p in files:
        if p.name == Path(__file__).name:
            continue                                  # 這支自己的 SENSITIVE 清單不算
        if p.suffix in (".py", ".md", ".bat", ".sh", ".csv", ".txt"):
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if SENSITIVE.search(line):
                    hits.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:80]}")
    if hits:
        print("有公司／專案字眼，先清掉再同步：")
        print("\n".join(hits))
        return 1
    if DEST.exists():
        shutil.rmtree(DEST)
    for p in files:
        d = DEST / p.relative_to(ROOT)
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, d)
    readme = DEST / "README.md"
    readme.write_text(NOTICE + readme.read_text(encoding="utf-8"), encoding="utf-8")
    (DEST / ".gitignore").write_text("build/\ndist/\nrelease/\n__pycache__/\n*.spec\nbuild.log\n*.pyc\n", encoding="utf-8")
    print(f"同步 {len(files)} 個檔到 {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

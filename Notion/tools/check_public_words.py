# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""這個資料夾在公開 repo 裡：提交前掃一遍有沒有公司／專案字眼、內網位址、個人路徑混進來。
跑法：python tools/check_public_words.py   （有就列出並 exit 1）
要加字眼：改 SENSITIVE。"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENSITIVE = re.compile(r"亞洲光學|亞光|aoci|ao-AI-Training|10\.7\.0\.|192\.168\.|OpenProject|清大|NTHU|MPPI|AO_AMR|ao_amr", re.I)
SKIP_DIRS = {"build", "dist", "release", "__pycache__", ".git"}
EXTS = {".py", ".md", ".bat", ".sh", ".csv", ".txt", ".json"}


def main() -> int:
    hits = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in EXTS or p.name == Path(__file__).name:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if SENSITIVE.search(line):
                hits.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:90]}")
    if hits:
        print("有公司／專案字眼，先清掉再提交：")
        print("\n".join(hits))
        return 1
    print("沒有公司／專案字眼。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

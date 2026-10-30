# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""色碼只准出現在 personalnote/ui/theme.py（Peter 2026-10-30：色碼要控制好）。
其他 .py 出現 "#rrggbb" 就列出來並回傳 1；make_release 打包前會跑。"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEX = re.compile(r"[\"']#[0-9a-fA-F]{6}[\"']")


def main() -> int:
    bad = []
    for p in sorted((ROOT / "personalnote").rglob("*.py")):
        if p.name == "theme.py":
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if HEX.search(line):
                bad.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:90]}")
    if bad:
        print("色碼只能寫在 personalnote/ui/theme.py，這些要改成引用 theme 的常數：")
        print("\n".join("  " + b for b in bad))
        return 1
    print("色碼都在 theme.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

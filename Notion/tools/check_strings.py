# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""翻譯表的整理工具（給翻譯社前、加新字串後都跑一次）。

做什麼：
1. 掃 personalnote/ 所有 .py 裡的 _("…") 取出 key（繁中原文）。
2. 跟 assets/lang/strings.csv 比對：程式有、表沒有 → 加一列（翻譯欄留空）；表有、程式沒有 → 列出（可能是改字了，自己決定刪不刪）。
3. 列出每個語言還有幾句沒翻。
跑法：python tools/check_strings.py            （只檢查、補 key）
      python tools/check_strings.py --strict   （有缺就 exit 1，給 build_exe.bat 用）
表的欄位：zh_TW,en,zh_CN,ja,note。儲存格裡的換行寫成 \\n（兩個字元），程式讀的時候會換回來；Excel 開、另存「CSV UTF-8」都行。
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CSV = ROOT / "assets" / "lang" / "strings.csv"
COLS = ["zh_TW", "en", "zh_CN", "ja", "note"]        # 新語言：這裡不用改，表裡多一欄就會跟著（見 read_cols）
NAME_ROW = "__name__"
KEY_RE = re.compile(r'_\(\s*"((?:[^"\\]|\\.)*)"\s*\)')
CONST_RE = re.compile(r'_\((EMPTY_TITLE|UNREADABLE_TITLE|UNREADABLE_TEXT|NEWER_FORMAT_TEXT|WEEKDAY_ZH\[[^\]]*\]|w)\)')


def source_keys() -> dict[str, str]:
    """key → 第一次出現的檔案:行（給 note 欄參考）。"""
    keys: dict[str, str] = {}
    for p in sorted((ROOT / "personalnote").rglob("*.py")):
        if p.name == "i18n.py":                      # 它的說明裡有 _("…") 的範例，不是畫面字串
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            for m in KEY_RE.finditer(line):
                k = m.group(1).encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8") \
                    if "\\" in m.group(1) else m.group(1)
                keys.setdefault(k, f"{p.relative_to(ROOT)}:{i}")
    # 用常數當 key 的（storage 的提示文字、星期）
    from personalnote import storage
    from personalnote.ui import theme
    for name in ("EMPTY_TITLE", "UNREADABLE_TITLE", "NEWER_TITLE", "UNREADABLE_TEXT", "NEWER_FORMAT_TEXT"):
        keys.setdefault(getattr(storage, name), f"storage.{name}")
    for w in theme.WEEKDAY_ZH:
        keys.setdefault(w, "theme.WEEKDAY_ZH")
    # 顯示時才 _() 的表（設定面板的主題名、快捷鍵表）：原始碼裡沒有 _("…")，要另外列進來
    from personalnote.ui.main_window import SettingsPanel
    for v in SettingsPanel._THEME_KEYS.values():
        keys.setdefault(v, "SettingsPanel._THEME_KEYS")
    for v in SettingsPanel._SIDE_KEYS.values():
        keys.setdefault(v, "SettingsPanel._SIDE_KEYS")
    from personalnote import keys as keys_mod
    for _a, _k, desc in keys_mod.ACTIONS:
        keys.setdefault(desc, "keys.ACTIONS")
    for key, what in keys_mod.GESTURES:
        keys.setdefault(key, "keys.GESTURES")
        keys.setdefault(what, "keys.GESTURES")
    for m in keys_mod.MESSAGES:
        keys.setdefault(m, "keys.MESSAGES")
    return keys


def read_cols() -> list[str]:
    """表現在有哪些欄（語言是 zh_TW 和 note 以外的每一欄）。"""
    global COLS
    if CSV.is_file():
        with CSV.open(encoding="utf-8-sig", newline="") as f:
            cols = next(csv.reader(f), None)
        if cols:
            COLS = [c for c in cols if c]
    return COLS


def lang_cols() -> list[str]:
    return [c for c in read_cols() if c not in ("zh_TW", "note")]


def read_csv() -> list[dict[str, str]]:
    if not CSV.is_file():
        return []
    read_cols()
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def write_csv(rows: list[dict[str, str]]) -> None:
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: (r.get(c) or "").replace("\n", "\\n") for c in COLS})


CJK = re.compile("[　-ヿ一-鿿！-～]")   # 中日文、全形標點（（）／… 英文版要換成半形，所以也算要翻）


def main() -> int:
    strict = "--strict" in sys.argv
    keys = {k: v for k, v in source_keys().items() if CJK.search(k)}   # 純英數的（Ctrl+N 這種）不用翻
    rows = read_csv()
    for r in rows:
        r["zh_TW"] = (r.get("zh_TW") or "").replace("\\n", "\n")
    have = {r["zh_TW"] for r in rows}
    added = [k for k in keys if k not in have]
    for k in added:
        rows.append({"zh_TW": k, **{c: "" for c in lang_cols()}, "note": keys[k]})
    # 沒中文又沒翻譯的列（之前誤加的 Ctrl+N 之類）直接拿掉；其他「程式已經沒有」的只列出來，不自動刪
    rows = [r for r in rows if r["zh_TW"] == NAME_ROW or CJK.search(r["zh_TW"]) or any((r.get(c) or "").strip() for c in lang_cols())]
    unused = [r["zh_TW"] for r in rows if r["zh_TW"] not in keys and r["zh_TW"] != NAME_ROW]
    write_csv(rows)
    missing = {c: [r["zh_TW"] for r in rows if r["zh_TW"] in keys and not (r.get(c) or "").strip()] for c in lang_cols()}
    for c in lang_cols():                                 # 每種語言在下拉選單的名字（__name__ 列）也不能空
        if not any(r["zh_TW"] == NAME_ROW and (r.get(c) or "").strip() for r in rows):
            missing[c].insert(0, f"{NAME_ROW}（這語言的顯示名稱）")
    print(f"程式裡的字串 {len(keys)} 句；表裡 {len(rows)} 列；這次新加 {len(added)} 列")
    for k in added:
        print("  新：", k.replace("\n", "\\n")[:70])
    if unused:
        print(f"表裡有、程式已經沒有的 {len(unused)} 列（改字了？自己決定要不要刪）：")
        for k in unused:
            print("  舊：", k.replace("\n", "\\n")[:70])
    bad = 0
    for c, lst in missing.items():
        print(f"{c} 還沒翻：{len(lst)} 句")
        for k in lst[:200]:
            print("   ", k.replace("\n", "\\n")[:80])
        bad += len(lst)
    return 1 if (strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())

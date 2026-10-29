# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""多語系。畫面上每一句字都寫成 _("繁體中文原文")，顯示時到 assets/lang/strings.csv 撈對應語言的翻譯。

表長這樣（UTF-8 帶 BOM，Excel 打得開）：
    zh_TW,en,zh_CN,ja,note
    __name__,EN,繁中,简中,日本語,（這一列是每種語言在下拉選單裡顯示的名字；zh_TW 那格寫在 note 以外的第一欄之後…見下）
    今天,Today,今天,今日,
    清掉 {0} 張筆記？,Clear {0} notes?,清掉 {0} 张笔记？,{0} 件のノートを消去しますか？,帶變數的句子 {0} 要保留

規則：
- 有哪些語言，看表的欄位：zh_TW 和 note 以外的每一欄就是一種語言，欄名就是語言代碼（en、zh_CN、ja…）。
  要加一種語言（例如韓文）：表加一欄 ko、__name__ 那列填「한국어」、把句子翻好，重新打包就有，程式不用改。
- 原文（繁中）就是 key；表裡沒有、或那一格是空的，就直接顯示繁中原文（不會壞，只是沒翻）。
- 帶變數的句子用 {0} {1} 佔位：_("清掉 {0} 張筆記？").format(n)。翻譯時 {0} 要保留、順序可以換。
- __name__ 那一列：每種語言的顯示名稱（工具列下拉選單、設定面板用）；zh_TW 的名稱寫在 __name__ 列的 zh_TW 欄…
  因為 zh_TW 欄是 key 本身，所以 zh_TW 的顯示名稱固定寫在程式裡（ZH_TW_NAME），其他語言從表拿。
- 預設語言 en（Peter 決定）；設定面板或工具列下拉可切，記在 settings.json 的 lang；切了畫面整個重畫，不用重開。
- 加新字串：程式裡直接寫 _("新句子")，跑 python tools/check_strings.py 會把新 key 補進 csv（空格待翻）並列出缺的。
- 模組層級的常數不要在 import 時就呼叫 _()（語言還沒設），要在用到時才呼叫。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

KEY_COL = "zh_TW"
NOTE_COL = "note"
NAME_ROW = "__name__"
ZH_TW_NAME = "繁中"
DEFAULT = "en"
_lang = KEY_COL                                          # 還沒 set_language 時＝原文（測試就是這樣跑）
_table: dict[str, dict[str, str]] | None = None          # key → {語言代碼: 翻譯}
_names: dict[str, str] = {}                              # 語言代碼 → 顯示名稱


def csv_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / "lang" / "strings.csv"


def _unescape(s: str) -> str:
    return (s or "").replace("\\n", "\n")


def load_table(path: Path | None = None) -> None:
    """讀整張表（含語言清單）。檔案不在就只有繁中。"""
    global _table, _names
    _table, _names = {}, {KEY_COL: ZH_TW_NAME}
    path = path or csv_path()
    if not path.is_file():
        return
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        codes = [c for c in (reader.fieldnames or []) if c and c not in (KEY_COL, NOTE_COL)]
        for code in codes:
            _names[code] = code                          # 沒有 __name__ 列就先用代碼當名字
        for row in reader:
            key = _unescape(row.get(KEY_COL))
            if key == NAME_ROW:
                for code in codes:
                    if (row.get(code) or "").strip():
                        _names[code] = row[code].strip()
                continue
            if key:
                _table[key] = {c: _unescape(row.get(c)) for c in codes}


def langs() -> dict[str, str]:
    """{語言代碼: 顯示名稱}，繁中永遠在第一個，其餘照表的欄位順序。"""
    if _table is None:
        load_table()
    return dict(_names)


def set_language(lang: str) -> None:
    """app 啟動或使用者切換時呼叫；不認得的代碼當 DEFAULT，DEFAULT 也沒有就繁中。"""
    global _lang
    if _table is None:
        load_table()
    _lang = lang if lang in _names else (DEFAULT if DEFAULT in _names else KEY_COL)


def current() -> str:
    return _lang


def _(text: str) -> str:
    if _lang == KEY_COL or _table is None:
        return text
    t = _table.get(text, {}).get(_lang, "")
    return t if t else text

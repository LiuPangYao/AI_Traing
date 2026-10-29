# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""翻譯表：語言清單由欄位決定、沒翻退回繁中、__name__ 列是顯示名稱、\\n 會換回換行。"""
import tempfile
import unittest
from pathlib import Path

from personalnote import i18n


class I18nTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / "strings.csv"
        self.csv.write_text(
            "zh_TW,en,ko,note\n"
            "__name__,EN,한국어,\n"
            "今天,Today,오늘,\n"
            "取消,Cancel,,\n"
            "多行\\n句子,Two\\nlines,,\n",
            encoding="utf-8-sig")
        i18n.load_table(self.csv)

    def tearDown(self):
        i18n._table = None
        i18n._lang = i18n.KEY_COL
        self.tmp.cleanup()

    def test_langs_come_from_columns(self):
        self.assertEqual(i18n.langs(), {"zh_TW": "繁中", "en": "EN", "ko": "한국어"})

    def test_translate_and_fallback(self):
        i18n._lang = "ko"
        self.assertEqual(i18n._("今天"), "오늘")
        self.assertEqual(i18n._("取消"), "取消")              # 韓文那格空的 → 繁中
        self.assertEqual(i18n._("沒這句"), "沒這句")
        i18n._lang = "en"
        self.assertEqual(i18n._("多行\n句子"), "Two\nlines")

    def test_set_language_unknown_code(self):
        i18n.set_language("xx")                                # 表裡沒有 → 預設 en
        self.assertEqual(i18n.current(), "en")
        self.assertEqual(i18n._("今天"), "Today")

    def test_real_table_has_every_language_named(self):
        i18n._table = None
        i18n.load_table()                                      # 真的那張表
        names = i18n.langs()
        self.assertIn("en", names)
        for code, name in names.items():
            self.assertTrue(name and name != code, f"{code} 在 __name__ 列沒填顯示名稱")


if __name__ == "__main__":
    unittest.main()

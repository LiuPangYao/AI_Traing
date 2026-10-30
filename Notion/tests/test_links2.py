# -*- coding: utf-8 -*-
# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""筆記互連：反向連結、改標題自動更新 [[連結]]。"""
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from personalnote.storage import NoteId, NoteStore


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pn_links_"))
        self.st = NoteStore(self.tmp)
        self.d1, self.d2 = date(2026, 10, 28), date(2026, 10, 29)
        self.a, self.b, self.c = NoteId(self.d1, 1), NoteId(self.d2, 1), NoteId(self.d2, 2)
        self.st.save(self.a, "# 會議\n看 [[想法]] 和 [[2026-10-29/002]]\n")
        self.st.save(self.b, "# 想法\n沒連別人\n")
        self.st.save(self.c, "# 第三張\n[[ 想法 ]] 大小寫不管\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_backlinks_by_title_and_id(self):
        ids = [r.id for r in self.st.backlinks(self.b)]
        self.assertEqual(ids, [self.c, self.a])           # 新的日期在前
        self.assertEqual([r.id for r in self.st.backlinks(self.c)], [self.a])   # [[日期/編號]] 也算
        self.assertEqual(self.st.backlinks(self.a), [])

    def test_rename_links(self):
        n = self.st.rename_links("想法", "想法2", exclude=self.b)
        self.assertEqual(n, 1)                             # 只有 a 是 [[想法]]；c 寫 [[ 想法 ]] 不是完全一樣，不動
        self.assertIn("[[想法2]]", self.st.try_load(self.a)[0])
        self.assertIn("[[2026-10-29/002]]", self.st.try_load(self.a)[0])
        self.assertEqual(self.st.rename_links("想法2", "想法2"), 0)
        self.assertEqual(self.st.rename_links("", "x"), 0)
        self.assertEqual(self.st.rename_links("想法2", "（未命名）"), 0)

    def test_find_note_day_form_not_a_note(self):
        self.assertIsNone(self.st.find_note("2026-10-29"))  # 那一天由主視窗 go_day 處理


if __name__ == "__main__":
    unittest.main()

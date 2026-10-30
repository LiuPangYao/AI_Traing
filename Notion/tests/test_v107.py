# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""1.0.7：筆記連結、範本、未完成清單、匯出日期區間、最近標籤、垃圾桶自動清、刪筆記連快照、原子寫入。"""
import json
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from personalnote import fileio, links, templates
from personalnote.storage import NoteId, NoteStore, APP_SUBDIR, TRASH_DIR
from personalnote.ui import todo_view


class NoteLinkTest(unittest.TestCase):
    def test_find_links_note(self):
        ls = links.find_links("看 [[會議記錄]] 和 [[2026-10-29/003]]，還有 [名稱](a.png)")
        self.assertEqual([l.target for l in ls], ["note:會議記錄", "note:2026-10-29/003", "a.png"])
        self.assertEqual(links.link_at("x [[abc]] y", 4), "note:abc")
        self.assertEqual(links.find_links("[[]] 空的不算"), [])


class StoreV107Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.st = NoteStore(self.root, encrypt=False)
        self.d1, self.d2, self.d3 = date(2026, 10, 27), date(2026, 10, 28), date(2026, 10, 30)
        self.st.save(NoteId(self.d1, 1), "# 會議記錄\n- [ ] 寄出週報 #週報\n- [x] 訂會議室\n")
        self.st.save(NoteId(self.d2, 1), "# 想法\n#專案A #專案A 內容\n")
        self.st.save(NoteId(self.d2, 2), "# 會議記錄\n第二次\n")
        self.st.save(NoteId(self.d3, 1), "# 今天\n- [ ] 回信給廠商 #專案A\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_find_note(self):
        self.assertEqual(self.st.find_note("會議記錄"), NoteId(self.d2, 2))       # 同名取新的
        self.assertEqual(self.st.find_note(" 想法 "), NoteId(self.d2, 1))
        self.assertEqual(self.st.find_note("2026-10-27/001"), NoteId(self.d1, 1))
        self.assertEqual(self.st.find_note("2026-10-27-1"), NoteId(self.d1, 1))
        self.assertIsNone(self.st.find_note("2026-10-27/009"))
        self.assertIsNone(self.st.find_note("沒有這張"))

    def test_export_range(self):
        out = self.root / "out" / "w.md"
        n = self.st.export_range(self.d2, self.d1, out)                      # 起訖反了也行
        self.assertEqual(n, 3)
        text = out.read_text(encoding="utf-8")
        self.assertIn("# 2026/10/27\n\n## 會議記錄", text)
        self.assertIn("# 2026/10/28\n\n## 想法", text)
        self.assertNotIn("今天", text)

    def test_recent_tags(self):
        self.assertEqual(self.st.recent_tags(days=10, limit=5, today=self.d3), ["#專案A", "#週報"])
        self.assertEqual(self.st.recent_tags(days=1, limit=5, today=self.d3), ["#專案A"])

    def test_todo_collect(self):
        rows = todo_view.collect(self.st, days=10, today=self.d3)
        self.assertEqual([(nid.day, items) for nid, _t, items in rows], [(self.d3, ["回信給廠商 #專案A"]), (self.d1, ["寄出週報 #週報"])])
        self.assertIn("10/30 今天\n- [ ] 回信給廠商 #專案A", todo_view.as_text(rows))

    def test_delete_removes_history_and_trash_cleanup(self):
        nid = NoteId(self.d1, 1)
        self.st.SNAPSHOT_MIN_GAP = 0
        self.st.snapshot(nid, "# 會議記錄\n舊")
        hist = self.st._history_dir(nid)
        self.assertTrue(hist.is_dir())
        self.st.delete(nid)
        self.assertFalse(hist.exists())
        trash = self.root / APP_SUBDIR / TRASH_DIR
        files = list(trash.iterdir())
        self.assertEqual(len(files), 1)
        self.assertEqual(self.st._clean_trash(now=datetime.now()), 0)
        self.assertEqual(self.st._clean_trash(now=datetime.now() + timedelta(days=31)), 1)
        self.assertEqual(list(trash.iterdir()), [])


class TemplatesTest(unittest.TestCase):
    def test_defaults_and_render(self):
        tmp = tempfile.TemporaryDirectory(); root = Path(tmp.name)
        d = templates.ensure_defaults(root)
        names = sorted(p.name for p in templates.list_templates(root))
        self.assertEqual(names, sorted(templates.DEFAULTS))
        text = templates.render(d / "週報.md", date(2026, 10, 30))
        self.assertTrue(text.startswith("# 週報 2026/10/30"))
        (d / "自己的.md").write_text("# 自訂 {date}\n", encoding="utf-8")
        self.assertEqual(len(templates.list_templates(root)), len(templates.DEFAULTS) + 1)
        templates.ensure_defaults(root)                                     # 已經有檔就不再放預設
        self.assertEqual(templates.render(d / "沒有.md", date.today()), "")
        tmp.cleanup()


class AtomicWriteTest(unittest.TestCase):
    def test_no_tmp_left_and_content(self):
        tmp = tempfile.TemporaryDirectory(); p = Path(tmp.name) / "a" / "x.json"
        fileio.atomic_write_text(p, json.dumps({"k": 1}))
        self.assertEqual(json.loads(p.read_text(encoding="utf-8")), {"k": 1})
        self.assertEqual([q.name for q in p.parent.iterdir()], ["x.json"])
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

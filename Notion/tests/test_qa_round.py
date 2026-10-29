# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""QA 代理抓到的洞，各留一個回歸測試。"""
import json
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

from personalnote import crypto
from personalnote.markup import inline_spans
from personalnote.storage import NEWER_TITLE, NoteId, NoteStore, UNREADABLE_TITLE


class MarkupSingleCharTest(unittest.TestCase):
    def test_single_char_marks_do_not_merge(self):
        def kinds(line):
            return [(s.kind, line[s.inner_start:s.inner_end]) for s in inline_spans(line)]
        self.assertEqual(kinds("==a== x ==b=="), [("mark", "a"), ("mark", "b")])
        self.assertEqual(kinds("**a** x **b**"), [("bold", "a"), ("bold", "b")])
        self.assertEqual(kinds("!!a!! x !!b!!"), [("red", "a"), ("red", "b")])
        self.assertEqual(kinds("==ab== x ==cd=="), [("mark", "ab"), ("mark", "cd")])


class StoreQaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.st = NoteStore(self.root, encrypt=False)
        self.d = date(2026, 10, 20)

    def tearDown(self):
        self.tmp.cleanup()

    def test_restore_uses_deletion_order_not_mtime(self):
        self.st.save(NoteId(self.d, 1), "# 舊\nx")
        self.st.save(NoteId(self.d, 2), "# 新\ny")
        old = self.st.path_for(NoteId(self.d, 1))
        import os
        os.utime(old, (time.time() - 86400 * 3, time.time() - 86400 * 3))   # 舊的那張 3 天前改的
        self.st.delete(NoteId(self.d, 2)); time.sleep(1.1)
        self.st.delete(NoteId(self.d, 1))                                   # 最後刪的是舊的那張
        self.assertEqual(self.st.restore_last_deleted(), NoteId(self.d, 1))

    def test_format_json_not_object(self):
        for bad in ("[]", "null", "42", '"1"'):
            (self.root / ".app").mkdir(exist_ok=True)
            (self.root / ".app" / "format.json").write_text(bad, encoding="utf-8")
            NoteStore(self.root, encrypt=False)                             # 不能炸

    def test_import_exported_numbered_file_keeps_no_title(self):
        src = self.root / "001.md"
        src.write_text("沒有標題的筆記\n第二行", encoding="utf-8")
        nid = self.st.import_file(src, self.d)
        self.assertEqual(self.st.load(nid), "沒有標題的筆記\n第二行")
        src2 = self.root / "會議.md"
        src2.write_text("內文", encoding="utf-8")
        self.assertEqual(self.st.load(self.st.import_file(src2, self.d)), "# 會議\n內文")

    def test_seq_1000_is_listed(self):
        self.st.save(NoteId(self.d, 999), "a"); self.st.save(NoteId(self.d, 1000), "b")
        self.assertEqual([r.id.seq for r in self.st.list_notes(self.d)], [999, 1000])
        self.assertEqual(self.st.next_id(self.d).seq, 1001)

    def test_clean_tmp_leaves_attachments_alone(self):
        (self.root / "attachments").mkdir(exist_ok=True)
        keep = self.root / "attachments" / "report.tmp"; keep.write_bytes(b"x")
        (self.root / "2026-10-20").mkdir(exist_ok=True)
        junk = self.root / "2026-10-20" / "001.note.tmp"; junk.write_bytes(b"half")
        NoteStore(self.root, encrypt=False)
        self.assertTrue(keep.is_file())
        self.assertFalse(junk.exists())

    def test_newer_format_title(self):
        (self.root / "2026-10-20").mkdir()
        (self.root / "2026-10-20" / "001.note").write_bytes(b"PNOTE9\n" + b"x" * 20)
        (self.root / "2026-10-20" / "002.note").write_bytes(crypto.MAGIC + b"garbage")
        titles = [r.title for r in self.st.list_notes(self.d)]
        self.assertEqual(titles, [NEWER_TITLE, UNREADABLE_TITLE])


if __name__ == "__main__":
    unittest.main()


class OrderTest(unittest.TestCase):
    def test_order_persists_and_new_notes_go_last(self):
        with tempfile.TemporaryDirectory() as d:
            st = NoteStore(Path(d), encrypt=False)
            day = date(2026, 10, 29)
            for i in (1, 2, 3):
                st.save(NoteId(day, i), f"# n{i}\nx")
            st.set_order(day, [3, 1, 2])
            self.assertEqual([r.id.seq for r in st.list_notes(day)], [3, 1, 2])
            st.save(NoteId(day, 4), "# n4\nx")                         # 新的一張接最後
            self.assertEqual([r.id.seq for r in st.list_notes(day)], [3, 1, 2, 4])
            st.delete(NoteId(day, 1))                                   # 刪掉的自動不見
            again = NoteStore(Path(d), encrypt=False)                   # 重開還記得
            self.assertEqual([r.id.seq for r in again.list_notes(day)], [3, 2, 4])
            self.assertEqual(again.next_id(day).seq, 5)                 # 編號不受順序影響

    def test_bad_order_file_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".app").mkdir()
            (Path(d) / ".app" / "order.json").write_text("[1,2]", encoding="utf-8")
            st = NoteStore(Path(d), encrypt=False)
            st.save(NoteId(date(2026, 10, 29), 1), "a")
            self.assertEqual(len(st.list_notes(date(2026, 10, 29))), 1)


class TodoTest(unittest.TestCase):
    def test_todo_is_single_and_on_top(self):
        from personalnote.storage import TODO_DAY, TODO_ID, tomorrow
        with tempfile.TemporaryDirectory() as d:
            st = NoteStore(Path(d), encrypt=False)
            st.save(NoteId(date(2026, 10, 29), 1), "# 今天\nx")
            st.save(TODO_ID, "# 待辦\n- 買牛奶")
            self.assertEqual(st.list_days()[0], TODO_DAY)                # 永遠最上面
            src = Path(d) / "x.md"; src.write_text("匯入的", encoding="utf-8")
            nid = st.import_file(src, TODO_DAY)                          # 已有一張 → 放到今天
            self.assertNotEqual(nid.day, TODO_DAY)
            self.assertEqual(len(st.list_notes(TODO_DAY)), 1)
            st.delete(TODO_ID); st.save(TODO_ID, "# 新待辦\n")
            back = st.restore_last_deleted()                              # 還原時待辦已有一張 → 放到今天
            self.assertNotEqual(back.day, TODO_DAY)
            self.assertEqual(len(st.list_notes(TODO_DAY)), 1)
            self.assertEqual(tomorrow(TODO_DAY), date.today())            # 沒有「後一天」

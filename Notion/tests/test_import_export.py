# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
import tempfile
import unittest
from datetime import date
from pathlib import Path

from personalnote.storage import NoteId, NoteStore


class ImportExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "notes"
        self.store = NoteStore(self.root, encrypt=False)
        self.d = date(2026, 10, 28)

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_single(self):
        nid = self.store.next_id(self.d)
        self.store.save(nid, "# 週報\n內容, 逗號\n")
        out = Path(self.tmp.name) / "out" / "週報.md"
        self.store.export_note(nid, out)
        self.assertEqual(out.read_text(encoding="utf-8"), "# 週報\n內容, 逗號\n")

    def test_import_file_uses_filename_as_title_when_missing(self):
        src = Path(self.tmp.name) / "會議紀錄.txt"
        src.write_text("﻿1. 討論 A\n2. 討論 B", encoding="utf-8")      # 有 BOM 也要吃
        nid = self.store.import_file(src, self.d)
        self.assertEqual(nid, NoteId(self.d, 1))
        self.assertEqual(self.store.load(nid), "# 會議紀錄\n1. 討論 A\n2. 討論 B")

    def test_import_keeps_existing_title_and_appends_seq(self):
        self.store.save(self.store.next_id(self.d), "既有的")
        src = Path(self.tmp.name) / "x.md"
        src.write_text("# 自己有標題\n內文", encoding="utf-8")
        nid = self.store.import_file(src, self.d)
        self.assertEqual(nid.seq, 2)
        self.assertEqual(self.store.list_notes(self.d)[1].title, "自己有標題")

    def test_import_empty_file_skipped(self):
        src = Path(self.tmp.name) / "empty.md"
        src.write_text("  \n", encoding="utf-8")
        self.assertIsNone(self.store.import_file(src, self.d))

    def test_import_big5_txt(self):
        src = Path(self.tmp.name) / "舊檔.txt"
        src.write_bytes("第一行\n第二行".encode("cp950"))
        nid = self.store.import_file(src, self.d)
        self.assertEqual(self.store.load(nid), "# 舊檔\n第一行\n第二行")

    def test_import_binary_raises(self):
        src = Path(self.tmp.name) / "圖.txt"
        src.write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00")
        with self.assertRaises(UnicodeDecodeError):
            self.store.import_file(src, self.d)

    def test_roundtrip_export_all_import_folder(self):
        d1, d2 = date(2026, 10, 20), date(2026, 10, 21)        # 不用今天，散檔會進今天
        self.store.save(self.store.next_id(d1), "# a\n1")
        self.store.save(self.store.next_id(d2), "# b\n2")
        self.store.save(self.store.next_id(d2), "# c\n3")
        exp = Path(self.tmp.name) / "export"
        self.assertEqual(self.store.export_plain(exp), 3)
        (exp / "loose.txt").write_text("散的", encoding="utf-8")
        (exp / "2026-10-20" / "009.note").write_bytes(b"PNOTE1\nfrom other pc")
        other = NoteStore(Path(self.tmp.name) / "other", encrypt=False)
        done, skipped = other.import_folder(exp)
        self.assertEqual((done, skipped), (4, 1))
        self.assertEqual([r.title for r in other.list_notes(d2)], ["b", "c"])
        self.assertEqual(other.list_notes(date.today())[0].title, "loose")
        # 再匯一次會接在後面，不覆蓋
        other.import_folder(exp)
        self.assertEqual(len(other.list_notes(d2)), 4)


if __name__ == "__main__":
    unittest.main()


class ExportDayTest(unittest.TestCase):
    def test_export_day_joins_notes(self):
        import tempfile, pathlib
        from datetime import date
        from personalnote.storage import NoteId, NoteStore
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="pn_expday_"))
        st = NoteStore(tmp / "n", encrypt=False)
        d = date(2026, 10, 29)
        st.save(NoteId(d, 1), "# 甲\n一\n")
        st.save(NoteId(d, 2), "# 乙\n二")
        out = tmp / "out" / "2026-10-29.md"
        self.assertEqual(st.export_day(d, out), 2)
        self.assertEqual(out.read_text(encoding="utf-8"), "# 甲\n一\n\n# 乙\n二\n")
        self.assertEqual(st.export_day(date(2026, 1, 1), tmp / "empty.md"), 0)


class TooBigTest(unittest.TestCase):
    def test_import_file_rejects_over_limit_and_folder_skips(self):
        import tempfile, pathlib
        from datetime import date
        from personalnote import storage
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="pn_big_"))
        st = storage.NoteStore(tmp / "n", encrypt=False)
        big = tmp / "big.txt"; big.write_bytes(b"a" * (storage.IMPORT_MAX_BYTES + 1))
        with self.assertRaises(storage.TooBig):
            st.import_file(big, date(2026, 10, 30))
        self.assertTrue(issubclass(storage.TooBig, OSError))           # 呼叫端照「讀不了」處理
        folder = tmp / "f"; folder.mkdir()
        (folder / "a.txt").write_bytes(b"b" * (storage.IMPORT_MAX_BYTES + 1))
        (folder / "b.md").write_text("# b\n", encoding="utf-8")
        self.assertEqual(st.import_folder(folder, today=date(2026, 10, 30)), (1, 1))

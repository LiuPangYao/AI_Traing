# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""存檔層測試。跑法：在 code/personalnote 下 python -m unittest -v"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from personalnote.storage import NoteId, NoteStore, join_title, split_title, title_of


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = NoteStore(Path(self.tmp.name), encrypt=False)
        self.d1 = date(2026, 10, 27)
        self.d2 = date(2026, 10, 28)

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_store(self):
        self.assertEqual(self.store.list_days(), [])
        self.assertEqual(self.store.next_id(self.d2), NoteId(self.d2, 1))
        self.assertEqual(self.store.load(NoteId(self.d2, 1)), "")

    def test_save_load_and_title(self):
        nid = self.store.next_id(self.d2)
        self.store.save(nid, "買牛奶\n第二行")
        self.assertEqual(self.store.load(nid), "買牛奶\n第二行")
        refs = self.store.list_notes(self.d2)
        self.assertEqual([r.title for r in refs], ["買牛奶"])
        self.assertTrue((Path(self.tmp.name) / "2026-10-28" / "001.md").is_file())

    def test_multiple_notes_per_day_and_order(self):
        a = self.store.next_id(self.d2); self.store.save(a, "A")
        b = self.store.next_id(self.d2); self.store.save(b, "B")
        self.assertEqual((a.seq, b.seq), (1, 2))
        self.assertEqual([r.title for r in self.store.list_notes(self.d2)], ["A", "B"])

    def test_days_newest_first(self):
        self.store.save(self.store.next_id(self.d1), "x")
        self.store.save(self.store.next_id(self.d2), "y")
        self.assertEqual(self.store.list_days(), [self.d2, self.d1])

    def test_empty_text_removes_file_to_trash(self):
        nid = self.store.next_id(self.d2)
        self.store.save(nid, "暫時")
        self.store.save(nid, "   \n")
        self.assertFalse(self.store.exists(nid))
        self.assertEqual(self.store.list_days(), [])
        trash = list((Path(self.tmp.name) / ".app" / "trash").iterdir())
        self.assertEqual(len(trash), 1)
        self.assertIn("2026-10-28_001", trash[0].name)

    def test_delete_day_and_all(self):
        self.store.save(self.store.next_id(self.d1), "a")
        self.store.save(self.store.next_id(self.d2), "b")
        self.store.save(self.store.next_id(self.d2), "c")
        self.assertEqual(self.store.delete_day(self.d2), 2)
        self.assertEqual(self.store.list_days(), [self.d1])
        self.assertEqual(self.store.delete_all(), 1)
        self.assertEqual(self.store.list_days(), [])

    def test_search(self):
        self.store.save(self.store.next_id(self.d1), "開會 10 點")
        self.store.save(self.store.next_id(self.d2), "買菜")
        hits = self.store.search("開會")
        self.assertEqual(list(hits.keys()), [self.d1])
        self.assertEqual(list(self.store.search("10-28").keys()), [self.d2])
        self.assertEqual(len(self.store.search("")), 2)

    def test_ignores_foreign_files(self):
        root = Path(self.tmp.name)
        (root / "readme.txt").write_text("not a note", encoding="utf-8")
        (root / "2026-10-28").mkdir()
        (root / "2026-10-28" / "photo.png").write_bytes(b"x")
        self.assertEqual(self.store.list_days(), [])

    def test_migrate_single_file(self):
        root = Path(self.tmp.name)
        (root / "2026-10-26.md").write_text("舊格式", encoding="utf-8")
        store = NoteStore(root, encrypt=False)
        self.assertEqual(store.list_days(), [date(2026, 10, 26)])
        self.assertEqual(store.load(NoteId(date(2026, 10, 26), 1)), "舊格式")

    def test_attachment_copy_and_resolve(self):
        src = Path(self.tmp.name) / "src.pdf"
        src.write_bytes(b"%PDF")
        rel = self.store.add_attachment(src)
        self.assertEqual(rel.as_posix(), "attachments/src.pdf")
        self.assertTrue(self.store.resolve(rel.as_posix()).is_file())
        rel2 = self.store.add_attachment(src)            # 同名不覆蓋
        self.assertNotEqual(rel, rel2)

    def test_title_of(self):
        self.assertEqual(title_of(""), "（空白）")
        self.assertEqual(title_of("# 標題 \n內文"), "標題")
        self.assertEqual(title_of("\n\n1. 買牛奶\n2. 拿包裹"), "買牛奶")   # 沒標題：第一個非空行、去清單標記
        self.assertEqual(title_of("- 項目"), "項目")
        self.assertTrue(title_of("x" * 50).endswith("…"))

    def test_split_join_title(self):
        self.assertEqual(split_title("# 週報\n1. a\n2. b"), ("週報", "1. a\n2. b"))
        self.assertEqual(split_title("1. a\n2. b"), ("", "1. a\n2. b"))
        self.assertEqual(join_title("週報", "內文"), "# 週報\n內文")
        self.assertEqual(join_title("  ", "內文"), "內文")
        t = "# 週報\n1. a"
        self.assertEqual(join_title(*split_title(t)), t)
        # 內文自己第一行是「# 」開頭：存了再讀，內文不能被吃成標題
        saved = join_title("", "# 這是內文的標題行\n下一行")
        self.assertEqual(split_title(saved), ("", "# 這是內文的標題行\n下一行"))

    def test_search_digits_do_not_match_whole_month(self):
        self.store.save(self.store.next_id(self.d2), "買 10 顆蛋")
        self.store.save(self.store.next_id(self.d1), "沒有數字")
        self.assertEqual(list(self.store.search("10").keys()), [self.d2])       # 只有內容含 10 的
        self.assertEqual(list(self.store.search("10-27").keys()), [self.d1])    # 像日期才當日期找
        self.assertEqual(list(self.store.search("2026").keys()), [self.d2, self.d1])

    def test_attachment_name_with_brackets_is_sanitized(self):
        src = Path(self.tmp.name) / "report (final) [v2].pdf"
        src.write_bytes(b"x")
        rel = self.store.add_attachment(src)
        self.assertEqual(rel.as_posix(), "attachments/report _final_ _v2_.pdf")

    def test_zero_byte_note_is_unreadable_not_empty(self):
        # 斷電留下 0 byte 的 .note：要當「解不開」保留，不能當空白被清掉
        d = Path(self.tmp.name) / "2026-10-28"; d.mkdir()
        (d / "001.note").write_bytes(b"")
        text, ok = self.store.try_load(NoteId(self.d2, 1))
        self.assertFalse(ok)

    def test_newest_file_wins_when_both_extensions_exist(self):
        import os, time
        d = Path(self.tmp.name) / "2026-10-28"; d.mkdir()
        (d / "001.note").write_bytes(b"PNOTE1\nold-garbage")
        time.sleep(0.01)
        (d / "001.md").write_text("新的純文字", encoding="utf-8")
        now = time.time(); os.utime(d / "001.md", (now + 5, now + 5))
        self.assertEqual(self.store.load(NoteId(self.d2, 1)), "新的純文字")

    def test_tmp_leftovers_cleaned_on_start(self):
        d = Path(self.tmp.name) / "2026-10-28"; d.mkdir()
        (d / "001.note.tmp").write_bytes(b"half")
        NoteStore(Path(self.tmp.name), encrypt=False)
        self.assertFalse((d / "001.note.tmp").exists())


if __name__ == "__main__":
    unittest.main()


class BulkTest(unittest.TestCase):
    """bulk() 期間 next_id 還是要看到剛寫的檔（匯入同一天多張不能撞號）；結束後索引重建。"""
    def test_import_many_into_one_day_numbers_unique(self):
        import tempfile
        from datetime import date
        with tempfile.TemporaryDirectory() as d:
            st = NoteStore(Path(d) / "n", encrypt=False)
            src = Path(d) / "src"; src.mkdir()
            for i in range(5):
                (src / f"f{i}.md").write_text(f"# t{i}\nx", encoding="utf-8")
            done, skipped = st.import_folder(src, today=date(2026, 10, 29))
            refs = st.list_notes(date(2026, 10, 29))
            self.assertEqual((done, skipped), (5, 0))
            self.assertEqual([r.id.seq for r in refs], [1, 2, 3, 4, 5])
            self.assertEqual(sorted(r.title for r in refs), [f"t{i}" for i in range(5)])

    def test_set_encrypt_bulk_keeps_everything(self):
        import tempfile
        from datetime import date, timedelta
        with tempfile.TemporaryDirectory() as d:
            st = NoteStore(Path(d) / "n", encrypt=False)
            for k in range(3):
                for i in range(1, 4):
                    st.save(NoteId(date(2026, 10, 1) + timedelta(days=k), i), f"# {k}-{i}\nbody")
            seen = []
            n = st.set_encrypt(True, progress=lambda a, b: seen.append((a, b)))
            self.assertEqual(n, 9)
            self.assertEqual(seen[-1], (9, 9))
            self.assertEqual(st.count_notes(), 9)
            self.assertEqual(st.load(NoteId(date(2026, 10, 2), 2)), "# 1-2\nbody")


class FavoritesTest(unittest.TestCase):
    def test_set_list_and_prune(self):
        tmp = tempfile.TemporaryDirectory()
        st = NoteStore(Path(tmp.name), encrypt=False)
        a, b = NoteId(date(2026, 10, 29), 1), NoteId(date(2026, 10, 30), 2)
        st.save(a, "# A\n1"); st.save(b, "# B\n2")
        self.assertFalse(st.is_favorite(a))
        st.set_favorite(a, True); st.set_favorite(b, True)
        self.assertEqual(st.favorites(), [b, a])                        # 新的日期在前
        self.assertEqual([r.title for r in st.favorite_refs()], ["B", "A"])
        st.set_favorite(a, False)
        self.assertEqual(st.favorites(), [b])
        st.delete(b)
        self.assertEqual(st.favorites(), [])                            # 刪掉的讀時濾掉
        st.set_favorite(NoteId(date(2026, 1, 1), 9), True)              # 不存在的也不列
        self.assertEqual(st.favorites(), [])
        tmp.cleanup()

# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""壞資料不能讓程式掛掉：解不開的筆記、壞的設定值、壞的 state.json。"""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from personalnote import crypto
from personalnote.config import Settings
from personalnote.state import AppState
from personalnote.storage import NoteId, NoteStore, UNREADABLE_TITLE


class UnreadableNoteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.d = date(2026, 10, 28)
        (self.root / "2026-10-28").mkdir()
        # 看起來像加密檔但解不開（模擬別台電腦加密的）
        (self.root / "2026-10-28" / "001.note").write_bytes(crypto.MAGIC + b"garbage-from-another-pc")
        (self.root / "2026-10-28" / "002.md").write_text("正常的", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_listing_does_not_crash(self):
        store = NoteStore(self.root, encrypt=False)
        refs = store.list_notes(self.d)
        self.assertEqual([r.title for r in refs], [UNREADABLE_TITLE, "正常的"])

    def test_try_load_flags_unreadable(self):
        store = NoteStore(self.root, encrypt=False)
        text, ok = store.try_load(NoteId(self.d, 1))
        self.assertFalse(ok)
        self.assertIn("解不開", text)
        self.assertEqual(store.try_load(NoteId(self.d, 2)), ("正常的", True))

    def test_search_export_and_toggle_skip_unreadable(self):
        store = NoteStore(self.root, encrypt=False)
        self.assertEqual(len(store.search("正常")[self.d]), 1)
        self.assertEqual(store.export_plain(self.root / "out"), 1)
        if sys.platform == "win32":
            self.assertEqual(store.set_encrypt(True), 1)
            self.assertTrue((self.root / "2026-10-28" / "001.note").read_bytes().endswith(b"garbage-from-another-pc"))

    def test_bad_utf8_plain_file(self):
        (self.root / "2026-10-28" / "003.md").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01bad")   # 真的不是文字（有控制字元）
        store = NoteStore(self.root, encrypt=False)
        self.assertEqual(store.list_notes(self.d)[-1].title, UNREADABLE_TITLE)


class BadConfigTest(unittest.TestCase):
    def test_bad_font_size_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            s = Settings.load([], env={"NOTE_DIR": d, "NOTE_FONT_SIZE": "abc"}, appdata=Path(d) / "x")
            self.assertEqual(s.font_size, 15)


class BadStateTest(unittest.TestCase):
    def test_bad_last_day_and_geometry(self):
        st = AppState(geometry="garbage", last_day="not-a-date")
        self.assertIsNone(st.last_day_or_none())
        self.assertEqual(st.safe_geometry(), AppState.geometry)

    def test_offscreen_geometry_reset(self):
        st = AppState(geometry="520x560+99999+99999")
        self.assertEqual(st.safe_geometry(), "520x560+240+120")
        st2 = AppState(geometry="520x560+240+120")
        self.assertEqual(st2.safe_geometry(), "520x560+240+120")


if __name__ == "__main__":
    unittest.main()

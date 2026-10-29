# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""加密相關測試（DPAPI 只有 Windows 有，其他平台會跳過）。"""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from personalnote import crypto
from personalnote.storage import NoteId, NoteStore


class CompatContractTest(unittest.TestCase):
    """相容契約：這三個值改了，所有舊的 .note 都解不開。要換加密方式請新增 PNOTE2，不要改這裡。"""

    def test_constants_never_change(self):
        self.assertEqual(crypto.MAGIC, b"PNOTE1\n")
        self.assertEqual(crypto._ENTROPY, b"PersonalNote-v1")
        self.assertEqual(crypto._DESCRIPTION, "PersonalNote")
        self.assertEqual(crypto.MAGIC_FAMILY, b"PNOTE")

    def test_newer_format_is_reported_as_newer_not_foreign(self):
        import tempfile
        from datetime import date
        from pathlib import Path
        from personalnote.storage import NoteStore, NoteId, NEWER_FORMAT_TEXT, UNREADABLE_TEXT
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "2026-10-28").mkdir()
            (root / "2026-10-28" / "001.note").write_bytes(b"PNOTE9\nfuture-format")
            (root / "2026-10-28" / "002.note").write_bytes(b"not-a-note-at-all")
            store = NoteStore(root, encrypt=False)
            self.assertEqual(store.try_load(NoteId(date(2026, 10, 28), 1)), (NEWER_FORMAT_TEXT, False))
            self.assertEqual(store.try_load(NoteId(date(2026, 10, 28), 2)), (UNREADABLE_TEXT, False))


@unittest.skipUnless(sys.platform == "win32", "DPAPI 只有 Windows")
class CryptoTest(unittest.TestCase):
    def test_roundtrip_and_not_plaintext(self):
        text = "買牛奶, \"引號\"\n第二行 English 123"
        blob = crypto.encrypt_text(text)
        self.assertTrue(crypto.is_encrypted(blob))
        self.assertNotIn("牛奶".encode("utf-8"), blob)
        self.assertEqual(crypto.decrypt_text(blob), text)

    def test_garbage_rejected(self):
        with self.assertRaises(crypto.CryptoError):
            crypto.decrypt_text(b"hello")
        with self.assertRaises(crypto.CryptoError):
            crypto.decrypt_text(crypto.MAGIC + b"not a real blob")


@unittest.skipUnless(sys.platform == "win32", "DPAPI 只有 Windows")
class EncryptedStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.d = date(2026, 10, 28)

    def tearDown(self):
        self.tmp.cleanup()

    def test_encrypted_save_is_note_file_and_unreadable(self):
        store = NoteStore(self.root, encrypt=True)
        nid = store.next_id(self.d)
        store.save(nid, "祕密")
        p = self.root / "2026-10-28" / "001.note"
        self.assertTrue(p.is_file())
        self.assertFalse((self.root / "2026-10-28" / "001.md").exists())
        self.assertNotIn("祕密".encode("utf-8"), p.read_bytes())
        self.assertEqual(store.load(nid), "祕密")
        self.assertEqual(store.list_notes(self.d)[0].title, "祕密")

    def test_reads_old_plain_and_rewrites_encrypted(self):
        (self.root / "2026-10-28").mkdir()
        (self.root / "2026-10-28" / "001.md").write_text("舊的純文字", encoding="utf-8")
        store = NoteStore(self.root, encrypt=True)
        nid = NoteId(self.d, 1)
        self.assertEqual(store.load(nid), "舊的純文字")
        store.save(nid, "舊的純文字 改過")
        self.assertFalse((self.root / "2026-10-28" / "001.md").exists())
        self.assertTrue((self.root / "2026-10-28" / "001.note").exists())

    def test_toggle_encrypt_converts_everything(self):
        store = NoteStore(self.root, encrypt=False)
        store.save(store.next_id(self.d), "a")
        store.save(store.next_id(self.d), "b")
        self.assertEqual(store.set_encrypt(True), 2)
        self.assertEqual(sorted(p.suffix for p in (self.root / "2026-10-28").iterdir()), [".note", ".note"])
        self.assertEqual(store.set_encrypt(False), 2)
        self.assertEqual(sorted(p.suffix for p in (self.root / "2026-10-28").iterdir()), [".md", ".md"])
        self.assertEqual(store.load(NoteId(self.d, 2)), "b")

    def test_export_plain(self):
        store = NoteStore(self.root, encrypt=True)
        store.save(store.next_id(self.d), "匯出我")
        dest = self.root / "export"
        self.assertEqual(store.export_plain(dest), 1)
        self.assertEqual((dest / "2026-10-28" / "001.md").read_text(encoding="utf-8"), "匯出我")

    def test_empty_removes_both_kinds(self):
        store = NoteStore(self.root, encrypt=True)
        nid = store.next_id(self.d)
        store.save(nid, "x")
        store.save(nid, "")
        self.assertFalse(store.exists(nid))
        self.assertEqual(store.list_days(), [])


if __name__ == "__main__":
    unittest.main()

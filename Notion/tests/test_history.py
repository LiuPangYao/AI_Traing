# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
import tempfile
import unittest
from datetime import date
from pathlib import Path

from personalnote.storage import NoteStore


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = NoteStore(Path(self.tmp.name), encrypt=False)
        self.store.SNAPSHOT_MIN_GAP = 0          # 這裡要一次存很多份，關掉 10 分鐘節流
        self.nid = self.store.next_id(date(2026, 10, 28))

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_only_when_changed(self):
        self.assertFalse(self.store.snapshot(self.nid, "第一版"))      # 之前是空的，不留
        self.store.save(self.nid, "第一版")
        self.assertFalse(self.store.snapshot(self.nid, "第一版"))      # 沒變，不留
        self.assertTrue(self.store.snapshot(self.nid, "第二版"))
        self.store.save(self.nid, "第二版")
        snaps = self.store.list_snapshots(self.nid)
        self.assertEqual(len(snaps), 1)
        self.assertEqual(self.store.load_snapshot(snaps[0][1]), "第一版")

    def test_keep_limit(self):
        self.store.save(self.nid, "v0")
        for i in range(1, 40):
            self.store.snapshot(self.nid, f"v{i}")
            self.store.save(self.nid, f"v{i}")
        self.assertEqual(len(self.store.list_snapshots(self.nid)), NoteStore.HISTORY_KEEP)
        newest = self.store.list_snapshots(self.nid)[0][1]
        self.assertEqual(self.store.load_snapshot(newest), "v38")

    def test_no_history_for_unknown_note(self):
        self.assertEqual(self.store.list_snapshots(self.nid), [])


if __name__ == "__main__":
    unittest.main()

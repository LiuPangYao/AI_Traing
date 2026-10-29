# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""PM 審查抓到的幾個洞，各留一個回歸測試：
- app.main --startup 不能炸（之前 `ns, _ = parse_known_args` 把翻譯函式蓋掉）
- 命令列 --lang 要生效
- 垃圾桶還原、快照節流
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from personalnote import app, startup
from personalnote.config import Settings
from personalnote.storage import NoteId, NoteStore


class StartupCommandTest(unittest.TestCase):
    """app.main 會依設定 set_language（全域），測完要還原成繁中，不然後面的測試看到英文。"""
    def tearDown(self):
        from personalnote import i18n
        i18n._table = None
        i18n._lang = i18n.KEY_COL

    def test_startup_status_does_not_crash(self):
        with mock.patch.object(startup, "is_enabled", return_value=False), \
             mock.patch.object(app, "_report") as rep, \
             mock.patch.object(app.applog, "setup", return_value=Path("x.log")):
            rc = app.main(["--startup", "status", "--lang", "zh_TW"])
        self.assertEqual(rc, 0)
        rep.assert_called_once()
        self.assertIn("關", rep.call_args[0][0])

    def test_startup_on_reports_error_instead_of_crashing(self):
        with mock.patch.object(startup, "enable", side_effect=RuntimeError("PowerShell 被擋")), \
             mock.patch.object(app, "_report") as rep, \
             mock.patch.object(app.applog, "setup", return_value=Path("x.log")):
            rc = app.main(["--startup", "on", "--lang", "zh_TW"])
        self.assertEqual(rc, 1)
        self.assertIn("PowerShell 被擋", rep.call_args[0][0])


class LangCliTest(unittest.TestCase):
    def test_cli_lang_wins(self):
        with tempfile.TemporaryDirectory() as d:
            s = Settings.load(["--note-dir", d, "--lang", "ja"], env={"NOTE_LANG": "en"}, appdata=Path(d) / "ad")
            self.assertEqual(s.lang, "ja")
            s2 = Settings.load(["--note-dir", d, "--lang", "nope"], env={}, appdata=Path(d) / "ad")
            self.assertEqual(s2.lang, "en")


class TrashRestoreTest(unittest.TestCase):
    def test_restore_last_deleted_goes_back_to_its_day(self):
        with tempfile.TemporaryDirectory() as d:
            st = NoteStore(Path(d), encrypt=False)
            day = date(2026, 10, 20)
            st.save(NoteId(day, 1), "# 一\nx")
            st.save(NoteId(day, 2), "# 二\ny")
            st.delete(NoteId(day, 2))
            self.assertEqual([r.id.seq for r in st.list_notes(day)], [1])
            nid = st.restore_last_deleted()
            self.assertEqual(nid, NoteId(day, 2))
            self.assertEqual(st.load(nid), "# 二\ny")
            # 編號被佔走：接在最後
            st.delete(NoteId(day, 1))
            st.save(NoteId(day, 1), "# 新的一\nz")
            nid = st.restore_last_deleted()
            self.assertEqual(nid, NoteId(day, 3))
            self.assertEqual(st.load(nid), "# 一\nx")
            self.assertIsNone(st.restore_last_deleted())


class SnapshotGapTest(unittest.TestCase):
    def test_second_snapshot_within_gap_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            st = NoteStore(Path(d), encrypt=False)
            nid = NoteId(date(2026, 10, 21), 1)
            st.save(nid, "v1")
            self.assertTrue(st.snapshot(nid, "v2"))
            st.save(nid, "v2")
            self.assertFalse(st.snapshot(nid, "v3"))        # 10 分鐘內：不留
            st.SNAPSHOT_MIN_GAP = 0
            self.assertTrue(st.snapshot(nid, "v3"))


if __name__ == "__main__":
    unittest.main()

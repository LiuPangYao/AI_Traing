# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""相容性：每一版都要讀得開 1.0.0 寫出來的資料（tests/fixtures/v1.0.0）。

規則（README「升級規則」）：
- 夾具檔案不准改。新版格式要另外加一組夾具（v1.0.x），舊的留著。
- 新版打開舊資料：全部讀得到、標題對、設定對。
- 舊版打開新資料：format.json 的版本比較大時只提示、不炸、不覆寫 format.json。
"""
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from personalnote import __version__
from personalnote.config import Settings
from personalnote.state import AppState
from personalnote.storage import FORMAT_VERSION, NoteId, NoteStore

FIXTURE = Path(__file__).parent / "fixtures" / "v1.0.0"


class CompatV100Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "data"
        shutil.copytree(FIXTURE, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_notes_readable_and_titles(self):
        store = NoteStore(self.root, encrypt=False)
        self.assertEqual(store.list_days(), [date(2026, 10, 28), date(2026, 10, 27)])
        refs27 = store.list_notes(date(2026, 10, 27))
        self.assertEqual([r.title for r in refs27], ["週報草稿", "沒有標題的舊筆記"])
        self.assertEqual(store.list_notes(date(2026, 10, 28))[0].title, "沒標題、第一行是清單")
        text, ok = store.try_load(NoteId(date(2026, 10, 27), 1))
        self.assertTrue(ok)
        self.assertIn("https://example.com/a", text)
        self.assertTrue(store.resolve("attachments/結案報告.pdf").is_file())

    def test_settings_and_state_still_load(self):
        s = Settings.load([], env={"NOTE_DIR": str(self.root)}, appdata=self.root / "no_appdata")
        self.assertEqual(s.font_size, 17)
        self.assertTrue(s.encrypt)
        st = AppState.load(self.root)
        self.assertEqual(st.last_day_or_none(), date(2026, 10, 28))

    def test_format_file_upgraded_not_downgraded(self):
        NoteStore(self.root, encrypt=False)
        data = json.loads((self.root / ".app" / "format.json").read_text(encoding="utf-8"))
        self.assertEqual(data["format"], FORMAT_VERSION)
        self.assertEqual(data["written_by"], __version__)

    def test_newer_data_only_warns(self):
        p = self.root / ".app" / "format.json"
        p.write_text(json.dumps({"format": FORMAT_VERSION + 1, "written_by": "9.9.9"}), encoding="utf-8")
        store = NoteStore(self.root, encrypt=False)
        self.assertEqual(store.newer_format_by, "9.9.9")
        self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["format"], FORMAT_VERSION + 1)  # 沒被降版覆寫
        self.assertTrue(store.list_notes(date(2026, 10, 27)))                                 # 還是讀得到

    def test_fixture_untouched_by_tests(self):
        # 測試只能動複本；夾具本身不能有 .tmp 或被改寫
        self.assertFalse(list(FIXTURE.rglob("*.tmp")))
        self.assertEqual(json.loads((FIXTURE / ".app" / "format.json").read_text(encoding="utf-8"))["written_by"], "1.0.0")


if __name__ == "__main__":
    unittest.main()

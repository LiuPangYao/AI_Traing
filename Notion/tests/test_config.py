# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""設定優先序測試：命令列 > 環境變數 > 設定檔 > 預設。"""
import json
import tempfile
import unittest
from pathlib import Path

from personalnote.config import Settings, default_note_dir


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_user_note_dir_pointer(self):
        appdata = self.dir / "appdata"
        chosen = self.dir / "elsewhere"
        s = Settings.load([], env={}, appdata=appdata).with_(note_dir=chosen)
        s.save_note_dir(appdata)
        again = Settings.load([], env={}, appdata=appdata)
        self.assertEqual(again.note_dir, chosen)
        # 環境變數還是贏過使用者指定
        s2 = Settings.load([], env={"NOTE_DIR": str(self.dir)}, appdata=appdata)
        self.assertEqual(s2.note_dir, self.dir)

    def test_save_note_dir_remembers_appdata_from_load(self):
        """load 時給了假 appdata，之後 save_note_dir() 不帶參數也要寫到假的那個，不能碰使用者真正的 %APPDATA%。"""
        appdata = self.dir / "appdata"
        s = Settings.load([], env={}, appdata=appdata).with_(note_dir=self.dir / "new")
        s.save_note_dir()
        self.assertTrue((appdata / "PersonalNote" / "note_dir.txt").is_file())
        self.assertEqual(Settings.load([], env={}, appdata=appdata).note_dir, self.dir / "new")

    def test_defaults(self):
        # 用空的暫存資料夾當 note_dir，才不會讀到桌面 personalNote 裡真的 settings.json
        s = Settings.load([], env={"NOTE_DIR": str(self.dir / "fresh")}, appdata=self.dir / "no_appdata")
        self.assertEqual(s.theme, "dark")
        self.assertEqual(s.font_size, 15)
        self.assertFalse(s.topmost)
        self.assertTrue(s.encrypt)
        self.assertTrue(str(default_note_dir()).endswith("Notion"))

    def test_env_overrides_file(self):
        (self.dir / ".app").mkdir()
        (self.dir / ".app" / "settings.json").write_text(json.dumps({"theme": "light", "font_size": 20}), encoding="utf-8")
        s = Settings.load([], env={"NOTE_DIR": str(self.dir), "NOTE_THEME": "system"}, appdata=self.dir / "ad")
        self.assertEqual(s.theme, "system")      # env 贏
        self.assertEqual(s.font_size, 20)        # 檔案裡的留著

    def test_cli_overrides_env(self):
        s = Settings.load(["--theme", "light", "--font-size", "9", "--topmost", "1"],
                          env={"NOTE_DIR": str(self.dir), "NOTE_THEME": "dark", "NOTE_TOPMOST": "0"}, appdata=self.dir / "ad")
        self.assertEqual(s.theme, "light")
        self.assertEqual(s.font_size, 9)
        self.assertTrue(s.topmost)

    def test_coerce_and_clamp(self):
        s = Settings.load([], env={"NOTE_DIR": str(self.dir), "NOTE_FONT_SIZE": "999", "NOTE_TOPMOST": "yes", "NOTE_THEME": "weird"}, appdata=self.dir / "ad")
        self.assertEqual(s.font_size, 48)
        self.assertTrue(s.topmost)
        self.assertEqual(s.theme, "dark")

    def test_save_only_persisted_fields(self):
        s = Settings.load([], env={"NOTE_DIR": str(self.dir)}, appdata=self.dir / "ad").with_(font_size=18, topmost=True)
        s.save()
        data = json.loads(s.settings_path.read_text(encoding="utf-8"))
        self.assertEqual(data, {"theme": "dark", "font_size": 18, "topmost": True, "encrypt": True, "lang": "en"})

    def test_bad_settings_file_ignored(self):
        (self.dir / ".app").mkdir()
        (self.dir / ".app" / "settings.json").write_text("{not json", encoding="utf-8")
        s = Settings.load([], env={"NOTE_DIR": str(self.dir)}, appdata=self.dir / "ad")
        self.assertEqual(s.font_size, 15)


if __name__ == "__main__":
    unittest.main()

# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""使用時間：累加、上限、寫檔節流、讀回、壞檔。"""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from personalnote import usage
from personalnote.config import APP_SUBDIR


class UsageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.d = date(2026, 10, 30)

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_clamp_save_reload(self):
        u = usage.UsageLog(self.root)
        u.add(self.d, 2); u.add(self.d, 2); u.add(self.d, 2)
        self.assertEqual(u.seconds(self.d), 6)
        u.add(self.d, 100)                                   # 一次最多算 MAX_TICK 秒（休眠醒來）
        self.assertEqual(u.seconds(self.d), 6 + usage.MAX_TICK)
        u.add(self.d, -5); u.add(self.d, 0)
        self.assertEqual(u.seconds(self.d), 6 + usage.MAX_TICK)
        self.assertFalse(u.save(now=10))                     # 不到 SAVE_EVERY 秒：先不寫
        self.assertTrue(u.save(now=10, force=True))
        self.assertFalse(u.save(now=11))                     # 沒有新變動
        u.add(self.d, 1)
        self.assertFalse(u.save(now=20))
        self.assertTrue(u.save(now=10 + usage.SAVE_EVERY))
        again = usage.UsageLog(self.root)
        self.assertEqual(again.seconds(self.d), 7 + usage.MAX_TICK)
        self.assertEqual(again.month(2026, 10), {self.d: 7 + usage.MAX_TICK})
        self.assertEqual(again.month(2026, 9), {})

    def test_bad_file(self):
        p = self.root / APP_SUBDIR / "usage.json"; p.parent.mkdir(parents=True)
        p.write_text("junk", encoding="utf-8")
        self.assertEqual(usage.UsageLog(self.root).seconds(self.d), 0)
        p.write_text(json.dumps({"2026-10-30": "x", "nope": 5, "2026-10-29": 7}), encoding="utf-8")
        u = usage.UsageLog(self.root)
        self.assertEqual((u.seconds(self.d), u.seconds(date(2026, 10, 29))), (0, 7))

    def test_fmt_duration(self):
        self.assertEqual(usage.fmt_duration(30), "不到 1 分")
        self.assertEqual(usage.fmt_duration(120), "2 分")
        self.assertEqual(usage.fmt_duration(3660), "1 小時 1 分")


if __name__ == "__main__":
    unittest.main()

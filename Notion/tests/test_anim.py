# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""動畫工具：混色、緩動、關閉時立刻完成。"""
import os
import unittest

from personalnote.ui import anim


class AnimTest(unittest.TestCase):
    def test_blend_and_ease(self):
        self.assertEqual(anim.blend("#000000", "#ffffff", 0), "#000000")
        self.assertEqual(anim.blend("#000000", "#ffffff", 1), "#ffffff")
        self.assertEqual(anim.blend("#000000", "#ffffff", 0.5), "#808080")
        self.assertEqual(anim.ease_out(0), 0)
        self.assertEqual(anim.ease_out(1), 1)
        self.assertGreater(anim.ease_out(0.5), 0.5)                     # 先快後慢

    def test_disabled_runs_done_immediately(self):
        os.environ["NOTE_ANIM"] = "0"
        try:
            calls = []
            anim.fade_bg([], "#000000", "#ffffff", done=lambda: calls.append("fade"))
            anim.collapse(None, lambda: calls.append("collapse"))
            self.assertEqual(calls, ["fade", "collapse"])
        finally:
            os.environ.pop("NOTE_ANIM", None)


if __name__ == "__main__":
    unittest.main()

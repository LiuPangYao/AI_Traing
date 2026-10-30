# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""state.json：左欄位置／尺寸的讀寫與壞值。"""
import json
import tempfile
import unittest
from pathlib import Path

from personalnote.state import AppState
from personalnote.config import APP_SUBDIR


class StateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_side_roundtrip(self):
        AppState().with_(sidebar_side="bottom", sidebar_height=300).save(self.dir)
        st = AppState.load(self.dir)
        self.assertEqual((st.sidebar_side, st.sidebar_height), ("bottom", 300))

    def test_bad_values_fall_back(self):
        p = self.dir / APP_SUBDIR / "state.json"; p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"sidebar_side": "top", "sidebar_height": "big", "sidebar_width": 300}), encoding="utf-8")
        st = AppState.load(self.dir)
        self.assertEqual((st.sidebar_side, st.sidebar_height, st.sidebar_width), ("left", 220, 300))


if __name__ == "__main__":
    unittest.main()

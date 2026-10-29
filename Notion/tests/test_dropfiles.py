# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""拖檔案進視窗：用假的 WM_DROPFILES 走一遍（不用真的拖）。只在 Windows 跑。"""
import sys
import tkinter as tk
import unittest
from pathlib import Path

from personalnote import dropfiles


@unittest.skipUnless(sys.platform == "win32", "只有 Windows")
class DropFilesTest(unittest.TestCase):
    def test_simulated_drop_delivers_paths(self):
        root = tk.Tk()
        root.geometry("+3000+3000")
        root.update()
        got = []
        self.assertTrue(dropfiles.enable(root, got.extend))
        self.assertTrue(dropfiles.enable(root, got.extend))          # 重複呼叫不會再包一層
        dropfiles.simulate_drop(root, [Path(r"D:\我的 筆記\今天.md"), Path(r"C:\tmp\截圖 1.png")])
        root.update()                                                 # after(0) 排進去的回呼在這裡跑
        root.update()
        self.assertEqual(got, [Path(r"D:\我的 筆記\今天.md"), Path(r"C:\tmp\截圖 1.png")])
        root.title("still alive")                                     # 其他訊息還是 Tk 原本在處理
        root.update()
        root.destroy()


if __name__ == "__main__":
    unittest.main()

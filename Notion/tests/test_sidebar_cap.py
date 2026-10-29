# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""左欄最多列幾張的切法（Tk grid 一欄上限 10000 列，超過整欄壞掉）。不開視窗，只測靜態函式。"""
import unittest
from datetime import date

from personalnote.ui.main_window import MainWindow


class CapTest(unittest.TestCase):
    def test_cap_keeps_order_and_counts_hidden(self):
        g = {date(2026, 10, 29): list(range(5)), date(2026, 10, 28): list(range(3)), date(2026, 10, 27): list(range(4))}
        shown, hidden = MainWindow._cap(g, 6)
        self.assertEqual(list(shown.keys()), [date(2026, 10, 29), date(2026, 10, 28)])
        self.assertEqual(shown[date(2026, 10, 28)], [0])
        self.assertEqual(hidden, 6)

    def test_cap_no_cut(self):
        g = {date(2026, 10, 29): [1, 2]}
        self.assertEqual(MainWindow._cap(g, 1000), (g, 0))

    def test_cap_zero(self):
        self.assertEqual(MainWindow._cap({date(2026, 10, 29): [1]}, 0), ({}, 1))


if __name__ == "__main__":
    unittest.main()

# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
import unittest

from personalnote.listing import next_marker


class ListingTest(unittest.TestCase):
    def test_numbered(self):
        self.assertEqual(next_marker("1. 買牛奶"), "2. ")
        self.assertEqual(next_marker("12) 第十二"), "13) ")
        self.assertEqual(next_marker("3、中文頓號"), "4、")
        self.assertEqual(next_marker("  2. 縮排"), "  3. ")

    def test_bullet(self):
        self.assertEqual(next_marker("- 項目"), "- ")
        self.assertEqual(next_marker("  • 子項"), "  • ")

    def test_empty_marker_ends_list(self):
        self.assertEqual(next_marker("4. "), "")
        self.assertEqual(next_marker("- "), "")

    def test_not_a_list(self):
        self.assertIsNone(next_marker("今天買牛奶"))
        self.assertIsNone(next_marker("1.沒空格"))
        self.assertIsNone(next_marker(""))


if __name__ == "__main__":
    unittest.main()


class ChecklistTest(unittest.TestCase):
    def test_checkbox_continues_unticked(self):
        self.assertEqual(next_marker("- [ ] 買牛奶"), "- [ ] ")
        self.assertEqual(next_marker("- [x] 做完了"), "- [ ] ")
        self.assertEqual(next_marker("  - [X] 子項"), "  - [ ] ")

    def test_empty_checkbox_ends_list(self):
        self.assertEqual(next_marker("- [ ] "), "")
        self.assertEqual(next_marker("- [ ]   "), "")

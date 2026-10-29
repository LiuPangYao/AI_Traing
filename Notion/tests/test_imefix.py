# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
import unittest

from personalnote.imefix import fixed_char


class ImeFixTest(unittest.TestCase):
    def test_period_misread_as_delete(self):
        self.assertEqual(fixed_char("Delete", "."), ".")
        self.assertEqual(fixed_char("Print", ","), ",")
        self.assertEqual(fixed_char("Insert", "-"), "-")

    def test_real_control_keys_untouched(self):
        self.assertIsNone(fixed_char("Delete", "\x7f"))
        self.assertIsNone(fixed_char("Delete", ""))
        self.assertIsNone(fixed_char("BackSpace", "\x08"))
        self.assertIsNone(fixed_char("Return", "\r"))

    def test_normal_typing_untouched(self):
        self.assertIsNone(fixed_char("period", "."))
        self.assertIsNone(fixed_char("a", "a"))
        self.assertIsNone(fixed_char("??", ""))          # 注音組字中的 keycode 229
        self.assertIsNone(fixed_char("space", " "))


if __name__ == "__main__":
    unittest.main()

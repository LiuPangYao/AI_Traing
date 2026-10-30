# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""快捷鍵：寫法整理、規則、tk 序列、設定檔疊預設、撞鍵。"""
import unittest

from personalnote import keys


class ParseTest(unittest.TestCase):
    def test_normalizes_case_and_order(self):
        self.assertEqual(keys.parse("ctrl + shift + h"), "Ctrl+Shift+H")
        self.assertEqual(keys.parse("Shift+Control+n"), "Ctrl+Shift+N")
        self.assertEqual(keys.parse("alt+pgup"), "Alt+PgUp")
        self.assertEqual(keys.parse("Ctrl+="), "Ctrl+=")
        self.assertEqual(keys.parse("Ctrl+\\"), "Ctrl+\\")

    def test_rules(self):
        with self.assertRaises(ValueError):
            keys.parse("H")                      # 沒帶 Ctrl／Alt
        with self.assertRaises(ValueError):
            keys.parse("Shift+H")
        self.assertEqual(keys.parse("F5"), "F5")  # F 鍵可以單獨
        with self.assertRaises(ValueError):
            keys.parse("Ctrl+C")                 # 系統保留
        with self.assertRaises(ValueError):
            keys.parse("Ctrl+")                  # 沒主鍵
        with self.assertRaises(ValueError):
            keys.parse("Ctrl+N+M")               # 兩個主鍵
        with self.assertRaises(ValueError):
            keys.parse("Ctrl+Mouse")             # 不支援的鍵
        self.assertEqual(keys.parse("Ctrl+Shift+C"), "Ctrl+Shift+C")   # Shift 版不算保留

    def test_sequences(self):
        self.assertEqual(keys.sequences("Ctrl+N"), ["<Control-n>", "<Control-N>"])
        self.assertEqual(keys.sequences("Ctrl+Shift+H"), ["<Control-Shift-h>", "<Control-Shift-H>"])
        self.assertEqual(keys.sequences("Ctrl+="), ["<Control-equal>", "<Control-plus>", "<Control-KP_Add>"])
        self.assertEqual(keys.sequences("Ctrl+PgUp"), ["<Control-Prior>"])
        self.assertEqual(keys.sequences("F5"), ["<F5>"])
        self.assertEqual(keys.sequences("Ctrl+\\"), ["<Control-backslash>"])

    def test_from_event(self):
        class E:
            def __init__(self, keysym, state):
                self.keysym, self.state = keysym, state
        self.assertEqual(keys.from_event(E("n", 4)), "Ctrl+N")
        self.assertEqual(keys.from_event(E("H", 4 | 1)), "Ctrl+Shift+H")
        self.assertEqual(keys.from_event(E("Prior", 4)), "Ctrl+PgUp")
        self.assertEqual(keys.from_event(E("F5", 0)), "F5")
        self.assertIsNone(keys.from_event(E("Control_L", 4)))      # 只按了修飾鍵
        self.assertIsNone(keys.from_event(E("Hangul", 4)))         # 不認得


class KeyMapTest(unittest.TestCase):
    def test_defaults_unique(self):
        km = keys.KeyMap.load()
        self.assertEqual(len(set(km.keys.values())), len(km.keys))
        self.assertEqual(km.key_of("new_note"), "Ctrl+N")
        self.assertEqual(km.overrides(), {})
        self.assertEqual(len(km.table()), len(keys.ACTIONS) + len(keys.GESTURES))

    def test_load_applies_valid_drops_bad(self):
        km = keys.KeyMap.load({"new_note": "ctrl+shift+n", "today": "H", "nope": "Ctrl+Q", "search": 5})
        self.assertEqual(km.key_of("new_note"), "Ctrl+Shift+N")
        self.assertEqual(km.key_of("today"), "Ctrl+T")              # 不合規則 → 預設
        self.assertEqual(km.overrides(), {"new_note": "Ctrl+Shift+N"})

    def test_load_conflict_falls_back(self):
        km = keys.KeyMap.load({"today": "Ctrl+F"})                   # 撞到搜尋的預設 → 退回
        self.assertEqual(km.key_of("today"), "Ctrl+T")
        self.assertEqual(km.key_of("search"), "Ctrl+F")

    def test_load_swap_is_fine(self):
        km = keys.KeyMap.load({"mark": "Ctrl+Shift+H", "red": "Ctrl+H"})
        self.assertEqual((km.key_of("mark"), km.key_of("red")), ("Ctrl+Shift+H", "Ctrl+H"))

    def test_set_and_conflict(self):
        km = keys.KeyMap.load()
        km2 = km.set("new_note", "ctrl+shift+n")
        self.assertEqual(km2.key_of("new_note"), "Ctrl+Shift+N")
        self.assertEqual(km.key_of("new_note"), "Ctrl+N")           # 原本的不變（frozen）
        with self.assertRaises(keys.Conflict) as cm:
            km2.set("today", "Ctrl+F")
        self.assertEqual(cm.exception.other, "search")
        self.assertEqual(km2.set("new_note", "Ctrl+Shift+N").overrides(), km2.overrides())   # 設成自己現在的鍵不算撞
        with self.assertRaises(ValueError):
            km2.set("today", "Ctrl+V")


if __name__ == "__main__":
    unittest.main()

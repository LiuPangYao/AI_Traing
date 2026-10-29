# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
import unittest

from personalnote.markup import block_text, checkbox, code_blocks, inline_spans, parse, plain, tags, toggle_checkbox


class InlineTest(unittest.TestCase):
    def kinds(self, line):
        return [(s.kind, line[s.inner_start:s.inner_end]) for s in inline_spans(line)]

    def test_each_kind(self):
        self.assertEqual(self.kinds("今天 ==重點== 和 !!警告!! 和 **粗** 和 *斜*"),
                         [("mark", "重點"), ("red", "警告"), ("bold", "粗"), ("italic", "斜")])

    def test_positions_include_markers(self):
        s = inline_spans("a ==bc== d")[0]
        self.assertEqual((s.start, s.end, s.inner_start, s.inner_end), (2, 8, 4, 6))

    def test_bold_before_italic(self):
        self.assertEqual(self.kinds("**粗體**"), [("bold", "粗體")])
        self.assertEqual(self.kinds("***全部***"), [("bold", "全部")])       # 多出來的星號當記號外的字

    def test_bullets_are_not_italic(self):
        self.assertEqual(self.kinds("* 項目一 * 項目二"), [])
        self.assertEqual(self.kinds("* 項目"), [])
        self.assertEqual(self.kinds("a * b"), [])

    def test_empty_or_spaces_not_marked(self):
        self.assertEqual(self.kinds("==== 和 !!!! 和 ****"), [])
        self.assertEqual(self.kinds("== 空白 =="), [])

    def test_english_and_mixed(self):
        self.assertEqual(self.kinds("Call ==Bob== at **9:00**!"), [("mark", "Bob"), ("bold", "9:00")])


class CodeBlockTest(unittest.TestCase):
    def test_closed_and_unclosed(self):
        lines = ["說明", "```", "ssh ao@host", "ls", "```", "後面", "```bash", "echo 1"]
        self.assertEqual(code_blocks(lines), [(1, 4), (6, 7)])
        self.assertEqual(block_text(lines, 1, 4), "ssh ao@host\nls")
        self.assertEqual(block_text(lines, 6, 7), "echo 1")

    def test_parse_skips_inline_inside_blocks(self):
        blocks, spans = parse("==外面==\n```\n==裡面==\n```\n**後面**")
        self.assertEqual(blocks, [(1, 3)])
        self.assertEqual(sorted(spans), [0, 4])
        self.assertEqual(spans[4][0].kind, "bold")

    def test_empty_text(self):
        self.assertEqual(parse(""), ([], {}))


if __name__ == "__main__":
    unittest.main()


class CheckboxTagPlainTest(unittest.TestCase):
    def test_checkbox(self):
        self.assertEqual(checkbox("- [ ] 買牛奶"), (0, 6, False))
        self.assertEqual(checkbox("  - [x] 做完"), (2, 8, True))
        self.assertEqual(checkbox("  - [X] 做完")[2], True)
        self.assertIsNone(checkbox("- [] 不是"))
        self.assertIsNone(checkbox("-[ ] 不是"))
        self.assertIsNone(checkbox("- [ ]沒空格"))
        self.assertIsNone(checkbox("普通"))

    def test_toggle(self):
        self.assertEqual(toggle_checkbox("- [ ] a"), "- [x] a")
        self.assertEqual(toggle_checkbox("  - [x] a"), "  - [ ] a")
        self.assertEqual(toggle_checkbox("- [X] a"), "- [ ] a")
        self.assertEqual(toggle_checkbox("沒有"), "沒有")

    def test_tags(self):
        self.assertEqual(tags("今天 #專案A 和 #todo-x 結束"), [(3, 7), (10, 17)])
        self.assertEqual(tags("issue #42 不是標籤"), [])
        self.assertEqual(tags("https://a.b/c#frag 網址裡的不算"), [])
        self.assertEqual(tags("C#語言 黏著字母不算"), [])
        self.assertEqual(tags("#開頭 可以"), [(0, 3)])
        self.assertEqual(tags("#タグ も可"), [(0, 3)])

    def test_plain(self):
        src = "看 **設計** 和 ==重點== !!紅!! *斜*\n[圖](attachments/a.png){w=3} 和 [](x.pdf)\n```\nls -l\n```\n- [x] 事 #tag"
        self.assertEqual(plain(src), "看 設計 和 重點 紅 斜\n圖 和 x.pdf\nls -l\n- [x] 事 #tag")
        self.assertEqual(plain("```\n沒關的區塊\n**裡面不動**"), "沒關的區塊\n**裡面不動**")
        self.assertEqual(plain(""), "")

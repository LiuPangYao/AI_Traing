# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
import unittest

from personalnote.links import find_links, link_at


class LinksTest(unittest.TestCase):
    def test_url_and_trailing_punctuation(self):
        ls = find_links("看這個 https://example.com/a?b=1, 再說。")
        self.assertEqual([l.target for l in ls], ["https://example.com/a?b=1"])
        self.assertEqual(link_at("看這個 https://example.com/a?b=1, 再說。", 8), "https://example.com/a?b=1")

    def test_www_gets_scheme(self):
        self.assertEqual(find_links("www.google.com")[0].target, "https://www.google.com")

    def test_windows_path(self):
        ls = find_links(r"檔案在 D:\AI\ai study\notes\58.md 這裡")
        self.assertEqual(ls[0].target, r"D:\AI\ai study\notes\58.md")      # 有空格、有副檔名：整段都算
        ls2 = find_links(r"C:\Users\Peter.Liu\Desktop\a.pdf")
        self.assertEqual(ls2[0].target, r"C:\Users\Peter.Liu\Desktop\a.pdf")
        ls3 = find_links(r"放在 D:\AI\ai study 這個資料夾")
        self.assertEqual(ls3[0].target, r"D:\AI\ai")                       # 純資料夾沒副檔名：空格就停（要用引號）
        ls4 = find_links(r'放在 "D:\AI\ai study\notes" 這個資料夾，還有 "C:\x y\z.txt"。')
        self.assertEqual([l.target for l in ls4], [r"D:\AI\ai study\notes", r"C:\x y\z.txt"])
        ls5 = find_links(r"D:\AI\ai study\notes\58.md, 然後 D:\b.txt")
        self.assertEqual([l.target for l in ls5], [r"D:\AI\ai study\notes\58.md", r"D:\b.txt"])
        ls6 = find_links(r"截圖 C:\Users\Peter.Liu\Pictures\Screenshots\螢幕擷取畫面 2026-10-28 171500.png 這張")
        self.assertEqual(ls6[0].target, r"C:\Users\Peter.Liu\Pictures\Screenshots\螢幕擷取畫面 2026-10-28 171500.png")
        ls7 = find_links(r"名單在 \\server\share\試務 2026\名單.xlsx，簡報 \\nas\會議\10月.pptx。")
        self.assertEqual([l.target for l in ls7], [r"\\server\share\試務 2026\名單.xlsx", r"\\nas\會議\10月.pptx"])

    def test_attachment_syntax(self):
        line = "[結案報告.pdf](attachments/結案報告.pdf) 已讀"
        ls = find_links(line)
        self.assertEqual(len(ls), 1)
        self.assertEqual(ls[0].target, "attachments/結案報告.pdf")
        self.assertEqual(link_at(line, 3), "attachments/結案報告.pdf")
        self.assertIsNone(link_at(line, len(line) - 1))

    def test_attachment_with_width_attribute(self):
        line = "[截圖.png](attachments/截圖.png){w=400} 說明"
        ls = find_links(line)
        self.assertEqual(len(ls), 1)
        self.assertEqual(ls[0].target, "attachments/截圖.png")
        self.assertEqual(line[ls[0].start:ls[0].end], "[截圖.png](attachments/截圖.png){w=400}")

    def test_attachment_with_url_inside_not_double_counted(self):
        line = "[官網](https://example.com)"
        ls = find_links(line)
        self.assertEqual(len(ls), 1)
        self.assertEqual(ls[0].target, "https://example.com")

    def test_no_links(self):
        self.assertEqual(find_links("今天買牛奶"), [])
        self.assertIsNone(link_at("今天買牛奶", 2))


if __name__ == "__main__":
    unittest.main()

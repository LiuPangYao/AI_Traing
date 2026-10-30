# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""查新版：版本比較、release JSON 解析、連不上與還沒發布的處理。不連網。"""
import unittest
import urllib.error

from personalnote import update


class VersionTest(unittest.TestCase):
    def test_parse_and_compare(self):
        self.assertEqual(update.parse_version("v1.0.3"), (1, 0, 3))
        self.assertEqual(update.parse_version("1.0.10"), (1, 0, 10))
        self.assertEqual(update.parse_version("junk"), (0,))
        self.assertTrue(update.is_newer("1.0.10", "1.0.9"))        # 逐段比數字，不是比字串
        self.assertFalse(update.is_newer("1.0.2", "1.0.2"))
        self.assertFalse(update.is_newer("0.9", "1.0.2"))
        self.assertTrue(update.is_newer("v2", "1.0.2"))


class ReleaseTest(unittest.TestCase):
    DATA = {"tag_name": "v1.0.3", "html_url": "https://github.com/x/releases/tag/v1.0.3",
            "assets": [{"name": "README.txt", "browser_download_url": "https://x/readme"},
                       {"name": "Notion_v1.0.3.zip", "browser_download_url": "https://x/Notion_v1.0.3.zip"}]}

    def test_parse_release_prefers_zip(self):
        info = update.parse_release(self.DATA, "1.0.2")
        self.assertEqual((info.version, info.url, info.newer), ("1.0.3", "https://x/Notion_v1.0.3.zip", True))

    def test_parse_release_without_zip_uses_page(self):
        info = update.parse_release({"tag_name": "1.0.3", "html_url": "https://x/page", "assets": []}, "1.0.3")
        self.assertEqual((info.url, info.newer), ("https://x/page", False))
        self.assertIsNone(update.parse_release({"assets": []}, "1.0.3"))
        self.assertIsNone(update.parse_release("junk", "1.0.3"))

    def test_check_states(self):
        self.assertEqual(update.check("1.0.2", lambda: self.DATA)[0], "ok")
        self.assertTrue(update.check("1.0.2", lambda: self.DATA)[1].newer)

        def not_found():
            raise urllib.error.HTTPError("u", 404, "nf", {}, None)
        self.assertEqual(update.check("1.0.2", not_found), ("no_release", None))

        def down():
            raise urllib.error.URLError("no net")
        self.assertEqual(update.check("1.0.2", down), ("offline", None))

        def boom():
            raise ValueError("bad json")
        self.assertEqual(update.check("1.0.2", boom), ("offline", None))
        self.assertEqual(update.check("1.0.2", lambda: {"assets": []}), ("no_release", None))


if __name__ == "__main__":
    unittest.main()

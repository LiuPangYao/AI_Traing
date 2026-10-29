# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""不要亂碼：別的程式寫的 txt（Big5、GBK、Shift-JIS、UTF-16）匯進來要正確；手改成 Big5 的 .md 也要讀得到；
程式自己存一律 UTF-8；真的不是文字的檔要明確失敗（不是亂碼開起來）。"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from personalnote.storage import NoteId, NoteStore, decode_text


class DecodeTest(unittest.TestCase):
    def test_unicode_always(self):
        for enc, text in (("utf-8", "中文 日本語 Ümlaut"), ("utf-8-sig", "有 BOM"), ("utf-16", "UTF-16 中文")):
            with self.subTest(enc=enc):
                self.assertEqual(decode_text(text.encode(enc)), text)

    def test_legacy_encoding_follows_preference(self):
        """Big5／GBK／Shift-JIS 互相都解得開（解出來是亂碼），所以要靠「畫面語言」或語系先猜：給對 prefer 就對。"""
        for enc, text in (("cp950", "台灣 Big5 繁體"), ("cp936", "简体中文 GBK"), ("cp932", "日本語のテキスト")):
            with self.subTest(enc=enc):
                self.assertEqual(decode_text(text.encode(enc), prefer=enc), text)

    def test_app_language_picks_encoding(self):
        from personalnote import i18n
        try:
            i18n._lang = "ja"
            self.assertEqual(decode_text("日本語のテキスト".encode("cp932")), "日本語のテキスト")
            i18n._lang = "zh_CN"
            self.assertEqual(decode_text("简体中文".encode("cp936")), "简体中文")
        finally:
            i18n._lang = i18n.KEY_COL

    def test_binary_raises(self):
        for raw in (b"\x89PNG\r\n\x1a\n\x00\x00\xff\xfe\x81\x81\x81", b"\xff\xfe\x00bad\x01", b"\x00\x01\x02\x03"):
            with self.subTest(raw=raw):
                with self.assertRaises(UnicodeDecodeError):
                    decode_text(raw)

    def test_empty(self):
        self.assertEqual(decode_text(b""), "")


class HandEditedNoteTest(unittest.TestCase):
    def test_big5_md_note_reads_and_resaves_as_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            st = NoteStore(Path(d), encrypt=False)
            nid = NoteId(date(2026, 10, 29), 1)
            st.save(nid, "# 原本\nUTF-8")
            p = st.path_for(nid)
            p.write_bytes("# 用記事本改過\n改成 Big5 存\r\n第二行".encode("cp950"))   # 使用者用舊記事本另存成 ANSI
            st.invalidate_caches()
            text, ok = st.try_load(nid)
            self.assertTrue(ok)
            self.assertEqual(text, "# 用記事本改過\n改成 Big5 存\n第二行")
            self.assertEqual(st.list_notes(nid.day)[0].title, "用記事本改過")
            st.save(nid, text)
            self.assertEqual(p.read_bytes().decode("utf-8"), text)      # 存回去就是 UTF-8


if __name__ == "__main__":
    unittest.main()

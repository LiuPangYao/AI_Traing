# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""簡單加密：Windows DPAPI（CryptProtectData，使用者範圍）。

為什麼選這個：
- 不用另外設密碼。能登入這個 Windows 帳號 = 能解開；硬碟拔到別台電腦、或用別的帳號登入，解不開。
- 系統內建，不用裝套件。
- 代價：**換電腦、重灌 Windows、刪帳號，舊的加密筆記就打不開。** 所以設定面板有「匯出成純文字」，換機前先匯出。

檔案格式（.note）：
    b"PNOTE1\\n" + DPAPI 加密後的 bytes
明文是 UTF-8 文字。storage.py 只呼叫 encrypt_text / decrypt_text，不知道 DPAPI 細節。
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

# ★ 相容契約：下面三個值決定舊筆記解不解得開，**永遠不能改**（tests/test_crypto_storage.py 有釘死）。
#   要換加密方式：新增 MAGIC = b"PNOTE2\n" 走新路徑，decrypt_text 同時認 PNOTE1 與 PNOTE2。
MAGIC = b"PNOTE1\n"
MAGIC_FAMILY = b"PNOTE"            # 檔頭是 PNOTE 開頭但不是我們認得的版本 → 較新版本寫的
_ENTROPY = b"PersonalNote-v1"      # 附加資料，只是避免跟別的 DPAPI 資料混淆；它在 exe 裡，不是秘密
_DESCRIPTION = "PersonalNote"      # CryptProtectData 的描述字串，也參與驗證

# 保護範圍（講清楚，README 也有同一張表）：
#   擋得住：硬碟拔到別台電腦、別的 Windows 帳號、沒登入就想讀檔。
#   擋不住：同帳號下跑的任何程式（惡意軟體）、知道你 Windows 密碼的人、網域管理員（網域帳號的 DPAPI 有備援金鑰）、
#           弱密碼被離線破解、休眠檔／分頁檔裡的明文（除非整顆碟 BitLocker）、attachments/ 與 .app/trash/ 裡的明文檔、匯出的純文字。
#   安全強度 = 你的 Windows 密碼強度。


class CryptoError(RuntimeError):
    pass


class NewerFormatError(CryptoError):
    """檔頭是 PNOTE 家族但不是這個版本認得的：資料是更新版程式寫的。"""


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> _DATA_BLOB:
    buf = ctypes.create_string_buffer(data, len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))


def _to_bytes(blob: _DATA_BLOB) -> bytes:
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob.pbData)


def available() -> bool:
    return sys.platform == "win32"


def encrypt_text(text: str) -> bytes:
    if not available():
        raise CryptoError("DPAPI 只有 Windows 有")
    out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(_blob(text.encode("utf-8"))), _DESCRIPTION, ctypes.byref(_blob(_ENTROPY)),
        None, None, 0, ctypes.byref(out))
    if not ok:
        raise CryptoError(f"CryptProtectData 失敗：{ctypes.GetLastError()}")
    return MAGIC + _to_bytes(out)


def decrypt_text(data: bytes) -> str:
    if not data.startswith(MAGIC):
        raise CryptoError("不是 PersonalNote 的加密檔")
    out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(_blob(data[len(MAGIC):])), None, ctypes.byref(_blob(_ENTROPY)),
        None, None, 0, ctypes.byref(out))
    if not ok:
        raise CryptoError(f"CryptUnprotectData 失敗（不是這台電腦／這個帳號加密的？）：{ctypes.GetLastError()}")
    return _to_bytes(out).decode("utf-8")


def is_encrypted(data: bytes) -> bool:
    return data.startswith(MAGIC)

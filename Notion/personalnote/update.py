# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""查有沒有新版：讀 GitHub Releases 的 latest（公開 repo，不用帳號、不用金鑰；只讀版本號，不傳任何東西出去）。

- fetch() 連網；check() 把結果整理成 (狀態, Info)。任何錯誤都不往上丟：沒網路、被防火牆擋、GitHub 壞掉，程式照常開。
- 狀態：ok（查到了，Info.newer 說有沒有比現在新）／no_release（repo 還沒發布過）／offline（連不上）。
- 主視窗在背景執行緒跑 check()，再用 after 輪詢結果（執行緒裡不碰 Tk）。
- 發布：tools/make_release.py --publish（有 gh 就自動上傳，沒有就印手動步驟）。
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

REPO = "LiuPangYao/AI_Traing"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
_ENV_URL = "NOTE_UPDATE_URL"      # 測試用：指到自己的伺服器（tools/stress/update_check.py 用它做端對端驗證）
PAGE_URL = f"https://github.com/{REPO}/releases/latest"
TIMEOUT = 6


@dataclass(frozen=True)
class Info:
    version: str        # 例如 "1.0.3"（tag 去掉 v）
    url: str            # zip 的下載網址；沒附 zip 就是 release 頁
    newer: bool         # 比現在跑的版本新


def parse_version(text: str) -> tuple[int, ...]:
    """'v1.0.3' → (1, 0, 3)；'1.0.10' > '1.0.9'（逐段比數字，不是比字串）。沒數字回 (0,)。"""
    nums = re.findall(r"\d+", str(text))
    return tuple(int(n) for n in nums) if nums else (0,)


def is_newer(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def parse_release(data: dict, current: str) -> Optional[Info]:
    """GitHub 的 release JSON → Info。沒有 tag 就回 None。"""
    if not isinstance(data, dict):
        return None
    tag = str(data.get("tag_name") or data.get("name") or "").strip()
    if not tag:
        return None
    version = tag[1:] if tag[:1] in ("v", "V") else tag
    url = ""
    for a in data.get("assets") or []:
        if isinstance(a, dict) and str(a.get("name", "")).lower().endswith(".zip"):
            url = str(a.get("browser_download_url") or "")
            break
    url = url or str(data.get("html_url") or PAGE_URL)
    return Info(version=version, url=url, newer=is_newer(version, current))


ALLOWED_PREFIXES = (f"https://github.com/{REPO}/", "https://api.github.com/")


def safe_url(url: str) -> str:
    """下載／開頁只認 GitHub 上這個 repo 的網址（JSON 被改也開不到別處）；測試用的本機網址（NOTE_UPDATE_URL 指到 127.0.0.1）放行。"""
    import os
    u = str(url or "")
    if u.startswith(ALLOWED_PREFIXES):
        return u
    if os.environ.get(_ENV_URL, "").startswith("http://127.0.0.1") and u.startswith("http://127.0.0.1"):
        return u
    return PAGE_URL


def fetch(timeout: int = TIMEOUT) -> dict:
    """連 GitHub 拿 latest release 的 JSON。失敗丟例外（check 會接）。"""
    from . import __version__, APP_NAME
    import os
    url = os.environ.get(_ENV_URL, "").strip() or API_URL
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": f"{APP_NAME}/{__version__}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check(current: str, fetch_fn: Callable[..., dict] = fetch) -> tuple[str, Optional[Info]]:
    """回 (狀態, Info)。狀態見模組說明；offline／no_release 時 Info 是 None。"""
    try:
        data = fetch_fn()
    except urllib.error.HTTPError as e:
        return ("no_release" if e.code == 404 else "offline"), None
    except Exception:
        return "offline", None
    info = parse_release(data, current)
    if info is None:
        return "no_release", None
    return "ok", info

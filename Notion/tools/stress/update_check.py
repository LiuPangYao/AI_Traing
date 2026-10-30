# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""端對端驗證「升級提醒」：拿一個打包好的 exe（舊版），開一個本機假伺服器說「有 v99.0.0」，看 exe 會不會跳出提醒視窗。

用法：python tools/stress/update_check.py <Notion.exe 的路徑> [--real]
  預設：本機 http 伺服器回 GitHub Releases 格式的 JSON，exe 以 NOTE_UPDATE_URL 指過來（1.0.6 起支援）。
  --real：不開假伺服器，exe 直接查真的 GitHub（要先在 GitHub 發布比這個 exe 新的 release）。
判定：主視窗出現後 20 秒內，同一個程序出現標題「New version」（英文介面）或「有新版」的視窗，而且 log 有「查新版：ok」。
只在 Windows 跑；視窗放螢幕外。"""
from __future__ import annotations

import ctypes
import http.server
import json
import os
import pathlib
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from ctypes import wintypes

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from personalnote import i18n  # noqa: E402

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
k32.OpenProcess.restype = ctypes.c_void_p
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_wchar_p, ctypes.POINTER(wintypes.DWORD)]
k32.CloseHandle.argtypes = [ctypes.c_void_p]
WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def image_of(pid: int) -> str:
    h = k32.OpenProcess(0x1000, False, pid)
    if not h:
        return ""
    buf = ctypes.create_unicode_buffer(1024); n = wintypes.DWORD(1024)
    ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)); k32.CloseHandle(h)
    return buf.value if ok else ""


def windows_of(exe: str) -> dict[str, int]:
    """這個 exe 的所有可見最上層視窗：標題 → hwnd。"""
    found: dict[str, int] = {}

    def cb(h, _lp):
        if not u32.IsWindowVisible(h):
            return True
        n = u32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1); u32.GetWindowTextW(h, buf, n + 1)
            pid = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if image_of(pid.value).lower() == exe.lower():
                found[buf.value] = h
        return True
    u32.EnumWindows(WNDENUM(cb), 0)
    return found


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__); return 2
    exe = str(pathlib.Path(sys.argv[1]).resolve())
    real = "--real" in sys.argv
    i18n.load_table()
    titles = set()
    for lang in i18n.langs():
        i18n.set_language(lang); titles.add(i18n._("有新版"))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="pn_upd_"))
    (tmp / "n" / ".app").mkdir(parents=True)
    (tmp / "n" / ".app" / "state.json").write_text(json.dumps({"geometry": "720x640+3000+3000", "tour_done": True}), encoding="utf-8")
    env = dict(os.environ, NOTE_DIR=str(tmp / "n"), NOTE_ALLOW_MULTI="1", NOTE_TOUR="0")
    srv = None
    if not real:
        payload = json.dumps({"tag_name": "v99.0.0", "html_url": "http://127.0.0.1/release",
                              "assets": [{"name": "Notion_v99.0.0.zip", "browser_download_url": "http://127.0.0.1/Notion_v99.0.0.zip"}]}).encode()

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(payload)

            def log_message(self, *a):
                pass
        srv = socketserver.TCPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        env["NOTE_UPDATE_URL"] = f"http://127.0.0.1:{srv.server_address[1]}/latest.json"
        print("假伺服器：", env["NOTE_UPDATE_URL"], "→ v99.0.0")
    p = subprocess.Popen([exe], env=env)
    t0 = time.time(); seen = {}
    while time.time() - t0 < 60:
        time.sleep(0.5)
        seen = windows_of(exe)
        if any(t in titles for t in seen):
            break
    got = [t for t in seen if t in titles]
    log = pathlib.Path(os.environ["APPDATA"]) / "PersonalNote" / "logs" / "personalnote.log"
    tail = log.read_text(encoding="utf-8", errors="replace")[-4000:] if log.is_file() else ""
    logged = "查新版：ok" in tail
    print("視窗：", sorted(seen), "| 提醒視窗出現：", bool(got), "| log 查到新版：", logged, "（%.0f 秒）" % (time.time() - t0))
    for h in seen.values():
        u32.PostMessageW(h, 0x0010, 0, 0)        # WM_CLOSE
    try:
        p.wait(timeout=15)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    if srv:
        srv.shutdown()
    ok = bool(got) and logged
    print("UPDATE CHECK:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

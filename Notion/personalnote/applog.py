# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""程式 log：出錯、當掉、卡死時留下可以分析的紀錄。

放哪裡：%LOCALAPPDATA%\\PersonalNote\\logs\\personalnote.log（最多 1 MB × 3 份輪替）。
        故意不放筆記資料夾：筆記資料夾在拔掉的隨身碟上時，log 還是寫得出來。
記什麼：啟動（版本、Python、參數、設定）、開哪張、存檔、匯入匯出、設定變更、關閉；
        所有沒接到的例外（含堆疊）；Python 層硬當（faulthandler）；主迴圈卡住（看門狗倒堆疊）。
怎麼看：設定面板「開啟 log 資料夾」，或直接到上面那個路徑。
"""
from __future__ import annotations

import faulthandler
import logging
import logging.handlers
import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

LOG_NAME = "personalnote"
_log = logging.getLogger(LOG_NAME)
_fault_file = None


def log_dir() -> Path:
    from . import platform_                 # Windows %LOCALAPPDATA%\PersonalNote\logs（1.0.7 起；之前在 %APPDATA%）；Linux ~/.local/state/PersonalNote/logs
    return platform_.data_dir() / "logs"


def setup() -> Path:
    """只呼叫一次。回傳 log 檔路徑。寫不進去（權限）就退回只寫 stderr，程式照開。"""
    global _fault_file
    d = log_dir()
    path = d / f"{LOG_NAME}.log"
    _log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(threadName)s] %(message)s")
    try:
        d.mkdir(parents=True, exist_ok=True)
        h = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        h.setFormatter(fmt)
        _log.addHandler(h)
        # Python 層硬當（例如 Tk 內部崩潰）：faulthandler 直接把堆疊寫進另一個檔，不經過 logging
        _fault_file = open(d / "crash.log", "a", encoding="utf-8")
        faulthandler.enable(file=_fault_file, all_threads=True)
    except OSError:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fmt)
        _log.addHandler(sh)
    # 沒接到的例外（主執行緒與其他執行緒）
    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook
    return path


def info(msg: str, *args) -> None:
    _log.info(msg, *args)


def warning(msg: str, *args) -> None:
    _log.warning(msg, *args)


def exception(msg: str, *args) -> None:
    """在 except 裡呼叫：連堆疊一起記。"""
    _log.exception(msg, *args)


def error_with_tb(msg: str, exc_info) -> None:
    _log.error(msg, exc_info=exc_info)


def _excepthook(exc, val, tb) -> None:
    _log.error("未接到的例外", exc_info=(exc, val, tb))
    sys.__excepthook__(exc, val, tb)


def _thread_excepthook(args) -> None:
    _log.error("執行緒 %s 未接到的例外", args.thread.name if args.thread else "?",
               exc_info=(args.exc_type, args.exc_value, args.exc_traceback))


class Watchdog:
    """主迴圈卡住偵測。主視窗每 2 秒 ping 一次；超過 stall_seconds 沒 ping，就把所有執行緒的堆疊
    倒進 crash.log（faulthandler.dump_traceback），之後卡死就有東西可以看。只倒一次，解除後重新武裝。"""

    def __init__(self, stall_seconds: float = 30.0):
        self.stall = stall_seconds
        self._last = time.monotonic()
        self._dumped = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="watchdog", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def ping(self) -> None:
        self._last = time.monotonic()
        if self._dumped:
            _log.warning("主迴圈恢復回應")
            self._dumped = False

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(2.0):
            gap = time.monotonic() - self._last
            if gap > self.stall and not self._dumped:
                self._dumped = True
                _log.error("主迴圈 %.0f 秒沒有回應，倒出所有執行緒堆疊到 crash.log", gap)
                try:
                    if _fault_file is not None:
                        _fault_file.write(f"\n==== 卡住 {time.strftime('%Y-%m-%d %H:%M:%S')} gap={gap:.0f}s\n")
                        _fault_file.flush()
                        faulthandler.dump_traceback(file=_fault_file, all_threads=True)
                        _fault_file.flush()
                except Exception:
                    pass

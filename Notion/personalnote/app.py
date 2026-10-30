# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""進入點。讀設定 → 建存檔層 → 開視窗。也處理不開視窗的維護指令（--startup）。"""
from __future__ import annotations

import ctypes
import os
import sys
from typing import Sequence

from . import i18n
from .i18n import _
from . import APP_NAME, __version__, applog, platform_, startup
from .config import Settings, build_arg_parser
from .storage import NoteStore



def _single_instance() -> bool:
    """開機時 bat 和捷徑可能各跑一次；第二個退出（Windows 順便把已開的視窗叫到前面）。實作在 platform_.py。"""
    return platform_.single_instance(APP_NAME)


def _report(msg: str) -> None:
    """維護指令的結果。打包成 --windowed 的 exe 沒有主控台（print 看不到），所以跳一個小框。"""
    if getattr(sys, "frozen", False):
        platform_.message_box(APP_NAME, msg)
    else:
        print(msg)


def _fatal(msg: str) -> None:
    """開視窗之前就掛掉（例如存檔資料夾在拔掉的隨身碟上）：打包成 exe 沒有主控台，一定要跳框。"""
    platform_.message_box(_("{0} 無法啟動").format(APP_NAME), msg, error=True)
    print(msg, file=sys.stderr)


_splash_stop = None


def _start_splash_anim() -> None:
    """啟動畫面的「載入中」每 0.3 秒換點點（Peter：不然不知道是不是卡了）。用 python 直接跑沒有 pyi_splash，跳過。
    文字區在 Notion.spec 的 Splash(text_pos=…)；這裡只負責換字。"""
    global _splash_stop
    try:
        import pyi_splash                        # noqa: F401  只有打包後才有
    except Exception:
        return
    import threading
    _splash_stop = threading.Event()
    stop = _splash_stop

    def run() -> None:
        i = 0
        while not stop.is_set():
            try:
                if not pyi_splash.is_alive():
                    return
                pyi_splash.update_text("載入中" + "." * (i % 4))
            except Exception:
                return
            i += 1
            stop.wait(0.3)
    threading.Thread(target=run, daemon=True, name="splash-anim").start()


def _close_splash() -> None:
    """PyInstaller 的啟動畫面收掉（Notion.spec 的 Splash）。用 python 直接跑沒有這個模組，跳過。"""
    if _splash_stop is not None:
        _splash_stop.set()
    try:
        import pyi_splash                        # noqa: F401  只有打包後才有
        pyi_splash.close()
    except Exception:
        pass


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _start_splash_anim()                     # 最先做：解壓完一進 Python 就讓「載入中」動起來
    log_path = applog.setup()
    ns, _rest = build_arg_parser().parse_known_args(argv)   # 不能叫 _，會把翻譯函式蓋掉（PM 審查抓到的 P0）
    settings = Settings.load(argv)
    i18n.set_language(settings.lang)      # 畫面文字的語言（設定裡可切；預設 en）
    applog.info("啟動 %s %s | python %s | frozen=%s | argv=%s | 設定=%s | log=%s",
                APP_NAME, __version__, sys.version.split()[0], getattr(sys, "frozen", False),
                argv, settings.as_dict(), log_path)

    if ns.startup:                       # 維護指令，做完就走
        try:
            if ns.startup == "on":
                msg = _("已建立開機捷徑：\n{0}").format(startup.enable(settings.launcher))
            elif ns.startup == "off":
                startup.disable()
                msg = _("已移除開機捷徑")
            else:
                msg = _("開機啟動：") + (_("開") if startup.is_enabled() else _("關"))
        except Exception as e:
            applog.exception("--startup 失敗")
            msg = _("開機啟動設定失敗：{0}").format(e)
            _report(msg)
            return 1
        applog.info("--startup %s → %s", ns.startup, msg.replace("\n", " "))
        _report(msg)
        return 0

    if not _single_instance():
        applog.info("已經有一個在跑（或上一個卡在錯誤框還沒關），這個退出")   # 不然第二次點沒反應，log 也看不出為什麼
        return 0

    try:
        from .ui.main_window import MainWindow   # 晚載入：維護指令不需要 GUI
        store = NoteStore(settings.note_dir, encrypt=settings.encrypt)
        win = MainWindow(settings, store)        # 關視窗後 customtkinter 可能還有一個排程的標題列回呼會撞「application has been destroyed」，在下面接掉
        _close_splash()                          # 視窗好了才收掉啟動畫面（onefile 解壓那 1～2 秒使用者才看得到有東西在動）
    except Exception as e:
        _close_splash()
        import traceback
        applog.exception("開視窗前就失敗")
        _fatal(_("{0}\n\n存檔位置：{1}\n詳細紀錄：{2}\n\n{3}").format(e, settings.note_dir, log_path, traceback.format_exc()[-1200:]))
        return 1
    try:
        win.mainloop()
    except Exception as e:
        if "application has been destroyed" in str(e):   # 關視窗後 customtkinter 排程的標題列回呼：視窗已經沒了，不算錯
            applog.info("關閉後的排程回呼撞到已關閉的視窗（忽略）")
        else:
            applog.exception("mainloop 跳出")
            raise
    applog.info("正常結束")
    return 0


if __name__ == "__main__":
    sys.exit(main())

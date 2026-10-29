# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""設定值。

優先序（高到低）：
1. 命令列參數      例如 --theme light
2. 環境變數        Notion.bat 裡的 set NOTE_xxx=...
3. 使用者指定的位置 %APPDATA%/PersonalNote/note_dir.txt（設定面板「更改存檔位置」寫這裡；只有 note_dir 這一項）
4. 設定檔          <note_dir>/.app/settings.json（程式內改外觀會寫這裡）
5. 預設值          下面 Settings 的欄位預設；note_dir 預設桌面 Notion，不存在會自動建

要加一個新設定，要改這幾處（漏一處會靜默失效，沒有錯誤訊息）：
  1. Settings 加欄位（有預設值）
  2. PERSISTED 加名字（要寫進 settings.json 的才加）
  3. _ENV_KEYS 加 NOTE_xxx 對應
  4. build_arg_parser 加 --xxx，且 _from_cli 的 keep 加名字
  5. _coerce 加型別轉換（不是字串的話）
  6. Notion.bat 加一行 set NOTE_xxx=
  7. ui/main_window.py 設定面板的「.bat 有填」清單加 NOTE_xxx
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict, fields, replace
from pathlib import Path
from typing import Any, Optional, Sequence

APP_SUBDIR = ".app"            # note_dir 底下放設定與狀態的隱藏資料夾
SETTINGS_FILE = "settings.json"

THEMES = ("dark", "light", "system")


def default_note_dir() -> Path:
    """預設存檔位置：Windows 認定的「桌面」底下的 Notion（2026-10-29 跟著程式改名，原本叫 personalNote）。
    用 SHGetFolderPath 問系統，公司電腦桌面被重新導向到 OneDrive 或網路槽時才會建在使用者看得到的地方；
    問不到才退回 USERPROFILE\\Desktop。"""
    return desktop_dir() / "Notion"


def desktop_dir() -> Path:
    from . import platform_                 # 跟作業系統有關的都在 platform_.py
    return platform_.desktop_dir()


@dataclass(frozen=True)
class Settings:
    note_dir: Path = default_note_dir()
    theme: str = "dark"                      # dark / light / system
    font_family: str = ""                    # 空＝依作業系統（platform_.ui_font_family）；bat 的 NOTE_FONT 可指定
    font_size: int = 15
    topmost: bool = False                    # 視窗永遠在最上層
    launcher: Optional[Path] = None          # 開機啟動捷徑要指向的 .bat；None = 指向程式本身
    encrypt: bool = True                     # 筆記用 Windows DPAPI 加密（綁這個 Windows 帳號）
    lang: str = "en"                         # 畫面語言＝翻譯表的欄名（en / zh_TW / zh_CN / ja…，看 assets/lang/strings.csv）；預設英文（Peter 決定）
    appdata: Optional[Path] = None          # note_dir.txt 要寫在哪個 APPDATA；None = 真的 %APPDATA%。測試一定要給假的，
                                             # 不然「換位置」會寫進使用者真正的設定（2026-10-29 發生過：壓力測試把 Peter 的指標改掉）

    # 這些欄位會寫進 settings.json（程式內可改的）；其餘只從 bat／命令列來
    PERSISTED = ("theme", "font_size", "topmost", "encrypt", "lang")

    # ---- 讀取 ----
    @classmethod
    def load(cls, argv: Sequence[str] | None = None,
             env: dict[str, str] | None = None,
             appdata: Path | None = None) -> "Settings":
        env = os.environ if env is None else env
        s = cls(appdata=appdata)
        # 先決定 note_dir（因為 settings.json 住在裡面），再疊其他來源
        s = s._apply({"note_dir": _user_note_dir(appdata)})
        s = s._apply({"note_dir": _from_env(env).get("note_dir")})
        s = s._apply({"note_dir": _from_cli(argv).get("note_dir")})
        s = s._apply(_from_file(s.note_dir))
        s = s._apply(_from_env(env))
        s = s._apply(_from_cli(argv))
        return s

    def save_note_dir(self, appdata: Path | None = None) -> None:
        """使用者在設定面板選了新位置：記到 APPDATA（load 時給的那個，測試才不會寫到真的），下次啟動照這個。"""
        p = _note_dir_pointer(appdata or self.appdata)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(self.note_dir), encoding="utf-8")

    def _apply(self, values: dict[str, Any]) -> "Settings":
        clean = {k: _coerce(k, v) for k, v in values.items() if v is not None and k in _FIELD_TYPES}
        return replace(self, **clean)

    # ---- 寫入（只寫 PERSISTED 那幾個）----
    def save(self) -> None:
        path = self.settings_path
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: getattr(self, k) for k in self.PERSISTED}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @property
    def settings_path(self) -> Path:
        return self.note_dir / APP_SUBDIR / SETTINGS_FILE

    def with_(self, **kw: Any) -> "Settings":
        return self._apply(kw)

    def as_dict(self) -> dict[str, Any]:
        return {k: (str(v) if isinstance(v, Path) else v) for k, v in asdict(self).items()}


# ---- 來源：使用者指定的存檔位置（APPDATA 小檔）----
def _note_dir_pointer(appdata: Path | None) -> Path:
    from . import platform_
    return platform_.config_dir(appdata) / "note_dir.txt"


def _user_note_dir(appdata: Path | None) -> Optional[str]:
    p = _note_dir_pointer(appdata)
    if p.is_file():
        v = p.read_text(encoding="utf-8").strip()
        return v or None
    return None


# ---- 來源 1：設定檔 ----
def _from_file(note_dir: Path) -> dict[str, Any]:
    path = note_dir / APP_SUBDIR / SETTINGS_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: data.get(k) for k in Settings.PERSISTED}


# ---- 來源 2：環境變數（Notion.bat 設的）----
_ENV_KEYS = {
    "NOTE_DIR": "note_dir",
    "NOTE_THEME": "theme",
    "NOTE_FONT": "font_family",
    "NOTE_FONT_SIZE": "font_size",
    "NOTE_TOPMOST": "topmost",
    "NOTE_LAUNCHER": "launcher",
    "NOTE_ENCRYPT": "encrypt",
    "NOTE_LANG": "lang",
}


def _from_env(env: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for env_key, field in _ENV_KEYS.items():
        raw = env.get(env_key)
        if raw is not None and raw.strip() != "":
            out[field] = raw.strip()
    return out


# ---- 來源 3：命令列 ----
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="personalnote", description="PersonalNote")
    p.add_argument("--note-dir", dest="note_dir", help="存檔資料夾")
    p.add_argument("--theme", choices=THEMES)
    p.add_argument("--font", dest="font_family")
    p.add_argument("--font-size", dest="font_size", type=int)
    p.add_argument("--topmost", dest="topmost", choices=("0", "1"))
    p.add_argument("--launcher", dest="launcher", help="開機捷徑指向的 .bat")
    p.add_argument("--encrypt", dest="encrypt", choices=("0", "1"), help="筆記是否加密")
    p.add_argument("--lang", dest="lang", help="畫面語言（翻譯表的欄名，例如 en、zh_TW、zh_CN、ja）")
    # 不開視窗的維護指令
    p.add_argument("--startup", choices=("on", "off", "status"),
                   help="安裝／移除／查詢開機啟動，做完就結束")
    return p


def _from_cli(argv: Sequence[str] | None) -> dict[str, Any]:
    ns, _unknown = build_arg_parser().parse_known_args(list(argv) if argv is not None else None)
    keep = ("note_dir", "theme", "font_family", "font_size", "topmost", "launcher", "encrypt", "lang")
    return {k: getattr(ns, k) for k in keep}


# ---- 型別轉換（字串 → 欄位型別）----
_FIELD_TYPES = {f.name: f.type for f in fields(Settings)}

_TRUE = {"1", "true", "yes", "on", "y"}


def _coerce(key: str, value: Any) -> Any:
    """字串 → 欄位型別。壞值（例如 NOTE_FONT_SIZE=abc）回預設，不讓程式開不起來。"""
    if key in ("note_dir", "launcher"):
        return Path(value).expanduser() if not isinstance(value, Path) else value
    if key == "font_size":
        try:
            n = int(value)
        except (TypeError, ValueError):
            return Settings.font_size
        return max(8, min(48, n))
    if key in ("topmost", "encrypt"):
        return value if isinstance(value, bool) else str(value).strip().lower() in _TRUE
    if key == "theme":
        v = str(value).strip().lower()
        return v if v in THEMES else "dark"
    if key == "lang":
        from . import i18n
        v = str(value).strip()
        return v if v in i18n.langs() else i18n.DEFAULT
    return value

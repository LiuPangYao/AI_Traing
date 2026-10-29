# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""存檔層：一天一個資料夾，一張筆記一個檔。

資料夾長這樣：
    Notion/            （桌面的筆記資料夾；原本叫 personalNote）
        2026-10-27/
            001.note         一張筆記＝一個檔。加密時副檔名 .note（Windows DPAPI，見 crypto.py）
            002.note
        2026-10-28/
            001.md           沒開加密時是 .md 純文字（UTF-8）；兩種都認得
        attachments/         圖片、PDF 的副本（add_attachment 放進來；**不加密**）
        .app/                程式自己的設定、狀態、垃圾桶；不是筆記

規則：
- 只認 YYYY-MM-DD 資料夾和裡面 NNN.md / NNN.note 的檔，其他東西不碰。
- 不是 CSV、不是資料庫：一張筆記就是一段 UTF-8 文字，逗號、換行、中英混雜都不會壞。
- 寫檔用「先寫暫存檔再改名」，中途當機不會留下半截檔。
- 內容清空的筆記會被刪掉（先搬到 .app/trash/），清單才不會一堆空白。
- 存檔時照 encrypt 旗標決定寫 .note 還是 .md，並把另一種副檔名的舊檔清掉，一張筆記永遠只有一個檔。
- 換電腦前用 export_plain 匯出純文字（DPAPI 綁帳號，別台電腦解不開）。
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from typing import Callable, Optional

from . import crypto
from .i18n import _
from .config import APP_SUBDIR

DAY_DIR_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
NOTE_FILE_RE = re.compile(r"^(\d{3,})\.(md|note)$")      # 至少 3 位，第 1000 張是 1000.note
EXT_PLAIN, EXT_ENC = ".md", ".note"
ATTACH_DIR = "attachments"
TRASH_DIR = "trash"
TITLE_MAX = 28
EMPTY_TITLE = "（空白）"
UNREADABLE_TITLE = "（解不開）"
NEWER_TITLE = "（較新版本的格式）"
UNREADABLE_TEXT = ("# （解不開）\n這張筆記是別台電腦或別的 Windows 帳號加密的，這裡解不開。\n"
                   "回到原來那台電腦，在設定裡「匯出全部」再搬過來。")
NEWER_FORMAT_TEXT = ("# （較新版本的格式）\n這張筆記是比這個程式更新的版本寫的，這個版本看不懂。\n"
                     "請更新 Notion 再開；不要在這裡改它。")


@dataclass(frozen=True, order=True)
class NoteId:
    day: date
    seq: int


TODO_DAY = date(9999, 12, 31)   # 待辦事項：不屬於任何日期，只有一張（TODO_ID）。資料夾 9999-12-31，日期排序永遠在最上面
TODO_ID = NoteId(TODO_DAY, 1)


@dataclass(frozen=True)
class NoteRef:
    """清單用：不含全文，只有標題。"""
    id: NoteId
    title: str


TITLE_PREFIX = "# "
_LIST_MARK_RE = re.compile(r"^\s*(?:\d+[.)、]\s*|[-•*]\s+)")


def split_title(text: str) -> tuple[str, str]:
    """檔案文字 → (標題, 內文)。標題＝第一行以「# 」開頭的那行；沒有就標題空、整份都是內文。"""
    first, sep, rest = text.partition("\n")
    if first.startswith(TITLE_PREFIX) or first == TITLE_PREFIX.rstrip():
        return first[len(TITLE_PREFIX):].strip(), rest
    return "", text


def join_title(title: str, body: str) -> str:
    """(標題, 內文) → 檔案文字。標題空就不寫那一行；
    但內文自己第一行是「# 」開頭時，寫一行空標題「# 」佔位，下次讀才不會把內文吃成標題。"""
    title = title.strip()
    if title:
        return f"{TITLE_PREFIX}{title}\n{body}"
    if body.startswith(TITLE_PREFIX) or body.startswith("#\n"):
        return f"{TITLE_PREFIX.rstrip()}\n{body}"
    return body


def title_of(text: str) -> str:
    """左欄顯示的字：有標題用標題；沒有就拿內文第一個非空行，去掉「1. 」「- 」這種清單標記。"""
    title, body = split_title(text)
    if not title:
        for line in body.splitlines():
            s = _LIST_MARK_RE.sub("", line).lstrip("# ").strip()   # 內文第一行若是「# xx」，左欄不要連井字一起顯示
            if s:
                title = s
                break
    if not title:
        return _(EMPTY_TITLE)
    return title if len(title) <= TITLE_MAX else title[:TITLE_MAX - 1] + "…"


FORMAT_VERSION = 1          # 存檔格式版本。規則見 README「升級規則」：只能加新的，不能改舊檔的意義
FORMAT_FILE = "format.json"
ORDER_FILE = "order.json"   # 左欄拖拉排過的順序：{"2026-10-29": [3, 1, 2]}；沒排過的天照編號。舊版程式不讀它也不會壞


class NoteStore:
    def __init__(self, root: Path, encrypt: bool = True):
        self.root = Path(root)
        self.encrypt = encrypt and crypto.available()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / ATTACH_DIR).mkdir(exist_ok=True)
        (self.root / APP_SUBDIR).mkdir(exist_ok=True)
        self.newer_format_by: Optional[str] = None   # 資料是更新版程式寫的 → 主視窗提示一次
        self._title_cache: dict[Path, tuple[float, int, str]] = {}   # 檔 → (mtime, size, 標題)；左欄重畫不用每次解密
        self._text_cache: dict[Path, tuple[float, int, str]] = {}    # 檔 → (mtime, size, 全文)；搜尋內容不用每次解密
        self._index: Optional[dict[date, list[NoteRef]]] = None      # 日期 → 筆記清單；掃一次後只在自己寫入時更新
        self._index_sig: tuple = ()
        self._order: dict[str, list[int]] = self._load_order()       # 每天的顯示順序（左欄長按拖拉排的）
        self._check_format()
        self._migrate_single_files()
        self._clean_tmp()

    # ---- 索引（幾千張時每切一張都重掃 1500 個資料夾要 3 秒，所以掃一次記起來）----
    def _build_index(self) -> dict[date, list[NoteRef]]:
        idx: dict[date, list[NoteRef]] = {}
        for p in self.root.iterdir():
            d = _parse_day(p)
            if d is None:
                continue
            refs = self._scan_day(d)
            if refs:
                idx[d] = refs
        self._index = idx
        self._index_sig = self._signature()
        return idx

    def _signature(self) -> tuple:
        """外部有沒有動過：日期資料夾與裡面每個筆記檔的 mtime 都算（別的程式就地覆寫筆記也抓得到）。
        幾千張約 0.1 秒，只在視窗取得焦點時（最多每 5 秒一次）算。"""
        try:
            sig = []
            for p in self.root.iterdir():
                if _parse_day(p):
                    sig.append(p.stat().st_mtime)
                    sig.extend(f.stat().st_mtime for f in p.iterdir() if NOTE_FILE_RE.match(f.name))
            return (self.root.stat().st_mtime, tuple(sig))
        except OSError:
            return ()

    def index(self) -> dict[date, list[NoteRef]]:
        if self._index is None:
            self._build_index()
        return self._index

    def invalidate_caches(self) -> None:
        """標題快取與索引全部作廢（換語言時「（解不開）」這種翻譯過的字要重算）。"""
        self._title_cache.clear()
        self._index = None

    @contextmanager
    def bulk(self):
        """大量寫入（加密切換、清全部、匯入資料夾）時用：期間 _touch 不重掃，結束一次作廢整個索引。
        不這樣做的話一天 400 張要掃 400×400 次（量過：加密 400 張 60 秒 → 用 bulk 後幾秒）。"""
        self._bulk = True
        self._stale: set = set()
        try:
            yield
        finally:
            self._bulk = False
            self._stale = set()
            self._index = None

    def _touch(self, day: Optional[date]) -> None:
        """自己寫入後更新索引：只重掃那一天；day=None 整個作廢。
        bulk() 期間只把那天記成「過期」，list_notes 真的問到那天才重掃（匯入時 next_id 要看到剛寫的檔，編號才不會撞）。"""
        if self._index is None:
            return
        if getattr(self, "_bulk", False):
            if day is None:
                self._index = None
            else:
                self._stale.add(day)
            return
        if day is None:
            self._index = None
            return
        refs = self._scan_day(day)
        if refs:
            self._index[day] = refs
        else:
            self._index.pop(day, None)

    def refresh_if_changed(self) -> bool:
        """視窗重新取得焦點時呼叫：資料夾被別的程式動過就整個重掃。回傳有沒有重掃。"""
        if self._index is not None and self._signature() != self._index_sig:
            self._index = None
            return True
        return False

    def _clean_tmp(self) -> None:
        """上次寫到一半的 .tmp 清掉（正式檔一定完整，因為改名是最後一步）。"""
        for p in self.root.glob("*/*.tmp"):
            if _parse_day(p.parent) is None:     # 只清日期資料夾的；attachments／.app 裡的 .tmp 可能是使用者的檔
                continue
            try:
                p.unlink()
            except OSError:
                pass

    # ---- 格式版本 ----
    def _check_format(self) -> None:
        """讀 .app/format.json：資料若是更新的格式版本寫的，記下來讓 UI 提示；然後寫回自己的版本（只升不降）。"""
        import json
        from . import __version__
        p = self.root / APP_SUBDIR / FORMAT_FILE
        existing = 0
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    data = {}
                existing = int(data.get("format", 0))
                if existing > FORMAT_VERSION:
                    self.newer_format_by = str(data.get("written_by", "?"))
        except (OSError, ValueError, TypeError):
            existing = 0
        if existing <= FORMAT_VERSION:
            want = json.dumps({"format": FORMAT_VERSION, "written_by": __version__}, ensure_ascii=False, indent=2)
            try:
                if not p.is_file() or p.read_text(encoding="utf-8") != want:   # 內容一樣就不碰，備份工具才不會天天看到異動
                    p.write_text(want, encoding="utf-8")
            except OSError:
                pass

    # ---- 路徑 ----
    def day_dir(self, day: date) -> Path:
        return self.root / day.isoformat()

    def path_for(self, nid: NoteId) -> Path:
        """這張筆記現在的檔。兩種副檔名都在（切換加密時中途當機）就取最新改的那個；
        都沒有就回傳「存檔時會寫的那個」。"""
        base = self.day_dir(nid.day) / f"{nid.seq:03d}"
        found = [base.with_suffix(ext) for ext in (EXT_ENC, EXT_PLAIN) if base.with_suffix(ext).is_file()]
        if found:
            return max(found, key=_mtime_or_zero)        # is_file 到 stat 之間檔案可能剛被搬走，不能炸
        return base.with_suffix(EXT_ENC if self.encrypt else EXT_PLAIN)

    @property
    def attachments_dir(self) -> Path:
        return self.root / ATTACH_DIR

    # ---- 查 ----
    def list_days(self) -> list[date]:
        """有筆記的日期，新的在前。"""
        return sorted(self.index().keys(), reverse=True)

    def list_notes(self, day: date) -> list[NoteRef]:
        """某天的筆記，照編號。bulk() 期間被寫過的那天先重掃再回。"""
        idx = self.index()
        if day in getattr(self, "_stale", ()):
            self._stale.discard(day)
            refs = self._scan_day(day)
            if refs:
                idx[day] = refs
            else:
                idx.pop(day, None)
        return list(idx.get(day, []))

    def _scan_day(self, day: date) -> list[NoteRef]:
        d = self.day_dir(day)
        if not d.is_dir():
            return []
        seqs = sorted({int(m[1]) for f in d.iterdir() if f.is_file() and (m := NOTE_FILE_RE.match(f.name))})
        seqs = self._apply_order(day, seqs)
        return [NoteRef(nid, self._title_cached(nid)) for nid in (NoteId(day, s) for s in seqs)]

    # ---- 顯示順序（左欄長按拖拉）----
    def _load_order(self) -> dict[str, list[int]]:
        import json
        try:
            data = json.loads((self.root / APP_SUBDIR / ORDER_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {k: [int(x) for x in v if isinstance(x, int) or str(x).isdigit()]
                for k, v in data.items() if isinstance(v, list)}

    def _apply_order(self, day: date, seqs: list[int]) -> list[int]:
        """排過的照排過的順序；沒排進去的（新的一張）接在後面、照編號。檔名和編號都不動。"""
        order = self._order.get(day.isoformat())
        if not order:
            return seqs
        have = set(seqs)
        head = [s for s in order if s in have]
        return head + [s for s in seqs if s not in set(head)]

    def set_order(self, day: date, seqs: list[int]) -> None:
        """左欄拖拉放開時呼叫：記住這一天的顯示順序（.app/order.json），更新索引。"""
        import json
        self._order[day.isoformat()] = [int(s) for s in seqs]
        self._order = {k: v for k, v in self._order.items() if (self.root / k).is_dir()}   # 整天清掉的就不留
        _atomic_write_bytes(self.root / APP_SUBDIR / ORDER_FILE,
                            json.dumps(self._order, ensure_ascii=False, indent=1).encode("utf-8"))
        self._touch(day)

    def _title_cached(self, nid: NoteId) -> str:
        """標題快取：檔案的 (mtime, size) 沒變就不重讀、不重解密。幾千張也不會每次重畫都解密一遍。"""
        p = self.path_for(nid)
        try:
            st = p.stat()
        except OSError:
            return _(UNREADABLE_TITLE)
        key = (st.st_mtime, st.st_size)
        hit = self._title_cache.get(p)
        if hit and hit[:2] == key:
            return hit[2]
        text, ok = self.try_load(nid)
        if ok:
            title = title_of(text)
        else:                                    # 解不開 vs 較新版本格式：左欄跟內文的說明要一致
            title = _(NEWER_TITLE) if text == _(NEWER_FORMAT_TEXT) else _(UNREADABLE_TITLE)
        self._title_cache[p] = (key[0], key[1], title)
        return title

    def load(self, nid: NoteId) -> str:
        """讀一張。解不開（別台電腦／別的帳號加密的）會丟 crypto.CryptoError，呼叫端自己決定怎麼顯示。"""
        p = self.path_for(nid)
        try:
            st = p.stat()
        except OSError:                                   # 剛被刪掉／搬走：當成空的
            return ""
        hit = self._text_cache.get(p)
        if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
            return hit[2]
        text = _read_note_file(p)
        if len(self._text_cache) > 5000:
            self._text_cache.clear()
        self._text_cache[p] = (st.st_mtime, st.st_size, text)
        return text

    def try_load(self, nid: NoteId) -> tuple[str, bool]:
        """(文字, 讀得到嗎)。讀不到時文字是給人看的說明，不可拿去存。
        分兩種說法：檔頭是我們認得的版本但解不開 → 別台電腦／別的帳號；檔頭是更新的版本 → 請更新程式。"""
        try:
            return self.load(nid), True
        except crypto.NewerFormatError:
            return _(NEWER_FORMAT_TEXT), False
        except (crypto.CryptoError, UnicodeDecodeError, OSError):
            return _(UNREADABLE_TEXT), False

    def exists(self, nid: NoteId) -> bool:
        return self.path_for(nid).is_file()

    def next_id(self, day: date) -> NoteId:
        """這一天下一個還沒用的編號（不建檔；第一次 save 才建）。"""
        used = [r.id.seq for r in self.list_notes(day)]
        return NoteId(day, (max(used) + 1) if used else 1)

    def previous_day_with_notes(self, day: date) -> Optional[date]:
        for d in self.list_days():
            if d < day:
                return d
        return None

    def search(self, keyword: str) -> dict[date, list[NoteRef]]:
        """關鍵字在日期或內容裡的筆記，依日期分組（新的在前）。空字串＝全部。"""
        kw = keyword.strip().lower()
        out: dict[date, list[NoteRef]] = {}
        for d in self.list_days():
            refs = self.list_notes(d)
            if kw and not _date_hit(kw, d):
                refs = [r for r in refs if kw in self.try_load(r.id)[0].lower()]
            if refs:
                out[d] = refs
        return out

    # ---- 寫 ----
    def save(self, nid: NoteId, text: str) -> None:
        base = self.day_dir(nid.day) / f"{nid.seq:03d}"
        try:
            if text.strip() == "":
                for ext in (EXT_ENC, EXT_PLAIN):
                    self._remove_to_trash(base.with_suffix(ext))
                self._remove_day_dir_if_empty(nid.day)
                return
            base.parent.mkdir(parents=True, exist_ok=True)
            if self.encrypt:
                _atomic_write_bytes(base.with_suffix(EXT_ENC), crypto.encrypt_text(text))
                _unlink(base.with_suffix(EXT_PLAIN))
            else:
                _atomic_write_bytes(base.with_suffix(EXT_PLAIN), text.encode("utf-8"))
                _unlink(base.with_suffix(EXT_ENC))
        finally:
            self._touch(nid.day)

    def delete(self, nid: NoteId) -> None:
        self._remove_to_trash(self.path_for(nid))
        self._remove_day_dir_if_empty(nid.day)
        self._touch(nid.day)

    def delete_day(self, day: date) -> int:
        """清掉某一天所有筆記（搬垃圾桶）。回傳張數。"""
        refs = self.list_notes(day)
        for r in refs:
            self._remove_to_trash(self.path_for(r.id))
        self._remove_day_dir_if_empty(day)
        self._touch(day)
        return len(refs)

    def delete_all(self, progress: Optional[Callable[[int, int], None]] = None) -> int:
        """清掉全部筆記（搬垃圾桶）。附件不動。回傳張數。progress 同 set_encrypt。"""
        n, total = 0, self.count_notes()
        with self.bulk():
            for d in self.list_days():
                n += self.delete_day(d)
                if progress:
                    progress(n, total)
        return n

    def _remove_to_trash(self, p: Path) -> None:
        if not p.is_file():
            return
        trash = self.root / APP_SUBDIR / TRASH_DIR
        trash.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.move(str(p), str(trash / f"{p.parent.name}_{p.stem}_{stamp}{p.suffix}"))

    def _remove_day_dir_if_empty(self, day: date) -> None:
        d = self.day_dir(day)
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    # ---- 版本快照（像 Word 的「回到之前的版本」）----
    HISTORY_DIR = "history"
    HISTORY_KEEP = 30
    SNAPSHOT_MIN_GAP = 600           # 秒：同一張兩份快照至少隔這麼久（測試會改小）

    def restore_last_deleted(self) -> Optional[NoteId]:
        """垃圾桶裡最新的那個檔搬回原本的日期；編號被佔走就接在那天最後。沒東西回 None。
        垃圾桶檔名：<日期>_<編號>_<時間戳><副檔名>（_remove_to_trash 寫的）。"""
        trash = self.root / APP_SUBDIR / TRASH_DIR
        if not trash.is_dir():
            return None
        files = [p for p in trash.iterdir() if p.is_file() and p.suffix in (EXT_ENC, EXT_PLAIN)]
        if not files:
            return None
        p = max(files, key=lambda q: q.name.split("_", 2)[-1])   # 檔名尾巴是刪除時間戳；mtime 是原檔的，不準
        try:
            day_s, seq_s = p.name.split("_")[:2]
            day, seq = date.fromisoformat(day_s), int(seq_s)
        except (ValueError, IndexError):
            return None
        if day == TODO_DAY and self.list_notes(TODO_DAY):
            day = date.today()                   # 待辦事項只能有一張：已經有了，還原的放到今天
        if self.path_for(NoteId(day, seq)).is_file():
            seq = self.next_id(day).seq
        dest = self.day_dir(day) / f"{seq:03d}{p.suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dest))
        self._touch(day)
        return NoteId(day, seq)

    def _history_dir(self, nid: NoteId) -> Path:
        return self.root / APP_SUBDIR / self.HISTORY_DIR / f"{nid.day.isoformat()}_{nid.seq:03d}"

    def snapshot(self, nid: NoteId, text: str) -> bool:
        """存檔前呼叫：把「存之前的內容」留一份。內容沒變、或之前是空的就不留。回傳有沒有留。
        快照跟正式檔用同一種格式（加密就加密），檔名是時間。"""
        old, ok = self.try_load(nid)
        if not ok or old.strip() == "" or old == text:
            return False
        d = self._history_dir(nid)
        d.mkdir(parents=True, exist_ok=True)
        # 每次自動存（停 1.2 秒）都留的話 30 份幾分鐘就洗光；距上一份不到 SNAPSHOT_MIN_GAP 秒就不留（PM 審查）
        newest = max((p.stat().st_mtime for p in d.iterdir()), default=0.0)
        if datetime.now().timestamp() - newest < self.SNAPSHOT_MIN_GAP:
            return False
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        ext = EXT_ENC if self.encrypt else EXT_PLAIN
        data = crypto.encrypt_text(old) if self.encrypt else old.encode("utf-8")
        _atomic_write_bytes(d / f"{stamp}{ext}", data)
        for p in sorted(d.iterdir())[:-self.HISTORY_KEEP]:      # 只留最近 N 份
            p.unlink()
        return True

    def list_snapshots(self, nid: NoteId) -> list[tuple[datetime, Path]]:
        """(時間, 檔案)，新的在前。"""
        d = self._history_dir(nid)
        if not d.is_dir():
            return []
        out = []
        for p in d.iterdir():
            try:
                out.append((datetime.strptime(p.stem[:19], "%Y%m%d_%H%M%S_%f"), p))
            except ValueError:
                continue
        return sorted(out, key=lambda t: t[1].name, reverse=True)   # 檔名含毫秒，照檔名排最穩

    def load_snapshot(self, path: Path) -> str:
        return _read_note_file(Path(path))

    # ---- 加密開關與匯出 ----
    def count_notes(self) -> int:
        return sum(len(self.list_notes(d)) for d in self.list_days())

    def set_encrypt(self, on: bool, progress: Optional[Callable[[int, int], None]] = None) -> int:
        """切換加密並把現有筆記全部改存成新格式。回傳改寫張數。
        progress(做了幾張, 總共幾張)：主視窗拿來畫「處理中… 120／3120」（幾千張要好幾秒）。"""
        self.encrypt = on and crypto.available()
        n, total = 0, self.count_notes()
        with self.bulk():
            for d in self.list_days():
                for r in self.list_notes(d):
                    text, ok = self.try_load(r.id)
                    if ok:                       # 解不開的原檔不動
                        self.save(r.id, text)
                        n += 1
                    if progress:
                        progress(n, total)
        return n

    def export_note(self, nid: NoteId, dest_file: Path) -> None:
        """單張匯出成純文字 .md（給別人、貼到別的地方用）。"""
        text, ok = self.try_load(nid)
        if not ok:
            raise crypto.CryptoError(_("這張解不開，沒辦法匯出"))
        dest_file = Path(dest_file)
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        dest_file.write_text(text, encoding="utf-8", newline="\n")

    def import_text(self, day: date, text: str, default_title: str = "") -> NoteId:
        """一段文字變成那一天的新筆記（接在最後面編號）。沒有「# 標題」行時用 default_title 當標題。"""
        title, body = split_title(text)
        if not title and default_title:
            text = join_title(default_title, body)
        if day == TODO_DAY and self.list_notes(TODO_DAY):
            day = date.today()                   # 待辦事項只能有一張：已經有了，匯入的放到今天
        nid = self.next_id(day)
        self.save(nid, text)
        return nid

    def import_file(self, src: Path, day: date) -> Optional[NoteId]:
        """匯入一個 .md / .txt。編碼判斷在 decode_text（UTF-8／UTF-16／Big5／GBK／Shift-JIS…）。空檔回 None。"""
        src = Path(src)
        text = decode_text(src.read_bytes())
        text = text.replace("\r\n", "\n").replace("\r", "\n")   # 記事本的 CRLF 統一成 LF（read_bytes 不會自動換）
        if text.strip() == "":
            return None
        return self.import_text(day, text, default_title=None if src.stem.isdigit() else src.stem)   # 001.md 這種是匯出的編號，不是標題

    def import_folder(self, src: Path, today: Optional[date] = None,
                      progress: Optional[Callable[[int, int], None]] = None) -> tuple[int, int]:
        """匯入「匯出全部」產生的那種資料夾：src/YYYY-MM-DD/*.md 回到各自的日期；
        src 根目錄散的 *.md / *.txt 放到 today（預設今天；測試可指定）。加密的 .note 跳過（別台電腦的解不開）。
        回傳 (匯入張數, 跳過張數)。"""
        src = Path(src)
        today = today or date.today()
        done = skipped = 0
        if not src.is_dir():
            return 0, 0
        with self.bulk():
            for p in sorted(src.iterdir()):
                d = _parse_day(p)
                if d is not None:
                    for f in sorted(p.iterdir()):
                        if f.suffix.lower() in (".md", ".txt") and f.is_file():
                            done += self.import_file(f, d) is not None
                        elif f.suffix == EXT_ENC:
                            skipped += 1
                elif p.is_file() and p.suffix.lower() in (".md", ".txt"):
                    done += self.import_file(p, today) is not None
                if progress:
                    progress(done + skipped, 0)      # 總數事先不知道，0 = 只顯示做了幾張
        return done, skipped

    def export_plain(self, dest: Path, progress: Optional[Callable[[int, int], None]] = None) -> int:
        """全部筆記解密後以純文字 .md 複製到 dest/YYYY-MM-DD/NNN.md（換電腦、備份用）。progress 同 set_encrypt。"""
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)      # 沒半張也要有資料夾，匯入那邊才不會找不到
        n, total, seen = 0, self.count_notes(), 0
        for d in self.list_days():
            for r in self.list_notes(d):
                seen += 1
                if progress:
                    progress(seen, total)
                text, ok = self.try_load(r.id)
                if not ok:
                    continue
                out = dest / d.isoformat() / f"{r.id.seq:03d}{EXT_PLAIN}"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text, encoding="utf-8", newline="\n")
                n += 1
        return n

    # ---- 附件（圖片／PDF）----
    def add_attachment(self, src: Path) -> Path:
        """複製進 attachments/，回傳相對路徑（寫進筆記用）。同名加時間戳，不覆蓋。"""
        src = Path(src)
        safe = re.sub(r"[()\[\]]", "_", src.name)        # 括號會讓 [名稱](路徑) 寫法認不出來
        dst = self.attachments_dir / safe
        if dst.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst = self.attachments_dir / f"{Path(safe).stem}_{stamp}{Path(safe).suffix}"
        shutil.copy2(str(src), str(dst))
        return dst.relative_to(self.root)

    def add_image(self, img, prefix: str = "貼圖") -> Path:
        """PIL 影像（截圖）存成 attachments/貼圖_YYYYMMDD_HHMMSS.png，回相對路徑。"""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = self.attachments_dir / f"{prefix}_{stamp}.png"
        n = 1
        while dst.exists():
            n += 1
            dst = self.attachments_dir / f"{prefix}_{stamp}_{n}.png"
        img.save(str(dst), format="PNG")
        return dst.relative_to(self.root)

    def resolve(self, link: str) -> Path:
        """筆記裡的連結 → 絕對路徑。相對的以筆記資料夾為準。"""
        p = Path(link.strip().strip('"'))
        return p if p.is_absolute() else (self.root / p)

    # ---- 相容：早期版本是一天一個 YYYY-MM-DD.md 放在根目錄 ----
    def _migrate_single_files(self) -> None:
        self._index = None
        for p in list(self.root.iterdir()):
            if p.is_file() and p.suffix == EXT_PLAIN and DAY_DIR_RE.match(p.stem):
                d = date.fromisoformat(p.stem)
                target = self.day_dir(d) / f"001{EXT_PLAIN}"
                if not target.exists() and not target.with_suffix(EXT_ENC).exists():
                    target.parent.mkdir(exist_ok=True)
                    shutil.move(str(p), str(target))


def _date_hit(kw: str, d: date) -> bool:
    """關鍵字算不算「在找日期」：要像日期的一段（有 - 或 /，或至少 4 個字），
    不然打「10」會把整個 10 月全列出來。"""
    forms = (d.isoformat(), f"{d.year}/{d.month:02d}/{d.day:02d}", f"{d.month}/{d.day}", f"{d.month:02d}/{d.day:02d}")
    if any(c in kw for c in "-/"):
        return any(kw in f for f in forms)
    return len(kw) >= 4 and kw in d.isoformat()


def _parse_day(p: Path) -> Optional[date]:
    if not p.is_dir():
        return None
    m = DAY_DIR_RE.match(p.name)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


LANG_ENCODING = {"zh_TW": "cp950", "zh_CN": "cp936", "ja": "cp932", "ko": "euc-kr"}   # 畫面語言 → 那個語言的舊編碼


def decode_text(raw: bytes, prefer: Optional[str] = None) -> str:
    """位元組 → 文字，不要出現亂碼。順序：UTF-8（含 BOM）→ UTF-16（有 BOM 才算）→ prefer（呼叫端給；
    程式用「畫面語言」對應的舊編碼，台灣 cp950、簡中 cp936、日文 cp932）→ 這台的語系編碼 → 其他幾個常見的。
    Big5／GBK／Shift-JIS 互相都「解得開」但會是亂碼，所以要靠 prefer 和語系先猜，再用 _looks_like_text 擋掉明顯不是文字的。
    全部不行才丟 UnicodeDecodeError（呼叫端提示「讀不了」）。程式自己存檔一律 UTF-8；這裡是給別的程式寫的 txt／手改的 .md 用的。"""
    try:
        text = raw.decode("utf-8-sig")
        if _looks_like_text(text):
            return text
        raise UnicodeDecodeError("text", raw[:16], 0, 1, "control characters: not a text file")
    except UnicodeDecodeError as e:
        if "control characters" in str(e):
            raise
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") and len(raw) % 2 == 0:
        try:
            text = raw.decode("utf-16")
            if _looks_like_text(text):
                return text
        except UnicodeDecodeError:
            pass
    import locale
    if prefer is None:
        from .i18n import current
        prefer = LANG_ENCODING.get(current())
    tried = []
    for enc in (prefer, locale.getpreferredencoding(False), "cp950", "cp936", "cp932", "euc-kr"):
        enc = (enc or "").lower()
        if not enc or enc in tried or enc.replace("-", "") in ("utf8", "utf8sig"):
            continue
        tried.append(enc)
        try:
            text = raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
        if _looks_like_text(text):           # Big5／GBK 幾乎什麼位元組都解得開，解出來是亂碼也算「成功」，要再驗一次
            return text
    raise UnicodeDecodeError("text", raw[:16], 0, 1, "not UTF-8 / UTF-16 / " + "/".join(tried))


_CONTROL = {chr(c) for c in range(0x20)} - {"\t", "\n", "\r"}


def _looks_like_text(s: str) -> bool:
    """舊編碼解出來的字是不是真的文字：有控制字元（圖檔、exe 一定有）就不是；私用區或罕見區字太多也不是。"""
    if any(ch in _CONTROL or ch == "\x7f" for ch in s):
        return False
    if not s:
        return True
    odd = sum(1 for ch in s if 0xE000 <= ord(ch) <= 0xF8FF or ord(ch) == 0xFFFD)
    return odd / len(s) < 0.01


def _read_note_file(p: Path) -> str:
    """副檔名說了算：.note 一定要是加密格式，.md 是純文字（程式存的是 UTF-8；手改成別的編碼也盡量讀，下次存檔就變 UTF-8）。
    0 byte 的 .note（斷電半截）或開頭不對 → CryptoError（呼叫端顯示「解不開」並保留原檔，不當成空白）。"""
    data = p.read_bytes()
    if p.suffix == EXT_ENC:
        if data.startswith(crypto.MAGIC_FAMILY) and not crypto.is_encrypted(data):
            raise crypto.NewerFormatError(f"{p.name} 是較新版本的格式（檔頭 {data[:7]!r}）")
        if not crypto.is_encrypted(data):
            raise crypto.CryptoError(f"{p.name} 不是完整的加密檔（{len(data)} bytes）")
        return crypto.decrypt_text(data)
    return decode_text(data).replace("\r\n", "\n").replace("\r", "\n")


def _mtime_or_zero(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def _atomic_write_bytes(p: Path, data: bytes) -> None:
    """先寫 .tmp、fsync、再改名蓋過去：中途當機只會留下 .tmp（啟動時會清），不會留半截正式檔。"""
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


def _unlink(p: Path) -> None:
    if p.is_file():
        p.unlink()


def yesterday(day: date) -> date:
    return day - timedelta(days=1)


def tomorrow(day: date) -> date:
    if day >= TODO_DAY - timedelta(days=1):      # 待辦事項（9999-12-31）沒有「後一天」
        return date.today()
    return day + timedelta(days=1)

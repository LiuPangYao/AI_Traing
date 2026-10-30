# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""文字框 + 自動存檔 + 連結 + 狀態列。

- 打字停 1.2 秒就呼叫 on_save(text)；切筆記或關視窗前主視窗會呼叫 flush() 強制存。
- Ctrl + 滾輪 → on_zoom(+1 / -1)，字體大小由主視窗管（它要寫設定檔）。
- 連結：網址、Windows 路徑、[名稱](附件路徑) 自動畫底線；Ctrl + 點 → on_open_link(目標)。
  「什麼算連結」的規則在 links.py（可單元測試），這裡只負責畫底線和接點擊。
- 圖片：連結指到圖檔（png/jpg/gif/bmp/webp）就把圖直接畫在那一行後面。**檔案裡還是只有那行文字**，
  圖是顯示時從 attachments 讀出來的（tk 的 image_create 不會進 get() 的文字）。
  Ctrl+V 剪貼簿是圖（截圖）→ 存成 attachments/貼圖_時間.png 並插一行連結 → 圖立刻出現。
- 標記：==重點==、!!紅字!!、**粗體**、*斜體* 照記號上色；``` 區塊等寬深底加「複製」按鈕；「- [ ] 」打勾清單。
  規則在 markup.py（可單元測試），這裡只負責上色、放按鈕、把選取的字包上記號（格式列的按鈕／Ctrl+B 等）。
- 記號藏起來：游標不在那一行時，記號（== !! ** *）、連結的 [ ](路徑)、``` 圍欄、- [ ] 都用 tk 的 elide 藏掉，
  畫面只剩上色後的字；游標移到那一行就全部現形可以改。檔案內容不變。
"""
from __future__ import annotations

import re
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk

from ..i18n import _
from .. import applog, imefix, links, listing, markup
from ..storage import join_title, split_title
from . import theme as T

AUTOSAVE_MS = 1200
HIGHLIGHT_MS = 300
LINK_TAG = "link"
IMG_TAG = "img"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
IMG_MAX_H = 360
IMG_MIN_W = 60
WIDTH_ATTR_RE = re.compile(r"\)\{w=(\d+)\}")      # [名稱](路徑){w=400}：使用者拉過的寬度
ELIDE_TAG = "elide"          # 長連結中段藏起來（tk 的 elide），檔案內容不變
ELL_TAG = "ell"              # 藏起來的位置放一個「…」小標籤
LINK_SHOW_MAX = 48           # 連結顯示超過這麼多字才折
MARKER_TAG = "marker"        # 記號本身（== !! ** * 和 ```）：游標在那行時淡灰，不在時藏起來（HIDE_TAG）
HIDE_TAG = "hide"            # 藏起來的記號（elide）；只加在游標不在的行
CODE_TAG = "code"            # ``` 區塊：等寬、深底
COPY_TAG = "copybtn"         # 區塊開頭那行尾巴放的「複製」小按鈕（跟「…」一樣是嵌進去的 widget，重畫前要先拿掉）
LABEL_TAG = "codelabel"      # 區塊開頭那行最前面的「指令」小標籤（嵌進去的 widget）
CHECK_TAG = "checkbox"       # 打勾清單行首的 ☐／☑（嵌進去的 widget，點了就改文字）
DONE_TAG = "done"            # 打勾完成的那行：劃掉、淡灰
TAG_TAG = "hashtag"          # #標籤：主色字，Ctrl+點 → 主視窗拿去搜尋
STYLE_TAGS = {"mark": "mark", "red": "red", "bold": "bold", "italic": "italic"}   # markup.KINDS → tag 名
MARK_BG, RED_FG, CODE_BG, CODE_FG, CODE_MUTED = T.MARK_BG, T.RED_FG, T.CODE_BG, T.CODE_FG, T.CODE_MUTED   # 色碼只在 theme.py
WIDGET_TAGS = (ELL_TAG, COPY_TAG, LABEL_TAG, CHECK_TAG)   # 嵌進文字框的小元件：重畫前全部拿掉
CHECK_GLYPH = {False: "☐", True: "☑"}
CURSOR_MOVE_MS = 60          # 游標換行後多久重畫（記號要現形）；打字是 HIGHLIGHT_MS
MONO_FAMILY = __import__("personalnote.platform_", fromlist=["x"]).mono_font_family()   # Consolas／DejaVu Sans Mono
LINK_HEAD, LINK_TAIL = 26, 16


from . import anim
_blend = anim.blend                      # 動畫（時間、曲線、混色）統一在 anim.py


def _py_to_tk_col(line: str, col: int) -> int:
    """Python 算字元、Tk 把 emoji 這種非 BMP 字算成 2 格，要換算，不然底線會偏。"""
    return len(line[:col].encode("utf-16-le")) // 2


def _tk_to_py_col(line: str, tk_col: int) -> int:
    units = 0
    for i, ch in enumerate(line):
        if units >= tk_col:
            return i
        units += len(ch.encode("utf-16-le")) // 2
    return len(line)


_BASE_CACHE: dict = {}          # (路徑, mtime) → 先縮到最多 1600 寬的 PIL 影像；超大圖不用每次重讀
_BASE_MAX_W = 1600
_BASE_CACHE_MAX = 40
_BASE_CACHE_BYTES = 64 * 1024 * 1024    # 總量上限（以前只限張數，40 張大圖可到 200 MB；QA 審查）
_BASE_CACHE_SIZE: dict = {}             # key → 這張佔的位元組


def _base_image(path: Path):
    """讀圖一次並縮到合理大小存起來（8000×6000 的截圖每次縮放都重讀太慢）。"""
    from PIL import Image
    key = (str(path), path.stat().st_mtime)
    hit = _BASE_CACHE.get(key)
    if hit is not None:
        return hit
    img = Image.open(path)
    img.draft("RGB", (_BASE_MAX_W, _BASE_MAX_W))          # JPEG 可以直接用低解析度解碼
    img.load()
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    w, h = img.size
    if w > _BASE_MAX_W:
        img = img.resize((_BASE_MAX_W, max(1, int(h * _BASE_MAX_W / w))), Image.LANCZOS)
    size = img.width * img.height * len(img.getbands())
    while _BASE_CACHE and (len(_BASE_CACHE) >= _BASE_CACHE_MAX or sum(_BASE_CACHE_SIZE.values()) + size > _BASE_CACHE_BYTES):
        old = next(iter(_BASE_CACHE))                      # 最早放進來的先丟
        _BASE_CACHE.pop(old); _BASE_CACHE_SIZE.pop(old, None)
    _BASE_CACHE[key] = (img, (w, h))                       # 也記原始尺寸，寬度換算用
    _BASE_CACHE_SIZE[key] = size
    return _BASE_CACHE[key]


def _load_photo(path: Path, max_w: int, want_w: Optional[int] = None):
    """讀圖，回 tk 用的 PhotoImage。want_w = 使用者拉過的寬度（等比例）；沒有就縮到最多 max_w 寬 / IMG_MAX_H 高。
    任何情況都不超過 max_w（視窗寬）。讀不了回 None。"""
    try:
        from PIL import Image, ImageTk
        img, (ow, oh) = _base_image(path)
        bw, bh = img.size
        if want_w:
            target_w = min(max(IMG_MIN_W, want_w), max_w)
        else:
            target_w = int(min(ow, max_w, ow * IMG_MAX_H / oh))
        scale = target_w / bw
        if abs(scale - 1.0) > 1e-3:
            img = img.resize((max(1, int(bw * scale)), max(1, int(bh * scale))), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        applog.exception("讀圖失敗 %s", path)
        return None


_tip = T.tooltip                 # 小提示：跟主視窗工具列同一套（theme.tooltip）


class Editor(ctk.CTkFrame):
    def __init__(self, master, font_family: str, font_size: int,
                 on_save: Callable[[str], None], on_zoom: Callable[[int], None],
                 on_open_link: Callable[[str], None],
                 resolve_link: Optional[Callable[[str], Path]] = None,
                 on_paste_image: Optional[Callable[[object], Optional[str]]] = None,
                 format_bar: bool = False,
                 on_format_toggle: Optional[Callable[[bool], None]] = None,
                 on_tag: Optional[Callable[[str], None]] = None,
                 on_titles: Optional[Callable[[], list[str]]] = None):
        """resolve_link：連結字串 → 絕對路徑（主視窗給 store.resolve）；沒有就不顯示圖。
        on_paste_image(PIL 影像) → 要插進筆記的那行文字（主視窗負責存成附件）；None = 不處理貼圖。
        format_bar：格式列一開始展開嗎（預設收起，Peter：不常改）；on_format_toggle(展開了嗎) 讓主視窗記到 state.json。"""
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._on_save = on_save
        self._on_zoom = on_zoom
        self._on_open_link = on_open_link
        self._resolve_link = resolve_link
        self._on_paste_image = on_paste_image
        self._on_tag = on_tag                   # Ctrl+點 #標籤 → on_tag("#標籤")（主視窗拿去搜尋）
        self._on_titles = on_titles             # [[ 自動完成：回所有筆記標題（主視窗給）
        self._ac: Optional[dict] = None         # 自動完成的小視窗狀態（_maybe_autocomplete）
        self._photos: list = []                 # 畫在筆記裡的圖（要留著參考，不然 tk 會把圖收掉）
        self._images_state: list = []           # 目前畫了哪些 (行, 路徑, 檔案mtime)；沒變就不重畫
        self._dirty = False
        self._save_timer: Optional[str] = None
        self._hl_timer: Optional[str] = None
        self._loading = False
        self.read_only = False
        self.last_error = ""

        # 標題欄：就是檔案的第一行。左欄顯示它；留空的話左欄拿內文第一行（去掉 1. / - 標記）
        # 大字、透明底、只留一圈細框（Peter 2026-10-30：全透明會不知道標題可以改）；空的時候有淡灰的提示字
        self._title_font = ctk.CTkFont(family=font_family, size=font_size + 6, weight="bold")
        self.title = ctk.CTkEntry(self, font=self._title_font, placeholder_text=_("標題（點這裡改）"),
                                  corner_radius=T.RADIUS, fg_color="transparent", border_width=1,
                                  border_color=T.TEXT_MUTED, height=40)
        self.title.grid(row=0, column=0, sticky="ew", padx=4, pady=(2, 10))      # 標題、格式列、內文之間留白（Peter：很擠）
        self.title.bind("<KeyRelease>", self._on_title_changed)
        self.title.bind("<Return>", lambda _e: (self.text.focus_set(), "break")[1])
        self.title.bind("<Control-MouseWheel>", self._on_ctrl_wheel)
        self.title.bind("<FocusOut>", lambda _e: self.flush())
        imefix.bind(self.title._entry)          # 注音標點修正（見 imefix.py）

        # 格式列：選字後按一下就包上記號；「指令」插一個 ``` 區塊。預設收起，左邊「▸ 格式」點開
        self._on_format_toggle = on_format_toggle
        bar_row = ctk.CTkFrame(self, fg_color="transparent")
        bar_row.grid(row=1, column=0, sticky="w", padx=4, pady=(0, 8))
        # 這顆要夠明顯（Peter：淡灰小字一般人不知道能按）：有框、正常字色、標籤寫「格式 ▸」
        self._fmt_toggle = ctk.CTkButton(bar_row, text=_("格式 ▸"), width=64, height=26, corner_radius=6, font=T.ui_font(11, "bold"),
                                         fg_color="transparent", border_width=1, border_color=T.ACCENT, hover_color=T.ROW_HOVER,
                                         text_color=T.ACCENT, command=self.toggle_format_bar)
        self._fmt_toggle.pack(side="left", padx=(0, 4))
        _tip(self._fmt_toggle, _("展開／收起格式列（上一步、下一步、重點、紅字、粗體、斜體、指令）"))
        bar = ctk.CTkFrame(bar_row, fg_color="transparent")
        self._fmt_bar = bar
        self._fmt_visible = False
        for text, cmd, tip in ((_("上一步"), self.undo, _("上一步（Ctrl+Z）")),
                               (_("下一步"), self.redo, _("下一步（Ctrl+Y）")),
                               ("│", None, ""),
                               (_("重點"), lambda: self.apply_style("mark"), _("黃底（Ctrl+H）")),
                               (_("紅字"), lambda: self.apply_style("red"), _("紅字（Ctrl+Shift+H）")),
                               (_("粗體"), lambda: self.apply_style("bold"), _("粗體（Ctrl+B）")),
                               (_("斜體"), lambda: self.apply_style("italic"), _("斜體（Ctrl+I）")),
                               (_("打勾"), self.insert_checkbox, _("這一行變成打勾清單（- [ ] ），點方框打勾")),
                               (_("指令"), self.insert_code_block, _("插一段可一鍵複製的指令（Ctrl+Shift+C）"))):
            if cmd is None:                          # 分隔線
                ctk.CTkLabel(bar, text=text, font=T.ui_font(10), text_color=T.TEXT_MUTED, width=8).pack(side="left", padx=1)
                continue
            b = ctk.CTkButton(bar, text=text, width=40, height=24, corner_radius=6, font=T.ui_font(10),
                              fg_color="transparent", hover_color=T.ROW_HOVER, text_color=T.TEXT_MUTED, command=cmd)
            b.pack(side="left", padx=(0, 2))
            _tip(b, tip)
        self.set_format_bar(format_bar, notify=False)

        self._font = ctk.CTkFont(family=font_family, size=font_size)
        self._font_bold = ctk.CTkFont(family=font_family, size=font_size, weight="bold")
        self._font_italic = ctk.CTkFont(family=font_family, size=font_size, slant="italic")
        self._font_mono = ctk.CTkFont(family=MONO_FAMILY, size=font_size)
        self.text = ctk.CTkTextbox(
            self, font=self._font, wrap="word", corner_radius=T.RADIUS,
            fg_color=T.EDITOR_BG, text_color=T.TEXT, border_width=1, border_color=T.EDITOR_BORDER,
            undo=True, maxundo=-1, padx=14, pady=12,
            spacing1=4, spacing2=3, spacing3=6,     # 行距鬆一點（Peter：擠在一起很呆板）；spacing2 是折行的行距
        )
        self.text.grid(row=2, column=0, sticky="nsew")
        # tag 建立順序＝優先順序（後建的蓋前面的）：區塊底色最低，記號灰字、連結色在上面
        self.text.tag_config(CODE_TAG)
        self.text.tag_config(STYLE_TAGS["mark"])
        self.text.tag_config(STYLE_TAGS["red"])
        self.text.tag_config(STYLE_TAGS["bold"])
        self.text.tag_config(STYLE_TAGS["italic"])
        self.text.tag_config(MARKER_TAG)
        self.text.tag_config(DONE_TAG, overstrike=True)
        self.text.tag_config(TAG_TAG)
        self.text.tag_config(LINK_TAG, underline=True)
        self.text.tag_config(HIDE_TAG, elide=True)
        self._apply_tag_fonts()
        self._apply_link_color()
        self._key_seqs: list = []                 # bind_keys 綁過的 (widget, 序列)；存檔、重點、粗體…的鍵由主視窗照快捷鍵表來綁
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<Control-MouseWheel>", self._on_ctrl_wheel)
        self.text.bind("<Control-Button-1>", self._on_ctrl_click)
        self.text.bind("<Return>", self._on_return)
        self.text.bind("<Tab>", lambda _e: self._on_tab(False))              # 清單行：縮排子項
        for seq in ("<Shift-Tab>", "<ISO_Left_Tab>"):                       # Windows／X11 的 Shift+Tab 名字不同
            try:
                self.text.bind(seq, lambda _e: self._on_tab(True))
            except Exception:
                pass
        self.text.bind("<FocusIn>", lambda _e: self._sync_ime_font(), add="+")   # 輸入法選字的字跟內文一樣大
        self.title.bind("<FocusIn>", lambda _e: self._sync_ime_font(), add="+")
        self.text.bind("<FocusOut>", lambda _e: self.flush())   # 切到別的視窗就先存，關機也少丟字
        self.text.bind("<FocusOut>", lambda _e: self.after(120, self._ac_close_if_unfocused), add="+")   # 點清單時先別關
        self.text.bind("<KeyRelease>", self._maybe_autocomplete, add="+")   # 打 [[ 跳出標題清單（Peter：不然不知道要打什麼）
        self.text.bind("<Button-1>", lambda _e: self._ac_close(), add="+")
        self.text.bind("<Control-v>", self._on_paste)            # 剪貼簿是圖就存成附件並顯示
        self.text.bind("<Button-1>", self._on_click)             # 點圖 → 出現縮放把手
        self.text.bind("<KeyPress>", lambda _e: (self._hide_handle(), self._hint.place_forget()), add="+")
        # 空筆記的提示（Peter：整片白很呆板）：內文空的才顯示，一打字就消失
        self._hint = tk.Label(self.text._textbox, text=_("上面那格是標題，點一下就能改。\n直接打字就會自動存。\nCtrl+V 貼截圖、把 .txt／.md 拖進來也可以。"),
                              font=(T.UI_FONT_FAMILY, 11), justify="left", bd=0,
                              fg=self._muted_color(), bg=self.text._textbox.cget("background"))
        self.text.bind("<Motion>", self._on_motion)              # 滑鼠停在連結上 → 顯示完整路徑
        self.text.bind("<Leave>", lambda _e: self._hide_tip())
        for seq in ("<KeyRelease-Left>", "<KeyRelease-Right>", "<KeyRelease-Up>", "<KeyRelease-Down>",
                    "<KeyRelease-Home>", "<KeyRelease-End>", "<KeyRelease-Prior>", "<KeyRelease-Next>",
                    "<ButtonRelease-1>"):
            self.text.bind(seq, lambda _e: self._schedule_refresh(CURSOR_MOVE_MS), add="+")   # 游標換行：藏起來的記號要現形
        self._image_lines: dict = {}
        self._selected_line = None
        self._ell_widgets: list = []
        self._tip = None
        self._tip_target = None
        self.text.bind("<Configure>", lambda _e: self._schedule_refresh())  # 視窗變寬變窄，圖跟著縮放
        imefix.bind(self.text._textbox)        # 注音標點修正（見 imefix.py）
        # 右鍵選單：剪下／複製／貼上／全選（貼上走 Ctrl+V 同一條路，剪貼簿是截圖也會變成圖）
        self.text._textbox.bind("<Button-3>", lambda e: self._context_menu(e, self.text._textbox, is_body=True))
        self.title._entry.bind("<Button-3>", lambda e: self._context_menu(e, self.title._entry, is_body=False))

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=3, column=0, sticky="ew", pady=(6, 0))            # 貼近視窗底邊一點（Peter 要的）
        foot.grid_columnconfigure(1, weight=1)
        self.counter = ctk.CTkLabel(foot, text="", font=T.ui_font(11), text_color=T.TEXT_MUTED, anchor="w")
        self.counter.grid(row=0, column=0, sticky="w")                  # 左：N 行 · N 字（打字停 0.3 秒更新）
        self.status = ctk.CTkLabel(foot, text="", font=T.ui_font(11), text_color=T.TEXT_MUTED, anchor="e")
        self.status.grid(row=0, column=1, sticky="ew")                  # 右：已儲存／輸入中…（已儲存 2.5 秒後淡出）
        self._fade_job: Optional[str] = None

    # ---- 主視窗用 ----
    def set_text(self, text: str, read_only: bool = False) -> None:
        """整份筆記文字進來：第一行是標題，其餘是內文（格式見 storage.split_title）。
        read_only=True 用在解不開的筆記：顯示說明，不給改、不會存。"""
        self.read_only = read_only
        self.text.configure(state="normal")
        self.title.configure(state="normal")
        title, body = split_title(text)
        self._loading = True
        self.title.delete(0, "end")
        if title:                              # 空字串不 insert，不然 placeholder 不會出現
            self.title.insert(0, title)
        self.text.delete("1.0", "end")
        self.text.insert("1.0", body)
        self.text.edit_reset()
        self.text.edit_modified(False)
        self._loading = False
        self._dirty = False
        if self._save_timer is not None:        # 上一張排程中的存檔作廢（flush 該做的，呼叫端已經做了）
            self.after_cancel(self._save_timer)
            self._save_timer = None
        self.status.configure(text=_("唯讀") if read_only else "")
        self._images_state = []                 # 換了一張筆記，圖全部重畫
        self._photos = []
        self._highlight_links()
        if read_only:
            self.text.configure(state="disabled")
            self.title.configure(state="disabled")

    def get_text(self) -> str:
        """整份筆記文字：標題行 + 內文。"""
        return join_title(self.title.get(), self.text.get("1.0", "end-1c"))

    def set_default_title(self, title: str) -> None:
        """新筆記預設標題（例如「筆記3」）：填進去、整個反白、算成有改（會自動存），直接打字就蓋掉。"""
        if self.read_only:
            return
        self.title.delete(0, "end")
        self.title.insert(0, title)
        self.title.focus_set()
        self.title._entry.select_range(0, "end")
        self.title._entry.icursor("end")
        self._mark_dirty()

    def insert_at_cursor(self, s: str) -> None:
        self.text.insert("insert", s)
        self.text.focus_set()

    def insert_own_line(self, s: str) -> None:
        """插在游標處，但一定自己一行：游標前面那行有字就先換行（附件連結黏在字後面會被當成同一段）。"""
        if self.text._textbox.get("insert linestart", "insert").strip():
            s = "\n" + s
        self.insert_at_cursor(s)

    def set_font_size(self, size: int) -> None:
        self._font.configure(size=size)
        self._title_font.configure(size=size + 6)
        for f in (self._font_bold, self._font_italic, self._font_mono):
            f.configure(size=size)
        self._apply_tag_fonts()
        self._sync_ime_font()

    def _sync_ime_font(self) -> None:
        """Windows 輸入法的組字視窗（注音選字）用跟內文／標題一樣的字型與大小。
        大小從 Tk 元件「實際」在用的字型讀（CustomTkinter 已把縮放算進去），再換成像素：正數是 point（×每 point 的像素），負數本身就是像素。"""
        import tkinter.font as tkfont
        from .. import platform_
        for widget in (self.text._textbox, self.title._entry):
            try:
                f = tkfont.Font(root=widget, font=widget.cget("font"))
                size = f.actual("size")
                px = -size if size < 0 else size * float(widget.winfo_fpixels("1p"))
                platform_.set_ime_font(widget, f.actual("family"), px)
            except Exception:
                pass

    # ---- [[ 自動完成 ----
    AC_MAX = 8

    def _maybe_autocomplete(self, e=None) -> None:
        """每次放開鍵：游標前這一行若有還沒關上的 [[，就列出符合的標題；沒有就關掉清單。"""
        if self._on_titles is None or self.read_only:
            return
        if e is not None and e.keysym in ("Up", "Down", "Return", "Tab", "Escape", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return
        tk_text = self.text._textbox
        line_no = int(tk_text.index("insert").split(".")[0])
        before = tk_text.get(f"{line_no}.0", "insert")
        m = re.search(r"\[\[([^\[\]\n]*)$", before)
        if not m:
            self._ac_close()
            return
        query = m.group(1).strip().lower()
        titles = [t for t in self._on_titles() if query in t.lower()][: self.AC_MAX]
        if not titles:
            self._ac_close()
            return
        start = f"{line_no}.{_py_to_tk_col(before, m.start(1))}"    # 查詢字（[[ 之後）的起點
        self._ac_show(titles, start)

    def _ac_show(self, titles: list[str], start: str) -> None:
        tk_text = self.text._textbox
        if self._ac is None:
            win = tk.Toplevel(self)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            dark = self._dark()
            bg = T.CARD_BG[1] if dark else T.CARD_BG[0]
            fg = T.TEXT[1] if dark else T.TEXT[0]
            lb = tk.Listbox(win, font=(T.UI_FONT_FAMILY, 11), bg=bg, fg=fg, bd=0, highlightthickness=1,
                            highlightbackground=T.DIVIDER[1] if dark else T.DIVIDER[0], activestyle="none",
                            selectbackground=T.ACCENT[1] if dark else T.ACCENT[0], selectforeground=T.ON_ACCENT, width=36)
            lb.pack()

            def on_press(e):                     # 按下就填（ButtonRelease 時內文框已失焦、清單早被關掉：Peter 回報點了沒反應）
                i = lb.nearest(e.y)
                if i >= 0:
                    lb.selection_clear(0, "end"); lb.selection_set(i); lb.activate(i)
                    self._ac_choose()
                return "break"                   # 不讓焦點跑到清單
            lb.bind("<Button-1>", on_press)
            binds = [(seq, tk_text.bind(seq, fn)) for seq, fn in (
                ("<Down>", lambda _e: self._ac_move(1)), ("<Up>", lambda _e: self._ac_move(-1)),
                ("<Return>", lambda _e: self._ac_choose()), ("<Tab>", lambda _e: self._ac_choose()),
                ("<Escape>", lambda _e: self._ac_close()))]
            self._ac = {"win": win, "list": lb, "binds": binds}
        ac = self._ac
        ac["items"], ac["start"] = titles, start
        lb = ac["list"]
        lb.delete(0, "end")
        for t in titles:
            lb.insert("end", "  " + t)
        lb.configure(height=len(titles))
        lb.selection_clear(0, "end"); lb.selection_set(0); lb.activate(0)
        bbox = tk_text.bbox("insert")
        x = tk_text.winfo_rootx() + (bbox[0] if bbox else 0)
        y = tk_text.winfo_rooty() + ((bbox[1] + bbox[3]) if bbox else 20) + 2
        ac["win"].geometry(f"+{x}+{y}")
        ac["win"].deiconify(); ac["win"].lift()

    def _ac_move(self, d: int) -> str:
        ac = self._ac
        if ac is None:
            return ""
        lb = ac["list"]
        cur = lb.curselection()
        i = (cur[0] if cur else 0) + d
        i = max(0, min(lb.size() - 1, i))
        lb.selection_clear(0, "end"); lb.selection_set(i); lb.activate(i); lb.see(i)
        return "break"

    def _ac_choose(self) -> str:
        """把選到的標題填進去：[[查詢字 → [[標題]]。"""
        ac = self._ac
        if ac is None:
            return ""
        lb = ac["list"]
        cur = lb.curselection()
        title = ac["items"][cur[0] if cur else 0]
        tk_text = self.text._textbox
        tk_text.delete(ac["start"], "insert")
        tk_text.insert(ac["start"], title + "]]")
        self._ac_close()
        self._mark_dirty()
        return "break"

    def _ac_close_if_unfocused(self) -> None:
        """內文框失焦 0.12 秒後：焦點不在清單上才關（點清單本身不算離開）。"""
        ac = self._ac
        if ac is None:
            return
        try:
            f = self.focus_get()
        except Exception:
            f = None
        if f is not ac["list"]:
            self._ac_close()

    def _ac_close(self) -> str:
        ac = self._ac
        if ac is None:
            return ""
        self._ac = None
        tk_text = self.text._textbox
        for seq, fid in ac["binds"]:
            try:
                tk_text.unbind(seq, fid)
            except Exception:
                pass
        try:
            ac["win"].destroy()
        except Exception:
            pass
        return "break"

    def _on_tab(self, out: bool) -> Optional[str]:
        """清單行（1.／-／- [ ]）按 Tab 縮排兩格、Shift+Tab 退回；不是清單行就照 tk 預設。"""
        from .. import listing
        tk_text = self.text._textbox
        line_no = int(tk_text.index("insert").split(".")[0])
        line = tk_text.get(f"{line_no}.0", f"{line_no}.end")
        if listing.next_marker(line) is None and not listing.CHECK_RE.match(line):
            return None
        if out:
            n = len(line) - len(line.lstrip(" "))
            if n:
                tk_text.delete(f"{line_no}.0", f"{line_no}.{min(2, n)}")
        else:
            tk_text.insert(f"{line_no}.0", "  ")
        return "break"

    def _apply_tag_fonts(self) -> None:
        """粗體／斜體／等寬的 tag 字型。CTkTextbox.tag_config 不准給 font（它怕跟 DPI 縮放打架），
        所以直接設在裡面的 tk Text 上，字型先經過它的縮放換算，125% 螢幕才不會比內文小。"""
        raw = self.text._textbox
        for tag, font in ((STYLE_TAGS["bold"], self._font_bold), (STYLE_TAGS["italic"], self._font_italic),
                          (CODE_TAG, self._font_mono)):
            raw.tag_config(tag, font=self.text._apply_font_scaling(font))

    # ---- 格式列展開／收起 ----
    def set_format_bar(self, visible: bool, notify: bool = True) -> None:
        self._fmt_visible = visible
        if visible:
            self._fmt_bar.pack(side="left")
        else:
            self._fmt_bar.pack_forget()
        self._fmt_toggle.configure(text=_("格式 ▾") if visible else _("格式 ▸"))
        if notify and self._on_format_toggle is not None:
            self._on_format_toggle(visible)

    def toggle_format_bar(self) -> None:
        self.set_format_bar(not self._fmt_visible)

    # ---- 標記（格式列按鈕、Ctrl+B 等）----
    def apply_style(self, kind: str) -> None:
        """選取的字包上記號；沒選字就插一對記號、游標放中間。"""
        if self.read_only:
            return
        m = markup.MARKERS[kind]
        tk_text = self.text._textbox
        try:
            a, b = tk_text.index("sel.first"), tk_text.index("sel.last")
        except tk.TclError:
            a = b = None
        if a is None:
            tk_text.insert("insert", m + m)
            tk_text.mark_set("insert", f"insert-{len(m)}c")
        else:
            if not tk_text.get(a, b).strip():
                return
            tk_text.insert(b, m)                 # 先插後面，前面的位置才不會跑掉
            tk_text.insert(a, m)
            tk_text.tag_remove("sel", "1.0", "end")
            tk_text.mark_set("insert", f"{b}+{2 * len(m)}c")
        self.text.focus_set()
        self._on_modified()

    def insert_code_block(self) -> None:
        """插一個 ``` 區塊：有選字就把那幾行包起來，沒有就插空區塊、游標放在裡面。"""
        if self.read_only:
            return
        tk_text = self.text._textbox
        try:
            a = tk_text.index("sel.first linestart")
            b = tk_text.index("sel.last lineend")
        except tk.TclError:
            a = b = None
        if a is None:
            at = tk_text.index("insert lineend")
            lead = "" if not tk_text.get("insert linestart", "insert lineend") else "\n"
            tk_text.insert(at, lead + "```\n\n```")
            tk_text.mark_set("insert", f"{at}+{len(lead) + 4}c")
        else:
            tk_text.insert(b, "\n```")
            tk_text.insert(a, "```\n")
            tk_text.tag_remove("sel", "1.0", "end")
        self.text.focus_set()
        self._on_modified()

    def insert_checkbox(self) -> None:
        """格式列「打勾」：游標那行（或選到的每一行）行首加「- [ ] 」；已經是打勾清單就拿掉。"""
        if self.read_only:
            return
        tk_text = self.text._textbox
        try:
            first = int(tk_text.index("sel.first").split(".")[0])
            last = int(tk_text.index("sel.last").split(".")[0])
        except tk.TclError:
            first = last = int(tk_text.index("insert").split(".")[0])
        tk_text.tag_remove("sel", "1.0", "end")
        for ln in range(first, last + 1):
            line = tk_text.get(f"{ln}.0", f"{ln}.end")
            cb = markup.checkbox(line)
            if cb is not None:
                tk_text.delete(f"{ln}.{_py_to_tk_col(line, cb[0])}", f"{ln}.{_py_to_tk_col(line, cb[1])}")
            else:
                indent = len(line) - len(line.lstrip(" \t"))
                tk_text.insert(f"{ln}.{_py_to_tk_col(line, indent)}", "- [ ] ")
        if first == last:
            tk_text.mark_set("insert", f"{first}.end")
        self.text.focus_set()
        self._on_modified()

    def _style_key(self, kind: str) -> str:
        self.apply_style(kind)
        return "break"                           # 擋掉 tk 自己的 Ctrl+H（退格）、Ctrl+I（插 tab）

    def focus(self) -> None:
        self.text.focus_set()

    def flush(self) -> None:
        """立刻存（如果有改）。"""
        if self._save_timer is not None:
            self.after_cancel(self._save_timer)
            self._save_timer = None
        if self._dirty and not self.read_only:
            self._dirty = False
            try:
                self._on_save(self.get_text())
            except Exception as e:             # 存不進去（磁碟拔掉、加密失敗）：留著 dirty，下次再試
                self._dirty = True
                self.last_error = str(e)
                applog.exception("存檔失敗")
                self.status.configure(text=_("存檔失敗：{0}").format(e))
                return
            self.last_error = ""
            self._set_status(_("已儲存 ") + datetime.now().strftime("%H:%M:%S"), fade=True)

    def is_dirty(self) -> bool:
        return self._dirty

    def bind_keys(self, keymap) -> None:
        """照快捷鍵表（keys.KeyMap）綁內文框與標題框的鍵：存檔、重點、紅字、粗體、斜體、指令區塊。改鍵時先解掉上次綁的。
        字母綁大小寫兩種（Caps Lock 開著 tk 送大寫）；Ctrl+H 與 Ctrl+Shift+H 同時綁時 tk 挑修飾鍵較多的那個（見 keys.sequences）。"""
        from .. import keys
        for w, seq, fid in self._key_seqs:
            w.unbind(seq, fid)                         # 帶 funcid 才會把 Tcl 命令也刪掉（不然每次改鍵都留一份）
        self._key_seqs = []
        text, title = self.text._textbox, self.title._entry   # 綁在 tk 的內層元件（CTk 的 unbind 不接受 funcid）

        def bind(action, widget, fn):
            for seq in keys.sequences(keymap.key_of(action)):
                self._key_seqs.append((widget, seq, widget.bind(seq, fn)))

        bind("save", text, lambda _e: self.flush())
        bind("save", title, lambda _e: self.flush())
        bind("mark", text, lambda _e: self._style_key("mark"))         # 順便擋掉 tk 自己的 Ctrl+H（退格）
        bind("red", text, lambda _e: self._style_key("red"))
        bind("bold", text, lambda _e: self._style_key("bold"))
        bind("italic", text, lambda _e: self._style_key("italic"))     # 擋掉 tk 的 Ctrl+I（插 tab）
        bind("code", text, lambda _e: (self.insert_code_block(), "break")[1])

    def destroy(self) -> None:
        for name in ("_fade_job", "_save_timer", "_hl_timer"):       # 排程中的工作先取消，視窗關了才不會 bgerror
            job = getattr(self, name, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
                setattr(self, name, None)
        super().destroy()

    STATUS_FADE_AFTER_MS = 2500
    STATUS_FADE_STEPS = anim.FADE // anim.FRAME     # 淡出幀數（動畫規則在 anim.py）

    def _set_status(self, text: str, fade: bool = False) -> None:
        """右下角那行字。fade=True（已儲存）：停 2.5 秒後慢慢淡掉，不要一直亮著。其他（輸入中、存檔失敗、唯讀）留著。"""
        if self._fade_job is not None:
            self.after_cancel(self._fade_job)
            self._fade_job = None
        self.status.configure(text=text, text_color=self._muted_color())
        if fade:
            self._fade_job = self.after(self.STATUS_FADE_AFTER_MS, lambda: self._fade_status(0))

    def _fade_status(self, step: int) -> None:
        self._fade_job = None
        if not self.status.winfo_exists():
            return
        total = max(1, anim.FADE // anim.FRAME)
        if step >= total:
            self.status.configure(text="", text_color=self._muted_color())
            return
        bg = T.MAIN_BG[1] if self._dark() else T.MAIN_BG[0]
        self.status.configure(text_color=anim.blend(self._muted_color(), bg, anim.ease_out((step + 1) / (total + 1))))
        self._fade_job = self.after(anim.FRAME, lambda: self._fade_status(step + 1))

    def refresh_theme(self) -> None:
        self._apply_link_color()

    # ---- 事件 ----
    def _on_title_changed(self, _e=None) -> None:
        if self._loading:
            return
        self._mark_dirty()

    def _on_modified(self, _e=None) -> None:
        if self._loading or not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self._mark_dirty()
        if self._hl_timer is not None:
            self.after_cancel(self._hl_timer)
        self._hl_timer = self.after(HIGHLIGHT_MS, self._highlight_links)

    def _mark_dirty(self) -> None:
        if self.read_only:
            return
        self._dirty = True
        self._set_status(_("輸入中…"))
        if self._save_timer is not None:
            self.after_cancel(self._save_timer)
        self._save_timer = self.after(AUTOSAVE_MS, self.flush)
        if self._hl_timer is not None:
            self.after_cancel(self._hl_timer)
        self._hl_timer = self.after(HIGHLIGHT_MS, self._highlight_links)

    def _on_return(self, _e=None) -> Optional[str]:
        """清單接續：行首「1. 」「- 」按 Enter 自動補下一個；只有標記沒內容就結束清單。規則在 listing.py。"""
        line = self.text.get("insert linestart", "insert lineend")
        marker = listing.next_marker(line)
        if marker is None:
            return None                      # 不是清單，照一般 Enter
        if marker == "":
            self.text.delete("insert linestart", "insert lineend")
            return "break"
        self.text.insert("insert", "\n" + marker)
        return "break"

    def _on_ctrl_wheel(self, e) -> str:
        self._on_zoom(1 if e.delta > 0 else -1)
        return "break"

    def _on_ctrl_click(self, e) -> Optional[str]:
        idx = self.text.index(f"@{e.x},{e.y}")
        link = self._link_at(idx)
        if link:
            self._on_open_link(link)
            return "break"
        tag = self._tag_at(idx)
        if tag and self._on_tag is not None:
            self._on_tag(tag)
            return "break"
        return None

    def _tag_at(self, idx: str) -> Optional[str]:
        """點的位置落在哪個 #標籤上（含 #）；沒有就 None。"""
        tk_text = self.text._textbox
        line_no = int(idx.split(".")[0])
        line = tk_text.get(f"{line_no}.0", f"{line_no}.end")
        col = len(tk_text.get(f"{line_no}.0", idx))
        for a, b in markup.tags(line):
            if a <= col <= b:
                return line[a:b]
        return None

    # ---- 連結 ----
    def _link_at(self, idx: str) -> Optional[str]:
        """點的位置（tk 的 "行.字元"）落在哪個連結上；規則在 links.py。
        用 get() 數字元算位置：emoji 與「…」標籤都不會讓位置跑掉。"""
        tk_text = self.text._textbox
        line_no = int(idx.split(".")[0])
        line = tk_text.get(f"{line_no}.0", f"{line_no}.end")
        return links.link_at(line, len(tk_text.get(f"{line_no}.0", idx)))

    def _highlight_links(self) -> None:
        """上色、藏記號、折長連結、放小元件（…、複製、指令標籤、☐）、畫圖。打字停 300 ms 後跑一次。
        游標所在那一行什麼都不藏（記號現形才能改），其他行只看得到上色後的字。"""
        self._hl_timer = None
        tk_text = self.text._textbox
        was_loading = self._loading
        self._loading = True                    # 下面插小元件會觸發 <<Modified>>
        tk_text.configure(undo=False)           # 重畫的 delete／insert 不能進復原堆疊（Ctrl+Z 會把筆記弄壞）
        try:
            # 先把上一次嵌進去的小元件拿掉（它們佔一個索引位置，要先清才能用字元位置算）
            for tag in WIDGET_TAGS:
                ranges = tk_text.tag_ranges(tag)
                for k in range(len(ranges) - 2, -1, -2):
                    tk_text.delete(ranges[k], ranges[k + 1])
            for w in self._ell_widgets:
                try:
                    w.destroy()
                except Exception:
                    pass
            self._ell_widgets = []
            for tag in (LINK_TAG, ELIDE_TAG, HIDE_TAG, MARKER_TAG, CODE_TAG, DONE_TAG, TAG_TAG, *STYLE_TAGS.values()):
                self.text.tag_remove(tag, "1.0", "end")
            cur_line, cur_col = self._cursor_line_col()
            # 只掃內文（get_text 會多一行標題，行號會差一）
            lines = self.text.get("1.0", "end-1c").split("\n")
            blocks, spans = markup.parse("\n".join(lines))
            fence_lines = set()
            for a, b in blocks:
                fence_lines.add(a)
                if b > a and markup.is_fence(lines[b]):
                    fence_lines.add(b)
            for i, line in enumerate(lines, start=1):
                here = (i == cur_line)
                c = lambda col, ln=line: _py_to_tk_col(ln, col)
                hide = (lambda a, b: None) if here else (lambda a, b: self.text.tag_add(HIDE_TAG, f"{i}.{a}", f"{i}.{b}"))
                ell_at: list[str] = []
                head_widget = None                # 行首要放的小元件（☐／指令標籤），最後才插，不然欄位會跑掉
                for s_ in spans.get(i - 1, ()):   # 記號：加 tag（欄位用乾淨的那行算）
                    self.text.tag_add(STYLE_TAGS[s_.kind], f"{i}.{c(s_.inner_start)}", f"{i}.{c(s_.inner_end)}")
                    self.text.tag_add(MARKER_TAG, f"{i}.{c(s_.start)}", f"{i}.{c(s_.inner_start)}")
                    self.text.tag_add(MARKER_TAG, f"{i}.{c(s_.inner_end)}", f"{i}.{c(s_.end)}")
                    hide(c(s_.start), c(s_.inner_start))
                    hide(c(s_.inner_end), c(s_.end))
                in_code = any(a <= i - 1 <= b for a, b in blocks)
                link_spans = [(l.start, l.end) for l in links.find_links(line)]
                if not in_code:                   # #標籤（連結裡的 # 不算）
                    for ta, tb in markup.tags(line):
                        if not any(a <= ta < b for a, b in link_spans):
                            self.text.tag_add(TAG_TAG, f"{i}.{c(ta)}", f"{i}.{c(tb)}")
                for l in links.find_links(line):
                    a, b = c(l.start), c(l.end)
                    self.text.tag_add(LINK_TAG, f"{i}.{a}", f"{i}.{b}")
                    raw = line[l.start:l.end]
                    name_end = raw.find("](") if raw.startswith("[") else -1
                    if name_end > 0 and not here:  # [名稱](路徑){w=…}：只留名稱，其他藏掉
                        hide(a, a + 1)
                        hide(c(l.start + name_end), b)
                        continue
                    shown = l.end - l.start
                    cursor_inside = (here and l.start <= cur_col <= l.end)
                    if shown > LINK_SHOW_MAX and not cursor_inside:
                        ha = c(l.start + LINK_HEAD)
                        hb = c(l.end - LINK_TAIL)
                        self.text.tag_add(ELIDE_TAG, f"{i}.{ha}", f"{i}.{hb}")
                        ell_at.append(f"{i}.{ha}")
                cb = None if in_code else markup.checkbox(line)
                if cb is not None:                # 打勾清單：「- [ ] 」藏起來換成 ☐／☑；完成的那行劃掉
                    if cb[2]:
                        self.text.tag_add(DONE_TAG, f"{i}.{c(cb[1])}", f"{i}.end")
                    if not here:
                        hide(c(cb[0]), c(cb[1]))
                        head_widget = ("check", f"{i}.{c(cb[0])}", cb[2])
                if (i - 1) in fence_lines and not here:
                    hide(0, c(len(line)))
                for idx in reversed(ell_at):    # 從右往左插，左邊的位置才不會跑掉
                    self._insert_ellipsis(idx)
                if head_widget is not None:
                    self._insert_check_widget(head_widget[1], i, head_widget[2])
            for a, b in blocks:                  # ``` 區塊：整段等寬深底，圍欄行淡灰（游標不在就藏），開頭行放「指令」與「複製」
                self.text.tag_add(CODE_TAG, f"{a + 1}.0", f"{b + 1}.end")
                self.text.tag_add(MARKER_TAG, f"{a + 1}.0", f"{a + 1}.end")
                if b > a and markup.is_fence(lines[b]):
                    self.text.tag_add(MARKER_TAG, f"{b + 1}.0", f"{b + 1}.end")
                self._insert_copy_button(f"{a + 1}.end", markup.block_text(lines, a, b))
                self._insert_code_label(f"{a + 1}.0")
            tk_text.edit_modified(False)
        finally:
            tk_text.configure(undo=True)
            self._loading = was_loading
        self._refresh_images()
        self._update_counter()

    def _update_hint(self, body: str) -> None:
        if body or self.read_only:
            self._hint.place_forget()
        else:
            self._hint.configure(fg=self._muted_color(), bg=self.text._textbox.cget("background"))
            self._hint.place(x=4, y=4)

    def _update_counter(self) -> None:
        """右下角的行數與字數：內文的行數、不含換行的字元數（空白也算一字）。"""
        body = self.text.get("1.0", "end-1c")
        self._update_hint(body)
        lines = body.count("\n") + 1 if body else 0
        chars = len(body) - body.count("\n")
        self.counter.configure(text=_("{0} 行 · {1} 字").format(lines, chars))

    def _cursor_line_col(self) -> tuple[int, int]:
        """游標在內文的 (行, Python 字元位置)。用 get() 數字元，不受 emoji、「…」標籤影響。"""
        tk_text = self.text._textbox
        idx = tk_text.index("insert")
        line = int(idx.split(".")[0])
        return line, len(tk_text.get(f"{line}.0", idx))

    def _insert_ellipsis(self, idx: str) -> None:
        import tkinter as tk
        tk_text = self.text._textbox
        lbl = tk.Label(tk_text, text="…", font=(T.UI_FONT_FAMILY, max(8, self._font.cget("size") - 2)),
                       fg=self._link_color(), bg=tk_text.cget("background"), bd=0, padx=1, cursor="hand2")
        lbl.bind("<Button-1>", lambda _e, i=idx: self._expand_at(i))
        lbl.bind("<Motion>", lambda e: self._on_motion(e, widget=lbl, idx=idx))
        lbl.bind("<Leave>", lambda _e: self._hide_tip())
        tk_text.window_create(idx, window=lbl)
        tk_text.tag_add(ELL_TAG, idx, f"{idx}+1c")
        self._ell_widgets.append(lbl)

    def _insert_check_widget(self, idx: str, line_no: int, done: bool) -> None:
        """打勾清單行首的 ☐／☑：點一下就把那行的「[ ]」↔「[x]」換掉（這是使用者的修改，會存檔、可復原）。"""
        tk_text = self.text._textbox
        idx = tk_text.index(idx)
        size = max(10, self._font.cget("size") + 1)
        lbl = tk.Label(tk_text, text=CHECK_GLYPH[done], font=(T.UI_FONT_FAMILY, size),
                       fg=self._link_color() if done else self._muted_color(),
                       bg=tk_text.cget("background"), bd=0, padx=2, cursor="hand2")
        lbl.bind("<Button-1>", lambda _e, w=lbl: (self._toggle_check(w), "break")[1])
        tk_text.window_create(idx, window=lbl)
        tk_text.tag_add(CHECK_TAG, idx, f"{idx}+1c")
        self._ell_widgets.append(lbl)

    def _toggle_check(self, widget) -> None:
        if self.read_only:
            return
        tk_text = self.text._textbox
        try:
            line_no = int(tk_text.index(widget).split(".")[0])
        except tk.TclError:
            return
        line = tk_text.get(f"{line_no}.0", f"{line_no}.end")       # get() 不含嵌進去的元件
        cb = markup.checkbox(line)
        if cb is None:
            return
        new = markup.toggle_checkbox(line)
        start = tk_text.index(f"{tk_text.index(widget)}+1c")    # 方框就插在「- [ ] 」前面（search 找不到藏起來的字）
        tk_text.delete(start, f"{start}+{cb[1] - cb[0]}c")
        tk_text.insert(start, new[cb[0]:cb[1]])
        self.text.focus_set()
        self._on_modified()
        self._highlight_links()                  # 馬上重畫：☐ 變 ☑，不等 300 ms

    def _insert_code_label(self, idx: str) -> None:
        """指令區塊開頭那行最前面的小標籤「指令」。"""
        tk_text = self.text._textbox
        idx = tk_text.index(idx)
        lbl = tk.Label(tk_text, text=_("指令"), font=(T.UI_FONT_FAMILY, 9), fg=self._code_muted(),
                       bg=self._code_bg(), bd=0, padx=4)
        tk_text.window_create(idx, window=lbl)
        tk_text.tag_add(LABEL_TAG, idx, f"{idx}+1c")
        self._ell_widgets.append(lbl)

    def _insert_copy_button(self, idx: str, payload: str) -> None:
        tk_text = self.text._textbox
        idx = tk_text.index(idx)                 # 先換成「行.欄」：「N.end」插了按鈕後會指到按鈕後面，tag 就會標到換行字元
        lbl = tk.Label(tk_text, text=_(" 複製 "), font=(T.UI_FONT_FAMILY, 9), fg=self._code_muted(),
                       bg=self._code_bg(), bd=0, padx=4, cursor="hand2")

        def copy(_e=None, w=lbl):
            text = payload
            try:                                 # 按的時候重算：上色前 300 ms 內改過的內容才不會是舊的
                line = int(tk_text.index(w).split(".")[0]) - 1
                lines = tk_text.get("1.0", "end-1c").split("\n")
                for a, b in markup.code_blocks(lines):
                    if a == line:
                        text = markup.block_text(lines, a, b)
            except Exception:
                pass
            self.clipboard_clear()
            self.clipboard_append(text)
            w.configure(text=_(" 已複製 "))
            w.after(1200, lambda: w.winfo_exists() and w.configure(text=_(" 複製 ")))
        lbl.bind("<Button-1>", copy)
        tk_text.window_create(idx, window=lbl)
        tk_text.tag_add(COPY_TAG, idx, f"{idx}+1c")
        self._ell_widgets.append(lbl)            # 跟「…」一起管：重畫前 destroy

    def _expand_at(self, idx: str) -> None:
        """點「…」：游標放進那段連結，重畫時就不折。"""
        self.text._textbox.mark_set("insert", idx)
        self.text.focus_set()
        self._highlight_links()

    # ---- 滑鼠停在連結上：顯示完整目標 ----
    def _on_motion(self, e, widget=None, idx: Optional[str] = None) -> None:
        tk_text = self.text._textbox
        if idx is None:
            idx = tk_text.index(f"@{e.x},{e.y}")
            if LINK_TAG not in tk_text.tag_names(idx):
                self._hide_tip()
                return
        line = int(idx.split(".")[0])
        col = len(tk_text.get(f"{line}.0", idx))
        target = links.link_at(tk_text.get(f"{line}.0", f"{line}.end"), col)
        if not target:
            self._hide_tip()
            return
        if target != self._tip_target:
            self._show_tip(target, e.x_root + 14, e.y_root + 18)

    def _show_tip(self, text: str, x: int, y: int) -> None:
        import tkinter as tk
        self._hide_tip()
        tip = tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        tk.Label(tip, text=text, font=(T.UI_FONT_FAMILY, 10), bg=T.TOOLTIP_BG, fg=T.TOOLTIP_FG,
                 padx=8, pady=4, justify="left", wraplength=520).pack()
        tip.geometry(f"+{x}+{y}")
        self._tip, self._tip_target = tip, text

    def _hide_tip(self) -> None:
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
        self._tip, self._tip_target = None, None

    # ---- 圖片顯示 ----
    def _schedule_refresh(self, ms: int = HIGHLIGHT_MS) -> None:
        if self._hl_timer is None:
            self._hl_timer = self.after(ms, self._highlight_links)

    def _wanted_images(self) -> list:
        """內文裡每一行指到圖檔的連結：(行號, 絕對路徑, mtime, 使用者指定寬度或 None)。一行只畫第一張。"""
        if self._resolve_link is None:
            return []
        out = []
        for i, line in enumerate(self.text.get("1.0", "end-1c").split("\n"), start=1):
            for l in links.find_links(line):
                if l.target.startswith(("http://", "https://")):
                    continue
                p = self._resolve_link(l.target)
                if p.suffix.lower() in IMAGE_EXT and p.is_file():
                    m = WIDTH_ATTR_RE.search(line)
                    out.append((i, p, p.stat().st_mtime, int(m.group(1)) if m else None))
                    break
        return out

    def _max_image_width(self) -> int:
        return max(120, self.text.winfo_width() - 72)   # 扣掉內距與捲軸，圖才不會撐出橫向捲軸

    def _refresh_images(self) -> None:
        """把圖畫到連結那一行後面。只在「哪些圖、在哪行、多寬」有變時才重畫，打字時不閃。"""
        wanted = self._wanted_images()
        width = self._max_image_width()
        state = [(i, str(p), m, w, width) for i, p, m, w in wanted]
        if state == self._images_state:
            return
        self._images_state = state
        self._hide_handle()
        tk_text = self.text._textbox
        was_loading = self._loading
        self.text._textbox.configure(undo=False)   # 畫圖的 delete／image_create 不進復原堆疊
        self._loading = True                    # 畫圖會觸發 <<Modified>>，不能算成使用者改了內容
        try:
            ranges = tk_text.tag_ranges(IMG_TAG)
            for k in range(len(ranges) - 2, -1, -2):          # 從後面刪，前面的索引才不會跑掉
                tk_text.delete(ranges[k], ranges[k + 1])
            self._photos = []
            self._image_lines = {}
            for i, p, _m, want_w in wanted:
                photo = _load_photo(p, width, want_w)
                if photo is None:
                    continue
                self._photos.append(photo)
                idx = tk_text.index(f"{i}.end")
                tk_text.image_create(idx, image=photo, padx=6, pady=6)
                tk_text.tag_add(IMG_TAG, idx, f"{idx}+1c")
                self._image_lines[i] = (p, photo.width(), photo.height())
            tk_text.edit_modified(False)
        except Exception:
            applog.exception("畫圖失敗")
        finally:
            self.text._textbox.configure(undo=True)
            self._loading = was_loading

    # ---- 圖片縮放：點圖 → 右下角出現把手，拖動等比例縮放，寬度寫進那行的 {w=…} ----
    def _on_click(self, e) -> None:
        tk_text = self.text._textbox
        idx = tk_text.index(f"@{e.x},{e.y}")
        if IMG_TAG not in tk_text.tag_names(idx):
            self._hide_handle()
            return
        line = int(idx.split(".")[0])
        if line not in getattr(self, "_image_lines", {}):
            self._hide_handle()
            return
        self._selected_line = line
        self._show_handle(idx)

    def _show_handle(self, idx: str) -> None:
        tk_text = self.text._textbox
        bbox = tk_text.bbox(idx)                 # (x, y, w, h) 圖在文字框裡的位置
        if not bbox:
            return
        x, y, w, h = bbox
        if not hasattr(self, "_handle"):
            self._handle = ctk.CTkFrame(tk_text, width=14, height=14, corner_radius=3,
                                        fg_color=T.ACCENT, cursor="size_nw_se")
            self._handle.bind("<ButtonPress-1>", self._drag_start)
            self._handle.bind("<B1-Motion>", self._drag_move)
            self._handle.bind("<ButtonRelease-1>", self._drag_end)
            self._size_lbl = ctk.CTkLabel(tk_text, text="", font=T.ui_font(10), text_color=T.ON_ACCENT,
                                          fg_color=T.ACCENT, corner_radius=4, padx=4)
        self._handle.place(x=x + w - 8, y=y + h - 8)
        self._size_lbl.configure(text=f"{self._image_lines[self._selected_line][1]} px")
        self._size_lbl.place(x=x + 6, y=y + 6)

    def _hide_handle(self) -> None:
        for name in ("_handle", "_size_lbl"):
            w = getattr(self, name, None)
            if w is not None:
                w.place_forget()
        self._selected_line = None

    def _drag_start(self, e) -> None:
        self._drag_x0 = e.x_root
        self._drag_w0 = self._image_lines[self._selected_line][1]

    def _drag_move(self, e) -> None:
        new_w = int(max(IMG_MIN_W, min(self._max_image_width(), self._drag_w0 + (e.x_root - self._drag_x0))))
        self._size_lbl.configure(text=f"{new_w} px")
        self._pending_w = new_w

    def _drag_end(self, _e) -> None:
        new_w = getattr(self, "_pending_w", None)
        line = self._selected_line
        if new_w is None or line is None:
            return
        self._pending_w = None
        tk_text = self.text._textbox
        text = tk_text.get(f"{line}.0", f"{line}.end")
        if WIDTH_ATTR_RE.search(text):
            new_text = WIDTH_ATTR_RE.sub(f"){{w={new_w}}}", text, count=1)
        else:
            m = links.ATTACH_RE.search(text)
            if not m:
                return
            new_text = text[:m.end()] + f"{{w={new_w}}}" + text[m.end():]
        # 只換文字部分：刪到「圖那個字元」之前（中間若有「…」標籤也一起清掉），再重畫
        img_range = tk_text.tag_nextrange(IMG_TAG, f"{line}.0", f"{line}.end")
        end_text = img_range[0] if img_range else f"{line}.end"
        tk_text.configure(undo=False)           # 拉大小不進復原堆疊：這段 delete 跨過「…」標籤，undo 會把連結行弄壞
        try:
            tk_text.delete(f"{line}.0", end_text)
            tk_text.insert(f"{line}.0", new_text)
        finally:
            tk_text.configure(undo=True)
        self._hide_handle()
        self._highlight_links()                 # 會把 modified 旗標清掉，所以下面要自己標 dirty
        self._mark_dirty()

    # ---- 復原／重做（工具列按鈕用；Ctrl+Z / Ctrl+Y 是 tkinter 內建）----
    def undo(self) -> None:
        try:
            self.text.edit_undo()
        except Exception:
            pass                                  # 沒東西可復原
        self._schedule_refresh()

    def redo(self) -> None:
        try:
            self.text.edit_redo()
        except Exception:
            pass
        self._schedule_refresh()

    def _context_menu(self, e, widget, is_body: bool) -> str:
        """右鍵選單。唯讀筆記只能複製、全選。"""
        widget.focus_set()
        try:
            has_sel = bool(widget.selection_get())
        except tk.TclError:
            has_sel = False
        if is_body and not has_sel:                  # 沒選字：游標移到點的地方，貼上才會貼在那裡
            widget.mark_set("insert", f"@{e.x},{e.y}")
        editable = not self.read_only
        m = tk.Menu(widget, tearoff=0, font=(T.UI_FONT_FAMILY, 10))
        m.add_command(label=_("剪下"), accelerator="Ctrl+X", state="normal" if (has_sel and editable) else "disabled",
                      command=lambda: widget.event_generate("<<Cut>>"))
        m.add_command(label=_("複製"), accelerator="Ctrl+C", state="normal" if has_sel else "disabled",
                      command=lambda: widget.event_generate("<<Copy>>"))
        m.add_command(label=_("貼上"), accelerator="Ctrl+V", state="normal" if editable else "disabled",
                      command=lambda: self._menu_paste(widget, is_body))
        m.add_separator()
        m.add_command(label=_("全選"), accelerator="Ctrl+A", command=lambda: self._select_all(widget, is_body))
        if is_body:                                  # 貼到別的地方用：== ** [..](..) ``` 都拿掉
            m.add_command(label=_("複製成純文字（去掉記號）"), command=lambda: self._copy_plain(widget, has_sel))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()
        return "break"

    def _copy_plain(self, widget, has_sel: bool) -> None:
        text = widget.get("sel.first", "sel.last") if has_sel else widget.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(markup.plain(text))
        self._set_status(_("已複製純文字"), fade=True)

    def _menu_paste(self, widget, is_body: bool) -> None:
        if is_body and self._on_paste() == "break":  # 剪貼簿是圖：已經存成附件插進去了
            self._on_modified()
            return
        try:                                         # 一般文字：有選字就取代，貼在選取的位置（不是游標原本的位置）
            first = widget.index("sel.first")
            widget.delete("sel.first", "sel.last")
            if is_body:
                widget.mark_set("insert", first)
            else:
                widget.icursor(first)
        except tk.TclError:
            pass
        widget.event_generate("<<Paste>>")
        if not is_body:
            self._on_title_changed()

    @staticmethod
    def _select_all(widget, is_body: bool) -> None:
        if is_body:
            widget.tag_add("sel", "1.0", "end-1c")
        else:
            widget.select_range(0, "end")
            widget.icursor("end")

    def _on_paste(self, _e=None) -> Optional[str]:
        """Ctrl+V：剪貼簿是圖 → 交給主視窗存附件、拿回要插的那行；不是圖就照一般貼上。"""
        if self.read_only or self._on_paste_image is None:
            return None
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
        except Exception:
            img = None
        if img is None or isinstance(img, list) or not hasattr(img, "size"):
            return None                          # 文字或檔案清單：讓 tkinter 自己貼
        line = self._on_paste_image(img)
        if not line:
            return "break"
        if self.text.index("insert").split(".")[1] != "0":
            line = "\n" + line
        self.text.insert("insert", line + "\n")
        return "break"

    def _link_color(self) -> str:
        return T.LINK_COLOR[1] if ctk.get_appearance_mode() == "Dark" else T.LINK_COLOR[0]

    def _dark(self) -> bool:
        return ctk.get_appearance_mode() == "Dark"

    def _muted_color(self) -> str:
        return T.TEXT_MUTED[1] if self._dark() else T.TEXT_MUTED[0]

    def _code_bg(self) -> str:
        return CODE_BG[1] if self._dark() else CODE_BG[0]

    def _code_muted(self) -> str:
        return CODE_MUTED[1] if self._dark() else CODE_MUTED[0]

    def _apply_link_color(self) -> None:
        """跟主題有關的顏色都在這裡：換主題時主視窗會呼叫 refresh_theme → 這裡。"""
        d = 1 if self._dark() else 0
        self.text.tag_config(LINK_TAG, foreground=self._link_color())
        self.text.tag_config(ELIDE_TAG, elide=True)
        self.text.tag_config(CODE_TAG, background=CODE_BG[d], foreground=CODE_FG[d],
                             lmargin1=8, lmargin2=8, rmargin=8)
        try:                                     # Tk 8.6.6+ 才有：左邊留白也上底色，區塊左緣才是直的
            self.text._textbox.tag_config(CODE_TAG, lmargincolor=CODE_BG[d])
        except tk.TclError:
            pass
        self.text.tag_config(STYLE_TAGS["mark"], background=MARK_BG[d])
        self.text.tag_config(STYLE_TAGS["red"], foreground=RED_FG[d])
        self.text.tag_config(MARKER_TAG, foreground=self._muted_color())
        self.text.tag_config(DONE_TAG, foreground=self._muted_color())
        self.text.tag_config(TAG_TAG, foreground=T.ACCENT[d])

> **公開版說明（Public copy notice）**
> 這份是 Notion（本機便利貼工具）的**架構與程式碼分享**，由企劃／PM 角度整理；不含任何公司資訊、專案資料或使用者筆記。
> 這個副本只供參考，**請勿直接在這裡修改**：原始碼在維護者的本機維護，改好後整份同步過來（tools/sync_public_copy.py）。
> This folder shares the architecture and source of a local sticky-notes tool for reference only. It contains no company data.
> Do not edit this copy directly; changes are made upstream and synced here.

# Notion 1.0.1（原名 PersonalNote，2026-10-29 改名）

名字只改看得到的地方：視窗標題、Notion.exe、Notion.bat、開機捷徑、release zip（`personalnote/__init__.py` 的 `APP_NAME`）。
不改的：套件名 `personalnote`、`%APPDATA%\PersonalNote`（log 與 note_dir.txt）、加密常數（改了舊筆記解不開）、單一執行個體的 mutex 名。桌面筆記資料夾預設改叫 Notion（Peter 的那份已由 personalNote 改名）。設定面板最底下顯示開發者（`AUTHOR`）與版本。

桌面便利貼。一天一個資料夾、一張筆記一個檔，全部存在本機（預設桌面 `Notion`），不經過任何雲端、不用帳號密碼。
截圖可以直接貼進筆記顯示；PDF、Word、PPT 用連結記位置，Ctrl+點就開。主要使用者是開發人員：指令、程式片段、路徑、網址都照原樣存。

[AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改（待審閱）。

## 放哪裡

- **原始碼**：`D:\AI\ai study\code\PersonalNote\`（改程式、跑測試、打包都在這裡）。
- **實際在用的**：桌面 `Notion\` 裡的 `Notion.exe` + 三個 .bat。筆記也存在同一個資料夾，程式只認日期資料夾，exe 和 .bat 放一起沒關係。
- **給別人的**：`release\Notion_v1.0.0.zip`（`tools\make_release.py` 產生）。
- 重新打包後記得把 `dist\Notion.exe` 再複製到桌面那份。

## 給使用者

| 要做什麼 | 怎麼做 |
|---|---|
| 啟動 | 點兩下 `Notion.bat`。第一次 Windows 可能跳「已保護您的電腦」：按「其他資訊」→「仍要執行」（exe 沒有數位簽章，正常）；有些防毒會先隔離 PyInstaller 打包的 exe，要加信任。直接點 exe 也能開，但 .bat 裡的設定不會生效 |
| 開機自動啟動 | Windows 自己設定：Win+R 輸入 `shell:startup`，把 `Notion.bat` 的捷徑丟進去（⚙ 設定裡有「開啟啟動資料夾」按鈕）。程式不代勞，因為公司電腦常擋 PowerShell／COM。Linux 才有程式內的開關（寫 autostart .desktop） |
| 改設定 | 平常在程式裡 ⚙ 改就好。`Notion.bat` 裡的 `set NOTE_xxx=` 預設全部留空；填了值就「每次用 .bat 開都以它為準」，程式裡改的會被蓋回去（面板會紅字提醒） |
| 寫筆記 | 上面是標題欄（可留空），下面是內文；停 1.2 秒自動存，關視窗、切到別的視窗也會存 |
| 左欄顯示什麼 | 有標題顯示標題；沒標題拿內文第一行，會去掉「1. 」「- 」這種清單標記 |
| 同一天多張 | 上排「＋ 新筆記」、Ctrl+N、或左欄日期旁的 ＋ |
| 看之前的 | 左欄依日期分組，點一張就開；◀ ▶ 前一天／後一天；搜尋框找日期（2026-10-28、10/28）或內容 |
| 把昨天沒做完的抄到今天 | 左欄那張筆記按右鍵 → 複製到今天 |
| 復原／重做 | 工具列 ↶ ↷，或 Ctrl+Z / Ctrl+Y（切到別張筆記才會清掉） |
| 回到之前的版本 | 每次存檔前自動留一份快照（每張最多 30 份）在 `.app/history`。加密開著時快照也是加密的，檔案總管打不開；要還原請先關加密（設定）再用檔案總管看，或等 1.1 的「之前的版本」按鈕 |
| 刪除 | 右鍵 → 刪除這張；🗑 → 清空這張／清掉整天／清掉全部。都先搬到 `.app/trash`，不會直接消失 |
| 字體大小 | Ctrl + 滑鼠滾輪，或設定面板的 ＋－；會記住 |
| 列清單 | 行首打「1. 」或「- 」，按 Enter 自動接 2.、3.；空的那行再按 Enter 結束清單 |
| 截圖 | 截圖後在內文 Ctrl+V：存成 `attachments/貼圖_時間.png`，圖直接顯示在那行下面。點圖 → 右下角把手拖拉縮放（等比例），大小記在那行後面 `{w=400}` |
| 檔案位置 | 直接打路徑就會變連結：`D:\AI\ai study\notes\58.md`（有副檔名、中間可有空格）、`\\server\share\試務 2026\名單.xlsx`、純資料夾用引號 `"D:\AI\ai study"`。📎 會把檔案複製一份進 `attachments/` 並插連結 |
| 網址 | 自動底線，Ctrl + 點開瀏覽器 |
| 太長的連結 | 畫面上中間折成「…」，滑鼠移上去顯示完整；點「…」或游標移進去就展開可改。檔案裡永遠是完整的 |
| 風格 | ⚙ 設定 → 一般／跟隨系統／暗黑模式 |
| 匯入／匯出 | ⚙ 設定：匯出這張、匯出全部（純文字 .md）、匯入檔案（可多選）、匯入資料夾（匯出全部產生的那種）。匯入接在那一天後面編號，不蓋掉既有的 |
| 加密 | 預設開。用 Windows 帳號加密（DPAPI）；⚙ 設定可關。保護範圍見下面 |
| 換電腦、重灌前 | ⚙ 設定 → 匯出全部…（加密綁帳號，不匯出的話新電腦打不開） |
| 出問題了 | 錯誤會跳框並記在 `%APPDATA%\PersonalNote\logs\`；卡住 30 秒會自動把堆疊倒進 `crash.log`；關閉時存不進去會寫救援檔到 `%APPDATA%\PersonalNote\rescue\`。回報問題請附 logs 資料夾 |

快捷鍵：Ctrl+N 新筆記、Ctrl+\ 收側欄、Ctrl+S 立刻存、Ctrl+Z／Y 上一步／下一步、Ctrl+PgUp／PgDn 前後一天、Ctrl+滾輪 或 Ctrl+加／減 縮放、Ctrl+點 開連結、Ctrl+V 貼截圖、Ctrl+H／Shift+H／B／I 重點／紅字／粗體／斜體、Ctrl+Shift+C 指令區塊。

左欄：一天一組，點日期（或 ▾）摺疊／展開；選中那張藍色、它那一天整組深灰（`theme.DAY_ACTIVE_BG`）；日期右邊的 ＋ 在那天加一張；最底下「＋ 額外新增」先跳月曆（`ui/datepick.py`）再加。摺疊狀態不存檔。

多語系：畫面上每句字都寫成 `_("繁中原文")`（`i18n.py`），顯示時到 `assets/lang/strings.csv` 撈對應欄；沒翻就顯示繁中。**有哪些語言由表決定**：zh_TW 和 note 以外的每一欄是一種語言，欄名就是代碼，`__name__` 那列是下拉選單顯示的名字；要加韓文就加一欄 ko、填 `__name__`、翻句子、重新打包，程式不用改。預設語言 en，工具列右上的下拉或設定裡可切（`settings.json` 的 `lang`、`NOTE_LANG`、`--lang`），切了整個視窗重畫（`MainWindow.rebuild_ui`），不用重開。流程：程式裡加 `_("新句子")` → `python tools/check_strings.py`（把新 key 補進 csv 並列出缺的） → 把 csv 給翻譯社填 → 放回來重新打包。第一版翻譯是 `tools/lang_seed.py` 填的（Claude 翻），翻譯社改 csv 就好。模組層級的常數不要在 import 時呼叫 `_()`（語言那時還沒設），要在用到時才呼叫。

拖檔案進視窗：`.md`／`.txt` 匯成今天的筆記，其他檔複製到 attachments 並插連結。靠 Windows 的 WM_DROPFILES（`dropfiles.py`），沒裝 tkinterdnd2；以系統管理員身分跑時 Windows 會擋掉從檔案總管拖來的檔。

標記：檔案裡存的是 `==重點==`、`!!紅字!!`、`**粗體**`、`*斜體*`、``` 區塊這些記號（規則在 `markup.py`），畫面照記號上色、記號本身淡灰；``` 區塊等寬灰底，開頭行尾有「複製」按鈕。字體大小只有全域一個（Ctrl+滾輪），不做局部字級。

## 資料放哪裡

```
Notion/                      ← 你的筆記（整個資料夾備份即可；原本叫 personalNote）
  2026-10-27/
    001.note                 ← 一張筆記。第一行若是「# 標題」就是標題欄的內容，其餘是內文。加密時副檔名 .note
    002.note
  2026-10-28/
    001.md                   ← 加密關掉時是 .md 純文字；兩種都讀得到
  attachments/               ← 📎 插進來的檔案副本、Ctrl+V 的截圖（不加密）
  .app/
    settings.json            ← 風格、字體大小、最上層、加密開關（程式內改會寫這裡）
    state.json               ← 視窗大小位置、側欄開合、上次看的日期
    format.json              ← 存檔格式版本（升級相容用）
    history/                 ← 每張筆記的版本快照
    trash/                   ← 刪掉的筆記先放這裡
    error.log                ← 程式畫面裡發生的錯誤（另一份更完整的在 %APPDATA%）
%APPDATA%\PersonalNote\note_dir.txt   ← 「更改位置」記的路徑
%APPDATA%\PersonalNote\logs\          ← personalnote.log（1 MB 滿了換檔，最多留 4 個）、crash.log
%APPDATA%\PersonalNote\rescue\        ← 關閉時存不進去的救援檔
```

資料夾名稱用 `2026-10-28`（ISO，檔案總管排序才對）；畫面上顯示台灣習慣 `2026/10/28（三）`。

不是 CSV、不是資料庫：一張筆記就是一段 UTF-8 文字（加密時是那段文字的 DPAPI 密文），逗號、換行、中英混雜、程式碼的 `{}[]()<>|\` 都照原樣存。圖片不在筆記檔裡，筆記裡只有一行連結，圖是顯示時從 attachments 讀的。

### 加密保護到哪裡（請照實理解）

Windows 內建的 DPAPI（`CryptProtectData`，使用者範圍）。程式本身沒有密碼、也不問密碼。

| 擋得住 | 擋不住 |
|---|---|
| 硬碟拔到別台電腦 | 同一個帳號底下跑的任何程式（惡意軟體） |
| 別的 Windows 帳號 | 知道你 Windows 密碼的人 |
| 沒登入就想讀檔 | 網域帳號：網域管理員有備援金鑰 |
| | 弱密碼被離線破解（安全強度＝你的 Windows 密碼強度） |
| | 休眠檔、分頁檔裡的明文（整顆碟 BitLocker 才擋得住） |
| | `attachments/`、`.app/trash/` 裡的純文字檔、你匯出的 .md |

代價：**換電腦、重灌、刪帳號，舊的 .note 就永遠打不開**，所以換機前一定先「匯出全部」。

## 給接手維護的人

### 用語（程式、註解、畫面統一用這幾個詞）

| 詞 | 意思 | 程式裡 |
|---|---|---|
| 筆記（note） | 一張便利貼＝一個 `NNN.note`（加密）或 `NNN.md`（純文字） | `NoteId(day, seq)`、`NoteRef` |
| 日期（day） | 一個 `YYYY-MM-DD` 資料夾，底下可以多張筆記 | `date` |
| 存檔位置（note_dir） | 放所有日期資料夾的那個資料夾，預設桌面 `Notion` | `Settings.note_dir`、`NoteStore.root` |
| 設定（settings） | 使用者可改的：風格、字體、最上層、加密、存檔位置 | `config.Settings` |
| 狀態（state） | 程式自己記的：視窗位置、上次日期 | `state.AppState` |
| 附件（attachment） | 📎 複製進 `attachments/` 的檔、Ctrl+V 的截圖 | `NoteStore.add_attachment / add_image` |
| 快照（snapshot） | 存檔前留的上一版 | `NoteStore.snapshot / list_snapshots` |
| 清除 | 搬到 `.app/trash`，不是真的刪 | `delete / delete_day / delete_all` |

### 程式分層

```
personalnote/
  __init__.py       APP_NAME、__version__（版本只在這裡改）
  app.py            進入點：log → 設定 → 單一執行個體 → NoteStore → MainWindow；--startup on/off/status 維護指令
  applog.py         log（%APPDATA%\PersonalNote\logs）、faulthandler、沒接到的例外、卡死看門狗
  config.py         Settings：命令列 > 環境變數(.bat) > APPDATA 指定位置 > settings.json > 預設
  storage.py        NoteStore：列日期、列筆記（標題快取）、讀、存（.tmp + fsync + 改名）、清除、附件、快照、匯入匯出、格式版本
  crypto.py         DPAPI 加解密（encrypt_text / decrypt_text / is_encrypted / available）；保護範圍與相容契約寫在檔頭
  links.py          什麼算連結（網址、Windows 路徑含空格、\\共用槽、[名稱](附件){w=…}）；純文字處理，可測試
  listing.py        清單接續（1. → 2.、- → -）；純文字處理，可測試
  imefix.py         修 tkinter 接微軟注音時把「.」「,」誤認成 Delete／Print 鍵；掛在文字框、標題、搜尋框
  state.py          AppState：視窗大小位置（含螢幕外修正）、上次日期、左欄寬、格式列展開否
  startup.py        開機啟動：只有 Linux 做（寫 autostart .desktop）；Windows 讓使用者自己放捷徑（實作在 platform_）
  platform_.py      跟作業系統有關的全部在這：設定／log 資料夾、桌面位置、開檔、字型、視窗圖示、單一執行個體、開機啟動
  i18n.py           多語系：_("繁中原文") → assets/lang/strings.csv 的對應欄；語言清單由表的欄位決定
  markup.py         行內記號（==重點== !!紅字!! **粗體** *斜體*）與 ``` 指令區塊的解析；純文字處理，可測試
  dropfiles.py      拖檔案進視窗（Windows WM_DROPFILES；非 Windows 自動關閉）
  ui/
    theme.py        顏色、間距、字型、日期格式（fmt_day）、圖示快取
    sidebar.py      左欄：搜尋（250 ms debounce）+ 一天一組的清單（摺疊、選中那天深灰、寬度可拖）；只回報點了什麼，不碰檔案
    editor.py       文字框：自動存檔、縮放、連結底線、長連結折「…」、圖片顯示與拖拉縮放、Ctrl+V 貼圖、清單接續、
                    標記上色與複製按鈕、格式列、行數字數
    datepick.py     小月曆（「額外新增」選日期）
    main_window.py  組裝：誰呼叫誰；工具列（含語言下拉）、右鍵選單、清除對話框、匯入匯出、拖檔、設定面板、處理中浮框、
                    錯誤處理、關閉時救援、換語言重畫（rebuild_ui）
tests/              unittest：storage、config、links、listing、imefix、crypto、robustness、compat（1.0.0 夾具）、import_export、
                    history、markup、dropfiles、i18n、sidebar_cap、review_fixes（PM 審查的回歸測試）
tests/fixtures/v1.0.0/   1.0.0 寫出來的資料範例，每一版都要讀得開（不准改）
tools/make_version_file.py   從 __version__ 產 exe 的版本資源
tools/make_release.py        跑檢查（單元測試、翻譯表、開視窗走一遍）→ 整理給別人的資料夾並壓 zip；使用說明.txt 的內容在這
tools/check_strings.py       翻譯表維護：掃 _() 的 key、補進 csv、列缺翻；--strict 給打包用
tools/lang_seed.py           第一版翻譯（只填空格）
tools/make_icons.py、make_splash.py   畫工具列圖示、啟動畫面
tools/stress/                壓力測試腳本（六角色、大量資料、隨機亂按、exe 反覆啟動與強制殺掉、中文與亂放路徑、ui_checks）
assets/icon.ico、icon.png    圖示（黑 N 白底；Windows 用 ico，Linux 用 png）
assets/icons/、splash.png    工具列圖示、啟動畫面
assets/lang/strings.csv      翻譯表（給翻譯社的就是這個檔）
run.py              PyInstaller 進入檔
Notion.bat、build_exe.bat    Windows 啟動／打包（安裝／移除開機啟動.bat 已停用，不隨 release 附）
Notion.sh、build_linux.sh    Linux 啟動／打包（寫好但沒有 Linux 機器實跑過）
```

規則：
- 筆記、設定、狀態的讀寫只在 `storage.py`、`config.py`、`state.py`；UI 層只能寫 log／救援檔（`applog`、`main_window._write_rescue`）、讀圖檔（`editor`、`theme.icon`）。
- UI 元件（sidebar、editor）只用回呼回報，不知道 NoteStore 的存在；主視窗負責接線。
- 顏色、字型、間距在 `theme.py`；各元件自己的時間常數（自動存檔 1.2 s、折疊門檻 48 字等）在該檔頭，不要散在函式裡。
- 使用者看得到的字一律繁體中文台灣用語；程式識別字英文。
- 已知的結構債（接手第一週最容易踩）：
  1. `main_window.py` 的流程邏輯（清除、複製、換位置）直接依賴 tk 對話框，沒有單元測試，靠 `tools/stress` 的角色腳本補。1.1 要抽成不依賴 tk 的 Controller。
  2. `editor.py` 一行文字有三套位置：Python 字元位置（links.py）、Tk index（emoji 算 2 格，`_py_to_tk_col`）、`get()` 的文字（不含「…」標籤與圖那個字元）。改底線／折疊／圖片時，位置一律用 `get()` 的文字數字元，再換成 Tk index。
  3. `storage.py` 的索引與標題快取只在自己 `save()/delete()` 時更新；別的程式改了檔案，要等視窗重新取得焦點（`refresh_if_changed`，比對每個檔的 mtime）才會重掃。新功能若直接寫檔，記得呼叫 `_touch(day)`。
  4. 加一個設定要改 7 處（`config.py` 檔頭有清單），漏一處會靜默失效。
- 這個資料夾不是 git 版本庫（公司 ai study 資料夾的慣例）。接手時建議先 `git init`，夾具與相容契約才有人守。

### 升級規則（1.0.1 以後一定要遵守，不然舊筆記打不開）

1. **不改舊檔的意義。** `.note` 檔頭 `PNOTE1\n` + DPAPI（`crypto.py` 的 `MAGIC`、`_ENTROPY`、`_DESCRIPTION` 三個常數永遠不能改，`tests/test_crypto_storage.py` 有釘死）、`.md` UTF-8、第一行 `# 標題`、`[名稱](路徑){w=N}`，這些讀法永遠保留。
2. **新格式只能新增**：新的檔頭（例如 `PNOTE2`）、新的副檔名、新的欄位；`storage.FORMAT_VERSION` 加 1。舊版程式碰到：`format.json` 版本較新 → 開啟時提示；單張 `.note` 檔頭是 `PNOTE` 家族但不認得 → 顯示「較新版本的格式，請更新程式」唯讀，不會被改寫。
3. **每一版都要過 `tests/test_compat.py`**：它用 `tests/fixtures/v1.0.0` 開舊資料。改格式時另外加一組新夾具（`v1.0.x`），舊夾具不准動。
4. `.app/settings.json`、`state.json` 多出來的欄位要忽略、缺的用預設（現在就是這樣寫的，不要改成嚴格檢查）。
5. 版本號只在 `personalnote/__init__.py` 改；`build_exe.bat` 會自動產版本資源。

### 常見修改

| 想做 | 改哪裡 |
|---|---|
| 加一個設定（例如行距） | 照 `config.py` 檔頭的 7 處清單（Settings、PERSISTED、_ENV_KEYS、build_arg_parser + _from_cli 的 keep、_coerce、.bat、設定面板鎖定清單）；用到的地方讀 `settings.xxx` |
| 加一個工具列按鈕 | `main_window.py` 的 `_build_topbar` 加一個 `mk(...)`，command 指到新方法 |
| 右鍵選單多一項 | `main_window.py` 的 `note_menu` 加 `add_command` |
| 換顏色、字型 | `ui/theme.py` |
| 認更多連結格式 | `links.py` 加 regex，`tests/test_links.py` 加一條 |
| 圖片九點縮放 | `editor.py` 的 `_show_handle` 現在一個角落把手；要九點就多放八個 Frame，`_drag_end` 改成寫 `{w=,h=}`，同時改 `links.ATTACH_RE` 與 `editor.WIDTH_ATTR_RE` 認新寫法 |
| 改存檔格式 | 只動 `storage.py`，遵守上面的升級規則，加夾具與 `test_compat.py` |
| 換加密方式（例如改成自己設密碼） | 只動 `crypto.py` 的 `encrypt_text / decrypt_text`，MAGIC 改成 `PNOTE2`，`decrypt_text` 認兩種；storage 不用改 |
| 改圖示 | 換 `assets/icon.ico`（256/128/64/48/32/24/16 多尺寸），重打包 |
| 再遇到中文打不出的符號 | 用 scratch 的按鍵診斷方式看 keysym，補進 `imefix.CONTROL_KEYSYMS` |

### 開發、打包、壓力測試

```bat
pip install -r requirements.txt
python -X utf8 -m unittest discover -s tests -t .     # 全部單元測試
python -m personalnote                                 # 用原始碼跑
build_exe.bat                                          # 先跑測試、產版本資源、再打包 → dist\Notion.exe
python -X utf8 tools\stress\run_all.py                 # 壓力測試（要先有 dist\Notion.exe；會開關視窗幾十次，跑的時候別碰滑鼠）
python tools\make_release.py --dest %USERPROFILE%\Desktop   # 整理 release\ 並壓 zip，順便複製到桌面
```

打包用 PyInstaller `--onefile --windowed`。exe 沒有數位簽章（要公司憑證才簽得了），所以第一次執行會遇到 SmartScreen；exe 每次啟動解壓到 `%TEMP%\_MEIxxxx`，慢 1～2 秒是正常的。

### 支援的作業系統

- Windows 10／11 64 位元：主要平台，全部功能都在這上面測。
- Windows 8.1：理論上可以（Python 3.12 的下限），沒測。Windows 7／8.0 跑不起來，Notion.bat 會先擋下來講清楚。
- Linux（X11／Wayland）：第二平台。跟作業系統有關的都走 `platform_.py`；沒有的功能：加密（DPAPI 是 Windows 獨有，設定裡會說明並自動存純文字）、拖檔案進視窗。
  用 `Notion.sh` 跑、`build_linux.sh` 打包；貼截圖要裝 xclip（X11）或 wl-paste（Wayland）；字型要有 Noto Sans CJK TC（沒有會變豆腐）。
  **這些 Linux 分支在 Windows 機器上寫的，沒有實跑過**，第一次在 Linux 跑請看 `~/.config/PersonalNote/logs`。
- macOS：platform_ 有留分支（open、PingFang），完全沒測。

### 授權與第三方元件（發給別人前看一下）

程式沒有把任何字型檔包進去，只「指名」系統字型（Windows 微軟正黑體、Consolas；Linux Noto Sans CJK TC、DejaVu Sans Mono；都是作業系統或發行版自帶，Noto／DejaVu 本身是開源授權），所以沒有字型授權問題。
打包進 exe 的第三方元件：Python（PSF 授權）、Tcl/Tk（BSD 類）、customtkinter（MIT）、Pillow（MIT-CMU）、PyInstaller（GPL 但附例外條款，允許打包閉源程式）。圖示、啟動畫面是自己畫的。
名稱「Notion」是現成商用軟體的商標：自己用沒差，對外發布或放到公司產品裡建議改名（只要改 `APP_NAME`、exe 名、.bat 檔名）。

### 已知限制

- 主要支援 Windows；Linux 分支寫了但沒實跑（見「支援的作業系統」）。
- 左欄一次最多列 1000 張（`MainWindow.SIDEBAR_MAX_NOTES`）；Tk 的 grid 一欄只能放 10000 列，超過整欄壞掉。多的用搜尋找。
- 設定裡的快捷鍵表格是 `SettingsPanel.SHORTCUTS`，加快捷鍵記得一起補。對話框一律經過 `_quiet_dialog()`，不然 customtkinter 的 Toplevel 開的時候會閃好幾下（原因寫在那個函式上）。
- 加密綁 Windows 帳號；保護範圍見上表。
- 「更改位置」不搬舊筆記，要搬自己用檔案總管搬整個資料夾。
- 圖片縮放只有等比例的角落把手；GIF 不會動。
- Windows 直接關機（不是關視窗）時，最後 1.2 秒內打的字可能來不及存。
- 同一個資料夾同時開兩個 Notion（例如 RDP 和本機各一個）沒有防護，後存的蓋掉先存的。
- 環境變數 `NOTE_ALLOW_MULTI=1` 會跳過單一執行個體檢查，只給 `tools/stress` 用，不要在 .bat 裡設。
- exe 是 PyInstaller onefile：工作管理員看到的是「啟動器＋子程序」兩個 Notion.exe，強制結束要結束整棵樹（`taskkill /F /T`），只殺一個會留下孤兒視窗。

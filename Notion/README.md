# Notion

本機便利貼工具（Windows）。一天一個資料夾、一張筆記一個檔，全部存在自己的電腦，不經過任何雲端、不用帳號密碼。

> 本資料夾只分享工具本身的架構與程式碼，不含任何使用者筆記或其他資料。

![主畫面（英文）](docs/main-en.png)

| 繁體中文介面（淺色） | 設定 |
|---|---|
| ![主畫面（繁中）](docs/main-zh.png) | ![設定](docs/settings-en.png) |

左欄依日期列筆記；中間是標題與內文，`==重點==`、`!!紅字!!`、`**粗體**` 照記號上色，``` 區塊有「複製」鈕，截圖直接顯示在筆記裡；右上角下拉切語言。

## 功能

| 功能 | 說明 |
|---|---|
| 依日期記事 | 左欄一天一組，一天可以很多張；點日期摺疊；「額外新增」可先選日期再加（補以前的紀錄） |
| 自動存檔 | 打字停 1.2 秒自動存，切換、關閉也存；存不進去會保留救援檔 |
| 標記 | 選字後標 `==重點==`（黃底）、`!!警告!!`（紅字）、`**粗體**`、`*斜體*`；檔案裡存的就是這些記號，匯出照樣看得懂 |
| 指令區塊 | ``` 區塊等寬灰底，右上角「複製」一鍵複製整段（常用指令、提示詞） |
| 連結 | 網址、Windows 路徑（含 `\\server\...`）自動變連結，Ctrl+點開啟；可執行檔會先確認 |
| 圖片與附件 | Ctrl+V 貼截圖直接顯示，角落把手拉大小；拖檔案進視窗：`.md`／`.txt` 變當天筆記，其他檔複製到 attachments 並插連結 |
| 清單 | 行首 `1. `／`- ` 按 Enter 自動接下一項 |
| 搜尋 | 日期或內容；大量筆記時顯示「搜尋中」 |
| 加密 | 預設用 Windows 帳號（DPAPI）加密，硬碟拔到別台電腦讀不到；換電腦前先「匯出全部」 |
| 匯入匯出 | 單張或全部匯成純文字 `.md`；匯入 `.md`／`.txt`（UTF-8、UTF-16、Big5、GBK、Shift-JIS 都認得） |
| 版本與垃圾桶 | 每張筆記保留舊版本快照；刪掉的先進垃圾桶，可「還原上一次刪除」 |
| 多語系 | 英文（預設）、繁中、簡中、日文；工具列右上下拉即時切換；翻譯表是一個 csv，加語言只要加一欄 |
| 外觀 | 一般／跟隨系統／暗黑模式；Ctrl+滾輪縮放；左欄寬度可拖；格式列可收起 |
| 其他 | 單一執行個體；啟動畫面；長時間動作顯示進度；行數與字數 |

## 怎麼用

**只想用**：拿打包好的資料夾（`Notion.exe` + `Notion.bat` + 使用說明.txt，由 `tools/make_release.py` 產生的 zip），解開放到想放的地方。

**clone 下來自己改或玩**（這個資料夾沒有 exe）：
```
pip install -r requirements.txt
python -m personalnote          # 直接跑
build_exe.bat                   # 或打包成 dist\Notion.exe（會先跑測試）
```
直接點這個資料夾裡的 `Notion.bat` 也可以：它找不到 exe 時會檢查 Python 與套件，缺了會說明。

1. 需要 Windows 10／11（64 位元）。用打包好的版本不用安裝任何東西。
2. 點 `Notion.bat`（.bat 裡可以改存檔位置、語言、字型等；留空＝用程式內設定）。第一次 Windows 可能跳「已保護您的電腦」→「其他資訊」→「仍要執行」（exe 沒有數位簽章）。
3. 筆記預設存在桌面的 `Notion` 資料夾，⚙ 設定可以改位置。
4. 開機自動啟動：Win+R 輸入 `shell:startup`，把 `Notion.bat` 的捷徑放進去（⚙ 設定裡有「開啟啟動資料夾」按鈕）。

快捷鍵：Ctrl+N 新筆記、Ctrl+S 立刻存、Ctrl+\ 收側欄、Ctrl+PgUp／PgDn 前後一天、Ctrl+滾輪 縮放、Ctrl+點 開連結、Ctrl+V 貼截圖、Ctrl+H／Shift+H／B／I 重點／紅字／粗體／斜體、Ctrl+Shift+C 指令區塊。

## 資料放哪裡

```
Notion/                       ← 筆記資料夾（整個備份即可）
  2026-10-28/001.note         ← 一張筆記一個檔；.note 加密、.md 純文字；第一行「# 標題」
  attachments/                ← 貼圖與附件（不加密）
  .app/settings.json          ← 程式內設定；state.json 視窗狀態；history/ 快照；trash/ 垃圾桶；error.log
%APPDATA%\PersonalNote\logs   ← 程式紀錄 personalnote.log、卡死堆疊 crash.log；rescue/ 救援檔
```

加密保護的範圍：筆記本文與快照會加密；attachments、匯出的 .md、垃圾桶裡的檔名不加密。加密綁 Windows 帳號：換電腦、重灌、刪帳號就打不開，換機前先匯出全部。

## 架構（給接手維護的人）

```
personalnote/
  __init__.py       APP_NAME、__version__、AUTHOR
  app.py            進入點：log → 設定 → 語言 → 單一執行個體 → NoteStore → MainWindow；--startup（Linux）
  config.py         Settings：命令列 > 環境變數(.bat) > 使用者指定位置 > settings.json > 預設（加設定要改的地方見檔頭）
  storage.py        NoteStore：索引與標題快取、讀存（.tmp + fsync + 改名）、編碼判斷、清除與垃圾桶、附件、快照、匯入匯出、格式版本
  crypto.py         DPAPI 加解密；相容契約常數（不能改）
  i18n.py           多語系：_("繁中原文") → assets/lang/strings.csv 對應欄；語言清單由表的欄位決定
  markup.py         行內記號與 ``` 區塊的解析（純文字處理）
  links.py / listing.py / imefix.py   連結判斷、清單接續、注音標點修正
  dropfiles.py      拖檔案進視窗（Windows WM_DROPFILES）
  platform_.py      跟作業系統有關的全部在這：路徑、開檔、字型、圖示、單一執行個體、開機啟動
  state.py / startup.py / applog.py   視窗狀態、開機啟動（Linux）、log 與看門狗
  ui/theme.py       顏色、間距、字型、日期格式
  ui/sidebar.py     左欄（只回報點了什麼，不碰檔案）
  ui/editor.py      文字框：自動存檔、上色、圖片、格式列、行數字數
  ui/datepick.py    小月曆
  ui/main_window.py 組裝與流程：工具列、右鍵選單、匯入匯出、拖檔、設定面板、換語言重畫
tests/              unittest（含相容夾具 tests/fixtures/v1.0.0，不准改）
tools/              make_release.py（打包檢查與 zip）、check_strings.py（翻譯表維護）、lang_seed.py、
                    make_icons.py、make_splash.py、make_version_file.py、check_public_words.py、stress/（壓力測試）
assets/             圖示、啟動畫面、lang/strings.csv（翻譯表）
```

規則：
- 檔案讀寫只在 `storage.py`、`config.py`、`state.py`；UI 元件只用回呼回報，主視窗負責接線。
- 畫面文字一律 `_("繁中原文")`；模組層級常數不要在 import 時呼叫 `_()`（語言還沒設）。加新字串後跑 `python tools/check_strings.py`，把 csv 的空格翻好。
- `crypto.py` 的常數、`.note` 檔頭、`format.json` 的升級規則不能改，不然舊筆記打不開。改格式要升版號並留舊版的讀法。
- 加一個設定要改的 7 處列在 `config.py` 檔頭，漏一處會靜默失效。

## 開發與打包

```
pip install -r requirements.txt
python -m personalnote                 # 直接跑
python -m unittest discover -s tests   # 單元測試
python tools/stress/run_all.py         # 壓力測試（開真視窗，放在螢幕外）
build_exe.bat                          # 打包成 dist\Notion.exe（會先跑測試與翻譯表檢查）
python tools/make_release.py --dest 桌面路徑   # 整理給別人的資料夾並壓 zip
python tools/check_public_words.py     # 提交前掃不該出現的字眼
```

## 支援的作業系統與授權

- Windows 10／11 為主要平台；Windows 7／8.0 跑不起來（Python 3.12 最低 8.1），`Notion.bat` 會先擋下來說明。
- Linux：平台相關都走 `platform_.py`，`Notion.sh`／`build_linux.sh` 可跑可打包；沒有加密與拖檔；尚未實機測試。
- 程式不含字型檔，只指名系統字型。第三方元件：Python（PSF）、Tcl/Tk（BSD 類）、customtkinter（MIT）、Pillow（MIT-CMU）、PyInstaller（GPL 含例外條款）。

## 已知限制

- 加密綁 Windows 帳號（見上）。「更改位置」不搬舊筆記。
- 圖片只有等比例的角落把手；GIF 不會動。
- Windows 直接關機時最後 1.2 秒內的字可能來不及存。
- 同一個資料夾同時開兩個程式（例如 RDP 與本機）沒有防護，後存的蓋掉先存的。
- 左欄一次最多列 1000 張，多的用搜尋找。

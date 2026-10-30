<!-- version: 1.0.5 -->
**繁體中文** | [English](README.en.md) | [日本語](README.ja.md) | [ไทย](README.th.md) | [हिन्दी](README.hi.md)

# Notion

本機便利貼工具（Windows）。一天一個資料夾、一張筆記一個檔，全部存在自己的電腦，不經過任何雲端、不用帳號密碼、不收集任何東西。
用 Python 3.12 寫的（畫面：tkinter ＋ customtkinter；打包：PyInstaller）。

> 本資料夾只分享工具本身的架構與程式碼，不含任何使用者筆記或其他資料。

![主畫面（英文）](docs/main-en.png)

| 繁體中文介面（淺色） | 設定（分頁） |
|---|---|
| ![主畫面（繁中）](docs/main-zh.png) | ![設定](docs/settings-en.png) |

左欄依日期列筆記，標題前的 ☆ 是我的最愛；中間是標題與內文，`==重點==`、`!!紅字!!`、`**粗體**` 照記號上色，``` 區塊有「複製」鈕，截圖直接顯示在筆記裡。語言、快捷鍵、左欄位置、更新都在右上角 ⚙ 設定。

## 功能

| 功能 | 說明 |
|---|---|
| 依日期記事 | 左欄一天一組，一天可以很多張；點日期摺疊；長按筆記列再拖可以調整同一天的順序；「額外新增」可先選日期再加（補以前的紀錄）；上排「＋ 新筆記」／Ctrl+N 一律加在今天 |
| 我的最愛 | 筆記標題前的 ☆ 點一下變 ★，最上面多一組「★ 我的最愛」（待辦事項下面），點那裡的列會開那張；再點一次取消 |
| 待辦事項 | 左欄最上面紅字「待辦事項」，固定一張、不屬於任何日期（存在 `9999-12-31` 資料夾，所以永遠排最上面） |
| 打勾清單 | 行首 `- [ ] `（格式列「打勾」或自己打）畫面變成方框，點一下打勾、完成的劃掉；檔案裡就是 GitHub 的 `- [x]` 寫法 |
| #標籤 | 內文的 `#專案A` 主色顯示，Ctrl+點 → 左欄直接搜尋那個標籤 |
| 右鍵選單 | 內文與標題：剪下、複製、貼上（剪貼簿是截圖會直接變成圖）、全選、複製成純文字（去掉記號）；筆記列：開啟、複製到今天、匯出、舊版本、加入我的最愛、分享、刪除；日期列：在這天新增、整天合成一個 `.md` 匯出、清整天 |
| 自動存檔 | 打字停 1.2 秒自動存，切換、關閉也存；存不進去會保留救援檔 |
| 標記 | 選字後標 `==重點==`（黃底）、`!!警告!!`（紅字）、`**粗體**`、`*斜體*`；檔案裡存的就是這些記號，匯出照樣看得懂。記號本身平常藏起來，游標移到那一行才現形 |
| 指令區塊 | ``` 區塊等寬深底，開頭「指令｜複製」一鍵複製整段（常用指令、提示詞） |
| 連結 | 網址、Windows 路徑（含 `\\server\...`）自動變連結，Ctrl+點開啟；可執行檔會先確認 |
| 圖片與附件 | Ctrl+V 貼截圖直接顯示，角落把手拉大小；拖檔案進視窗：`.md`／`.txt`（1 MB 以內）變當天筆記，其他檔不收（附件用 📎） |
| 清單 | 行首 `1. `／`- ` 按 Enter 自動接下一項 |
| 搜尋 | Ctrl+F，日期或內容；大量筆記時顯示「搜尋中」 |
| 快捷鍵 | 設定 → 快捷鍵：每個功能可以自己改組合鍵，要帶 Ctrl 或 Alt、系統的複製貼上不給用、兩個功能不准撞同一組，可全部還原預設 |
| 加密 | 預設用 Windows 帳號（DPAPI）加密，硬碟拔到別台電腦讀不到；換電腦前先「匯出全部」。細節見 [docs/加密與本機說明.md](docs/加密與本機說明.md)（zip 裡也有一份 .txt） |
| 匯入匯出 | 單張、整天（合成一個檔）或全部匯成純文字 `.md`；匯入 `.md`／`.txt`（UTF-8、UTF-16、Big5、GBK、Shift-JIS 都認得） |
| 版本與垃圾桶 | 每張筆記保留舊版本快照（右鍵「舊版本…」可以看、可以還原，還原前會把現在的內容也留一份）；刪掉的先進垃圾桶，可「還原上一次刪除」 |
| 分享 | 筆記列右鍵「分享」：用郵件寄出（開系統郵件程式，主旨＝標題、內文＝純文字）；複製到 Google Drive 桌面版的同步資料夾（找不到就讓你選資料夾） |
| 多語系 | 英文（預設）、繁中、簡中、日文；設定 → 外觀 切換，馬上換不用重開；翻譯表是一個 csv，加語言只要加一欄 |
| 更新 | 啟動幾秒後查 GitHub Releases 有沒有新版（只讀版本號）。有新版會提醒：下載 zip、這一版略過、或關掉提醒（設定 → 更新）。更新＝關掉程式、把 `Notion.exe` 換掉，筆記與設定都不會動 |
| 使用教學 | 第一次開有五頁教學，看一次就不再出現；設定 → 更新 可以再看 |
| 外觀 | 一般／跟隨系統／暗黑模式；Ctrl+滾輪縮放；左欄可放左／右／下、寬度可拖；格式列可收起；空筆記有提示；「已儲存」幾秒後自動淡出；跳出視窗都在主視窗正中央 |
| 其他 | 單一執行個體；啟動畫面；長時間動作顯示進度；行數與字數；過了午夜「今天」記號自動換天 |

## 怎麼用

**只想用**：拿打包好的 zip（`Notion.exe` + `Notion.bat` + 使用說明.txt + 加密與本機說明.txt，由 `tools/make_release.py` 產生），解開放到想放的地方。

**clone 下來自己改或玩**（這個資料夾沒有 exe）：
```
pip install -r requirements.txt
python -m personalnote          # 直接跑
build_exe.bat                   # 或打包成 dist\Notion.exe（會先跑測試）
```
直接點這個資料夾裡的 `Notion.bat` 也可以：它找不到 exe 時會檢查 Python 與套件，缺了會說明。

1. 需要 Windows 10／11（64 位元）。用打包好的版本不用安裝任何東西。
2. 點 `Notion.bat`（.bat 裡可以改存檔位置、語言、字型、要不要查更新等；留空＝用程式內設定）。第一次 Windows 可能跳「已保護您的電腦」→「其他資訊」→「仍要執行」（exe 沒有數位簽章）。
3. 筆記預設存在桌面的 `Notion` 資料夾，⚙ 設定 → 存檔 可以改位置。
4. 開機自動啟動：Win+R 輸入 `shell:startup`，把 `Notion.bat` 的捷徑放進去（⚙ 設定 → 存檔 有「開啟啟動資料夾」按鈕）。

快捷鍵（預設；設定裡可以自己改）：Ctrl+N 新筆記（加在今天）、Ctrl+T 回今天、Ctrl+F 搜尋、Ctrl+S 立刻存、Ctrl+\ 收側欄、Ctrl+PgUp／PgDn 前後一天、Ctrl+H／Ctrl+Shift+H 重點／紅字、Ctrl+B／I 粗體／斜體、Ctrl+Shift+C 指令區塊、Ctrl+=／Ctrl+- 字體大小。

## 資料放哪裡

```
Notion/                       ← 筆記資料夾（整個備份即可）
  2026-10-28/001.note         ← 一張筆記一個檔；.note 加密、.md 純文字；第一行「# 標題」
  attachments/                ← 貼圖與附件（不加密）
  .app/settings.json          ← 程式內設定（含快捷鍵、更新提醒）；state.json 視窗狀態與左欄位置；order.json 左欄排過的順序；
                                 favorites.json 我的最愛；history/ 快照；trash/ 垃圾桶；error.log
%APPDATA%\PersonalNote\logs   ← 程式紀錄 personalnote.log、卡死堆疊 crash.log；rescue/ 救援檔
```

加密保護的範圍：筆記本文與快照會加密；attachments、匯出的 .md、垃圾桶裡的檔名不加密。加密綁 Windows 帳號：換電腦、重灌、刪帳號就打不開，換機前先匯出全部。

程式不連網、不收集；唯一的網路動作是啟動時讀一次 GitHub 上的版本號，`Notion.bat` 裡 `set NOTE_UPDATE_CHECK=0` 可完全關掉。

## 架構（給接手維護的人）

```
personalnote/
  __init__.py       APP_NAME、__version__、AUTHOR
  app.py            進入點：log → 設定 → 語言 → 單一執行個體 → NoteStore → MainWindow；--startup（Linux）
  config.py         Settings：命令列 > 環境變數(.bat) > 使用者指定位置 > settings.json > 預設（加設定要改的地方見檔頭）
  storage.py        NoteStore：索引與標題快取、讀存（.tmp + fsync + 改名）、編碼判斷、清除與垃圾桶、附件、快照、匯入匯出、我的最愛、格式版本
  crypto.py         DPAPI 加解密；相容契約常數（不能改）
  i18n.py           多語系：_("繁中原文") → assets/lang/strings.csv 對應欄；語言清單由表的欄位決定
  markup.py         行內記號與 ``` 區塊的解析（純文字處理）
  links.py / listing.py / imefix.py   連結判斷、清單接續、注音標點修正
  dropfiles.py      拖檔案進視窗（Windows WM_DROPFILES；回呼裡不碰 Tk，由 after 輪詢）
  keys.py           快捷鍵表：預設、規則（要帶 Ctrl／Alt、系統鍵不給用、不准重複）、「Ctrl+Shift+N」轉 tk 序列
  update.py         查新版：GitHub Releases latest，只讀版本號
  platform_.py      跟作業系統有關的全部在這：路徑、開檔、字型、圖示、單一執行個體、開機啟動
  state.py / startup.py / applog.py   視窗狀態、開機啟動（Linux）、log 與看門狗
  ui/theme.py       顏色、間距、字型、日期格式、跳出視窗置中
  ui/sidebar.py     左欄（只回報點了什麼，不碰檔案）
  ui/editor.py      文字框：自動存檔、上色、圖片、格式列、行數字數、快捷鍵綁定
  ui/datepick.py    小月曆；ui/versions.py 舊版本視窗
  ui/main_window.py 組裝與流程：工具列、右鍵選單、匯入匯出、拖檔、設定面板（分頁）、更新提醒、使用教學、換語言重畫
tests/              unittest（含相容夾具 tests/fixtures/v1.0.0，不准改）
tools/              make_release.py（打包檢查、zip、--publish）、check_strings.py（翻譯表維護）、lang_seed.py、
                    make_icons.py、make_splash.py、make_version_file.py、check_public_words.py、stress/（壓力測試）
assets/             圖示、啟動畫面、lang/strings.csv（翻譯表）
docs/               截圖、加密與本機說明.md
```

規則：
- 檔案讀寫只在 `storage.py`、`config.py`、`state.py`；UI 元件只用回呼回報，主視窗負責接線。
- 畫面文字一律 `_("繁中原文")`；模組層級常數不要在 import 時呼叫 `_()`（語言還沒設）。加新字串後跑 `python tools/check_strings.py`，把 csv 的空格翻好。
- `crypto.py` 的常數、`.note` 檔頭、`format.json` 的升級規則不能改，不然舊筆記打不開。改格式要升版號並留舊版的讀法。
- 加一個設定要改的 7 處列在 `config.py` 檔頭，漏一處會靜默失效。
- Windows 訊息回呼（dropfiles）裡絕不能呼叫 tkinter，會讓程式被 C 執行階段直接終止。
- 升版號時五份 README（繁中、英、日、泰、印地）的 `<!-- version -->` 一起更新，`make_release.py` 會檢查。

## 開發與打包

```
pip install -r requirements.txt
python -m personalnote                 # 直接跑
python -m unittest discover -s tests   # 單元測試
python tools/stress/ui_checks.py       # 開真視窗走一遍（放在螢幕外）
build_exe.bat                          # 打包成 dist\Notion.exe（會先跑測試與翻譯表檢查）
python tools/make_release.py --dest 桌面路徑 [--publish]   # 整理給別人的資料夾並壓 zip；--publish 上傳 GitHub Releases（要裝 gh）
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
- exe 沒有數位簽章，第一次執行會被 SmartScreen 擋一次。

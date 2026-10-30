@echo off
chcp 65001 >nul
rem ============================================================
rem  Notion 啟動檔
rem  設定全部「留空 = 用程式裡 ⚙ 設定面板的值」。只有你在這裡填了值，才會蓋過程式裡的設定，
rem  而且每次用這個檔開都會蓋。所以平常留空就好；要固定某個值（例如公司統一存檔位置）才填。
rem  開機自動啟動的捷徑也是指到這個檔。
rem ============================================================

rem 筆記存哪裡。留空 = 桌面的 Notion（不存在會自動建立），或程式裡「設定 > 更改位置」選的位置。
set NOTE_DIR=

rem 風格：light（一般）/ system（跟隨系統）/ dark（暗黑模式）。留空 = 用程式裡的設定。
set NOTE_THEME=

rem 字體（留空 = Microsoft JhengHei UI）與大小 8~48（留空 = 用程式裡的設定；Ctrl+滾輪改了會記住）
set NOTE_FONT=
set NOTE_FONT_SIZE=

rem 視窗永遠在最上層：0 / 1。留空 = 用程式裡的設定。
set NOTE_TOPMOST=

rem 筆記加密：1 = 用 Windows 帳號加密；0 = 純文字 .md。留空 = 用程式裡的設定（預設加密）。
set NOTE_ENCRYPT=

rem 畫面語言：翻譯表 assets\lang\strings.csv 的欄名：en（英文，預設）、zh_TW（繁中）、zh_CN（簡中）、ja（日文）。留空 = 用程式設定裡選的。
set NOTE_LANG=

rem 啟動時查 GitHub 有沒有新版：留空或 1 = 查（只讀版本號）；0 = 完全不查（公司電腦擋外網可以關）。
set NOTE_UPDATE_CHECK=

rem ------------------------------------------------------------
rem 以下不用動
rem ------------------------------------------------------------
set NOTE_LAUNCHER=%~f0
cd /d "%~dp0"
rem Windows 7／8.0 跑不起來（Python 3.12 最低 Windows 8.1）：先講清楚，不然會跳一個看不懂的 DLL 錯誤
for /f "tokens=4-5 delims=. " %%i in ('ver') do set WINVER=%%i.%%j
if "%WINVER%"=="6.1" goto :oldwin
if "%WINVER%"=="6.2" goto :oldwin
if "%WINVER%"=="6.0" goto :oldwin
if exist "%~dp0dist\Notion.exe" (
    start "" "%~dp0dist\Notion.exe" %*
    exit /b 0
)
if exist "%~dp0Notion.exe" (
    start "" "%~dp0Notion.exe" %*
    exit /b 0
)
rem 這裡是原始碼資料夾（clone 下來的）：沒有 exe，用 Python 跑。先檢查 Python 與套件，缺了就講清楚
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=python
"%PY%" -c "import sys; assert sys.version_info >= (3, 11)" 2>nul || (
    echo 這是原始碼資料夾，沒有打包好的 Notion.exe。要直接用請拿打包好的 zip；
    echo 要從原始碼跑需要 Python 3.11 以上：https://www.python.org/downloads/
    pause & exit /b 1
)
"%PY%" -c "import customtkinter, PIL" 2>nul || (
    echo 這是原始碼資料夾，還沒裝套件。請先執行：
    echo     "%PY%" -m pip install -r requirements.txt
    echo 或者直接用打包好的 zip（build_exe.bat 可以自己打包）。
    pause & exit /b 1
)
"%PY%" -X utf8 -m personalnote %*
exit /b 0
:oldwin
echo 這台是 Windows %WINVER%（7 或 8.0），Notion 需要 Windows 8.1 以上（建議 10／11）。
pause

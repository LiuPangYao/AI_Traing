@echo off
chcp 65001 >nul
rem 把程式打包成單一 exe：dist\Notion.exe
rem 需要先裝：pip install -r requirements.txt
cd /d "%~dp0"
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=python
"%PY%" -c "import sys; assert sys.version_info >= (3, 11)" 2>nul || (echo 找不到 Python 3.11 以上：裝好後把這個 .bat 第 6 行的路徑改成你的 python.exe & pause & exit /b 1)
"%PY%" -X utf8 -m unittest discover -s tests -t . || (echo 測試沒過，不打包 & pause & exit /b 1)
"%PY%" -X utf8 tools\check_strings.py --strict || (echo 翻譯表有缺（看上面哪幾句沒翻），不打包 & pause & exit /b 1)
"%PY%" -X utf8 tools\make_version_file.py build\version_info.txt || (echo 版本檔產生失敗 & pause & exit /b 1)
rem 啟動畫面上印著版號，每次打包重畫，才不會跟設定裡的版號對不上
"%PY%" -X utf8 tools\make_splash.py || (echo 啟動畫面產生失敗 & pause & exit /b 1)
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name Notion --icon assets\icon.ico --version-file build\version_info.txt --noupx ^
  --add-data "assets;assets" --collect-data customtkinter --splash assets\splash.png ^
  run.py
if errorlevel 1 (echo 打包失敗 & pause & exit /b 1)
echo.
echo 完成：dist\Notion.exe   （記得複製到桌面 Notion 那份）
pause

@echo off
chcp 65001 >nul
rem 把 Notion 從「開機啟動」移除（等同程式內「設定 > 開機自動啟動」）。結果會跳一個小框。
cd /d "%~dp0"
set NOTE_LAUNCHER=%~dp0Notion.bat
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=python
if exist "%~dp0dist\Notion.exe" (
    "%~dp0dist\Notion.exe" --startup off
) else if exist "%~dp0Notion.exe" (
    "%~dp0Notion.exe" --startup off
) else (
    "%PY%" -m personalnote --startup off
    pause
)

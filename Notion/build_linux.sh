#!/usr/bin/env bash
# 在 Linux 上打包成單一執行檔 dist/Notion（跟 build_exe.bat 對應）。
# 需要：python3 3.11+、pip install -r requirements.txt、系統有 Tk（Debian/Ubuntu: apt install python3-tk）。
# 注意：這支腳本寫完沒有 Linux 機器實跑過，第一次跑有錯請看訊息調整。
set -e
cd "$(dirname "$0")"
python3 -X utf8 -m unittest discover -s tests -t .
python3 -X utf8 tools/check_strings.py --strict
python3 -m PyInstaller --noconfirm --clean --onefile --windowed \
  --name Notion --icon assets/icon.png \
  --add-data "assets:assets" --collect-data customtkinter --splash assets/splash.png \
  run.py
echo "完成：dist/Notion（放到想放的資料夾，連同 Notion.sh 一起）"

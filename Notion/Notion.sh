#!/usr/bin/env bash
# Notion 啟動檔（Linux／mac）。跟 Notion.bat 一樣：這裡的設定會蓋過程式裡的設定；留空＝用程式裡的。
# 第一次跑：chmod +x Notion.sh；需要 python3（3.11 以上）與 customtkinter、pillow：pip install -r requirements.txt
# 打包成單一執行檔：./build_linux.sh → dist/Notion

export NOTE_DIR=            # 筆記存哪裡。留空 = ~/Desktop/Notion（沒有桌面就家目錄）
export NOTE_THEME=          # light / dark / system
export NOTE_FONT=           # 字型；留空 = Noto Sans CJK TC
export NOTE_FONT_SIZE=
export NOTE_TOPMOST=        # 0 / 1
export NOTE_ENCRYPT=        # Linux 沒有加密（DPAPI 是 Windows 獨有），設了也會存純文字
export NOTE_LANG=           # en / zh_TW / zh_CN / ja（翻譯表的欄名）
export NOTE_LAUNCHER="$(cd "$(dirname "$0")" && pwd)/Notion.sh"

cd "$(dirname "$0")" || exit 1
if [ -x "./dist/Notion" ]; then
    exec ./dist/Notion "$@"
elif [ -x "./Notion" ]; then
    exec ./Notion "$@"
else
    exec python3 -X utf8 -m personalnote "$@"
fi

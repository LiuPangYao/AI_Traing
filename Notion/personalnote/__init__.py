# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""PersonalNote：本機存檔的每日便利貼。

套件分層（改功能時找對檔案）：
- config.py   設定值從哪來（命令列 > 環境變數(.bat) > 設定檔 > 預設）
- storage.py  一天一個資料夾、一張筆記一個檔（.note 加密／.md 純文字）的讀寫、清除、附件、匯出
- crypto.py   Windows DPAPI 加解密（綁登入帳號，不設密碼）
- links.py    什麼算連結（網址、路徑、[名稱](附件)）
- state.py    視窗位置、上次看的日期這類「程式自己記的狀態」
- startup.py  Windows 開機啟動捷徑的建立與移除
- ui/         視窗。theme 常數、sidebar 日期清單、editor 文字框、main_window 組裝
- app.py      進入點：把上面幾層接起來
"""

__version__ = "1.0.8"
APP_NAME = "Notion"          # 視窗、exe、.bat、捷徑都用這個名字（Peter 2026-10-29 從 PersonalNote 改的）；
                             # 套件名、%APPDATA%\PersonalNote、加密常數不跟著改，舊資料才讀得到；桌面筆記資料夾預設改叫 Notion（config.default_note_dir）
AUTHOR = "Peter Liu"         # 設定面板最底下與 exe 的版本資訊顯示

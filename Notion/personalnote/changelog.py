# [AI協助 Claude] 由 Peter Liu 於 2026-10-30 審閱修改
"""每一版改了什麼（設定 → 更新 → 版本紀錄，預設收起）。新的在前。
不走翻譯表：每條直接給中文與英文，簡中／日文畫面用英文那欄。升版號時在最上面加一段。"""
from __future__ import annotations

ENTRIES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("1.0.7",
     ("筆記連結：[[標題]] Ctrl+點跳到另一張，「返回」（Alt+Left）回來；右鍵「複製筆記連結」",
      "範本：新筆記旁的 ▾（會議紀錄、週報…，.app/templates 可自己加）；未完成清單（Ctrl+L）；匯出日期區間；清單行 Tab 縮排；搜尋框下列最近標籤",
      "設定多一頁「說明」（教學、關於、版本紀錄）；「額外新增」改成看得出可以按；標題、格式列、內文間距拉開",
      "輸入法選字的字跟內文一樣大；工具列圖示與啟動畫面重畫（不再鋸齒）",
      "設定／狀態檔原子寫入；圖片快取總量上限；垃圾桶 30 天自動清、刪筆記連舊版本一起；可執行檔清單補齊；log 與救援檔改放 %LOCALAPPDATA%"),
     ("Note links: [[title]] with Ctrl+click jumps to another note, “Back” (Alt+Left) returns; right-click “Copy note link”",
      "Templates: ▾ next to New note (meeting notes, weekly report…; add your own in .app/templates); Open items list (Ctrl+L); export a date range; Tab indents list lines; recent tags under the search box",
      "Settings gets a “Help” page (tour, about, version history); “Add elsewhere” now looks clickable; more space between title, format bar and text",
      "IME composition text matches the note font size; toolbar icons and splash redrawn (no more jagged edges)",
      "Settings/state files written atomically; image cache byte limit; trash auto-cleaned after 30 days and snapshots removed with the note; executable list extended; logs and rescue files moved to %LOCALAPPDATA%")),
    ("1.0.6",
     ("月曆：哪幾天有筆記、每天用多久（熱度圖），點日期就跳過去；工具列「月曆」或 Ctrl+M",
      "每天使用時間統計（視窗有焦點且有在動才算），存在 .app/usage.json",
      "設定改成左邊導覽＋卡片；按鈕統一樣式；這份版本紀錄",
      "升級檢查可指定測試網址（NOTE_UPDATE_URL），附自動化驗證工具；記憶體檢查工具"),
     ("Calendar: which days have notes and how long you used the app each day (heat map); click a day to jump; toolbar “Calendar” or Ctrl+M",
      "Daily usage time (counted only while the window is focused and active), stored in .app/usage.json",
      "Settings redone as side navigation + cards; unified button style; this version history",
      "Update check can point at a test URL (NOTE_UPDATE_URL) with an automated end-to-end check; memory check tool")),
    ("1.0.5",
     ("設定改分頁；存檔頁加「你的資料與隱私」與加密說明；更新頁寫出四步流程；關於列寫明用 Python 寫的",
      "教學視窗改版（圖示＋三句重點＋進度點）",
      "新增 docs/加密與本機說明.md，zip 裡附 .txt；README 五種語言"),
     ("Settings split into tabs; Files page explains privacy and encryption; Update page shows the four steps; About line says it is written in Python",
      "Tour redesigned (icon + three bullets + progress dots)",
      "New docs/加密與本機說明.md (also as .txt in the zip); README in five languages")),
    ("1.0.4",
     ("只改版號",),
     ("Version number only",)),
    ("1.0.3",
     ("啟動時查 GitHub 有沒有新版，有就提醒（可關、可略過這版）；設定裡有「更新」",
      "第一次開有五頁使用教學，只出現一次",
      "標題格加細框與提示字，看得出可以改"),
     ("Update check against GitHub Releases at startup with a reminder (can be turned off or skip a version); “Update” in Settings",
      "Five-page tour on first launch, shown once",
      "Title box gets a border and a hint so it is clearly editable")),
    ("1.0.2",
     ("修正：拖檔案進視窗會讓程式直接關閉",
      "快捷鍵可以在設定裡改（不准撞鍵）；我的最愛 ☆；左欄可放左／右／下；語言切換移到設定",
      "拖檔只收 .md／.txt 且 1 MB 以內；新筆記一律加在今天；過午夜「今天」自動換；跳出視窗置中"),
     ("Fix: dropping a file into the window terminated the app",
      "Shortcuts editable in Settings (no duplicates); Favorites ☆; side panel left / right / bottom; language switch moved to Settings",
      "Drops accept only .md / .txt up to 1 MB; new notes always go to today; “today” rolls over at midnight; dialogs centred")),
    ("1.0.1",
     ("右鍵選單、左欄長按拖拉排序、待辦事項、藏記號、打勾清單、#標籤、左欄色帶、匯出整天、舊版本還原、分享（郵件／Google Drive）",
      "Linux 平台層；開機啟動改成自己放捷徑；PM 審查與 QA 複檢修正"),
     ("Right-click menus, long-press reorder in the side panel, To-do, hidden marks, checklists, #tags, colour bands, export a whole day, restore older versions, share (email / Google Drive)",
      "Linux platform layer; autostart by placing a shortcut yourself; fixes from the PM review and QA re-check")),
    ("1.0.0",
     ("第一版：每日便利貼、記號上色、指令區塊、圖片與附件、匯入匯出、加密、垃圾桶、多語系",),
     ("First release: daily sticky notes, coloured markup, command blocks, images and attachments, import / export, encryption, trash, multiple languages",)),
)


def entries(lang: str) -> list[tuple[str, tuple[str, ...]]]:
    """(版號, 那版的條目) 清單；lang 以 zh 開頭給中文，其餘英文。"""
    zh = str(lang).lower().startswith("zh")
    return [(v, zh_items if zh else en_items) for v, zh_items, en_items in ENTRIES]

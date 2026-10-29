# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""第一版翻譯（Claude 翻的，翻譯社之後可以直接改 assets/lang/strings.csv，不用再跑這個）。
跑法：python tools/check_strings.py && python tools/lang_seed.py
只填表裡還空著的格子，已經有字的不動（翻譯社改過的不會被蓋掉）。"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.check_strings import CSV, COLS, read_csv, write_csv  # noqa: E402

# zh_TW → (en, zh_CN, ja)
T = {
    "{0} 無法啟動": ("{0} could not start", "{0} 无法启动", "{0} を起動できません"),
    "已建立開機捷徑：\n{0}": ("Startup shortcut created:\n{0}", "已建立开机快捷方式：\n{0}", "スタートアップのショートカットを作成しました：\n{0}"),
    "已移除開機捷徑": ("Startup shortcut removed", "已移除开机快捷方式", "スタートアップのショートカットを削除しました"),
    "開機啟動：": ("Run at startup: ", "开机启动：", "スタートアップ起動："),
    "開": ("on", "开", "オン"),
    "關": ("off", "关", "オフ"),
    "開機啟動設定失敗：{0}": ("Could not change the startup setting: {0}", "开机启动设置失败：{0}", "スタートアップ設定に失敗しました：{0}"),
    "{0}\n\n存檔位置：{1}\n詳細紀錄：{2}\n\n{3}": ("{0}\n\nNotes folder: {1}\nLog: {2}\n\n{3}", "{0}\n\n存档位置：{1}\n详细记录：{2}\n\n{3}", "{0}\n\n保存先：{1}\nログ：{2}\n\n{3}"),
    "這張解不開，沒辦法匯出": ("This note cannot be decrypted, so it cannot be exported", "这张解不开，无法导出", "このノートは復号できないため書き出せません"),
    "選日期": ("Pick a date", "选日期", "日付を選択"),
    "{0} 年 {1} 月": ("{1} / {0}", "{0} 年 {1} 月", "{0}年{1}月"),
    "開機自動啟動：把 Notion.bat 的捷徑放進 Windows 的「啟動」資料夾（右邊按鈕會開那個資料夾）。":
        ("Run at startup: put a shortcut to Notion.bat in the Windows Startup folder (the button opens that folder).",
         "开机自动启动：把 Notion.bat 的快捷方式放进 Windows 的“启动”文件夹（右边按钮会打开那个文件夹）。",
         "自動起動：Notion.bat のショートカットを Windows の「スタートアップ」フォルダーに入れてください（右のボタンで開きます）。"),
    "開啟啟動資料夾": ("Open Startup folder", "打开启动文件夹", "スタートアップを開く"),
    "今天": ("Today", "今天", "今日"),
    "取消": ("Cancel", "取消", "キャンセル"),
    "標題（可留空）": ("Title (optional)", "标题（可留空）", "タイトル（空欄可）"),
    "格式 ▸": ("Format ▸", "格式 ▸", "書式 ▸"),
    "格式 ▾": ("Format ▾", "格式 ▾", "書式 ▾"),
    "展開／收起格式列（上一步、下一步、重點、紅字、粗體、斜體、指令）": ("Show / hide the format bar (undo, redo, highlight, red, bold, italic, command)", "展开／收起格式栏（上一步、下一步、重点、红字、粗体、斜体、命令）", "書式バーの表示／非表示（元に戻す、やり直し、強調、赤字、太字、斜体、コマンド）"),
    "上一步": ("Undo", "上一步", "元に戻す"),
    "上一步（Ctrl+Z）": ("Undo (Ctrl+Z)", "上一步（Ctrl+Z）", "元に戻す（Ctrl+Z）"),
    "下一步": ("Redo", "下一步", "やり直し"),
    "下一步（Ctrl+Y）": ("Redo (Ctrl+Y)", "下一步（Ctrl+Y）", "やり直し（Ctrl+Y）"),
    "重點": ("Highlight", "重点", "強調"),
    "黃底（Ctrl+H）": ("Yellow highlight (Ctrl+H)", "黄底（Ctrl+H）", "黄色マーカー（Ctrl+H）"),
    "紅字": ("Red", "红字", "赤字"),
    "紅字（Ctrl+Shift+H）": ("Red text (Ctrl+Shift+H)", "红字（Ctrl+Shift+H）", "赤字（Ctrl+Shift+H）"),
    "粗體": ("Bold", "粗体", "太字"),
    "粗體（Ctrl+B）": ("Bold (Ctrl+B)", "粗体（Ctrl+B）", "太字（Ctrl+B）"),
    "斜體": ("Italic", "斜体", "斜体"),
    "斜體（Ctrl+I）": ("Italic (Ctrl+I)", "斜体（Ctrl+I）", "斜体（Ctrl+I）"),
    "指令": ("Command", "命令", "コマンド"),
    "插一段可一鍵複製的指令（Ctrl+Shift+C）": ("Insert a command block with a one-click copy button (Ctrl+Shift+C)", "插入一段可一键复制的命令（Ctrl+Shift+C）", "ワンクリックでコピーできるコマンドブロックを挿入（Ctrl+Shift+C）"),
    "唯讀": ("Read-only", "只读", "読み取り専用"),
    "存檔失敗：{0}": ("Save failed: {0}", "保存失败：{0}", "保存に失敗しました：{0}"),
    "已儲存 ": ("Saved ", "已保存 ", "保存済み "),
    "輸入中…": ("Typing…", "输入中…", "入力中…"),
    " 複製 ": (" Copy ", " 复制 ", " コピー "),
    " 已複製 ": (" Copied ", " 已复制 ", " コピー済み "),
    "這些筆記是較新版本（{0}）寫的，這個程式是 {1}。\n": ("These notes were written by a newer version ({0}); this program is {1}.\n", "这些笔记是较新版本（{0}）写的，这个程序是 {1}。\n", "これらのノートは新しいバージョン（{0}）で書かれています。このプログラムは {1} です。\n"),
    "舊版能讀多少讀多少；請更新程式再開，才不會把新格式的東西弄壞。": ("The old version reads what it can. Please update the program before editing, so the newer format is not damaged.", "旧版能读多少读多少；请更新程序再打开，以免破坏新格式的内容。", "旧バージョンでは読める範囲しか表示できません。新しい形式を壊さないよう、更新してから開いてください。"),
    "前一天（Ctrl+PgUp）": ("Previous day (Ctrl+PgUp)", "前一天（Ctrl+PgUp）", "前の日（Ctrl+PgUp）"),
    "後一天（Ctrl+PgDn）": ("Next day (Ctrl+PgDn)", "后一天（Ctrl+PgDn）", "次の日（Ctrl+PgDn）"),
    "收起／展開左欄（Ctrl+\\）": ("Hide / show the sidebar (Ctrl+\\)", "收起／展开左栏（Ctrl+\\）", "サイドバーの表示／非表示（Ctrl+\\）"),
    "回到今天": ("Go to today", "回到今天", "今日へ"),
    "新筆記": ("New note", "新笔记", "新しいノート"),
    "在這一天加一張（Ctrl+N）": ("Add a note on this day (Ctrl+N)", "在这一天加一张（Ctrl+N）", "この日にノートを追加（Ctrl+N）"),
    "插入檔案（複製一份到 attachments）": ("Insert a file (a copy goes into attachments)", "插入文件（复制一份到 attachments）", "ファイルを挿入（attachments にコピー）"),
    "清除…": ("Clear…", "清除…", "消去…"),
    "設定": ("Settings", "设置", "設定"),
    "搜尋中": ("Searching", "搜索中", "検索中"),
    " 今天": (" Today", " 今天", " 今日"),
    "筆記{0}": ("Note {0}", "笔记{0}", "ノート{0}"),
    "開啟": ("Open", "打开", "開く"),
    "複製到今天": ("Copy to today", "复制到今天", "今日にコピー"),
    "匯出這張…": ("Export this note…", "导出这张…", "このノートを書き出す…"),
    "刪除這張": ("Delete this note", "删除这张", "このノートを削除"),
    "清掉 {0} 整天": ("Clear the whole day {0}", "清掉 {0} 整天", "{0} の全ノートを消去"),
    "清除": ("Clear", "清除", "消去"),
    "清掉的東西會先搬到 .app/trash，不會直接消失。": ("Cleared notes are moved to .app/trash first, not deleted outright.", "清掉的内容会先移到 .app/trash，不会直接消失。", "消去したものは .app/trash に移動され、すぐには消えません。"),
    "清空目前這張": ("Clear this note", "清空当前这张", "このノートを空にする"),
    "清掉全部筆記": ("Clear all notes", "清掉全部笔记", "すべてのノートを消去"),
    "清掉 {0} 的 {1} 張筆記？": ("Clear the {1} note(s) of {0}?", "清掉 {0} 的 {1} 张笔记？", "{0} の {1} 件のノートを消去しますか？"),
    "清掉全部 {0} 張筆記？（附件保留）": ("Clear all {0} notes? (attachments are kept)", "清掉全部 {0} 张笔记？（附件保留）", "全 {0} 件のノートを消去しますか？（添付は残ります）"),
    "清除中": ("Clearing", "清除中", "消去中"),
    "{0}… {1}／{2}": ("{0}… {1} / {2}", "{0}… {1}／{2}", "{0}… {1}／{2}"),
    "插入檔案連結（會複製一份到 attachments）": ("Insert a file link (a copy goes into attachments)", "插入文件链接（会复制一份到 attachments）", "ファイルリンクを挿入（attachments にコピーされます）"),
    "這些沒收進來（不是 UTF-8 文字檔或是資料夾）：\n": ("These were not imported (not UTF-8 text, or a folder):\n", "这些没有导入（不是 UTF-8 文本文件或是文件夹）：\n", "次は取り込めませんでした（UTF-8 テキストでない、またはフォルダー）：\n"),
    "截圖存不進去：{0}": ("Could not save the screenshot: {0}", "截图保存失败：{0}", "スクリーンショットを保存できません：{0}"),
    "找不到：{0}": ("Not found: {0}", "找不到：{0}", "見つかりません：{0}"),
    "這張是空的或解不開，沒有東西可以匯出。": ("This note is empty or cannot be decrypted; nothing to export.", "这张是空的或解不开，没有内容可以导出。", "このノートは空か復号できないため、書き出すものがありません。"),
    "匯出這張筆記": ("Export this note", "导出这张笔记", "このノートを書き出す"),
    "純文字": ("Plain text", "纯文本", "テキスト"),
    "全部筆記要匯出到哪個資料夾（純文字）": ("Folder to export all notes to (plain text)", "全部笔记要导出到哪个文件夹（纯文本）", "全ノートの書き出し先フォルダー（テキスト）"),
    "匯出中": ("Exporting", "导出中", "書き出し中"),
    "已匯出 {0} 張筆記到\n{1}": ("Exported {0} note(s) to\n{1}", "已导出 {0} 张笔记到\n{1}", "{0} 件のノートを書き出しました：\n{1}"),
    "匯入筆記檔（可多選）": ("Import note files (multiple allowed)", "导入笔记文件（可多选）", "ノートファイルを取り込む（複数可）"),
    "全部": ("All", "全部", "すべて"),
    "不是 UTF-8 純文字，跳過：{0}": ("Not UTF-8 plain text, skipped: {0}", "不是 UTF-8 纯文本，跳过：{0}", "UTF-8 テキストではないためスキップ：{0}"),
    "要匯入的資料夾（匯出全部產生的那種）": ("Folder to import (the kind created by Export all)", "要导入的文件夹（导出全部生成的那种）", "取り込むフォルダー（「すべて書き出す」で作ったもの）"),
    "匯入中": ("Importing", "导入中", "取り込み中"),
    "匯入 {0} 張。": ("Imported {0} note(s).", "导入 {0} 张。", "{0} 件を取り込みました。"),
    "\n另有 {0} 張 .note 是別台電腦加密的，解不開，已跳過。": ("\n{0} .note file(s) were encrypted on another computer and were skipped.", "\n另有 {0} 张 .note 是别的电脑加密的，解不开，已跳过。", "\n別のパソコンで暗号化された .note が {0} 件あり、復号できないためスキップしました。"),
    "語言已改為 {0}，重新開啟程式後生效。": ("Language set to {0}. Restart the program to apply.", "语言已改为 {0}，重新打开程序后生效。", "言語を {0} に変更しました。再起動後に反映されます。"),
    "這個位置用不了：{0}\n{1}": ("This location cannot be used: {0}\n{1}", "这个位置无法使用：{0}\n{1}", "この場所は使えません：{0}\n{1}"),
    "加密中": ("Encrypting", "加密中", "暗号化中"),
    "解密中": ("Decrypting", "解密中", "復号中"),
    "程式出錯了（已記在 .app/error.log）：\n{0}": ("Something went wrong (logged in .app/error.log):\n{0}", "程序出错了（已记在 .app/error.log）：\n{0}", "エラーが発生しました（.app/error.log に記録）：\n{0}"),
    "這張筆記存不進去：{0}\n": ("This note could not be saved: {0}\n", "这张笔记无法保存：{0}\n", "このノートを保存できません：{0}\n"),
    "已另存救援檔：{0}\n\n仍要關閉？": ("A rescue copy was written to:\n{0}\n\nClose anyway?", "已另存救援文件：{0}\n\n仍要关闭？", "救済ファイルを保存しました：{0}\n\nそれでも閉じますか？"),
    "一般": ("Light", "一般", "ライト"),
    "跟隨系統": ("System", "跟随系统", "システムに従う"),
    "暗黑模式": ("Dark", "暗黑模式", "ダーク"),
    "Notion.bat 裡有填：": ("Set in Notion.bat: ", "Notion.bat 里有填：", "Notion.bat で設定済み："),
    "。這幾項以 .bat 為準，這裡改了下次用 .bat 開會被蓋回去；要在這裡改就把 .bat 裡那行留空。": (". Those follow the .bat; changes made here are overwritten next time you start from the .bat. To change them here, leave that line blank in the .bat.", "。这几项以 .bat 为准，这里改了下次用 .bat 打开会被覆盖；要在这里改就把 .bat 里那行留空。", "。これらは .bat の値が優先され、ここで変えても次回 .bat から起動すると戻ります。ここで変えるには .bat のその行を空にしてください。"),
    "外觀": ("Appearance", "外观", "外観"),
    "風格": ("Theme", "风格", "テーマ"),
    "語言": ("Language", "语言", "言語"),
    "－": ("－", "－", "－"),
    "＋": ("＋", "＋", "＋"),
    "字體大小（Ctrl+滾輪也可）": ("Font size (Ctrl+wheel also works)", "字体大小（Ctrl+滚轮也可）", "文字サイズ（Ctrl+ホイールでも可）"),
    "視窗永遠在最上層": ("Keep window on top", "窗口永远在最上层", "ウィンドウを常に手前に表示"),
    "啟動與安全": ("Startup & security", "启动与安全", "起動とセキュリティ"),
    "開機自動啟動": ("Run at Windows startup", "开机自动启动", "Windows 起動時に自動起動"),
    "加密存檔（綁這個 Windows 帳號；換電腦前先匯出）": ("Encrypt notes (tied to this Windows account; export before changing computers)", "加密存档（绑定这个 Windows 账户；换电脑前先导出）", "ノートを暗号化（この Windows アカウントに紐付け。PC を替える前に書き出してください）"),
    "存檔位置": ("Notes folder", "存档位置", "保存先"),
    "開啟資料夾": ("Open folder", "打开文件夹", "フォルダーを開く"),
    "更改位置…": ("Change…", "更改位置…", "変更…"),
    "垃圾桶": ("Trash", "回收站", "ごみ箱"),
    "匯入／匯出（純文字 .md）": ("Import / export (plain-text .md)", "导入／导出（纯文本 .md）", "取り込み／書き出し（テキスト .md）"),
    "匯出全部…": ("Export all…", "导出全部…", "すべて書き出す…"),
    "匯入檔案…": ("Import files…", "导入文件…", "ファイルを取り込む…"),
    "匯入資料夾…": ("Import folder…", "导入文件夹…", "フォルダーを取り込む…"),
    "匯入的筆記接在那一天後面編號，不會蓋掉既有的；換電腦前先「匯出全部」。": ("Imported notes are numbered after the existing ones for that day and never overwrite them. Use Export all before changing computers.", "导入的笔记接在那一天后面编号，不会覆盖已有的；换电脑前先“导出全部”。", "取り込んだノートはその日の末尾に番号付けされ、既存のものを上書きしません。PC を替える前に「すべて書き出す」を。"),
    "快捷鍵": ("Shortcuts", "快捷键", "ショートカット"),
    "紀錄與當機檔（回報問題時把這些一起給）": ("Logs & crash files (include these when reporting a problem)", "记录与崩溃文件（反馈问题时一并提供）", "ログとクラッシュファイル（問題報告時に添えてください）"),
    "程式紀錄 personalnote.log、卡死堆疊 crash.log": ("Program log personalnote.log, hang dump crash.log", "程序记录 personalnote.log、卡死堆栈 crash.log", "プログラムログ personalnote.log、フリーズ時のダンプ crash.log"),
    "關閉時存不進去的字（救援檔）": ("Text that could not be saved on close (rescue files)", "关闭时无法保存的文字（救援文件）", "終了時に保存できなかった文章（救済ファイル）"),
    "筆記的舊版本 history／垃圾桶 trash／畫面錯誤 error.log": ("Note history, trash, UI errors error.log", "笔记的旧版本 history／回收站 trash／界面错误 error.log", "ノートの履歴 history／ごみ箱 trash／画面エラー error.log"),
    "{0} {1}   開發：{2}": ("{0} {1}   Developer: {2}", "{0} {1}   开发：{2}", "{0} {1}   開発：{2}"),
    "立刻存（平常停 1.2 秒就自動存）": ("Save now (normally auto-saves 1.2 s after you stop typing)", "立刻保存（平常停 1.2 秒就自动保存）", "今すぐ保存（通常は入力停止 1.2 秒後に自動保存）"),
    "收起／展開左欄": ("Hide / show the sidebar", "收起／展开左栏", "サイドバーの表示／非表示"),
    "選取的字標黃底 ==重點== ／ 紅字 !!警告!!": ("Highlight selection ==like this== / red !!like this!!", "选中的字标黄底 ==重点== ／ 红字 !!警告!!", "選択部分を黄色 ==強調== ／ 赤字 !!警告!!"),
    "選取的字 **粗體** ／ *斜體*": ("Selection **bold** / *italic*", "选中的字 **粗体** ／ *斜体*", "選択部分を **太字** ／ *斜体*"),
    "插一段 ``` 指令區塊（右上角可一鍵複製）": ("Insert a ``` command block (one-click copy at the top right)", "插入一段 ``` 命令块（右上角可一键复制）", "``` コマンドブロックを挿入（右上でワンクリックコピー）"),
    "前一天／後一天": ("Previous / next day", "前一天／后一天", "前の日／次の日"),
    "Ctrl+滾輪、Ctrl+±": ("Ctrl+wheel, Ctrl+±", "Ctrl+滚轮、Ctrl+±", "Ctrl+ホイール、Ctrl+±"),
    "字體放大縮小": ("Zoom text in / out", "字体放大缩小", "文字の拡大／縮小"),
    "貼截圖（剪貼簿是圖就存成附件）": ("Paste a screenshot (an image on the clipboard is saved as an attachment)", "粘贴截图（剪贴板是图片就存为附件）", "スクリーンショットを貼り付け（クリップボードの画像を添付として保存）"),
    "Ctrl+點連結": ("Ctrl+click a link", "Ctrl+点击链接", "Ctrl+リンクをクリック"),
    "開網址或檔案路徑": ("Open a URL or file path", "打开网址或文件路径", "URL やファイルパスを開く"),
    "行首 1. 或 - 後 Enter": ("Enter after a line starting with 1. or -", "行首 1. 或 - 后 Enter", "行頭が 1. か - の行で Enter"),
    "自動接下一項，空項再 Enter 結束": ("Continues the list; Enter on an empty item ends it", "自动接下一项，空项再 Enter 结束", "次の項目を自動で続ける。空の項目で Enter すると終了"),
    "筆記列按右鍵": ("Right-click a note in the list", "笔记行点右键", "ノート一覧を右クリック"),
    "開啟、複製到今天、匯出、刪除、清整天": ("Open, copy to today, export, delete, clear the day", "打开、复制到今天、导出、删除、清整天", "開く、今日にコピー、書き出し、削除、その日を消去"),
    "拖檔案進視窗": ("Drag files into the window", "拖文件进窗口", "ファイルをウィンドウにドロップ"),
    ".md／.txt 匯成今天的筆記；其他檔變附件連結": (".md / .txt become today's notes; other files become attachment links", ".md／.txt 导入为今天的笔记；其他文件变成附件链接", ".md／.txt は今日のノートに、他のファイルは添付リンクに"),
    "筆記要存在哪個資料夾": ("Folder to keep the notes in", "笔记要保存在哪个文件夹", "ノートを保存するフォルダー"),
    "Notion.bat 裡的 NOTE_DIR 有設值，下次用 .bat 開會以它為準。\n": ("NOTE_DIR is set in Notion.bat; it wins next time you start from the .bat.\n", "Notion.bat 里的 NOTE_DIR 有设值，下次用 .bat 打开会以它为准。\n", "Notion.bat で NOTE_DIR が設定されているため、次回 .bat から起動するとそちらが優先されます。\n"),
    "要長期改位置，請把 .bat 裡的 NOTE_DIR 改掉或留空。": ("To change the location permanently, edit or blank NOTE_DIR in the .bat.", "要长期改位置，请把 .bat 里的 NOTE_DIR 改掉或留空。", "恒久的に変えるには .bat の NOTE_DIR を書き換えるか空にしてください。"),
    "關掉加密後，硬碟拔走就能直接讀到內容。確定？": ("With encryption off, anyone who takes the disk can read the notes. Continue?", "关掉加密后，硬盘拔走就能直接读到内容。确定？", "暗号化を切ると、ディスクを抜かれたら内容を読まれます。続けますか？"),
    "🔍 搜尋日期或內容": ("🔍 Search date or text", "🔍 搜索日期或内容", "🔍 日付や内容を検索"),
    "＋ 額外新增": ("＋ Add on another date", "＋ 额外新增", "＋ 別の日に追加"),
    "還沒有筆記\n按右邊的 ＋ 開第一張": ("No notes yet\nPress ＋ on the right to start one", "还没有笔记\n按右边的 ＋ 开第一张", "まだノートがありません\n右の ＋ で最初の一枚を"),
    "還有 {0} 張沒列出，用搜尋找": ("{0} more not listed; use search", "还有 {0} 张没列出，用搜索找", "他に {0} 件は表示されていません。検索を使ってください"),
    "顯示更多（還有 {0} 天）": ("Show more ({0} more days)", "显示更多（还有 {0} 天）", "もっと見る（あと {0} 日）"),
    "{0}（{1}）": ("{0} ({1})", "{0}（{1}）", "{0}（{1}）"),
    "（空白）": ("(empty)", "（空白）", "（空）"),
    "（解不開）": ("(cannot decrypt)", "（解不开）", "（復号不可）"),
    "# （解不開）\n這張筆記是別台電腦或別的 Windows 帳號加密的，這裡解不開。\n回到原來那台電腦，在設定裡「匯出全部」再搬過來。": ("# (cannot decrypt)\nThis note was encrypted on another computer or Windows account and cannot be opened here.\nGo back to the original computer, use Export all in Settings, then bring the files over.", "# （解不开）\n这张笔记是别的电脑或别的 Windows 账户加密的，这里解不开。\n回到原来那台电脑，在设置里“导出全部”再搬过来。", "# （復号不可）\nこのノートは別のパソコンまたは別の Windows アカウントで暗号化されており、ここでは開けません。\n元のパソコンで設定の「すべて書き出す」を使ってから持ってきてください。"),
    "# （較新版本的格式）\n這張筆記是比這個程式更新的版本寫的，這個版本看不懂。\n請更新 Notion 再開；不要在這裡改它。": ("# (newer format)\nThis note was written by a newer version of the program than this one.\nPlease update Notion before opening it; do not edit it here.", "# （较新版本的格式）\n这张笔记是比这个程序更新的版本写的，这个版本看不懂。\n请更新 Notion 再打开；不要在这里改它。", "# （新しい形式）\nこのノートはこのプログラムより新しいバージョンで書かれており、読めません。\nNotion を更新してから開いてください。ここでは編集しないでください。"),
    "{0} 行 · {1} 字": ("{0} lines · {1} chars", "{0} 行 · {1} 字", "{0} 行 · {1} 文字"),
    "已另存救援檔：{0}": ("A rescue copy was written to: {0}", "已另存救援文件：{0}", "救済ファイルを保存しました：{0}"),
    "刪除「{0}」？（會先搬到垃圾桶，設定裡可以還原）": ("Delete \"{0}\"? (It goes to the trash first; Settings can restore it)", "删除“{0}”？（会先移到回收站，设置里可以还原）", "「{0}」を削除しますか？（まずごみ箱に移動します。設定から復元できます）"),
    "垃圾桶是空的。": ("The trash is empty.", "回收站是空的。", "ごみ箱は空です。"),
    "還原上一次刪除": ("Restore last deleted", "还原上一次删除", "最後に削除したものを復元"),
    "這是可以執行的檔案：{0}\n確定要執行？": ("This file is executable:\n{0}\nRun it?", "这是可执行文件：{0}\n确定要运行？", "これは実行可能なファイルです：{0}\n実行しますか？"),
    "這個作業系統沒有加密功能，筆記是純文字檔。": ("Encryption is not available on this operating system; notes are plain text files.", "这个操作系统没有加密功能，笔记是纯文本文件。", "このOSでは暗号化は利用できません。ノートはテキストファイルとして保存されます。"),
    "{0} 有 {1} MB，複製進 attachments 會等一下，繼續？": ("{0} is {1} MB; copying it into attachments will take a moment. Continue?", "{0} 有 {1} MB，复制进 attachments 会等一下，继续？", "{0} は {1} MB あります。attachments へのコピーに時間がかかります。続けますか？"),
    "複製中": ("Copying", "复制中", "コピー中"),
    "一": ("Mon", "一", "月"),
    "二": ("Tue", "二", "火"),
    "三": ("Wed", "三", "水"),
    "四": ("Thu", "四", "木"),
    "五": ("Fri", "五", "金"),
    "六": ("Sat", "六", "土"),
    "日": ("Sun", "日", "日"),
}
JUNK = {"繁體中文原文", "清掉 {0} 張筆記？", "新句子", "re",      # 從 docstring 誤抓的，不是畫面字串
        "語言已改為 {0}，重新開啟程式後生效。"}                  # 已經不用重開了，這句拿掉


def main() -> int:
    rows = read_csv()
    for r in rows:
        r["zh_TW"] = (r.get("zh_TW") or "").replace("\\n", "\n")
    rows = [r for r in rows if r["zh_TW"] not in JUNK]
    if not any(r["zh_TW"] == "__name__" for r in rows):      # 每種語言在下拉選單的顯示名稱
        rows.insert(0, {"zh_TW": "__name__", "en": "EN", "zh_CN": "简中", "ja": "日本語", "note": "這列是語言的顯示名稱，不是句子"})
    filled = missing = 0
    for r in rows:
        tr = T.get(r["zh_TW"])
        if tr is None:
            missing += 1
            print("沒準備翻譯：", r["zh_TW"].replace("\n", "\\n")[:60])
            continue
        for col, val in zip(("en", "zh_CN", "ja"), tr):
            if not (r.get(col) or "").strip():
                r[col] = val
                filled += 1
    write_csv(rows)
    print(f"填了 {filled} 格；{missing} 句沒準備翻譯；表共 {len(rows)} 列 → {CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

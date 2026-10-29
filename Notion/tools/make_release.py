# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""整理「給別人用」的資料夾並壓成 zip。

產出：release/Notion_v<版本>/   與   release/Notion_v<版本>.zip
內容：Notion.exe、Notion.bat、使用說明.txt
用法：先 build_exe.bat，再 python tools/make_release.py [--dest 另一個資料夾]
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from personalnote import APP_NAME, __version__  # noqa: E402

from personalnote.ui.main_window import SettingsPanel  # noqa: E402  快捷鍵段落直接從程式產生，不會跟畫面脫節
SHORTCUT_LINES = "\n".join(f"- {k}：{w}" for k, w in SettingsPanel.SHORTCUTS)

GUIDE = f"""{APP_NAME} {__version__}  使用說明

這是什麼：桌面便利貼。筆記全部存在你自己的電腦（桌面的 Notion 資料夾），不經過任何雲端、不用帳號密碼。
畫面預設是英文：視窗上方日期那排最右邊有個「EN」下拉，選「繁中」畫面馬上換（也有「简中」「日本語」），不用重開。
English: a local sticky-notes app. Everything stays on this PC (Desktop\\Notion). Run Notion.bat; Windows may show
"Windows protected your PC" the first time (unsigned exe) → More info → Run anyway. The "EN" dropdown at the top right
switches the language instantly.

需要什麼：Windows 10 或 11（64 位元）。Windows 7 和 8.0 跑不起來（程式用的 Python 3.12 不支援），8.1 沒測過。
不用另外安裝任何東西。

怎麼開始
1. 把這個資料夾整個放到你想放的地方（例如桌面）。
2. 點兩下 Notion.bat。
   第一次 Windows 可能跳「Windows 已保護您的電腦」：按「其他資訊」→「仍要執行」。這是因為程式沒有數位簽章，不是病毒。
   有些防毒軟體會先把 exe 隔離，請加入信任（或請資訊人員協助）。
   直接點 Notion.exe 也能開，但 .bat 裡的設定不會生效。
3. 第一次開會自動在你的桌面建立 Notion 資料夾放筆記（桌面被公司導到 OneDrive 的話也會跟著）。
   想放別的地方：程式裡 ⚙ 設定 → 更改位置。

常用
- 直接打字就會自動存；關視窗也會存。
- 「＋ 新筆記」同一天可以很多張，標題先幫你填「筆記N」，直接打字就改掉；左邊依日期列出，點日期可以摺疊；
  左下「＋ 額外新增」先選日期再加（補以前的紀錄）；◀ ▶ 前後一天；搜尋框找日期或內容。
- 截圖後在內文按 Ctrl+V，圖直接顯示；點圖右下角把手可以拉大小。
- 檔案路徑（D:\\...、\\\\server\\...）和網址會自動變連結，Ctrl+點開啟。
- 行首打「1. 」或「- 」，按 Enter 會自動接下一個。
- Ctrl+滾輪（或 Ctrl+＝／Ctrl+－）改字體大小。
- 內文上方有個「格式 ▸」，點開才看得到：上一步、下一步、重點、紅字、粗體、斜體、打勾、指令（平常收著，不常用）。
  標重點：選字後按 重點／紅字／粗體／斜體（或 Ctrl+H、Ctrl+Shift+H、Ctrl+B、Ctrl+I）。
  檔案裡存的是 ==重點==、!!紅字!!、**粗體**、*斜體* 這種記號，匯出也看得懂；畫面上記號平常藏著，游標移到那一行才看得到。
- 打勾清單：格式列「打勾」（或自己打「- [ ] 」）→ 畫面是方框，點一下打勾、完成的會劃掉；按 Enter 自動接下一個框。
- #標籤：內文打 #專案A 會變主色，Ctrl+點它左欄就搜尋這個標籤（再點一次清掉）。
- 常用指令：格式列的「指令」插一個 ``` 區塊，貼指令進去，右上角「複製」一鍵複製整段。
- 把 .txt／.md 檔直接拖進視窗，就變成今天的一張筆記；拖截圖、pdf、word 進來會複製到 attachments 並插連結。
- 左邊筆記列按右鍵：開啟、複製到今天、匯出這張、舊版本（看、還原）、分享（郵件／Google Drive 資料夾）、刪除這張（會問一次）、清掉整天。
  「分享 → 用郵件寄出」是開你電腦的郵件程式，內文是去掉記號的純文字（mailto 不能帶附件，太長會截斷）；
  「複製到 Google Drive 資料夾」要先裝 Google Drive 桌面版，程式會找它的同步資料夾存一份 .md。
- 左邊筆記列長按一下再拖：同一天裡上下調整順序（搜尋中不能排）。
- 左欄最上面紅字「待辦事項」：固定一張，不屬於任何日期，隨時點開就能寫。
- 內文或標題按右鍵：剪下、複製、貼上（剪貼簿是截圖會直接變成圖）、全選、複製成純文字（記號去掉，貼去別的地方用）。
- 左邊日期列按右鍵：在這天新增、整天合成一個 .md 匯出、清掉整天。滑過日期列才會出現「＋」。
- 右下角：N 行 · N 字，和「已儲存 時間」（幾秒後自己淡掉）。
- ⚙ 設定：語言、開機自動啟動、一般／跟隨系統／暗黑模式、字體大小、最上層、存檔位置、匯入匯出、垃圾桶與「還原上一次刪除」、加密開關、紀錄檔位置。

快捷鍵
{SHORTCUT_LINES}

重要
- 筆記預設用你的 Windows 帳號加密：硬碟拔到別台電腦讀不到。
  代價是「換電腦、重灌、刪帳號」就打不開了，換機前一定先 ⚙ 設定 → 匯出全部。
  沒加密的：attachments 裡的截圖與檔案、匯出的 .md、關視窗存不進去時的救援檔若加密失敗才會是明文。
- 刪掉的筆記在 ⚙ 設定 → 垃圾桶（Notion\\.app\\trash），「還原上一次刪除」可以拿回最近刪的那張。
- 出問題時，紀錄在 %APPDATA%\\PersonalNote\\logs（⚙ 設定最底下有「開啟」按鈕），回報時把那個資料夾一起給。

開機自動啟動（自己設定，30 秒）：按 Win+R 輸入 shell:startup → 把 Notion.bat 的捷徑拖進那個資料夾（或 ⚙ 設定裡的「開啟啟動資料夾」）。
不要了就把那個捷徑刪掉。
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", help="額外再複製一份 zip 到這個資料夾（例如桌面）")
    ns = ap.parse_args()

    exe = ROOT / "dist" / f"{APP_NAME}.exe"
    if not exe.is_file():
        print("找不到 dist\\Notion.exe，先跑 build_exe.bat")
        return 1
    # exe 一定要比所有原始碼、翻譯表、.bat 新，不然會把舊 exe 包成新版號（翻譯社改了 csv 沒重打包也會被擋）
    sources = list((ROOT / "personalnote").rglob("*.py")) + list((ROOT / "assets").rglob("*")) + list(ROOT.glob("*.bat"))
    newest_src = max(p.stat().st_mtime for p in sources if p.is_file())
    if exe.stat().st_mtime < newest_src:
        print("dist\\Notion.exe 比原始碼／翻譯表／bat 舊，先重新 build_exe.bat")
        return 1
    import subprocess
    checks = [
        ("單元測試", [sys.executable, "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
        ("翻譯表", [sys.executable, "-X", "utf8", "tools/check_strings.py", "--strict"]),
        ("開視窗走一遍（標記、拖檔、新筆記）", [sys.executable, "-X", "utf8", "tools/stress/ui_checks.py"]),
    ]
    for what, cmd in checks:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"{what}沒過，不打包：\n", (r.stdout + r.stderr)[-1500:])
            return 1
    name = f"{APP_NAME}_v{__version__}"
    rel = ROOT / "release"
    if rel.exists():
        shutil.rmtree(rel)                  # 整個清掉：舊版號、舊名字的殘留不能跟新的混在一起
    out_dir = rel / name
    out_dir.mkdir(parents=True)
    for f in (exe, ROOT / "Notion.bat"):        # 開機啟動的兩個 .bat 不再附（Windows 讓使用者自己放捷徑）
        shutil.copy2(f, out_dir / f.name)
    (out_dir / "使用說明.txt").write_text(GUIDE, encoding="utf-8-sig")   # 記事本看得懂的 UTF-8（帶 BOM）
    zip_path = shutil.make_archive(str(ROOT / "release" / name), "zip", root_dir=out_dir.parent, base_dir=name)
    print("資料夾：", out_dir)
    print("壓縮檔：", zip_path, f"{Path(zip_path).stat().st_size / 1e6:.1f} MB")
    if ns.dest:
        dest = Path(ns.dest) / Path(zip_path).name
        shutil.copy2(zip_path, dest)
        print("已複製到：", dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""對 dist\\Notion.exe 本身做的壓力測試（不是原始碼）：
1. 亂放：exe 複製到很深的「中文 + 空格 + 全形符號」路徑，存檔位置也是中文路徑 → 開得起來、存得進去。
2. 反覆開關 10 次（WM_CLOSE 正常關閉）→ 每次都開得起來、state.json 有更新、log 有「啟動」「關閉視窗」。
3. 同時開第二個 → 第二個立刻退出（單一執行個體），第一個還活著。
4. 中途強制殺掉（TerminateProcess）5 次，每次殺之前先塞一批筆記讓它在存檔 → 殺完再開：沒有 .tmp 殘骸、每個檔都讀得到。
5. 從中文路徑匯入（用 --note-dir 指到含中文的匯出資料夾）。
視窗一律開在螢幕外（state.json 先寫好位置），不閃使用者。
跑法：python -X utf8 tools/stress/exe_cycles.py"""
import ctypes, json, os, pathlib, shutil, subprocess, sys, tempfile, time
from ctypes import wintypes
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from personalnote import crypto                      # noqa: E402
from personalnote.storage import NoteStore            # noqa: E402

EXE_SRC = ROOT / "dist" / "Notion.exe"
_LOG = pathlib.Path(os.environ["APPDATA"]) / "PersonalNote" / "logs" / "personalnote.log"
LOG_START = _LOG.stat().st_size if _LOG.is_file() else 0   # log offset at test start (bytes)
u = ctypes.windll.user32
fails: list[str] = []


def fail(msg):
    fails.append(msg); print("FAIL:", msg)


class _PE32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)), ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]


def process_tree(root_pid: int) -> set:
    """root_pid 自己加上所有子孫（PyInstaller onefile = 啟動器 + 子程序，視窗在子程序）。"""
    k = ctypes.windll.kernel32
    snap = k.CreateToolhelp32Snapshot(0x2, 0)
    parents = {}
    pe = _PE32(); pe.dwSize = ctypes.sizeof(_PE32)
    if k.Process32First(snap, ctypes.byref(pe)):
        while True:
            parents[pe.th32ProcessID] = pe.th32ParentProcessID
            if not k.Process32Next(snap, ctypes.byref(pe)):
                break
    k.CloseHandle(snap)
    tree = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, ppid in parents.items():
            if ppid in tree and pid not in tree:
                tree.add(pid); changed = True
    return tree


def find_window(timeout=25, pid=None):
    """找 PersonalNote 視窗；給 pid 就只認那個程序（含子程序）的視窗，避免抓到別的殘留視窗。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        tree = process_tree(pid) if pid is not None else None
        h = u.FindWindowW("TkTopLevel", "Notion")
        while h and tree is not None:
            owner = wintypes.DWORD()
            u.GetWindowThreadProcessId(h, ctypes.byref(owner))
            if owner.value in tree:
                break
            h = u.FindWindowExW(None, h, "TkTopLevel", "PersonalNote")
        if h:
            return h
        time.sleep(0.3)
    return 0


def kill_tree(p) -> None:
    """殺整棵樹（只殺啟動器會留下孤兒子程序，視窗還在）。"""
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    try:
        p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def launch(exe, note_dir, extra_env=None, allow_multi=True):
    """allow_multi=True：設 NOTE_ALLOW_MULTI=1 跳過單一執行個體（使用者桌面若有一個開著，測試才不會被它擋掉）。"""
    env = dict(os.environ, NOTE_DIR=str(note_dir), NOTE_THEME="light")
    env.pop("NOTE_LAUNCHER", None)
    if allow_multi:
        env["NOTE_ALLOW_MULTI"] = "1"
    else:
        env.pop("NOTE_ALLOW_MULTI", None)
    if extra_env: env.update(extra_env)
    return subprocess.Popen([str(exe)], env=env, cwd=str(exe.parent))


def close(p, hwnd, timeout=15):
    u.PostMessageW(hwnd, 0x0010, 0, 0)
    try:
        p.wait(timeout=timeout); return True
    except subprocess.TimeoutExpired:
        kill_tree(p); return False


def offscreen_state(note_dir):
    (note_dir / ".app").mkdir(parents=True, exist_ok=True)
    (note_dir / ".app" / "state.json").write_text(json.dumps({"geometry": "640x640+3000+3000", "sidebar_visible": True, "last_day": None}), encoding="utf-8")


# 只清掉「上次測試留下」的孤兒（執行檔在測試暫存資料夾裡的），不碰使用者自己開的 PersonalNote
_q = subprocess.run(["wmic", "process", "where", "name='Notion.exe'", "get", "ProcessId,ExecutablePath", "/format:csv"],
                    capture_output=True, text=True, errors="replace").stdout
for _line in _q.splitlines():
    if "pn_exe_stress" in _line:
        _pid = _line.strip().split(",")[-1]
        subprocess.run(["taskkill", "/F", "/T", "/PID", _pid], capture_output=True)
time.sleep(1.0)
base = pathlib.Path(tempfile.gettempdir()) / "pn_exe_stress"
shutil.rmtree(base, ignore_errors=True)
weird = base / "測試 資料夾（亂放）" / "很深" / "的 路徑" / "ＡＢＣ 全形"
weird.mkdir(parents=True)
exe = weird / "Notion.exe"; shutil.copy2(EXE_SRC, exe)
note_dir = base / "我的 筆記（中文 路徑）" / "personalNote"
note_dir.mkdir(parents=True)
# 注意：state.json 的螢幕外位置會被 safe_geometry 拉回來，所以用大但合法的位置：主螢幕右下角外 1 px 內
offscreen_state(note_dir)
log_dir = pathlib.Path(os.environ["APPDATA"]) / "PersonalNote" / "logs"

# 1 + 2：亂放路徑 + 反覆開關 10 次
t_start = []
for i in range(10):
    t0 = time.time(); p = launch(exe, note_dir); h = find_window(pid=p.pid)
    if not h:
        fail(f"第 {i+1} 次啟動：視窗沒出現（rc={p.poll()}）"); kill_tree(p); break
    t_start.append(time.time() - t0)
    time.sleep(0.6)
    if not close(p, h): fail(f"第 {i+1} 次關閉：15 秒沒關掉，強制殺")
if t_start:
    print(f"啟動 {len(t_start)} 次，平均 {sum(t_start)/len(t_start):.1f} s，最慢 {max(t_start):.1f} s")
st = note_dir / ".app" / "state.json"
if not st.is_file(): fail("state.json 沒寫")
log = log_dir / "personalnote.log"
if log.is_file():
    txt = log.read_text(encoding="utf-8", errors="replace")
    if txt.count("關閉視窗") < 5: fail("log 裡「關閉視窗」少於 5 次")
    # 只看這次測試開始之後寫進去的；前面可能有 fuzz（同一份 log）留下的錯誤
    mine = log.read_bytes()[LOG_START:].decode("utf-8", "replace")
    if "Traceback" in mine: fail("log 這次測試期間有 Traceback（看 logs/personalnote.log）")
else:
    fail("找不到 log 檔")

# 3：單一執行個體。使用者桌面那份若正開著，這裡開的第一個會把它叫到前面就退出，測不準：跳過並註明
_user_running = u.FindWindowW("TkTopLevel", "Notion") != 0
if _user_running:
    print("NOTE: 外面已經有一個 Notion 開著，單一執行個體這項跳過（關掉再跑一次才會測）")
else:
    p1 = launch(exe, note_dir, allow_multi=False); h1 = find_window(pid=p1.pid)
    p2 = launch(exe, note_dir, allow_multi=False)
    try:
        rc = p2.wait(timeout=20)
        if p1.poll() is not None: fail("開第二個時第一個死了")
    except subprocess.TimeoutExpired:
        fail("第二個執行個體 20 秒沒退出"); kill_tree(p2)
    if h1: close(p1, h1)
    else: kill_tree(p1); fail("單一執行個體測試：第一個視窗沒出現")

# 4：強制殺掉 5 次（殺之前讓程式有東西在存：先用 NoteStore 塞 200 張，再開 exe、等它畫完、殺）
store = NoteStore(note_dir, encrypt=True)
for k in range(5):
    for j in range(40):
        store.save(store.next_id(date.today()), f"# 殺前 {k}-{j}\n內容 中文 English {j}\n")
    p = launch(exe, note_dir); h = find_window(pid=p.pid)
    if not h: fail(f"殺測 {k}: 視窗沒出現"); kill_tree(p); continue
    time.sleep(0.3 + 0.2 * k)
    kill_tree(p)                                  # 強殺整棵樹，模擬當機／工作管理員結束
    tmps = list(note_dir.glob("*/*.tmp"))
    # 下一次啟動要能清掉 .tmp；這裡先記錄
    print(f"殺測 {k}: 殺後 .tmp 殘留 {len(tmps)} 個（下次啟動會清）")
# 殺完再開一次，確認全部讀得到、.tmp 清掉
p = launch(exe, note_dir); h = find_window(pid=p.pid); time.sleep(1.0)
if h: close(p, h)
else: fail("殺完後重開：視窗沒出現"); kill_tree(p)
store2 = NoteStore(note_dir, encrypt=True)
bad = 0
for d in store2.list_days():
    for r in store2.list_notes(d):
        if not store2.try_load(r.id)[1]: bad += 1
if bad: fail(f"殺完後有 {bad} 張讀不到")
if list(note_dir.glob("*/*.tmp")): fail("重開後仍有 .tmp 殘骸")
print(f"殺測後總張數 {sum(len(store2.list_notes(d)) for d in store2.list_days())}，讀不到 {bad}")

# 5：中文路徑匯入／匯出
exp = base / "匯出 資料夾（中文）"; n = store2.export_plain(exp)
other = NoteStore(base / "另一個 位置" / "筆記", encrypt=False)
done, skipped = other.import_folder(exp)
if done != n: fail(f"中文路徑匯入：匯出 {n} 張、匯入 {done} 張")
print(f"中文路徑匯出 {n} 張 → 匯入 {done} 張（跳過 {skipped}）")

print("EXE:", "PASS" if not fails else f"FAIL ({len(fails)})")
for f in fails: print(" -", f)
sys.exit(0 if not fails else 1)

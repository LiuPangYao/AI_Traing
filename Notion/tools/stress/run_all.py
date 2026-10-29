# -*- coding: utf-8 -*-
# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""一次跑完所有壓力測試，結果寫到 build/stress_report.txt。
順序：單元測試 → 六角色 → 中英文 → 大量資料 → 隨機亂按 → exe 反覆開關與強殺（要先有 dist/Notion.exe）。
視窗都開在螢幕外；跑的時候仍請不要強制關掉 python。"""
import pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
STEPS = [
    ("單元測試", [PY, "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
    ("六角色", [PY, "-X", "utf8", "tools/stress/personas.py", "build/persona_report.txt"]),
    ("中英文", [PY, "-X", "utf8", "tools/stress/lang.py"]),
    ("標記與拖檔", [PY, "-X", "utf8", "tools/stress/ui_checks.py"]),
    ("大量資料", [PY, "-X", "utf8", "tools/stress/big_data.py", "--days", "1500"]),
    ("隨機亂按", [PY, "-X", "utf8", "tools/stress/fuzz.py", "--steps", "2000"]),
    ("exe 開關強殺", [PY, "-X", "utf8", "tools/stress/exe_cycles.py"]),
]
report = ROOT / "build" / "stress_report.txt"
report.parent.mkdir(exist_ok=True)
lines = [f"Notion 壓力測試 {time.strftime('%Y-%m-%d %H:%M')}"]
all_ok = True
for name, cmd in STEPS:
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr)
    keep = [l for l in out.splitlines() if l.strip() and "invalid command name" not in l and "while executing" not in l
            and "after\" script" not in l and not l.startswith('"')]
    tail = "\n".join(keep[-12:])
    ok = r.returncode == 0
    all_ok &= ok
    lines.append(f"\n=== {name}：{'PASS' if ok else 'FAIL'}（{time.time()-t0:.0f} s）\n{tail}")
    print(f"{name}: {'PASS' if ok else 'FAIL'} ({time.time()-t0:.0f} s)")
lines.append(f"\n總結：{'全部通過' if all_ok else '有失敗，看上面'}")
report.write_text("\n".join(lines), encoding="utf-8")
print("報告：", report)
sys.exit(0 if all_ok else 1)

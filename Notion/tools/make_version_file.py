# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""產生 PyInstaller 的版本資源檔，讓 exe 的「內容」頁有版本號、產品名稱。
版本只在 personalnote/__init__.py 的 __version__ 一處維護；build_exe.bat 會先跑這個。
用法：python tools/make_version_file.py build/version_info.txt"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from personalnote import APP_NAME, __version__  # noqa: E402

parts = [int(p) for p in __version__.split(".")] + [0, 0, 0, 0]
v4 = tuple(parts[:4])
out = Path(sys.argv[1] if len(sys.argv) > 1 else "build/version_info.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={v4}, prodvers={v4}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040404B0', [
      StringStruct('CompanyName', 'Peter Liu'),
      StringStruct('FileDescription', '{APP_NAME} 桌面便利貼'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', '{APP_NAME}'),
      StringStruct('OriginalFilename', '{APP_NAME}.exe'),
      StringStruct('ProductName', '{APP_NAME}'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [1028, 1200])])
  ]
)
""", encoding="utf-8")
print("wrote", out, __version__)

# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""PyInstaller 的進入檔（build_exe.bat 用）。平常開發用 python -m personalnote。"""
import sys

from personalnote.app import main

sys.exit(main())

"""
PyInstaller runtime hook for Shioaji / pysolace.

`pysolace` wheel 會在 import 時透過 `__file__` 推算 `pysolace.libs` 的 DLL 目錄。
在 PyInstaller onefile 模式下，明確把 `_MEIPASS` 與 `pysolace.libs` 加入
Windows DLL 搜尋路徑，可降低 `_core.pyd` / `libsolclient*.dll` 載入失敗機率。
"""

import os
import sys


def _register_dll_dirs() -> None:
    if not hasattr(sys, "_MEIPASS"):
        return

    candidates = [
        sys._MEIPASS,
        os.path.join(sys._MEIPASS, "pysolace.libs"),
        os.path.join(sys._MEIPASS, "pysolace"),
        os.path.join(sys._MEIPASS, "shioaji"),
    ]

    existing = [path for path in candidates if os.path.isdir(path)]
    if not existing:
        return

    for path in existing:
        try:
            os.add_dll_directory(path)
        except (AttributeError, FileNotFoundError, OSError):
            pass

    current_path = os.environ.get("PATH", "")
    prefix = os.pathsep.join(existing)
    os.environ["PATH"] = prefix + (os.pathsep + current_path if current_path else "")


_register_dll_dirs()


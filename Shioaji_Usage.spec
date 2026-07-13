# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包規格檔 — 永豐金 API 用量評估工具

前置：
    pip install pyinstaller
    （使用專案指定環境：C:\\Users\\Alex\\anaconda3\\envs\\stock_rating\\python.exe）

打包：
    <python> -m PyInstaller Shioaji_Usage.spec
    產物在 dist 資料夾下，單一 exe（onefile）：
    dist/永豐金 API 用量評估工具 v<yyyyMMdd>.exe

注意：
    - shioaji / pysolace 執行時依 __file__ 找 DLL，必須以原始檔收集
      （module_collection_mode="py"）並搭配 runtime_hook_shioaji.py。
    - ttkbootstrap 的 Meter 元件用 PIL 畫圖，Pillow 不可排除。
"""

from datetime import datetime
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

project_root = Path(SPECPATH).resolve()
icon_file = project_root / "Shioaji_Usage.ico"
runtime_hook = project_root / "runtime_hook_shioaji.py"

# ── 建置日期：寫入 _build_date.txt 隨程式打包，供 utils.app_version() 讀取 ──
BUILD_DATE = datetime.now().strftime("%Y%m%d")
(project_root / "_build_date.txt").write_text(BUILD_DATE, encoding="utf-8")

datas = []
binaries = []
hiddenimports = []
excludes = []


def _append_unique(target, items):
    """用 list 比對避免遇到不可雜湊型別時 set() 失敗。"""
    for item in items:
        if item not in target:
            target.append(item)


def _collect_package(package_name: str) -> None:
    """完整收集 package 的程式、資料與二進位；未安裝只警告不失敗。"""
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name)
    except Exception as e:  # noqa: BLE001
        print(f"Warning: Failed to collect package '{package_name}': {e}")
        return
    _append_unique(datas, pkg_datas)
    _append_unique(binaries, pkg_binaries)
    _append_unique(hiddenimports, pkg_hiddenimports)


def _copy_metadata_safe(dist_name: str) -> None:
    try:
        _append_unique(datas, copy_metadata(dist_name))
    except Exception as e:  # noqa: BLE001
        print(f"Warning: Failed to copy metadata '{dist_name}': {e}")


# ── 本地資源檔 ────────────────────────────────────────────────

datas.append((str(icon_file), "."))                        # 視窗/工作列圖示
datas.append((str(project_root / "_build_date.txt"), "."))  # 打包日期

# ── GUI 套件（ttkbootstrap 的 Meter 依賴 Pillow）──────────────

for package_name in ("ttkbootstrap", "PIL"):
    _collect_package(package_name)

# ── Shioaji 與其常見依賴 ────────────────────────────────────

for package_name in (
    "shioaji",
    "pysolace",
    "orjson",
    "xxhash",
    "msgpack",
    "pydantic",
    "pydantic_core",
    "typing_inspection",
    "annotated_types",
    "nacl",
    "pyrsca",
    "filelock",
    "based58",
    "base58",
):
    _collect_package(package_name)

# ── 套件 metadata（shioaji 啟動時會查版本資訊）───────────────

for dist_name in (
    "ttkbootstrap",
    "Pillow",
    "shioaji",
    "pysolace",
    "pydantic",
    "pydantic_core",
    "typing-inspection",
    "annotated-types",
    "PyNaCl",
    "pyrsca",
    "filelock",
    "based58",
    "base58",
    "cryptography",
):
    _copy_metadata_safe(dist_name)

# ── 額外 hidden imports ─────────────────────────────────────

_append_unique(hiddenimports, [
    # tkinter / Pillow
    "tkinter",
    "tkinter.ttk",
    "tkinter.font",
    "tkinter.messagebox",
    "PIL._tkinter_finder",
    "PIL.Image",
    "PIL.ImageTk",
    "PIL.ImageDraw",

    # 金鑰加密：非 Windows 備援用 Fernet；Windows DPAPI 走 ctypes 免額外處理
    "cryptography.fernet",

    # 專案內模組（MVP 架構）
    "utils",
    "models.config_store",
    "models.shioaji_client",
    "models.usage_store",
    "views.main_view",
    "views.login_dialog",
    "presenters.usage_presenter",
])

# ── 排除用不到的大型套件，縮小體積（已確認 shioaji 匯入不依賴它們）──

_append_unique(excludes, [
    "pandas",
    "numpy",
    "matplotlib",
    "scipy",
    "IPython",
    "ipykernel",
    "jupyter_client",
    "notebook",
    "pytest",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "wx",
])


a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(runtime_hook)] if runtime_hook.exists() else [],
    excludes=excludes,
    noarchive=False,
    optimize=0,
    module_collection_mode={
        # pysolace / shioaji 在執行時會依 __file__ 找 DLL / libs
        "pysolace": "py",
        "shioaji": "py",
    },
)

pyz = PYZ(a.pure)

# ── onefile：單一 exe，桌面顯示「永豐金 API 用量評估工具 v<yyyyMMdd>」──

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f"永豐金 API 用量評估工具 v{BUILD_DATE}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # GUI 程式，不開主控台視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file),         # exe 檔本身的圖示
)

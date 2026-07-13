# -*- coding: utf-8 -*-
"""
utils — 共用工具與參數（MVP 架構的 utils 層）

- 資料目錄位置（DATA_DIR / init_data_dir）：程式同一層的 .data/
- 資源檔路徑（resource_path）：開發＝專案根；打包後＝PyInstaller _MEIPASS
- 應用程式名稱與版本（APP_NAME / app_version / app_title）
- human_bytes：bytes 轉人性化字串（儀表板顯示用）
"""

from __future__ import annotations

import sys
from pathlib import Path

# ═══════════════════ 資料目錄 ═══════════════════
# 所有程式產生的資料（config.json、secrets.bin、last_usage.json）放在
# 「程式同一層」的 .data/：原始碼執行＝專案根；PyInstaller 打包後＝exe 同層。


def _app_root() -> Path:
    if getattr(sys, "frozen", False):                  # PyInstaller 打包後
        return Path(sys.executable).resolve().parent   # exe 所在層
    return Path(__file__).resolve().parent             # utils.py 位於專案根


APP_ROOT = _app_root()
DATA_DIR = APP_ROOT / ".data"


def init_data_dir() -> None:
    """建立資料目錄（可冪等重跑）。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def resource_path(name: str) -> Path:
    """資源檔（如 Shioaji_Usage.ico）路徑：打包後在 _MEIPASS，原始碼在專案根。"""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / name
    return APP_ROOT / name


# ═══════════════════ 應用程式名稱與版本 ═══════════════════

APP_NAME = "永豐金 API 用量評估工具"
APP_AUTHOR = "Alex Yu"


def app_version() -> str:
    """版本字串 yyyyMMdd：打包後（frozen）讀隨附的 _build_date.txt（打包當日），
    原始碼開發時一律用今天日期（不讀根目錄殘留的 _build_date.txt）；讀檔失敗退今天。"""
    from datetime import date
    if getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None):
        try:
            txt = resource_path("_build_date.txt").read_text(encoding="utf-8").strip()
            if txt:
                return txt
        except Exception:  # noqa: BLE001 — 缺檔就退今天
            pass
    return date.today().strftime("%Y%m%d")


def app_title() -> str:
    """視窗標題：永豐金 API 用量評估工具 - by Alex Yu - v<yyyyMMdd>。"""
    return f"{APP_NAME} - by {APP_AUTHOR} - v{app_version()}"


# ═══════════════════ 顯示格式化 ═══════════════════

def human_bytes(n: int | float | None) -> str:
    """bytes 轉人性化字串：1536000 → '1.5 MB'；None/負值回 '—'。"""
    if n is None or n < 0:
        return "—"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"

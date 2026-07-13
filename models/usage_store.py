# -*- coding: utf-8 -*-
"""
models.usage_store — 上次查詢紀錄的持久化

只存最近 1 筆：.data/last_usage.json（整檔覆寫＝有更新時舊資料即刪除）。
欄位：queried_at（yyyy-MM-dd HH:mm:ss）、simulation、
      connections、bytes_used、limit_bytes、remaining_bytes
"""

from __future__ import annotations

import json

from utils import DATA_DIR

LAST_USAGE_FILE = DATA_DIR / "last_usage.json"


def save_last_usage(record: dict) -> None:
    """整檔覆寫最近 1 筆查詢紀錄。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAST_USAGE_FILE.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def load_last_usage() -> dict | None:
    """讀取上次查詢紀錄；檔案不存在或 JSON 壞掉回 None，不噴例外。"""
    try:
        return json.loads(LAST_USAGE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None

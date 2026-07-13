# -*- coding: utf-8 -*-
"""
models.config_store — 使用者設定與金鑰的持久化

- 一般設定（上次帳戶模式）：明文 JSON，存 .data/config.json
- 敏感金鑰（Shioaji API Key / Secret Key）：加密後存 .data/secrets.bin
    * Windows：DPAPI（CryptProtectData，綁定目前 Windows 使用者帳戶，無需自管金鑰）
    * 其他平台：cryptography Fernet，金鑰檔存 .data/.fernet_key

（實作沿用 Stock_Rating 專案的 config_store 模式）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from utils import DATA_DIR

CONFIG_DIR = DATA_DIR   # 統一資料目錄（程式同一層的 .data/）
CONFIG_FILE = CONFIG_DIR / "config.json"
SECRETS_FILE = CONFIG_DIR / "secrets.bin"

DEFAULT_CONFIG = {
    "simulation": False,   # 上次選擇的帳戶模式：False=真實、True=模擬
}


# ═══════════════════ 一般設定 ═══════════════════

def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════ 加密後端 ═══════════════════

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as _wt

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", _wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _dpapi(data: bytes, protect: bool) -> bytes:
        buf = ctypes.create_string_buffer(data, len(data))
        blob_in = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = _DATA_BLOB()
        fn = (ctypes.windll.crypt32.CryptProtectData if protect
              else ctypes.windll.crypt32.CryptUnprotectData)
        if not fn(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
            raise OSError("DPAPI 呼叫失敗（金鑰可能是在其他 Windows 帳戶下加密的）")
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)

    def _encrypt(data: bytes) -> bytes:
        return _dpapi(data, True)

    def _decrypt(data: bytes) -> bytes:
        return _dpapi(data, False)

else:  # 非 Windows：Fernet + 本機金鑰檔
    _KEY_FILE = CONFIG_DIR / ".fernet_key"

    def _fernet():
        from cryptography.fernet import Fernet
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not _KEY_FILE.exists():
            _KEY_FILE.write_bytes(Fernet.generate_key())
            _KEY_FILE.chmod(0o600)
        return Fernet(_KEY_FILE.read_bytes())

    def _encrypt(data: bytes) -> bytes:
        return _fernet().encrypt(data)

    def _decrypt(data: bytes) -> bytes:
        return _fernet().decrypt(data)


# ═══════════════════ 金鑰存取 ═══════════════════

def save_keys(api_key: str, secret_key: str) -> None:
    """加密保存 Shioaji 金鑰。空字串代表清除。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not api_key and not secret_key:
        SECRETS_FILE.unlink(missing_ok=True)
        return
    payload = json.dumps({"api_key": api_key, "secret_key": secret_key}).encode("utf-8")
    SECRETS_FILE.write_bytes(_encrypt(payload))


def load_keys() -> tuple[str, str]:
    """回傳 (api_key, secret_key)；無保存或解密失敗回傳 ("", "")。"""
    try:
        payload = json.loads(_decrypt(SECRETS_FILE.read_bytes()).decode("utf-8"))
        return payload.get("api_key", ""), payload.get("secret_key", "")
    except Exception:
        return "", ""

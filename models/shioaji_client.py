# -*- coding: utf-8 -*-
"""
models.shioaji_client — 永豐金 Shioaji API 連線與用量查詢

只保留本工具需要的功能：login / logout / get_usage。
- 登入固定 fetch_contract=False（本工具只查用量，不需合約；下載合約會耗流量且慢）
- shioaji 採函式內延遲匯入（import 慢且打包時體積大；onefile 模式下延遲匯入
  也能保留真正的匯入錯誤訊息，而不是在啟動階段被吞掉）
- 錯誤訊息以 explain_login_failure() 翻成中文，供 UI 顯示

（登入與錯誤解讀沿用 Stock_Scoring_Shioaji 專案的實作模式）
"""

from __future__ import annotations

import importlib
import os
import threading

from utils import DATA_DIR


# ═══════════════════ 錯誤訊息中文化 ═══════════════════

def explain_login_failure(exc: BaseException) -> str:
    text = str(exc).strip()
    lower = text.lower()

    if "permission denied (10013)" in lower or "tcp connection failure" in lower:
        return (
            "Shioaji 連線被作業系統拒絕（Windows 10013）。\n"
            "請確認 Windows 防火牆、公司代理、VPN 或資安軟體沒有阻擋本程式對外 TCP 連線。"
        )

    if "session connection attempt failed" in lower or "connected failed" in lower:
        return (
            "Shioaji 與永豐金主機的 TCP 連線建立失敗。\n"
            "這通常是網路、防火牆、代理或資安軟體限制，而不是憑證格式錯誤。"
        )

    if "topic: api/v1/auth/token_login" in lower and "payload:" in lower:
        return (
            "Shioaji 授權逾時：登入請求已送出，但等待永豐金授權主機回應時逾時。\n"
            "這通常是本機防火牆、公司代理、VPN 或資安軟體阻擋外連，"
            "不一定是 API Key / Secret Key 錯誤。"
        )

    if "invalid api key" in lower or "invalid secret key" in lower:
        return "Shioaji 驗證失敗：API Key 或 Secret Key 不正確。"

    if "importerror" in lower or "缺少相依模組" in lower or "dll" in lower:
        return f"Shioaji 模組載入失敗：{text}"

    return f"{type(exc).__name__}: {text}"


def login_retry_guidance(error_text: str) -> str:
    lower = error_text.lower()
    if "防火牆" in error_text or "tcp" in lower or "授權逾時" in error_text:
        return (
            "請先確認目前網路允許對外連線，再重試。\n"
            "可優先檢查：Windows 防火牆、公司代理 / VPN、資安軟體，"
            "或改用手機熱點做交叉測試。"
        )
    if "api key" in lower or "secret key" in lower or "驗證失敗" in error_text:
        return "請重新確認 API Key 與 Secret Key 後再查詢。"
    return "請確認憑證與網路狀態後再查詢。"


# ═══════════════════ 延遲匯入 shioaji ═══════════════════

_sj_module = None


def _load_shioaji():
    """延遲匯入 shioaji；失敗時把原始錯誤包進 ImportError 供 UI 顯示。"""
    global _sj_module
    if _sj_module is not None:
        return _sj_module
    # shioaji 預設把 shioaji.log 寫到工作目錄；改導向 .data/（需求：資料統一放 .data）
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("SJ_LOG_PATH", str(DATA_DIR / "shioaji.log"))
    try:
        _sj_module = importlib.import_module("shioaji")
        return _sj_module
    except Exception as exc:
        raise ImportError(
            "shioaji 匯入失敗，這通常不是單純『未安裝』，"
            f"而是缺少相依模組或 DLL。原始錯誤：{type(exc).__name__}: {exc}"
        ) from exc


# ═══════════════════ Shioaji 客戶端 ═══════════════════

class ShioajiClient:
    def __init__(self):
        self._api = None
        self._logged_in = False
        self._simulation = False
        self._lock = threading.Lock()   # 保護登入狀態（GUI 背景執行緒會呼叫）

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    @property
    def simulation(self) -> bool:
        return self._simulation

    def login(self, api_key: str, secret_key: str, simulation: bool = False) -> None:
        """
        登入永豐金 Shioaji API（fetch_contract=False：查用量不需合約資料）
        simulation=True  → 模擬帳戶
        simulation=False → 真實帳戶
        """
        sj = _load_shioaji()
        with self._lock:
            if self._logged_in:
                return
            try:
                self._api = sj.Shioaji(simulation=simulation)
                self._api.login(
                    api_key=api_key,
                    secret_key=secret_key,
                    fetch_contract=False,
                )
                self._simulation = simulation
                self._logged_in = True
            except Exception as e:
                self._api = None
                self._logged_in = False
                raise ConnectionError(explain_login_failure(e)) from e

    def logout(self) -> None:
        with self._lock:
            if self._api is not None:
                try:
                    self._api.logout()
                except Exception:  # noqa: BLE001 — 登出失敗不影響關閉流程
                    pass
            self._api = None
            self._logged_in = False

    def get_usage(self) -> dict:
        """
        查詢目前憑證的流量與連線數狀態（api.usage()）
        回傳欄位：
          connections     - 目前連線數（上限 5）
          bytes_used      - 今日已用流量 (bytes)
          limit_bytes     - 每日上限 (bytes)
          remaining_bytes - 剩餘流量 (bytes)
        模擬帳戶的欄位可能缺漏或為 None，一律以 0 帶入，不噴例外。
        """
        self._require_login()
        try:
            with self._lock:
                status = self._api.usage()
        except Exception as e:
            raise ConnectionError(f"流量查詢失敗：{e}") from e

        def _safe_int(value) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        return {
            "connections":     _safe_int(getattr(status, "connections", None)),
            "bytes_used":      _safe_int(getattr(status, "bytes", None)),
            "limit_bytes":     _safe_int(getattr(status, "limit_bytes", None)),
            "remaining_bytes": _safe_int(getattr(status, "remaining_bytes", None)),
        }

    def _require_login(self) -> None:
        if not self._logged_in or self._api is None:
            raise ConnectionError("尚未登入 Shioaji API，請先完成永豐金憑證設定")

# -*- coding: utf-8 -*-
"""
presenters.usage_presenter — 儀表板流程控制（MVP 的 Presenter 層）

流程（設計決策 D1–D4）：
- 啟動：讀 .data 上次紀錄顯示，不連線（D2）
- 查詢：未登入 → 有存金鑰直接登入、無金鑰跳對話框；登入固定 fetch_contract=False（D1）；
        成功後加密儲存金鑰、查 usage、覆寫上次紀錄；保持登入（D4）
- 金鑰設定：隨時可改；改完若已登入先登出（下次查詢用新金鑰/新模式）
- 關閉視窗：已登入則登出

login / usage 是網路呼叫，一律走背景執行緒，用 view.after() 回主執行緒更新 UI。
"""

from __future__ import annotations

import threading
from datetime import datetime

from models import config_store, usage_store
from models.shioaji_client import ShioajiClient, login_retry_guidance
from views.login_dialog import LoginDialog


class UsagePresenter:
    def __init__(self, view):
        self.view = view
        self.client = ShioajiClient()
        self.cfg = config_store.load_config()
        view.on_query = self.query
        view.on_settings = self.open_settings
        view.on_close = self.close

    # ── 啟動（D2：只讀上次紀錄，不連線）─────────────────────

    def start(self) -> None:
        self.view.render_usage(usage_store.load_last_usage())
        self.view.render_status(False)

    # ── 查詢 ──────────────────────────────────────────────────

    def query(self) -> None:
        if self.client.is_logged_in:
            self.view.set_busy(True)
            self._run_in_thread(self._fetch_usage_job)
            return

        api_key, secret_key = config_store.load_keys()
        simulation = bool(self.cfg.get("simulation", False))
        if not api_key or not secret_key:
            result = self._ask_credentials(api_key, secret_key, simulation)
            if result is None:
                return   # 使用者取消
            api_key, secret_key, simulation = result

        self.view.set_busy(True)
        self._run_in_thread(self._login_and_fetch_job, api_key, secret_key, simulation)

    def _login_and_fetch_job(self, api_key: str, secret_key: str, simulation: bool):
        """背景執行緒：登入（fetch_contract=False）→ 查 usage。"""
        try:
            self.client.login(api_key, secret_key, simulation=simulation)
        except (ConnectionError, ImportError) as e:
            self.view.after(0, self._on_login_failed, str(e))
            return
        # 登入成功：加密儲存金鑰＋記住帳戶模式（需求 3）
        self.view.after(0, self._save_credentials, api_key, secret_key, simulation)
        self._fetch_usage_job()

    def _fetch_usage_job(self):
        """背景執行緒：查 usage。失敗時保留畫面上的舊紀錄。"""
        try:
            usage = self.client.get_usage()
        except ConnectionError as e:
            self.view.after(0, self._on_usage_failed, str(e))
            return
        record = {
            "queried_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "simulation": self.client.simulation,
            **usage,
        }
        self.view.after(0, self._on_usage_ok, record)

    # ── 主執行緒回呼 ─────────────────────────────────────────

    def _save_credentials(self, api_key: str, secret_key: str, simulation: bool):
        config_store.save_keys(api_key, secret_key)
        self.cfg["simulation"] = simulation
        config_store.save_config(self.cfg)

    def _on_usage_ok(self, record: dict):
        usage_store.save_last_usage(record)   # 覆寫＝舊資料即刪除
        self.view.render_usage(record)
        self.view.render_status(True, self.client.simulation)   # 保持登入（D4）
        self.view.set_busy(False)

    def _on_login_failed(self, message: str):
        self.view.set_busy(False)
        self.view.render_status(False)
        self.view.show_error("登入失敗", f"{message}\n\n{login_retry_guidance(message)}")
        self.open_settings()   # 讓使用者立即修正金鑰

    def _on_usage_failed(self, message: str):
        self.view.set_busy(False)
        self.view.show_error("查詢失敗", message)

    # ── 金鑰設定 ─────────────────────────────────────────────

    def open_settings(self) -> None:
        api_key, secret_key = config_store.load_keys()
        result = self._ask_credentials(
            api_key, secret_key, bool(self.cfg.get("simulation", False)))
        if result is None:
            return
        new_key, new_secret, new_sim = result
        self._save_credentials(new_key, new_secret, new_sim)
        if self.client.is_logged_in:
            # 金鑰或模式已變更：登出，下次查詢以新設定重新登入（D4）
            self.client.logout()
            self.view.render_status(False)

    def _ask_credentials(self, key: str, secret: str, simulation: bool):
        dialog = LoginDialog(self.view, initial_key=key, initial_secret=secret,
                             initial_simulation=simulation)
        self.view.wait_window(dialog)
        return dialog.result

    # ── 關閉 ──────────────────────────────────────────────────

    def close(self) -> None:
        if self.client.is_logged_in:
            self.client.logout()
        self.view.destroy()

    # ── 工具 ──────────────────────────────────────────────────

    def _run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

# -*- coding: utf-8 -*-
"""
views.main_view — 主視窗儀表板（MVP 的 View 層，不含業務邏輯）

- 視窗預設位置/大小：螢幕 10%~60%（左上角 10%,10%；寬高各 50%），同時為最小尺寸
- 標題：utils.app_title()；圖示：Shioaji_Usage.ico（標題列 + Windows 工作列）
- 儀表板：登入狀態、流量儀表（Meter）、連線數、上次查詢時間、查詢/金鑰設定按鈕
- 與 presenter 的介面：on_query / on_settings / on_close callback，
  render_usage / render_status / set_busy / show_error 更新方法
"""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from tkinter import ttk, messagebox

import ttkbootstrap as tb

from utils import app_title, human_bytes, resource_path

ICON_PATH = resource_path("Shioaji_Usage.ico")
THEME = "cosmo"
FONT_UI = ("Microsoft JhengHei UI", 11)
FONT_SMALL = ("Microsoft JhengHei UI", 9)
FONT_BIG = ("Microsoft JhengHei UI", 13, "bold")

WARN_THRESHOLD = 80.0   # 用量 % 達此值儀表改警示色


class MainView(tb.Window):
    def __init__(self):
        if sys.platform == "win32":
            try:
                # 讓 Windows 工作列以本程式（而非 python.exe）識別視窗，
                # 工作列/Alt-Tab 才會顯示 Shioaji_Usage.ico 而非 Python 圖示
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "AlexYu.ShioajiUsage")
            except (AttributeError, OSError):
                pass
        # iconphoto=None：停用 ttkbootstrap 預設標題列圖（會蓋過 iconbitmap），
        # 改由下方 iconbitmap(default=) 套用 .ico（標題列/工作列/Alt-Tab 共用）
        super().__init__(themename=THEME, iconphoto=None)
        self.title(app_title())
        if ICON_PATH.exists():
            try:
                self.iconbitmap(default=str(ICON_PATH))
            except tk.TclError:
                pass  # 非 Windows 平台不支援 .ico，忽略

        # 視窗位置與大小（D5）：左上角在螢幕 10%,10%，寬高各 50%；同時為最小尺寸
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.5), int(sh * 0.5)
        self.geometry(f"{w}x{h}+{int(sw * 0.1)}+{int(sh * 0.1)}")
        self.minsize(w, h)

        # presenter 掛上的 callback
        self.on_query = None
        self.on_settings = None
        self.on_close = None

        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    # ── 版面 ──────────────────────────────────────────────────

    def _build_widgets(self):
        body = ttk.Frame(self, padding=24)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)   # 儀表區彈性吸收多餘空間

        # row=0：登入狀態列
        self._status_lbl = ttk.Label(body, text="● 未連線", font=FONT_UI,
                                     foreground="#7F8C8D")
        self._status_lbl.grid(row=0, column=0, sticky="w")

        # row=1：分隔線
        ttk.Separator(body, orient="horizontal").grid(
            row=1, column=0, sticky="ew", pady=(8, 0))

        # row=2：儀表區（流量 Meter 置中 + 右側數值明細）
        gauge_frame = ttk.Frame(body)
        gauge_frame.grid(row=2, column=0, sticky="nsew", pady=12)
        gauge_frame.columnconfigure(0, weight=1)
        gauge_frame.columnconfigure(1, weight=1)
        gauge_frame.rowconfigure(0, weight=1)

        self._meter = tb.Meter(
            gauge_frame,
            metersize=220,
            amounttotal=100,
            amountused=0,
            metertype="semi",
            subtext="今日流量用量",
            textright="%",
            bootstyle="info",
            interactive=False,
        )
        self._meter.grid(row=0, column=0, padx=(0, 16))

        detail = ttk.Frame(gauge_frame)
        detail.grid(row=0, column=1, sticky="w")
        self._used_lbl = ttk.Label(detail, text="已用流量：—", font=FONT_BIG)
        self._used_lbl.pack(anchor="w", pady=3)
        self._limit_lbl = ttk.Label(detail, text="每日上限：—", font=FONT_UI)
        self._limit_lbl.pack(anchor="w", pady=3)
        self._remain_lbl = ttk.Label(detail, text="剩餘流量：—", font=FONT_UI)
        self._remain_lbl.pack(anchor="w", pady=3)
        self._conn_lbl = ttk.Label(detail, text="目前連線數：— / 5", font=FONT_UI)
        self._conn_lbl.pack(anchor="w", pady=(12, 3))

        # row=3：上次查詢資訊列
        self._last_lbl = ttk.Label(body, text="尚無查詢紀錄", font=FONT_SMALL,
                                   foreground="#7F8C8D")
        self._last_lbl.grid(row=3, column=0, sticky="w", pady=(0, 10))

        # row=4：按鈕列
        btn_frame = ttk.Frame(body)
        btn_frame.grid(row=4, column=0, sticky="ew")
        btn_frame.columnconfigure(0, weight=3)
        btn_frame.columnconfigure(1, weight=1)
        self._query_btn = tb.Button(btn_frame, text="查詢", bootstyle="primary",
                                    command=self._handle_query)
        self._query_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=4)
        self._settings_btn = tb.Button(btn_frame, text="金鑰設定",
                                       bootstyle="secondary-outline",
                                       command=self._handle_settings)
        self._settings_btn.grid(row=0, column=1, sticky="ew", ipady=4)

    # ── callback 轉接 ─────────────────────────────────────────

    def _handle_query(self):
        if self.on_query:
            self.on_query()

    def _handle_settings(self):
        if self.on_settings:
            self.on_settings()

    def _handle_close(self):
        if self.on_close:
            self.on_close()
        else:
            self.destroy()

    # ── presenter 呼叫的更新方法 ─────────────────────────────

    def render_usage(self, record: dict | None) -> None:
        """更新儀表板。record=None → 尚無查詢紀錄。"""
        if record is None:
            self._meter.configure(amountused=0, bootstyle="info")
            self._used_lbl.config(text="已用流量：—")
            self._limit_lbl.config(text="每日上限：—")
            self._remain_lbl.config(text="剩餘流量：—")
            self._conn_lbl.config(text="目前連線數：— / 5")
            self._last_lbl.config(text="尚無查詢紀錄")
            return

        used = record.get("bytes_used", 0)
        limit = record.get("limit_bytes", 0)
        remain = record.get("remaining_bytes", 0)
        pct = (used / limit * 100) if limit > 0 else 0.0
        self._meter.configure(
            amountused=round(pct, 1),
            bootstyle="danger" if pct >= WARN_THRESHOLD else "info",
        )
        self._used_lbl.config(text=f"已用流量：{human_bytes(used)}")
        self._limit_lbl.config(text=f"每日上限：{human_bytes(limit)}")
        self._remain_lbl.config(text=f"剩餘流量：{human_bytes(remain)}")
        self._conn_lbl.config(
            text=f"目前連線數：{record.get('connections', '—')} / 5")
        mode = "模擬帳戶" if record.get("simulation") else "真實帳戶"
        self._last_lbl.config(
            text=f"上次查詢：{record.get('queried_at', '—')}（{mode}）")

    def render_status(self, logged_in: bool, simulation: bool = False) -> None:
        """更新登入狀態列。"""
        if logged_in:
            mode = "模擬帳戶" if simulation else "真實帳戶"
            self._status_lbl.config(text=f"● 已登入（{mode}）", foreground="#27AE60")
        else:
            self._status_lbl.config(text="● 未連線", foreground="#7F8C8D")

    def set_busy(self, busy: bool) -> None:
        """查詢中停用按鈕，防止連點。"""
        state = "disabled" if busy else "normal"
        self._query_btn.config(state=state)
        self._settings_btn.config(state=state)
        self._query_btn.config(text="查詢中…" if busy else "查詢")

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self)

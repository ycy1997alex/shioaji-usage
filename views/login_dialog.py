# -*- coding: utf-8 -*-
"""
views.login_dialog — 永豐金 API 金鑰設定對話框（MVP 的 View 層）

只負責收集輸入：關閉後 self.result = (api_key, secret_key, simulation) 或 None（取消）。
儲存與登入由 presenter 處理。
（版面沿用 Stock_Scoring_Shioaji 專案的 CredentialDialog 模式）
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox


class LoginDialog(tk.Toplevel):
    def __init__(self, parent, initial_key: str = "", initial_secret: str = "",
                 initial_simulation: bool = False):
        super().__init__(parent)
        self.title("🔑  永豐金證券 Shioaji API 金鑰設定")
        self.resizable(True, True)
        self.grab_set()
        self.result: tuple[str, str, bool] | None = None

        # 視窗大小自適應螢幕、置中
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(670, sw - 100), min(390, sh - 100)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.minsize(670, 390)

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(6, weight=1)   # row 6 是說明文字，彈性吸收多餘空間

        # row=0：標題
        ttk.Label(
            frame,
            text="永豐金證券 Shioaji API 憑證設定",
            font=("Microsoft JhengHei UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        # row=1：副標題
        ttk.Label(
            frame,
            text="API Key 與 Secret Key 請至 www.sinotrade.com.tw/newweb/PythonAPIKey/ 申請",
            foreground="#7F8C8D",
            font=("Microsoft JhengHei UI", 9),
            wraplength=540,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))

        # row=2：API Key
        ttk.Label(frame, text="API Key：").grid(row=2, column=0, sticky="w", pady=5)
        self._key_var = tk.StringVar(value=initial_key)
        ttk.Entry(frame, textvariable=self._key_var).grid(
            row=2, column=1, sticky="ew", pady=5, padx=8)

        # row=3：Secret Key（星號遮蔽）
        ttk.Label(frame, text="Secret Key：").grid(row=3, column=0, sticky="w", pady=5)
        self._secret_var = tk.StringVar(value=initial_secret)
        ttk.Entry(frame, textvariable=self._secret_var, show="*").grid(
            row=3, column=1, sticky="ew", pady=5, padx=8)

        # row=4：分隔線
        ttk.Separator(frame, orient="horizontal").grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=8)

        # row=5：帳戶模式（D3：保留模擬/真實切換）
        ttk.Label(frame, text="帳戶模式：").grid(row=5, column=0, sticky="w", pady=4)
        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=5, column=1, sticky="w", padx=8)
        self._simulation_var = tk.BooleanVar(value=initial_simulation)
        ttk.Radiobutton(
            mode_frame, text="🟢 真實帳戶",
            variable=self._simulation_var, value=False,
        ).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(
            mode_frame, text="🧪 模擬帳戶",
            variable=self._simulation_var, value=True,
        ).pack(side="left")

        # row=6：說明文字（彈性空間）
        ttk.Label(
            frame,
            text=(
                "金鑰會加密儲存於本機（綁定目前的 Windows 使用者帳戶），下次查詢免重輸。\n"
                "本工具登入時不下載合約資料，通常數秒內完成。"
            ),
            foreground="#7F8C8D",
            font=("Microsoft JhengHei UI", 8),
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="sw", pady=(6, 8))

        # row=7：按鈕列
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        btn_frame.columnconfigure((0, 1), weight=1)
        ttk.Button(btn_frame, text="確認", command=self._confirm).grid(
            row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(btn_frame, text="取消", command=self._cancel).grid(
            row=0, column=1, sticky="ew", padx=(4, 0))

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _confirm(self):
        k = self._key_var.get().strip()
        s = self._secret_var.get().strip()
        if not k or not s:
            messagebox.showwarning(
                "欄位不完整", "請填寫 API Key 與 Secret Key", parent=self)
            return
        self.result = (k, s, self._simulation_var.get())
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

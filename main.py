# -*- coding: utf-8 -*-
"""
永豐金 API 用量評估工具 — 主程式入口

組裝 MVP 各層：MainView（儀表板）＋ UsagePresenter（流程控制）。
啟動時只顯示 .data 的上次查詢紀錄，不自動連線（設計決策 D2）。
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils import init_data_dir
from views.main_view import MainView
from presenters.usage_presenter import UsagePresenter


def main() -> None:
    init_data_dir()
    view = MainView()
    presenter = UsagePresenter(view)
    presenter.start()
    view.mainloop()


if __name__ == "__main__":
    main()

# 永豐金 API 用量評估工具（Shioaji_Usage）— 開發者文件

## Overview（概觀）

查詢永豐金證券 Shioaji API 目前用量的桌面小工具：以單頁儀表板呈現「今日流量用量」與「目前連線數」。
啟動時只顯示 `.data` 內的上次查詢紀錄、不自動連線；使用者按「查詢」才登入取數。
登入固定 `fetch_contract=False`（查用量不需合約，可省流量與時間）；查詢後保持登入以佔用連線做後續快查，關閉視窗才登出。
金鑰以 Windows 帳戶綁定加密後落地，絕不明文儲存。以 PyInstaller 打包成單一無主控台 EXE 交付給終端使用者。

相關文件（任一份改動需連動檢查全部）：

- 開發者 UI 互動文件：`UI_README.html`（不啟動程式即可核對版面與互動是否做對）
- 終端使用者說明書：`UI_User_Guide.html`（終端使用者只會拿到它與 EXE）

## Architecture（架構）

採 **MVP（Model–View–Presenter）** 分層，跨層只透過 Presenter 橋接：

- **Model**（`models/`）：純資料與外部服務，**不 import tkinter**。負責金鑰／設定持久化、Shioaji 連線與用量查詢、上次紀錄存取。
- **View**（`views/`）：純 UI，**不 import shioaji、不碰檔案系統**。只暴露 callback 掛點與 `render_*/set_busy/show_error` 更新方法。
- **Presenter**（`presenters/`）：唯一的跨層橋樑。控制查詢／登入／設定／關閉流程，把 `login`／`usage` 這類網路呼叫丟背景執行緒，再用 `view.after()` 回主執行緒更新 UI。

```
[查詢按鈕] → view.on_query → presenter.query()
   ├─ 已登入 ─────────→ 背景執行緒 _fetch_usage_job → client.get_usage()
   └─ 未登入 ─ load_keys()
              ├─ 有金鑰 → 直接用存檔金鑰＋上次模式
              └─ 無金鑰 → 跳 LoginDialog（取消＝中止）
              → 背景執行緒 _login_and_fetch_job
                → client.login(fetch_contract=False)
                → save_keys()（加密）＋ save_config()（記住模式）
                → client.get_usage()
→ 組 record{queried_at, simulation, connections, bytes_used, limit_bytes, remaining_bytes}
→ view.after(0, ...) → usage_store.save_last_usage()（整檔覆寫＝舊資料即刪除）
→ view.render_usage() + render_status(True)（保持登入，D4）
```

## Directory structure（目錄結構）

```
Shioaji_Usage/
├─ main.py                      # 入口：init_data_dir → 組裝 MainView + UsagePresenter
├─ utils.py                     # 共用層：DATA_DIR(.data)/resource_path/app_title/human_bytes
├─ models/                      # Model：不碰 tkinter
│  ├─ config_store.py           #   設定(config.json 明文) + 金鑰(secrets.bin 加密) + DPAPI/Fernet 後端
│  ├─ shioaji_client.py         #   ShioajiClient(login/logout/get_usage) + 錯誤訊息中文化
│  └─ usage_store.py            #   上次查詢紀錄 last_usage.json（單筆、整檔覆寫）
├─ views/                       # View：不 import shioaji、不碰檔案系統
│  ├─ main_view.py              #   MainView：主視窗儀表板（Meter + 明細 + 按鈕）
│  └─ login_dialog.py           #   LoginDialog：金鑰設定對話框（Key/Secret/模擬切換）
├─ presenters/
│  └─ usage_presenter.py        # UsagePresenter：流程控制、背景執行緒、跨層唯一橋樑
├─ Shioaji_Usage.spec           # PyInstaller onefile 打包規格
├─ runtime_hook_shioaji.py      # 打包 runtime hook（把 _MEIPASS 加入 pysolace DLL 搜尋路徑）
├─ requirements.txt             # 相依套件版本鎖定
├─ _build_date.txt              # 打包當日 yyyyMMdd（spec 產生並隨包，frozen 時當版本號）
├─ Shioaji_Usage.ico / .png     # 應用程式圖示
└─ .data/                       # 執行期資料（見 Configuration；打包後在 EXE 同層）
```

## Setup & run（安裝與執行）

```powershell
# 1. 安裝相依套件（使用專案指定的 conda 環境）
& python.exe -m pip install -r requirements.txt

# 2. 開發執行
& python.exe main.py

# 3. 打包成單一 EXE（onefile、無主控台）
& python.exe -m PyInstaller Shioaji_Usage.spec --noconfirm
```

- 打包產物：`dist\永豐金 API 用量評估工具 v<yyyyMMdd>.exe`
- `yyyyMMdd`＝打包當日：spec 執行時寫入 `_build_date.txt` 一併打包；`utils.app_version()` 在 frozen 時讀它，開發時一律用今天日期。
- 視窗標題（開發與打包皆同）：`永豐金 API 用量評估工具 - by Alex Yu - v<yyyyMMdd>`
- 平台注意：僅在 Windows 驗證。金鑰加密在 Windows 走 DPAPI，其他平台改用 Fernet（見 Configuration）；`.ico` 圖示為 Windows 專屬，非 Windows 會忽略。

打包要點：

- `shioaji` / `pysolace` 用 `module_collection_mode="py"` 收集，再搭配 `runtime_hook_shioaji.py`：pysolace 執行時靠 `__file__` 找 DLL，onefile 模式需把 `_MEIPASS` 加入 DLL 搜尋路徑。
- ttkbootstrap 的 `Meter` 元件用 PIL 畫圖 → **Pillow 不可 exclude**。
- pandas / numpy / matplotlib 已確認 shioaji 匯入不依賴 → exclude 縮體積。

## Dependencies（相依套件）

版本鎖定於 `requirements.txt`；各套件選用理由：

| 套件 | 版本 | 為何選它 |
|---|---|---|
| `shioaji` | 1.5.5 | 永豐金官方 Python API，`api.usage()` 是本工具流量／連線數的唯一資料來源。 |
| `ttkbootstrap` | 1.20.4 | 為 tkinter 提供現代主題與 `Meter` 圓形儀表元件，免自繪即得儀表板外觀。 |
| `cryptography` | 49.0.0 | 非 Windows 平台的金鑰加密後端（Fernet）；Windows 走系統 DPAPI 不經此套件。 |
| `pyinstaller` | 6.21.0 | 打包成單一無主控台 EXE，讓終端使用者免安裝 Python 即可雙擊執行。 |
| Pillow (PIL) | 隨 ttkbootstrap | `Meter` 繪圖相依，非直接匯入但打包時不可排除。 |

## Configuration（設定與資料）

程式無需環境設定即可執行；所有執行期資料放在「程式同一層」的 `.data/`（原始碼執行＝專案根；打包後＝EXE 同層），由 `utils.init_data_dir()` 建立。

`.data/` 內容：

| 檔案 | 內容 | 格式 | 產生者 |
|---|---|---|---|
| `config.json` | 上次帳戶模式 `{"simulation": false}` | 明文 JSON | `config_store.save_config` |
| `secrets.bin` | API Key / Secret Key | **加密**二進位 | `config_store.save_keys` |
| `last_usage.json` | 最近 1 筆查詢紀錄 | 明文 JSON | `usage_store.save_last_usage` |
| `.fernet_key` | Fernet 金鑰（僅非 Windows） | 二進位 | `config_store._fernet` |
| `shioaji.log` | shioaji 函式庫日誌 | 文字 | shioaji（見下） |

環境變數：

- `SJ_LOG_PATH`：`shioaji_client._load_shioaji()` 以 `os.environ.setdefault` 設為 `.data/shioaji.log`，把 shioaji 預設寫到工作目錄的日誌導向 `.data/`，避免散落 EXE 同層。

金鑰存放與加密（**鐵律：金鑰絕不落地明文、絕不寫 log**）：

- **Windows**：DPAPI（`CryptProtectData` / `CryptUnprotectData`），綁定目前 Windows 使用者帳戶，無需自管金鑰。換電腦或換 Windows 帳戶後無法解密 → `load_keys()` 回 `("", "")` → 重新輸入即可。
- **非 Windows**：cryptography Fernet，金鑰檔 `.data/.fernet_key`（權限 `0o600`）。

## 圖示

- 執行時：`SetCurrentProcessExplicitAppUserModelID("AlexYu.ShioajiUsage")` + `iconbitmap(default=Shioaji_Usage.ico)`（標題列 / 工作列 / Alt-Tab 共用）。注意 ttkbootstrap 需以 `iconphoto=None` 建視窗，否則預設圖會蓋過 iconbitmap。
- exe 檔案圖示：spec 的 `EXE(icon=...)`。

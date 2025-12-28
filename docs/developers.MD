# Online Judge Backend – 開發人員 README

本專案為 OJ (Online Judge) 後端系統，使用 **Django + Django REST Framework** 實作。請依照本文指引統一開發流程與環境。

---

## 環境建置

### 1. Python 虛擬環境

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 資料庫遷移

每次更新資料表時都要進行。
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. 環境檔 `.env`

請複製 `.env.example` 為 `.env`，並依需求調整：

```env
# Django 基本設定
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=dev-secret
ALLOWED_HOSTS=127.0.0.1,localhost
DB_ENGINE=sqlite
CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173

# Celery 設定
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Sandbox API 設定
SANDBOX_API_URL=http://34.81.90.111:8000
SANDBOX_TIMEOUT=30
SANDBOX_API_KEY=happylittle7
```

#### 環境變數說明

**Django 基本設定：**
- `DJANGO_DEBUG`: 開發模式開關，正式環境須設為 `False`
- `DJANGO_SECRET_KEY`: Django 加密金鑰，請參考下方「如何產生 DJANGO_SECRET_KEY」
- `ALLOWED_HOSTS`: 允許的主機名稱，多個用逗號分隔
- `DB_ENGINE`: 資料庫引擎，開發用 `sqlite`，正式環境用 `postgresql`
- `CORS_ALLOWED_ORIGINS`: CORS 允許的來源，前端位址
- `CSRF_TRUSTED_ORIGINS`: CSRF 信任的來源 (如用 Session Auth)

**Celery 設定：**
- `CELERY_BROKER_URL`: Celery 訊息佇列位址，使用 Redis database 0
- `CELERY_RESULT_BACKEND`: Celery 結果儲存位址，使用 Redis database 0

**Sandbox API 設定：**
- `SANDBOX_API_URL`: Sandbox 判題系統 API 位址
- `SANDBOX_TIMEOUT`: API 請求超時時間（秒）
- `SANDBOX_API_KEY`: Sandbox API 認證金鑰
- `BACKEND_BASE_URL` = Backend 公開網址（用於 Sandbox callback）
#### 注意事項

- SQLite 用於本機測試；正式環境將改為 **PostgreSQL**
- 請勿將 `.env` 提交到 Git，已加入 `.gitignore`

---

## 啟動必要服務

本專案需要以下服務同時運行，**建議開啟 4 個終端視窗**分別執行：

### 終端 1: Redis（訊息佇列）

Redis 用於 Celery 的訊息佇列和結果儲存。

#### 方法 1: 使用 Docker（推薦）

```bash
# 確保 Docker Desktop 已啟動（看到頂部選單欄的 Docker 圖示）

# 啟動 Redis 容器
docker-compose -f docker-compose.redis.yml up -d

# 檢查 Redis 是否運行
docker ps | grep redis
```

#### 方法 2: 本機安裝 Redis

```bash
# macOS 使用 Homebrew
brew install redis
brew services start redis

# 或手動啟動
redis-server
```

**驗證 Redis 是否運行：**
```bash
redis-cli ping
# 應該回傳: PONG
```

---

### 終端 2: Celery Worker（非同步任務處理）

Celery 用於處理非同步任務（如提交判題、郵件發送等）。

```bash
# 確保已啟動 Redis
# 啟動 Celery Worker
celery -A back_end worker -l info

# 看到以下訊息表示成功：
# [tasks]
#   . submissions.tasks.submit_to_sandbox_task
#   . submissions.tasks.submit_selftest_to_sandbox_task
```

**注意事項：**
- Celery Worker 不會自動重新載入程式碼
- 修改 `tasks.py` 或相關程式碼後，需要**重啟 Celery Worker**
- 使用 `Ctrl+C` 停止，然後重新啟動

---

### 終端 3: Django 開發伺服器

```bash
python manage.py runserver
```

Django 會在 `http://localhost:8000` 啟動。

**API 文件：**
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`

---

### 終端 4: 測試或其他命令

保留一個終端用於執行測試、資料庫操作等。

```bash
# 執行測試
pytest

# 建立超級使用者
python manage.py createsuperuser

# 進入 Django Shell
python manage.py shell
```

---

## 快速啟動檢查清單

開發前請確認以下服務都已啟動：

- [ ] **Docker Desktop** 已開啟（如果使用 Docker 版 Redis）
- [ ] **Redis** 正在運行
  ```bash
  redis-cli ping  # 應回傳 PONG
  ```
- [ ] **Celery Worker** 正在運行
  ```bash
  # 檢查終端是否顯示 "celery@... ready."
  ```
- [ ] **Django Server** 正在運行
  ```bash
  curl http://localhost:8000/api/  # 應回傳 API 資訊
  ```

---

## 常見問題

### Q: Redis 連線失敗 "Connection refused"
**A:** 
1. 確認 Redis 是否啟動：`docker ps | grep redis` 或 `redis-cli ping`
2. 檢查 `.env` 中的 `CELERY_BROKER_URL` 設定是否正確
3. 如果使用 Docker，確保 Docker Desktop 已啟動

### Q: Celery 找不到任務
**A:**
1. 確認 Redis 已啟動
2. 檢查 `celery -A back_end worker -l info` 啟動日誌中是否有顯示任務列表
3. 修改程式碼後需要重啟 Celery Worker

### Q: Django 啟動失敗
**A:**
1. 確認已執行 `python manage.py migrate`
2. 檢查 `.env` 檔案是否存在且設定正確
3. 確認虛擬環境已啟動

### Q: Docker daemon 無法連接
**A:**
1. 手動開啟 Docker Desktop 應用程式
2. 等待 Docker 圖示出現在頂部選單欄且停止轉動
3. 執行 `docker info` 確認 Docker 已啟動

---

## Branch

* **main**：正式環境分支（最終 Demo 使用），僅組長/PM 可 merge。
* **dev**：開發主要分支，所有功能分支須合併回 dev。
* **feature branches**：每位開發者從 `dev` 開新分支，例如：

  * `feat/users-auth`
  * `fix/submissions-bug`

合併流程：

1. 從 `dev` 建立分支並開發。
2. 開發完成 → 提交 PR → Code Review。
3. 經組長審核後 **merge 回 dev**（在 DC @ 組長）。
4. 確認穩定後，由組長/PM merge dev → main。

---

## Commit 規則

格式：

```
type: subject
```

### type 可選：

* **feat**: 新增/修改功能。
* **fix**: 修補 bug。
* **docs**: 文件或註解。
* **refactor**: 重構（不影響功能）。
* **chore**: 環境設定（例如 requirements.txt 變更）。

### subject：簡述更動內容。

### 範例：

```bash
feat: add login backend support
fix: correct submission serializer bug
docs: update API usage in README
refactor: simplify course query logic
chore: update Django version to 5.0.1
```

**建議 commit 切細**，處理完一個段落就提交一次。

---

## 環境管理

本專案使用 **Python 虛擬環境**。

統一依賴請更新 `requirements.txt`：

```bash
pip freeze > requirements.txt
```

其他人只需：

```bash
pip install -r requirements.txt
```

即可同步環境。

---

## 專案架構（主要 apps）

* `users/` – 使用者管理與權限
* `auths/` – 認證與安全
* `courses/` – 課程與成員管理
* `problems/` – 題目管理
* `assignments/` – 作業系統
* `submissions/` – 提交與評測

---

## 開發流程總結

1. 從 `dev` 建立新 branch。
2. 完成功能後切細 commit。
3. 發 PR → Review → Merge 回 dev。
4. 由組長/PM 決定何時 merge dev → main。

---

## 備註

* 資料庫在開發測試階段使用 SQLite；部署時會切換到 PostgreSQL。
* `.venv/` 已加入 `.gitignore`，請勿提交虛擬環境檔案。
* 如需測試種子資料，請使用 `fixtures/` 並透過 `loaddata` 匯入。

---

## 如何產生 `DJANGO_SECRET_KEY`

> 請在本機 `.env` 產生並填入，不要把 `.env` 提交到 Git。

### 1) 使用 Django 內建工具

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

把輸出貼到 `.env`：

```env
DJANGO_SECRET_KEY= <貼上剛剛那串>
```

### 2) 不依賴 Django 的通用 Python 方式

```bash
python -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#$%^&*(-_=+)') for _ in range(64)))"
```

### 3) macOS / Linux（OpenSSL）

```bash
openssl rand -base64 48
```

### 4) Windows PowerShell

```powershell
[Convert]::ToBase64String((New-Object Byte[] 48 | %{$_=0}; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($args[0]); $args[0]))
```

### 注意事項

* `SECRET_KEY` 長度建議 50+，來源需隨機；請放入本機 `.env`。
* **不要**把正式環境的 `SECRET_KEY` 放進 repo；請用部署平台的 Secrets / 環境變數管理。
* 更換正式環境 `SECRET_KEY` 後既有 **Django session/CSRF** 會失效，使用者需重新登入。


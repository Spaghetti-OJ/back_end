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

### 4. 啟動伺服器

```bash
python manage.py runserver
```

### 5. 環境檔 `.env`

請複製 `.env.example` 為 `.env`，並依需求調整：

```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=dev-secret
ALLOWED_HOSTS=127.0.0.1,localhost
DB_ENGINE=sqlite
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

SQLite 用於本機測試；正式環境將改為 **PostgreSQL**。

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

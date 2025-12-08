# 認證與授權 API 文檔

本文檔涵蓋三個相關模組：**API Tokens**、**Authentication (auths)**、**Plagiarism Detection (copycat)**

---

## 📋 目錄

1. [全域回應格式](#全域回應格式)
2. [認證機制](#認證機制)
3. [API Tokens 管理](#api-tokens-管理)
4. [使用者認證](#使用者認證)
5. [登入日誌與活動追蹤](#登入日誌與活動追蹤)
6. [抄襲檢測 (MOSS)](#抄襲檢測-moss)
7. [錯誤處理](#錯誤處理)

---

## 全域回應格式

所有 API 端點都遵循統一的回應格式：

```json
{
  "data": <實際資料 (Object 或 Array)>,
  "message": "操作訊息",
  "status": "ok" | "error"
}
```

- **成功 (2xx)**：`status` 為 `"ok"`，`data` 包含請求的資源
- **失敗 (4xx/5xx)**：`status` 為 `"error"`，`message` 包含錯誤原因

---

## 認證機制

系統支援兩種認證方式：

### 1. Session 認證 (瀏覽器/Web 前端)

**適用場景：** 一般使用者在瀏覽器操作

**機制：**
- 登入後取得 `sessionid` Cookie
- 所有 **POST/PUT/DELETE** 請求必須在 Header 附帶 `X-CSRFToken`
- CSRF Token 從 `csrftoken` Cookie 讀取

**範例：**
```javascript
// 從 Cookie 讀取 CSRF Token
const csrfToken = document.cookie
  .split('; ')
  .find(row => row.startsWith('csrftoken='))
  ?.split('=')[1];

// 在請求中使用
fetch('/api/endpoint/', {
  method: 'POST',
  headers: {
    'X-CSRFToken': csrfToken,
    'Content-Type': 'application/json'
  },
  credentials: 'include',
  body: JSON.stringify(data)
});
```

### 2. API Token 認證 (CLI/自動化工具)

**適用場景：** CLI 工具、CI/CD、自動化腳本

**Header 格式：**
```
Authorization: Bearer noj_pat_xxxxxxxxxxxxxxxx
```

**範例：**
```bash
curl -H "Authorization: Bearer noj_pat_abc123..." \
     https://api.example.com/api-tokens/
```

---

## API Tokens 管理

**基礎路徑：** `/api-tokens/`

### 列出 API Tokens

```http
GET /api-tokens/
```

**權限：** 登入使用者

**回應範例：**
```json
{
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "name": "我的筆電 CLI Token",
      "prefix": "noj_pat_aBcD",
      "permissions": ["read:user", "read:problems"],
      "usage_count": 42,
      "last_used_at": "2025-10-18T10:30:00Z",
      "last_used_ip": "192.168.1.100",
      "created_at": "2025-10-10T08:00:00Z",
      "expires_at": null,
      "is_active": true,
      "is_expired": false
    }
  ],
  "message": "成功取得 Token 列表",
  "status": "ok"
}
```

### 建立 API Token

```http
POST /api-tokens/
```

**權限：** 登入使用者

**請求 Body：**
```json
{
  "name": "我的測試 Token",
  "permissions": ["read:user"],
  "expires_at": "2026-12-31T23:59:59Z"
}
```

**欄位說明：**
- `name` (必填)：Token 的描述性名稱
- `permissions` (選填)：權限範圍陣列，可用值：
  - `read:user`
  - `read:courses`, `write:courses`
  - `read:problems`, `write:problems`
  - `read:submissions`, `write:submissions`
- `expires_at` (選填)：過期時間 (ISO 8601 格式)

**成功回應 (201 Created)：**
```json
{
  "data": {
    "full_token": "noj_pat_aBcDeFgHiJkLmNoPqRsTuvWxyZ1234567890abcdef"
  },
  "message": "API Token 已建立，請妥善保存",
  "status": "ok"
}
```

> ⚠️ **重要：** `full_token` 只會顯示這一次，請立即儲存！

### 刪除 API Token

```http
DELETE /api-tokens/<uuid:id>/
```

**權限：** 登入使用者（只能刪除自己的 Token）

**成功回應 (200 OK)：**
```json
{
  "data": {},
  "message": "Token 已成功刪除",
  "status": "ok"
}
```

---

## 使用者認證

**基礎路徑：** `/auth/`

### 註冊新使用者

```http
POST /auth/signup/
```

**權限：** 公開 (AllowAny)

**請求 Body：**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password_123",
  "real_name": "John Doe",
  "role": "student",
  "student_id": "B12345678",
  "bio": "Computer Science student"
}
```

**欄位說明：**
- `username` (必填)：使用者名稱
- `email` (必填)：電子郵件
- `password` (必填)：密碼
- `real_name` (必填)：真實姓名
- `role` (必填)：角色，可選值依 User.Identity 定義
- `student_id` (選填)：學號
- `bio` (選填)：個人簡介

**成功回應 (201 Created)：**
```json
{
  "data": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "real_name": "John Doe",
    "role": "student"
  },
  "message": "OK",
  "status": "ok"
}
```

### 登入 (取得 Session Token)

```http
POST /auth/session/
```

**權限：** 公開 (AllowAny)

**請求 Body：**
```json
{
  "username": "john_doe",
  "password": "secure_password_123"
}
```

**成功回應 (200 OK)：**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

> 📝 **說明：** 使用 JWT (JSON Web Token) 機制
> - `access`: 短期存取 token (用於 API 請求)
> - `refresh`: 長期刷新 token (用於更新 access token)

### 刷新 Access Token

```http
POST /auth/refresh/
```

**請求 Body：**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**成功回應 (200 OK)：**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### 驗證 Token

```http
POST /auth/verify/
```

**請求 Body：**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**成功回應 (200 OK)：**
```json
{}
```

### 撤銷 Session (登出)

```http
POST /auth/session/revoke/
```

**權限：** 已認證使用者

**請求 Body：**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**成功回應 (205 Reset Content)：**
```json
{
  "data": {},
  "message": "Session revoked",
  "status": "ok"
}
```

### 取得當前使用者資訊

```http
GET /auth/me/
```

**權限：** 已認證使用者

**成功回應 (200 OK)：**
```json
{
  "data": {
    "user_id": "uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "student"
  },
  "message": "Get current user",
  "status": "ok"
}
```

---

## 登入日誌與活動追蹤

### 取得個人登入日誌

```http
GET /auth/login-logs/
```

**權限：** 已認證使用者（查看自己的日誌）

**成功回應 (200 OK)：**
```json
{
  "data": [
    {
      "id": 1,
      "username": "john_doe",
      "login_status": "成功",
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0 ...",
      "location": "Taipei, Taiwan",
      "created_at": "2025-11-25T12:00:00Z"
    }
  ],
  "message": "成功取得使用者登入日誌",
  "status": "ok"
}
```

### 記錄使用者活動

```http
POST /auth/activity/
```

**權限：** 已認證使用者

**用途：** 前端記錄使用者行為（例如：進入題目頁面、點擊下載）

**請求 Body：**
```json
{
  "activity_type": "view_problem",
  "description": "User viewed Problem 101",
  "metadata": {
    "problem_id": 101
  }
}
```

**可用的 activity_type：**
- `login` - 登入
- `logout` - 登出
- `submit` - 提交程式碼
- `view_problem` - 查看題目
- `download_testcase` - 下載測試資料

**成功回應 (201 Created)：**
```json
{
  "data": {
    "id": "uuid",
    "user": "uuid",
    "username": "john_doe",
    "activity_type": "view_problem",
    "description": "User viewed Problem 101",
    "ip_address": "127.0.0.1",
    "user_agent": "Mozilla/5.0 ...",
    "success": true,
    "created_at": "2025-11-25T12:00:00Z",
    "metadata": {
      "problem_id": 101
    }
  },
  "message": "活動記錄成功",
  "status": "ok"
}
```

---

## 管理員專用 API

> ⚠️ **權限要求：** 以下端點僅限管理員 (`is_staff=True`) 使用

### 查看特定使用者的登入日誌

```http
GET /auth/login-logs/<uuid:user_id>/
```

**權限：** 管理員

**成功回應：** 與個人登入日誌格式相同

### 查看特定使用者的活動記錄

```http
GET /auth/activity/<uuid:user_id>/
```

**權限：** 管理員

**成功回應：** 活動記錄陣列

### 查看異常登入活動

```http
GET /auth/suspicious-activities/
```

**權限：** 管理員

**用途：** 列出所有登入失敗記錄，用於資安審計

**查詢參數：**
- `page` (選填)：頁碼，預設為 1

**成功回應 (200 OK)：**
```json
{
  "data": {
    "count": 42,
    "next": "http://.../?page=2",
    "previous": null,
    "results": [
      {
        "id": 123,
        "username": "hacker",
        "login_status": "密碼錯誤",
        "ip_address": "192.168.1.100",
        "user_agent": "curl/7.68.0",
        "location": null,
        "created_at": "2025-11-28T12:00:00Z"
      }
    ]
  },
  "message": "成功取得異常登入紀錄列表",
  "status": "ok"
}
```

---

## 抄襲檢測 (MOSS)

**基礎路徑：** `/copycat/`

> ⚠️ **權限要求：** 此模組僅限管理員使用  
> 🔐 **驗證方式：** Session Cookie + CSRF Token

### 觸發抄襲檢測

```http
POST /copycat/
```

**權限：** 管理員

**說明：** 將指定題目的所有學生程式碼上傳至 Stanford MOSS 伺服器進行比對（非同步執行）

**請求 Body：**
```json
{
  "problem_id": 101,
  "language": "python"
}
```

**欄位說明：**
- `problem_id` (必填)：題目 ID
- `language` (選填)：程式語言，預設為 `"python"`
  - 支援：`c`, `cpp`, `java`, `python`, `javascript`

**成功回應 (202 Accepted)：**
```json
{
  "data": {
    "report_id": 15,
    "status": "pending"
  },
  "message": "已開始進行抄襲比對",
  "status": "ok"
}
```

**錯誤回應：**

**400 Bad Request** - 缺少參數或語言不支援：
```json
{
  "data": null,
  "message": "缺少 problem_id 參數",
  "status": "error"
}
```

**404 Not Found** - 題目不存在：
```json
{
  "data": null,
  "message": "題目 ID 101 不存在",
  "status": "error"
}
```

**429 Too Many Requests** - 已有進行中的任務：
```json
{
  "data": {
    "report_id": 15,
    "status": "pending"
  },
  "message": "該題目已有正在進行中的抄襲比對任務，請稍後再試",
  "status": "error"
}
```

### 查詢檢測報告

```http
GET /copycat/?problem_id=<int>
```

**權限：** 管理員

**說明：** 查詢指定題目的最新一份 MOSS 檢測報告

**查詢參數：**
- `problem_id` (必填)：題目 ID

**範例：** `GET /copycat/?problem_id=101`

**成功回應 - 處理中 (200 OK)：**
```json
{
  "data": {
    "id": 15,
    "status": "pending",
    "moss_url": null,
    "created_at": "2025-11-28T10:00:00Z",
    "error_message": ""
  },
  "message": "報告狀態：處理中",
  "status": "ok"
}
```

**成功回應 - 完成 (200 OK)：**
```json
{
  "data": {
    "id": 15,
    "status": "success",
    "moss_url": "http://moss.stanford.edu/results/9/8894923489/",
    "created_at": "2025-11-28T10:05:00Z",
    "error_message": ""
  },
  "message": "成功取得報告",
  "status": "ok"
}
```

> 💡 **提示：** 前端可直接使用 `moss_url` 在 iframe 或新視窗中顯示結果

**成功回應 - 失敗 (200 OK)：**
```json
{
  "data": {
    "id": 15,
    "status": "failed",
    "moss_url": null,
    "created_at": "2025-11-28T10:05:00Z",
    "error_message": "Connection to MOSS server timed out."
  },
  "message": "報告狀態：失敗",
  "status": "ok"
}
```

**錯誤回應 (404 Not Found)：**
```json
{
  "data": null,
  "message": "此題目尚未進行過抄襲比對",
  "status": "error"
}
```

---

## 錯誤處理

### 常見錯誤碼

| HTTP 狀態碼 | 說明 | 可能原因 |
|------------|------|---------|
| 400 | Bad Request | 請求參數錯誤或缺少必填欄位 |
| 401 | Unauthorized | 未提供認證資訊或認證失敗 |
| 403 | Forbidden | 沒有權限存取該資源 |
| 404 | Not Found | 資源不存在 |
| 429 | Too Many Requests | 請求過於頻繁 |
| 500 | Internal Server Error | 伺服器內部錯誤 |

### 錯誤回應格式

所有錯誤都遵循統一格式：

```json
{
  "data": null,
  "message": "詳細錯誤訊息",
  "status": "error"
}
```

### 欄位驗證錯誤

當請求 body 包含無效資料時：

```json
{
  "data": {
    "field_name": ["錯誤訊息1", "錯誤訊息2"]
  },
  "message": "資料驗證失敗",
  "status": "error"
}
```

**範例：**
```json
{
  "data": {
    "permissions": ["包含無效的權限範圍: read:invalid. 合法的權限為: read:user, read:courses, ..."]
  },
  "message": "資料驗證失敗",
  "status": "error"
}
```

---

## 附錄

### API Token 權限範圍 (Scopes)

| Scope | 說明 |
|-------|------|
| `read:user` | 讀取使用者資訊 |
| `read:courses` | 讀取課程資訊 |
| `write:courses` | 建立/修改課程 |
| `read:problems` | 讀取題目 |
| `write:problems` | 建立/修改題目 |
| `read:submissions` | 讀取提交記錄 |
| `write:submissions` | 提交程式碼 |

### 登入狀態類型

| 狀態值 | 顯示名稱 |
|--------|---------|
| `success` | 成功 |
| `failed_credentials` | 密碼錯誤 |
| `failed_user_not_found` | 用戶不存在 |
| `blocked_ip` | IP 被封鎖 |
| `blocked_account` | 帳號被停用 |

### 活動類型

| 類型值 | 顯示名稱 |
|--------|---------|
| `login` | 登入 |
| `logout` | 登出 |
| `submit` | 提交程式碼 |
| `view_problem` | 查看題目 |
| `download_testcase` | 下載測試測資 |

### MOSS 支援的程式語言

| API 參數值 | 語言名稱 | 檔案副檔名 |
|-----------|---------|-----------|
| `c` | C | `.c` |
| `cpp`, `cc`, `c++` | C++ | `.cpp` |
| `python`, `py` | Python | `.py` |
| `java` | Java | `.java` |
| `javascript`, `js` | JavaScript | `.js` |

---

## 更新日誌

### v1.0.0 (2025-12-01)
- 初始版本
- 整合 API Tokens、Authentication、Copycat 三個模組的文檔
- 統一回應格式說明
- 新增錯誤處理章節
- 新增附錄參考表格

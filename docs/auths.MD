# 後端 API 說明

本專案後端使用 **Django + Django REST Framework**，所有 API 採 **JSON** 傳輸。

> 本文件涵蓋「API Tokens」與「Auths (日誌)」相關端點。

-----

## 認證 (Authentication)

本後端使用 **Session 認證** (`SessionAuthentication`)。

這意味著前端在呼叫 API 之前**必須先登入**，並在請求 (Request) 中附帶有效的 `sessionid` Cookie。

###  關於 CSRF Token

由於使用 `Session` 認證，所有**會修改資料**的請求（`POST`, `PUT`, `DELETE`）都必須附帶 `X-CSRFToken` 標頭 (Header) 來防止 CSRF 攻擊。

  * **前端 Web App (同網域)：**
    1.  Django 會在登入時自動設定一個 `csrftoken` cookie。
    2.  前端在發送 `POST` 等請求時，需要**讀取這個 cookie 的值**。
    3.  將這個值放入 HTTP 請求標頭：`X-CSRFToken: "your_csrf_token_value_here"`。
  * **Postman / cURL 測試：**
    1.  你需要先登入 (例如 `POST /api-auth/login/` 或 `/admin/`) 以取得 `sessionid` 和 `csrftoken`。
    2.  在 cURL 中，你需要同時附帶 `-H "Cookie: sessionid=...; csrftoken=..."` 和 `-H "X-CSRFToken: ..."`。

-----

## 1\. API Tokens API (App: `api_tokens`)

**基礎路徑**：`/api-tokens/`

### 1.1 列出 API Tokens

**路徑**：`GET /api-tokens/`

**說明**：取得**當前登入使用者**的所有 API Tokens 的元數據。

**權限**：使用者必須為登入狀態 (Authenticated)。

**回應格式 (200, JSON)**：

```json
[
    {
        "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "name": "我的筆電 CLI Token",
        "prefix": "ojt_aBcD", 
        "permissions": ["submission:create", "problem:read"],
        "created_at": "2025-10-10T08:00:00Z",
        "expires_at": "2026-10-10T08:00:00Z"
        // ... 其他舊文件中提到的欄位 (last_used_at 等，取決於你的 Serializer)
    },
    {
        "id": "f1e2d3c4-b5a6-9876-5432-10fedcba9876",
        "name": "CI/CD 專用 Token",
        "prefix": "ojt_xYzW",
        "permissions": [],
        "created_at": "2025-09-01T00:00:00Z",
        "expires_at": null
    }
]
```

**失敗回應 (401/403, JSON)**：

```json
{
    "detail": "Authentication credentials were not provided."
}
```

-----

### 1.2 建立 API Token

**路徑**：`POST /api-tokens/`

**說明**：為當前登入的使用者建立一個新的 API Token。

**權限**：使用者必須為登入狀態 (Authenticated)。

**請求格式 (JSON)**：
| 欄位名 | 型別 | 必填 | 說明 |
| --- | --- | :-: | --- |
| `name` | string | ✅ | Token 的自訂名稱，方便使用者識別。 |
| `permissions` | array (of strings) | ❌ | (保留欄位) |
| `expires_at` | string (ISO 8601) | ❌ | 過期時間 (例如 `YYYY-MM-DDTHH:MM:SSZ`)。 |

**請求範例**：

```json
{
    "name": "我的 VS Code 開發工具"
}
```

**回應格式 (201, JSON)**：

**重要**：`full_token` 只會在此次建立成功時回傳**一次**，前端務必提示使用者妥善保存。

```json
{
    "message": "API Token created...",
    "full_token": "ojt_aBcDeFgHiJkLmNoPqRsTuvWxyZ1234567890abcdef"
}
```

**失敗回應 (400, JSON)**：

```json
{
    "name": [ "This field is required." ]
}
```

-----

### 1.3 刪除 API Token

**路徑**：`DELETE /api-tokens/<uuid:id>/`

**說明**：刪除一個屬於當前登入使用者的指定 API Token。

**權限**：使用者必須為登入狀態 (Authenticated)。

**URL 參數**：
| 參數 | 型別 | 必填 | 說明 |
| --- | --- | :-: | --- |
| `id` | uuid | ✅ | 要刪除的 Token 的 `id` (UUID 格式)。 |

**請求格式**：
此請求無需附帶任何 Body。

**回應格式**：

  * **成功回應 (204 No Content)**：
    (伺服器不返回任何內容，代表刪除成功)

  * **失敗回應 (404 Not Found)**：
    (Token 不存在，或不屬於目前的使用者)

    ```json
    {
        "detail": "Not found."
    }
    ```

**cURL 測試 (包含 CSRF)**：

```bash
# 假設你的 UUID 是 a1b2c3d4-e5f6-7890-1234-567890abcdef
curl -X DELETE http://127.0.0.1:8000/api-tokens/a1b2c3d4-e5f6-7890-1234-567890abcdef/ \
  -H "Cookie: sessionid=your_session_id_here; csrftoken=your_csrf_token_here" \
  -H "X-CSRFToken: your_csrf_token_here"
```

-----

-----

## 2\. Auths API (App: `auths`)

**基礎路徑**：`/auth/`

### 2.1 列出登入日誌

**路徑**：`GET /auth/login-logs/`

**說明**：取得系統中**所有使用者**的登入日誌。

**🚨 權限**：**僅限管理員 (Admin)**。 (`is_staff = True`)

  * 一般使用者 (包含 student) 呼叫此 API 會收到 `403 Forbidden`。
  * 前端在開發時，請確保使用**管理員帳號**登入測試。

**回應格式 (200, JSON)**：

```json
[
    {
        "id": 1,
        "user": "blanktsai", // 登入成功的 User (如果失敗則為 null)
        "username": "blanktsai", // 嘗試登入的帳號
        "login_status": "成功", // 人類可讀的狀態
        "ip_address": "127.0.0.1",
        "user_agent": "Mozilla/5.0 ...",
        "location": null,
        "created_at": "2025-11-08T00:15:00Z"
    },
    {
        "id": 2,
        "user": null,
        "username": "admin_hacker",
        "login_status": "密碼錯誤", // 人類可讀的狀態
        "ip_address": "10.20.30.40",
        "user_agent": "Python/3.11 ...",
        "location": "Taipei",
        "created_at": "2025-11-08T00:10:00Z"
    }
]
```

**失敗回應 (403 Forbidden, JSON)**：

  * 當登入者不是管理員時：
    ```json
    {
        "detail": "You do not have permission to perform this action."
    }
    ```



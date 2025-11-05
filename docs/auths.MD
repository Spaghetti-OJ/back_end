# 後端 API 說明（提供給前端）

本專案後端使用 **Django + Django REST Framework + Simple JWT**，所有 API 採 **JSON** 傳輸。

> 本文件僅涵蓋「使用者認證」端點；**目前不啟用 reCAPTCHA**。

---

## Auths API 文件

### **通用設定**

所有 `Auths` 相關的 API 都需要使用者處於登入狀態。在測試時，請先透過瀏覽器登入網站後台 (`/admin/`) 以取得有效的 `sessionid` cookie，並在 cURL 或其他工具的請求中附帶此 cookie。

---

## 列出 API Tokens API

**路徑**：`GET /auth/me/api-tokens/`

**說明**：取得當前登入使用者的所有 API Tokens 的元數據。

**權限**：使用者必須為登入狀態 (Authenticated)。

### 請求格式

此請求無需附帶任何 Body。

### 回應格式

**成功回應（200, JSON）**

回應一個包含多個 Token 物件的陣列。`is_expired` 為後端根據 `expires_at` 動態計算的布林值。

```json
[
    {
        "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "name": "我的筆電 CLI Token",
        "prefix": "ctp_aBcD",
        "permissions": ["submission:create", "problem:read"],
        "usage_count": 42,
        "last_used_at": "2025-10-18T10:30:00Z",
        "last_used_ip": "192.168.1.100",
        "created_at": "2025-10-10T08:00:00Z",
        "expires_at": "2026-10-10T08:00:00Z",
        "is_active": true,
        "is_expired": false
    },
    {
        "id": "f1e2d3c4-b5a6-9876-5432-10fedcba9876",
        "name": "CI/CD 專用 Token",
        "prefix": "ctp_xYzW",
        "permissions": [],
        "usage_count": 108,
        "last_used_at": "2025-10-17T05:00:00Z",
        "last_used_ip": "10.0.0.5",
        "created_at": "2025-09-01T00:00:00Z",
        "expires_at": null,
        "is_active": true,
        "is_expired": false
    }
]
```

**失敗回應（403 Forbidden, JSON）**

*   使用者未登入：
    ```json
    {
        "detail": "Authentication credentials were not provided."
    }
    ```

### cURL 測試

**注意**：請先登入網站，然後從瀏覽器的開發者工具中找到 `sessionid` cookie 的值，替換掉下面的 `your_session_id_here`。

```bash
curl -X GET http://127.0.0.1:8000/auth/me/api-tokens/ \
  -H "Cookie: sessionid=your_session_id_here"
```

---

## 建立 API Token API

**路徑**：`POST /auth/me/api-tokens/`

**說明**：為當前登入的使用者建立一個新的 API Token。

**權限**：使用者必須為登入狀態 (Authenticated)。

### 請求格式（JSON）

| 欄位名         | 型別               |  必填 | 說明                                                                 |
| -------------- | ------------------ | :-: | -------------------------------------------------------------------- |
| `name`         | string             |  ✅  | Token 的自訂名稱，最多 100 字元，方便使用者識別。                           |
| `permissions`  | array (of strings) |  ❌  | Token 的權限範圍 (Scopes)，例如 `["submission:create"]`。目前為保留欄位。 |
| `expires_at`   | string             |  ❌  | Token 的過期時間，ISO 8601 格式 (例如 `YYYY-MM-DDTHH:MM:SSZ`)。         |

**請求範例**：

*   基本請求：
    ```json
    {
      "name": "我的 VS Code 開發工具"
    }
    ```
*   帶有選填欄位的請求：
    ```json
    {
      "name": "自動化部署腳本",
      "permissions": ["submission:create", "problem:read"],
      "expires_at": "2026-12-31T23:59:59Z"
    }
    ```

### 回應格式

**成功回應（201, JSON）**

**極度重要**：`full_token` 只會在此次建立成功時回傳**一次**，後端不會儲存完整 Token，前端務必提示使用者妥善保存。

```json
{
    "message": "API Token created successfully. Please save it securely, as it will not be shown again.",
    "full_token": "ctp_aBcDeFgHiJkLmNoPqRsTuvWxyZ1234567890abcdef"
}
```

**失敗回應（400, JSON）**

*   `name` 欄位未填：
    ```json
    {
        "name": [
            "此為必需欄位。"
        ]
    }
    ```
*   `expires_at` 格式錯誤：
    ```json
    {
        "expires_at": [
            "日期時間格式錯誤。請使用ISO 8601格式。"
        ]
    }
    ```

### cURL 測試

```bash
curl -X POST http://127.0.0.1:8000/auth/me/api-tokens/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=your_session_id_here" \
  -H "X-CSRFToken: your_csrf_token_here" \
  -d '{
    "name": "我的 cURL 測試 Token"
  }'
```

**關於 `X-CSRFToken`**：
由於我們使用 `SessionAuthentication`，DRF 的可瀏覽 API 會自動處理 CSRF Token。但若前端是從不同來源（網域）的腳本呼叫 API，則需要從 `csrftoken` cookie 中獲取此值，並將其放入 `X-CSRFToken` 請求標頭中。這是 Django 的標準安全機制。

# 後端 API 說明（提供給前端）

本專案後端使用 **Django + Django REST Framework + Simple JWT**，所有 API 採 **JSON** 傳輸。

> 本文件僅涵蓋「使用者認證」端點；**目前不啟用 reCAPTCHA**。

---

## 使用者註冊 API

**路徑**：`POST /auth/signup/`

**說明**：建立新使用者帳號。

### 請求格式（JSON）

| 欄位名          | 型別     |  必填 | 說明                                                          |
| ------------ | ------ | :-: | ----------------------------------------------------------- |
| `username`   | string |  ✅  | 最多 150 字元，**唯一**                                            |
| `password`   | string |  ✅  | 使用者密碼（後端會雜湊儲存）                                              |
| `email`      | string |  ✅  | 有效 Email，**唯一**                                             |
| `real_name`  | string |  ✅  | 最多 150 字元                                                   |
| `identity`   | string |  ✅  | 身分：`teacher` / `admin` / `student`（**必填**；模型預設仍為 `student`） |
| `student_id` | string |  ❌  | 最多 50 字元（唯一）。若無可省略                                          |
| `bio`        | string |  ❌  | 自我介紹                                                        |

**請求範例**：

```json
{
  "username": "momo",
  "email": "momo@example.com",
  "password": "abc12345",
  "real_name": "小桃",
  "identity": "student",
  "student_id": "1160001",
  "bio": "我愛娃娃"
}
```

**成功回應（201, JSON）** ＊回傳欄位可能依後端序列化調整，`password` 不會回傳：

```json
{
  "id": "b1b6c3f4-6e9b-4bfa-9a78-9e1d1e6b8a21",
  "username": "momo",
  "email": "momo@example.com",
  "real_name": "小桃",
  "identity": "student",
  "date_joined": "2025-10-03T07:15:14.123Z",
  "last_login": null
}
```

**失敗回應（400, JSON）**

* 已存在：

  ```json
  {"username":["這個 username 在 user 已經存在。"],"email":["這個 email 在 user 已經存在。"]}
  ```
* `username` 未填：

  ```json
  {"username":["此為必需欄位。"]}
  ```
* Email 格式錯誤：

  ```json
  {"email":["請輸入有效的電子郵件地址。"]}
  ```
* `identity` 未填或值錯誤：

  ```json
  {"identity":["此為必需欄位。或值必須為 teacher/admin/student 之一"]}
  ```

**cURL 測試**：

```bash
curl -X POST http://127.0.0.1:8000/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "username":"momo",
    "email":"momo@example.com",
    "password":"abc12345",
    "real_name":"小桃",
    "identity":"student"
  }'
```

---

## 使用者登入 API

**路徑**：`POST /auth/session/`

**說明**：以帳號密碼登入，取得 JWT。

### 請求格式（JSON）

| 欄位名        | 型別     |  必填 | 說明                    |
| ---------- | ------ | :-: | --------------------- |
| `username` | string |  ✅  | 登入帳號（目前以 username 登入） |
| `password` | string |  ✅  | 密碼                    |

**成功請求範例**：

```json
{ "username": "momo", "password": "abc12345" }
```

**成功回應（200, JSON）**

```json
{ "refresh": "<refresh.jwt>", "access": "<access.jwt>" }
```

**失敗回應**

* 認證失敗（401）：

  ```json
  { "detail": "No active account found with the given credentials" }
  ```
* 缺少欄位（400）：

  ```json
  { "username": ["This field is required."] }
  ```

**cURL 測試**：

```bash
curl -X POST http://127.0.0.1:8000/auth/session/ \
  -H "Content-Type: application/json" \
  -d '{"username":"momo","password":"abc12345"}'
```

> 欄位說明：
>
> * `access`：短效 token，之後的 API 需帶 `Authorization: Bearer <access>`。
> * `refresh`：用於在 access 過期時換取新 access。

---

## 附錄：常見錯誤總表

| 錯誤情境                | HTTP 狀態 | 回應訊息                                                                          |
| ------------------- | :-----: | ----------------------------------------------------------------------------- |
| 帳密錯誤（登入）            |   401   | `{"detail":"No active account found with the given credentials"}`             |
| 未帶 access（/auth/me） |   401   | `{"detail":"Authentication credentials were not provided."}`                  |
| 帳號/信箱已存在（註冊）        |   400   | `{"username":["這個 username 在 user 已經存在。"],"email":["這個 email 在 user 已經存在。"]}` |
| Email 格式錯誤（註冊）      |   400   | `{"email":["請輸入有效的電子郵件地址。"]}`                                                 |
| 欄位缺漏（註冊/登入）         |   400   | `{"username":["This field is required."]}`                                    |
| `identity` 缺漏或值錯誤   |   400   | `{"identity":["此為必需欄位。或值必須為 teacher/admin/student 之一"]}`                      |

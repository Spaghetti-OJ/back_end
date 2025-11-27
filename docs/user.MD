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
| `role`   | string |  ✅  | 身分：`teacher` / `admin` / `student`（**必填**；模型預設仍為 `student`） |
| `student_id` | string |  ❌  | 最多 50 字元（唯一）。若無可省略                                          |
| `bio`        | string |  ❌  | 自我介紹                                                        |

**請求範例**：

```json
{
  "username": "momo",
  "email": "momo@example.com",
  "password": "abc12345",
  "real_name": "小桃",
  "role": "student",
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
  "role": "student",
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
* `role` 未填或值錯誤：

  ```json
  {"role":["此為必需欄位。或值必須為 teacher/admin/student 之一"]}
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
    "role":"student"
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

## Refresh Token API

**路徑**：`POST /auth/refresh/`

**說明**：使用現有的 refresh token 取得新的 access token。

### 請求格式（JSON）

| 欄位名       | 型別     |  必填 | 說明                     |
| --------- | ------ | :-: | ---------------------- |
| `refresh` | string |  ✅  | 先前登入時取得的 refresh token |

**成功請求範例**：

```json
{ "refresh": "<refresh.jwt>" }
```

**成功回應（200, JSON）**

```json
{ "access": "<new.access.jwt>" }
```

> 若伺服器設定 `ROTATE_REFRESH_TOKENS = True`，則回應中也可能同時包含新的 refresh token：
>
> ```json
> { "access": "<new.access.jwt>", "refresh": "<new.refresh.jwt>" }
> ```

**失敗回應**

* refresh token 遺失或無效（401）：

  ```json
  { "detail": "Token is invalid or expired", "code": "token_not_valid" }
  ```

* 缺少欄位（400）：

  ```json
  { "refresh": ["This field is required."] }
  ```

**cURL 測試**：

```bash
curl -X POST http://127.0.0.1:8000/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh.jwt>"}'
```

> 欄位說明：
>
> * `refresh`：登入時發放的長效 token，用於換取新的 access。
> * `access`：短效 token，用於 API 認證，過期時需重新以 refresh 換取。

---

## Verify Token API

**路徑**：`POST /auth/verify/`

**說明**：驗證指定的 access token 是否有效（未過期、未竄改）。

### 請求格式（JSON）

| 欄位名     | 型別     |  必填 | 說明                |
| ------- | ------ | :-: | ----------------- |
| `token` | string |  ✅  | 要驗證的 access token |

**成功請求範例**：

```json
{ "token": "<access.jwt>" }
```

**成功回應（200, JSON）**

```json
{}
```

> 表示該 access token 有效。

**失敗回應**

* token 無效或過期（401）：

  ```json
  { "detail": "Token is invalid or expired", "code": "token_not_valid" }
  ```

* 缺少欄位（400）：

  ```json
  { "token": ["This field is required."] }
  ```

**cURL 測試**：

```bash
curl -X POST http://127.0.0.1:8000/auth/verify/ \
  -H "Content-Type: application/json" \
  -d '{"token":"<access.jwt>"}'
```

> 欄位說明：
>
> * `token`：欲驗證的 access token。若 token 已過期、被修改或不合法，伺服器會回傳 401 錯誤。

---

## Revoke Refresh Token（登出）

**路徑**：`POST /auth/session/revoke/`

**用途**：註銷（撤銷）一顆 **refresh token**，使其無法再換發新的 access token。

**權限**：`Authorization: Bearer <access>`（`IsAuthenticated`）

### 請求（JSON）

| 欄位名       | 型別     |  必填 | 說明                                                                                                 |
| --------- | ------ | :-: | -------------------------------------------------------------------------------------------------- |
| `refresh` | string |  ✅  | 先前登入或 refresh 時取得的 refresh token。 |

**成功請求範例**：

```json
{ "refresh": "<refresh.jwt>" }
```

### 成功回應

```
HTTP/1.1 205 Reset Content
```

> 代表該 refresh 已加入黑名單。建議前端立即清除本地憑證與狀態。

### 失敗回應

* 缺少欄位（400）：

  ```json
  { "detail": "refresh field required" }
  ```
* refresh 無效或過期（400）：

  ```json
  { "detail": "Invalid or expired refresh token" }
  ```
* 未授權（401）：

  ```json
  { "detail": "Authentication credentials were not provided." }
  ```

### cURL 測試

```bash
ACCESS="<access.jwt>"
REFRESH="<refresh.jwt>"

curl -i -X POST "http://127.0.0.1:8000/auth/session/revoke/" \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\":\"$REFRESH\"}"
```

---

### 相關端點對照

| 功能         | 路徑                      | 方法       | 說明                                               |
| ---------- | ----------------------- | -------- | ------------------------------------------------ |
| 登入         | `/auth/session/`        | POST     | SimpleJWT 取得 `access` + `refresh`                |
| Refresh    | `/auth/refresh/`        | POST     | 用 `refresh` 換新 `access`；若啟用 rotate，會回新 `refresh` |
| Verify（可選） | `/auth/verify/`         | POST     | 驗證 `access` 是否有效（有效時回 `{}`）                      |
| **安全登出**   | `/auth/session/revoke/` | **POST** | 將 `refresh` 加入黑名單（立即失效）                          |

---

### 範例使用情境（用戶按「登出」）

1. 前端呼叫 `POST /auth/session/revoke/`（帶 access；body 帶 refresh 或由 cookie 取）。
2. 收到 `205` ⇒ 清除本地 `access/refresh`、停止自動 refresh、跳轉登入。
3. 若用戶返回頁面且 access 過期，攔截器判定 401 → 嘗試 `/auth/refresh/`；若後端回 `token_not_valid / blacklisted` ⇒ 直接跳轉登入。

---

## GET /auth/me/

**路徑**：`GET /auth/me/`

**說明**：
使用目前登入狀態（Authorization Header 帶入 `Bearer <access>`）取得當前使用者的基本資料，包含 `user_id`、`username`、`email`、`role`。

### 請求格式

此 API 為 `GET`，不需請求 body，但必須在 Header 帶入 JWT access token。

**HTTP Header 必填項：**

| 欄位名             | 型別     |  必填 | 說明                          |
| --------------- | ------ | :-: | --------------------------- |
| `Authorization` | string |  ✅  | 格式為 `Bearer <access_token>` |

**請求範例（不含 body）**：

```http
GET /auth/me/ HTTP/1.1
Host: 127.0.0.1:8000
Authorization: Bearer <ACCESS_TOKEN>
```

---

### 成功回應（200, JSON）

```json
{
  "status": "ok",
  "message": "Get current user",
  "data": {
    "user_id": "f07e9f90-89c3-49a6-b241-2fe8f73ff80b",
    "username": "momo",
    "email": "momo@example.com",
    "role": "student"
  }
}
```

各欄位說明：

| 路徑              | 型別     | 說明                 |
| --------------- | ------ | ------------------ |
| `status`        | string | 狀態字串，成功固定為 `"ok"`  |
| `message`       | string | 描述訊息               |
| `data.user_id`   | string | 使用者在系統中的唯一 ID      |
| `data.username` | string | 使用者帳號              |
| `data.email`    | string | 使用者註冊 email        |
| `data.role`     | string | 使用者角色（如：`student`） |

---

### 失敗回應範例

* 未帶 token 或 token 無效（401）：

  ```json
  {
    "detail": "Authentication credentials were not provided."
  }
  ```

  或

  ```json
  {
    "detail": "Given token not valid for any token type",
    "code": "token_not_valid"
  }
  ```

---

### cURL 測試範例

```bash
curl -X GET "http://127.0.0.1:8000/auth/me/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

> 使用說明：
>
> * 建議登入後（呼叫 `POST /auth/session/` 拿到 access）就立刻呼叫一次 `GET /auth/me/`，
>   將回傳的 `user_id`、`username`、`email`、`role` 存到前端的全域狀態（例如 Redux / Zustand / Vuex），作為之後顯示使用者名稱或判斷角色權限之用。
> * 若收到 401，請先確認 access token 是否過期，可搭配 `POST /auth/refresh/` 重新取得新的 access。

---

## GET /profile/

**說明**：
取得目前登入使用者的個人資料。

**權限需求**：

* 需要登入（JWT Access Token）

**Request Header**：

| Header        | Type   | Required | 說明                          |
| ------------- | ------ | -------- | --------------------------- |
| Authorization | string | ✅        | 格式為 `Bearer <ACCESS_TOKEN>` |
| Content-Type  | string | ✅        | `application/json`          |

**Request Body**：
無

---

### Response

**成功範例 (200 OK)**

```json
{
  "real_name": "陳天天",
  "username": "momo",
  "role": "Student",
  "email": "412470100S@gapps.ntnu.edu.tw",
  "user_id": "omuba",
  "student_id": "41247057S",
  "bio": "哈囉我是資工116",
  "avatar":null
}
```

**欄位說明**：

| 欄位           | 型別     | 說明                               |
| ------------ | ------ | -------------------------------- |
| real_name    | string | 使用者真實姓名                          |
| username    | string | 使用者帳號（username）                  |
| role         | string | 使用者身份（Student / Teacher / Admin） |
| email        | string | 使用者電子郵件                          |
| user_id      | string | 使用者的 ID             |
| student_id   | string | 學號（若有）                           |
| bio | string | 個人簡介                             |
| avatar       | string | 頭像 url                |

---

### 錯誤回應

| 狀態碼              | 說明            | 範例                                                                   |
| ---------------- | ------------- | -------------------------------------------------------------------- |
| 401 Unauthorized | Token 遺失或無效   | `{ "detail": "Authentication credentials were not provided." }`      |
| 403 Forbidden    | 使用者權限不足（若未登入） | `{ "detail": "You do not have permission to perform this action." }` |

---

### 測試指令

```bash
curl -X GET http://127.0.0.1:8000/profile/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json"
```

---

## GET /profile/{username}/

**說明**
查看**其他使用者**的公開個人資料。

> 與 `GET /profile/`（查看自己的完整資料）不同，本端點**不會**回傳 `real_name`、`student_id` 等私密欄位。

---

### 權限需求

* 需要登入（JWT Access Token）

---

### Request

#### Method & URL

```
GET /profile/{username}/
```

#### Path Parameters

| 參數名      | 類型     | 必填 | 說明              |
| -------- | ------ | -- | --------------- |
| username | string | ✅  | 目標使用者帳號（大小寫不敏感） |

#### Headers

| Header        | 類型     | 必填 | 說明                      |
| ------------- | ------ | -- | ----------------------- |
| Authorization | string | ✅  | `Bearer <ACCESS_TOKEN>` |
| Content-Type  | string | ✅  | `application/json`      |

#### Request Body

* 無

---

#### 成功回應（200 OK）

```json
{
  "username": "momo",
  "role": "Student",
  "email": "momo@example.com",
  "user_id": "f07e9f90-89c3-49a6-b241-2fe8f73ff80b",
  "bio": "哈囉我是資工116",
  "avatar":null
}
```

#### 欄位說明

| 欄位           | 類型     | 說明                                        |
| ------------ | ------ | ----------------------------------------- |
| username    | string | 使用者帳號（username）                           |
| role         | string | 使用者身份（例如：`Student` / `Teacher` / `Admin`） |
| email        | string | 使用者電子郵件（依隱私策略可能顯示或遮蔽）                     |
| user_id      | string | 使用者的公開 ID（預設為使用者主鍵；若系統有自訂公開 ID 則為該值）      |
| bio | string | 個人簡介（來源：UserProfile.bio；若未設定可能為空字串）       |
| avatar       | string | 頭像 url                |

> 注意：**不包含** `real_name`、`student_id`。

---

### 失敗回應

#### 401 Unauthorized（未登入或 Token 失效）

```json
{
  "detail": "Authentication credentials were not provided or are invalid."
}
```

#### 404 Not Found（找不到使用者）

```json
{
  "detail": "User not found."
}
```

> 其他錯誤（5xx）多半為伺服器端異常，請檢查日誌。

---

### 範例

#### cURL

```bash
curl -i -X GET "http://127.0.0.1:8000/profile/momo/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json"
```

---

## POST /profile/

### 說明

更新登入使用者的個人資料。所有欄位皆為非必填，僅會更新請求中提供的欄位，其餘保持不變。

可修改欄位：

* `real_name`：真實姓名（User）
* `email`：Email（User）
* `student_id`：學號，可空（UserProfile）
* `bio`：個人簡介，可空（UserProfile）
* `avatar`：頭像圖片檔案，可選（UserProfile）

📌 不含檔案 → 使用 `application/json`
📌 含 `avatar` → 使用 `multipart/form-data`

---

## 請求格式

### JSON（不含檔案）

```
POST /profile/
Content-Type: application/json
Authorization: Bearer <ACCESS_TOKEN>
```

```json
{
  "real_name": "新名字",
  "email": "new_email@example.com",
  "student_id": "4103xxxx",
  "bio": "更新後的自我介紹"
}
```

### multipart/form-data（含 avatar）

```
POST /profile/
Content-Type: multipart/form-data
Authorization: Bearer <ACCESS_TOKEN>
```

欄位：

* `avatar`: file
* `bio`: text
* 其餘文字欄位：`real_name`, `email`, `student_id`

---

## 成功回應（200）

```json
{
  "data": {
    "real_name": "新名字",
    "username": "momo",
    "role": "Student",
    "email": "new_email@example.com",
    "user_id": "f07e9f90-89c3-49a6-b241-2fe8f73ff80b",
    "student_id": "4103xxxx",
    "bio": "更新後的自我介紹",
    "avatar": "http://127.0.0.1:8000/media/avatars/xxx.png"
  },
  "message": "Profile updated",
  "status": "ok"
}
```

---

## 失敗回應（400）

```json
{
  "data": {
    "email": ["Enter a valid email address."],
    "avatar": ["The submitted file is empty."]
  },
  "message": "Validation error",
  "status": "error"
}
```

---

## curl 範例

### 修改文字欄位（JSON）

```bash
curl -X POST "http://127.0.0.1:8000/profile/" \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "real_name": "小桃改名版",
    "email": "new_momo@example.com",
    "bio": "這是新的自介！"
  }'
```

### 上傳頭像（multipart/form-data）

```bash
curl -X POST "http://127.0.0.1:8000/profile/" \
  -H "Authorization: Bearer $ACCESS" \
  -F "avatar=@/home/rokusenn/Pictures/avatar.png" \
  -F "bio=更新過的自我介紹"
```
---

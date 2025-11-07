# 後端 API 說明

本專案後端使用 **Django + Django REST Framework + Simple JWT**，所有 API 採 **JSON** 傳輸。

---

## 課程列表 API

**路徑**：`GET /course/`

**說明**：取得登入使用者的課程列表（老師：自己教授；學生/助教：加入的課程），依建立時間新到舊排序。

**成功回應 (200 OK)**：

```json
{
  "message": "Success.",
  "courses": [
    {
      "id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12",
      "course": "人工智慧導論",
      "teacher": {
        "id": "c1234f56-789a-4bde-b123-456789abcd12",
        "username": "teacher01",
        "real_name": "王小明",
        "identity": "teacher"
      }
    }
  ]
}
```

**cURL 測試**：
```bash
curl http://127.0.0.1:8000/course/ \
    -H "Authorization: Bearer <access>"
```

---

## 課程建立 API

**路徑**：`POST /course/`

**說明**：建立課程。需具管理員或教師身分；教師僅能將自己設為課程教師。

### 請求格式 (JSON)

| 欄位名     | 型別   | 必填 | 說明                                             |
| ---------- | ------ | ---- | ------------------------------------------------ |
| `course`   | string | ✅   | 課程名稱；需符合 `^[a-zA-Z0-9._\- ]+$` 格式        |
| `teacher`  | string | ✅   | 指定教師的使用者名稱；必須為已存在的教師帳號           |

---

**請求範例**

```json
{
  "course": "Algorithms_2025",
  "teacher": "teacher01"
}
```

---

**成功回應 (200 OK)**

```json
{ "message": "Success." }
```

**失敗回應**

| 狀況                     | HTTP | 範例訊息                       |
| ------------------------ | ---- | ------------------------------ |
| 未登入                   | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 課程名稱格式錯誤         | 400  | `{ "message": "Not allowed name." }` |
| 課程名稱已存在           | 400  | `{ "message": "Course exists." }` |
| 權限不足                 | 403  | `{ "message": "Forbidden." }`  |
| 指定教師不存在/非教師身份 | 404  | `{ "message": "User not found." }` |

**cURL 測試**：
```bash
curl -X POST http://127.0.0.1:8000/course/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access>" \
    -d '{
    "course": "Algorithms_2025",
    "teacher": "teacher01"
    }'
```

---

## 課程編輯 API

**路徑**：`PUT /course/`

**說明**：編輯課程名稱與授課教師。需具管理員身分或為該課程的現任教師。

### 請求格式 (JSON)

| 欄位名        | 型別   | 必填 | 說明                                             |
| ------------- | ------ | ---- | ------------------------------------------------ |
| `course`      | string | ✅   | 目前課程名稱（大小寫不敏感）                          |
| `new_course`  | string | ✅   | 新課程名稱；需符合 `^[a-zA-Z0-9._\- ]+$` 格式        |
| `teacher`     | string | ✅   | 新教師的使用者名稱；必須為已存在的教師帳號             |

---

**請求範例**

```json
{
  "course": "Algorithms_2025",
  "new_course": "Algorithms_2026",
  "teacher": "teacher02"
}
```

---

**成功回應 (200 OK)**

```json
{ "message": "Success." }
```

**失敗回應**

| 狀況                     | HTTP | 範例訊息                       |
| ------------------------ | ---- | ------------------------------ |
| 未登入                   | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 課程名稱格式錯誤         | 400  | `{ "message": "Not allowed name." }` |
| 課程名稱已存在           | 400  | `{ "message": "Course exists." }` |
| 權限不足                 | 403  | `{ "message": "Forbidden." }`  |
| 指定課程不存在           | 404  | `{ "message": "Course not found." }` |
| 指定教師不存在/非教師身份 | 404  | `{ "message": "User not found." }` |

**cURL 測試**：
```bash
curl -X PUT http://127.0.0.1:8000/course/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access>" \
    -d '{
    "course": "Algorithms_2025",
    "new_course": "Algorithms_2026",
    "teacher": "teacher02"
    }'
```

---

## 課程刪除 API

**路徑**：`DELETE /course/`

**說明**：刪除指定課程。需具管理員身分或為該課程的現任教師。

### 請求格式 (JSON)

| 欄位名   | 型別   | 必填 | 說明                         |
| -------- | ------ | ---- | ---------------------------- |
| `course` | string | ✅   | 需要刪除的課程名稱（大小寫不敏感） |

---

**請求範例**

```json
{
  "course": "Algorithms_2025"
}
```

---

**成功回應 (200 OK)**

```json
{ "message": "Success." }
```

**失敗回應**

| 狀況           | HTTP | 範例訊息                          |
| -------------- | ---- | --------------------------------- |
| 未登入         | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 權限不足       | 403  | `{ "message": "Forbidden." }`     |
| 課程不存在     | 404  | `{ "message": "Course not found." }` |

**cURL 測試**：
```bash
curl -X DELETE http://127.0.0.1:8000/course/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access>" \
    -d '{
    "course": "Algorithms_2025"
    }'
```

---

## 課程統計摘要 API

**路徑**：`GET /course/summary`

**說明**：僅管理員可呼叫，回傳所有課程的統計摘要。

**成功回應 (200 OK)**

```json
{
  "message": "Success.",
  "courseCount": 1,
  "breakdown": [
    {
      "course": "人工智慧導論",
      "userCount": 35,
      "homeworkCount": 5,
      "submissionCount": 120,
      "problemCount": 12
    }
  ]
}
```

**失敗回應**

| 狀況      | HTTP | 範例訊息                                      |
| ------- | ---- | ----------------------------------------- |
| 未登入     | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 非管理員   | 403  | `{ "detail": "只有管理員可以查看課程統計。" }` |

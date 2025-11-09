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

## 課程詳情 API

**路徑**：`GET /course/<course_id>/`

**說明**：查看課程基本資訊與成員。需登入並且為該課程的教師、助教或學生。

**路徑參數**

| 參數名        | 型別   | 必填 | 說明            |
| ------------- | ------ | ---- | --------------- |
| `course_id`   | UUID   | ✅   | 課程的 UUID |

**成功回應 (200 OK)**：

```json
{
  "message": "Success.",
  "course": {
    "id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12",
    "course": "人工智慧導論",
    "description": "課程介紹…",
    "joinCode": "XYZ12AB",
    "studentLimit": 60,
    "semester": "Spring",
    "academicYear": "2025",
    "studentCount": 35,
    "isActive": true,
    "createdAt": "2025-01-01T08:00:00Z",
    "updatedAt": "2025-01-05T08:00:00Z"
  },
  "teacher": {
    "id": "c1234f56-789a-4bde-b123-456789abcd12",
    "username": "teacher01",
    "real_name": "王小明",
    "identity": "teacher"
  },
  "TAs": [
    {
      "id": "24242424-aaaa-bbbb-cccc-123456789000",
      "username": "ta_user",
      "real_name": "助教 A",
      "identity": "student"
    }
  ],
  "students": [
    {
      "id": "65656565-aaaa-bbbb-cccc-123456789000",
      "username": "student01",
      "real_name": "學生 A",
      "identity": "student"
    }
  ]
}
```

**失敗回應**

| 狀況       | HTTP | 範例訊息                                                 |
| ---------- | ---- | -------------------------------------------------------- |
| 未登入     | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 非課程成員 | 403  | `{ "message": "You are not in this course." }`           |
| 課程不存在 | 404  | `{ "message": "Course not found." }`                     |

**cURL 測試**：
```bash
curl http://127.0.0.1:8000/course/4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12/ \
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
| `course_id`   | string | ✅   | 需要編輯的課程 ID（UUID）                              |
| `new_course`  | string | ✅   | 新課程名稱；需符合 `^[a-zA-Z0-9._\- ]+$` 格式        |
| `teacher`     | string | ✅   | 新教師的使用者名稱；必須為已存在的教師帳號             |

---

**請求範例**

```json
{
  "course_id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12",
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
    "course_id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12",
    "new_course": "Algorithms_2026",
    "teacher": "teacher02"
    }'
```

---

## 課程成績查詢 API

**路徑**：`GET /course/<course_id>/grade/<student>`

**說明**：查看指定學生在指定課程的成績項目。需登入且需為課程成員；學生身分只能查詢自己的成績。

**成功回應 (200 OK)**：

```json
{
  "message": "Success.",
  "grades": [
    {
      "title": "Midterm",
      "content": "Midterm exam",
      "score": 95,
      "timestamp": "2025-11-10T08:15:00Z"
    },
    {
      "title": "Quiz 1",
      "content": "Intro quiz",
      "score": 80,
      "timestamp": "2025-10-30T02:00:00Z"
    }
  ]
}
```

**失敗回應**

| 狀況                         | HTTP | 範例訊息                              |
| ---------------------------- | ---- | ------------------------------------- |
| 未登入                       | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 不在課程內                   | 403  | `{ "message": "You are not in this course." }` |
| 學生嘗試查詢他人成績         | 403  | `{ "message": "You can only view your score." }` |
| 課程不存在                   | 404  | `{ "message": "Course not found." }` |
| 學生不存在或不在該課程       | 404  | `{ "message": "The student is not in the course." }` |

**cURL 測試**：
```bash
curl http://127.0.0.1:8000/course/<course_id>/grade/<student>/ \
    -H "Authorization: Bearer <access>"
```

## 課程成績刪除 API

**路徑**：`DELETE /course/<course_id>/grade/<student>`

**說明**：刪除指定學生在指定課程內的單一成績項目。需登入且需為教師或擁有助教權限才能操作。

### 請求格式 (JSON)

| 欄位名 | 型別 | 必填 | 說明           |
| ------ | ---- | ---- | -------------- |
| `title` | string | ✅ | 要刪除的成績項目標題 |

**成功回應 (200 OK)**

```json
{ "message": "Success." }
```

**失敗回應**

| 狀況                   | HTTP | 範例訊息                                  |
| ---------------------- | ---- | ----------------------------------------- |
| 未登入                 | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 不在課程內             | 403  | `{ "message": "You are not in this course." }` |
| 沒有評分權限（如學生） | 403  | `{ "message": "You can only view your score." }` |
| 課程不存在             | 404  | `{ "message": "Course not found." }` |
| 學生不存在或不在課程   | 404  | `{ "message": "The student is not in the course." }` |
| 成績不存在             | 404  | `{ "message": "Score not found." }` |

**cURL 測試**：

```bash
curl -X DELETE http://127.0.0.1:8000/course/<course_id>/grade/<student>/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access>" \
    -d '{
        "title": "Quiz 1"
    }'
```

## 課程刪除 API

**路徑**：`DELETE /course/`

**說明**：刪除指定課程。需具管理員身分或為該課程的現任教師。

### 請求格式 (JSON)

| 欄位名   | 型別   | 必填 | 說明                         |
| -------- | ------ | ---- | ---------------------------- |
| `course_id` | string | ✅   | 需要刪除的課程 ID（UUID） |

---

**請求範例**

```json
{
  "course_id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12"
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
    "course_id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12"
    }'
```

## 課程刪除 API

**路徑**：`DELETE /course/`

**說明**：刪除指定課程。需具管理員身分或為該課程的現任教師。

### 請求格式 (JSON)

| 欄位名   | 型別   | 必填 | 說明                         |
| -------- | ------ | ---- | ---------------------------- |
| `course_id` | string | ✅   | 需要刪除的課程 ID（UUID） |

---

**請求範例**

```json
{
  "course_id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12"
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
    "course_id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12"
    }'
```

## 課程刪除 API

**路徑**：`DELETE /course/`

**說明**：刪除指定課程。需具管理員身分或為該課程的現任教師。

### 請求格式 (JSON)

| 欄位名   | 型別   | 必填 | 說明                         |
| -------- | ------ | ---- | ---------------------------- |
| `course_id` | string | ✅   | 需要刪除的課程 ID（UUID） |

---

**請求範例**

```json
{
  "course_id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12"
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
    "course_id": "4b1c2a3d-8e1f-45c3-9c62-ff33b4aa6f12"
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

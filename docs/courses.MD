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
      "id": 42,
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
| `course_id`   | int   | ✅   | 課程的流水號 ID |

**成功回應 (200 OK)**：

```json
{
  "message": "Success.",
  "course": {
    "id": 42,
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
curl http://127.0.0.1:8000/course/42/ \
    -H "Authorization: Bearer <access>"
```

---

## 課程邀請加入 API

**路徑**：`POST /course/<course_id>/join`

**說明**：學生以邀請代碼加入課程。僅學生身分可使用，代碼不分大小寫。

**請求格式 (JSON)**

| 欄位名    | 型別   | 必填 | 說明                 |
| --------- | ------ | ---- | -------------------- |
| `joinCode` | string | ✅   | 7 碼英數邀請代碼 |

**成功回應 (200 OK)**：

```json
{ "message": "Success.", "data": { "course": { "id": 42 } }, "status_code": 200 }
```

**失敗回應**

| 狀況                 | HTTP | 範例訊息                                   |
| -------------------- | ---- | ------------------------------------------ |
| 未登入               | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 非學生身分           | 403  | `{ "message": "Forbidden." }`              |
| 課程不存在           | 404  | `{ "message": "Course not found." }`       |
| 邀請代碼錯誤/失效    | 400  | `{ "message": "Invalid join code." }`      |
| 已在課程內           | 400  | `{ "message": "You are already in this course." }` |
| 已達人數上限         | 403  | `{ "message": "Course is full." }`         |

**cURL 測試**：
```bash
curl -X POST http://127.0.0.1:8000/course/42/join/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access>" \
    -d '{"joinCode": "ABC1234"}'
```

---

## 課程成員調整 API

**路徑**：`PUT /course/<course_id>/`

**說明**：同步指定課程的助教名單，並可移除特定學生。僅課程教師本人或系統管理員可執行；教師只能操作自己的課程。

**路徑/查詢參數**

| 參數名      | 來源 | 型別 | 必填 | 說明                     |
| ----------- | ---- | ---- | ---- | ------------------------ |
| `course_id` | URL  | int | ✅   | 課程 ID（整數）                  |
| `student`   | URL  | UUID | ⭕   | 要移除的學生 ID（可選） |

**請求格式 (JSON)**

| 欄位名 | 型別 | 必填 | 說明                                 |
| ------ | ---- | ---- | ------------------------------------ |
| `TAs`  | list | ⭕   | 要保留的助教帳號列表；缺省表示不異動 |

> 備註：`TAs` 給空陣列 `[]` 代表移除所有助教；若提供 `student` 查詢參數，會刪除該學生在課程中的成員紀錄。

**成功回應 (200 OK)**

```json
{ "message": "Success." }
```

**失敗回應**

| 狀況                           | HTTP | 範例訊息                                 |
| ------------------------------ | ---- | ---------------------------------------- |
| 未登入                         | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 權限不足（非教師/管理員）      | 403  | `{ "message": "Forbidden." }`            |
| 非授課教師操作他人課程         | 403  | `{ "message": "You are not in this course." }` |
| 課程不存在                     | 404  | `{ "message": "Course not found." }`     |
| 指定助教帳號不存在             | 404  | `{ "message": "User: <username> not found." }` |
| 指定學生不存在或不在該課程內   | 404  | `{ "message": "Student not found." }`    |

**cURL 測試**

```bash
curl -X PUT "http://127.0.0.1:8000/course/<course_id>/?student=<student_id>" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access>" \
    -d '{
    "TAs": ["ta_user_1", "ta_user_2"]
    }'
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
{ "message": "Success.", "data": { "course": { "id": 42 } }, "status_code": 200 }
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
| `course_id`   | int | ✅   | 需要編輯的課程 ID（整數）                              |
| `new_course`  | string | ✅   | 新課程名稱；需符合 `^[a-zA-Z0-9._\- ]+$` 格式        |
| `teacher`     | string | ✅   | 新教師的使用者名稱；必須為已存在的教師帳號             |

---

**請求範例**

```json
{
  "course_id": 42,
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
    "course_id": 42,
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

**路徑**：`POST /course/<course_id>/grade/<student>`

**說明**：新增指定學生的成績項目。需登入且必須為該課程的教師、助教或管理員（且為課程成員）。

**請求格式 (JSON)**

| 欄位名 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| `title` | string | ✅ | 成績項目標題（同一學生同一課程必須唯一） |
| `content` | string | ✅ | 成績說明，可為空字串 |
| `score` | number / string | ✅ | 分數，可為數字或字母（例如 `95`、`"A+"`） |

**成功回應 (200 OK)**：

```json
{ "message": "Success." }
```

**失敗回應**：

| 狀況 | HTTP | 訊息 |
| --- | --- | --- |
| 不在課程內 | 403 | `{ "message": "You are not in this course." }` |
| 無評分權限 | 403 | `{ "message": "You can only view your score." }` |
| 標題重複 | 400 | `{ "message": "This title is taken." }` |
| 課程不存在 | 404 | `{ "message": "Course not found." }` |
| 學生不在課程 | 404 | `{ "message": "The student is not in the course." }` |

**cURL 測試**：

```bash
curl -X POST http://127.0.0.1:8000/course/<course_id>/grade/<student>/ \
    -H "Authorization: Bearer <access>" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Final",
        "content": "Final exam score",
        "score": 95
    }'
```

**路徑**：`PUT /course/<course_id>/grade/<student>`

**說明**：修改指定學生的成績項目。需登入且必須為該課程的教師、助教或管理員（並為課程成員）。若提供 `new_title`，會以其覆蓋原標題；若未提供則沿用原標題。

**請求格式 (JSON)**

| 欄位名 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| `title` | string | ✅ | 要修改的成績項目原標題 |
| `new_title` | string | ⭕ | 新標題，若缺省則維持原標題 |
| `content` | string | ✅ | 成績說明，可為空字串 |
| `score` | number / string | ✅ | 分數，可為數字或字母（例如 `92`、`"A"`） |

**成功回應 (200 OK)**：

```json
{ "message": "Success." }
```

**失敗回應**：

| 狀況 | HTTP | 訊息 |
| --- | --- | --- |
| 不在課程內 | 403 | `{ "message": "You are not in this course." }` |
| 無評分權限 | 403 | `{ "message": "You can only view your score." }` |
| 課程不存在 | 404 | `{ "message": "Course not found." }` |
| 學生不在課程 | 404 | `{ "message": "The student is not in the course." }` |
| 要修改的成績不存在 | 404 | `{ "message": "Score not found." }` |
| `new_title` 與該學生其他成績項目重複 | 400 | `{ "message": "This title is taken." }` |

**cURL 測試**：

```bash
curl -X PUT http://127.0.0.1:8000/course/<course_id>/grade/<student>/ \
    -H "Authorization: Bearer <access>" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Quiz 1",
        "new_title": "Quiz 1 (make-up)",
        "content": "Updated after regrade",
        "score": 85
    }'
```

**路徑**：`DELETE /course/<course_id>/grade/<student>`

**說明**：刪除指定學生的單一成績項目。需登入且必須為該課程的教師、助教或管理員（並為課程成員）。

**請求格式 (JSON)**

| 欄位名 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| `title` | string | ✅ | 要刪除的成績項目標題 |

**成功回應 (200 OK)**：

```json
{ "message": "Success." }
```

**失敗回應**：

| 狀況 | HTTP | 訊息 |
| --- | --- | --- |
| 不在課程內 | 403 | `{ "message": "You are not in this course." }` |
| 無評分權限 | 403 | `{ "message": "You can only view your score." }` |
| 課程不存在 | 404 | `{ "message": "Course not found." }` |
| 學生不在課程 | 404 | `{ "message": "The student is not in the course." }` |
| 成績不存在 | 404 | `{ "message": "Score not found." }` |
| 缺少 `title` | 400 | `{ "message": "This field is required." }` |

**cURL 測試**：

```bash
curl -X DELETE http://127.0.0.1:8000/course/<course_id>/grade/<student>/ \
    -H "Authorization: Bearer <access>" \
    -H "Content-Type: application/json" \
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
| `course_id` | int | ✅   | 需要刪除的課程 ID（整數） |

---

**請求範例**

```json
{
  "course_id": 42
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
    "course_id": 42
    }'
```

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

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
        "role": "teacher"
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
    "role": "teacher"
  },
  "TAs": [
    {
      "id": "24242424-aaaa-bbbb-cccc-123456789000",
      "username": "ta_user",
      "real_name": "助教 A",
      "role": "student"
    }
  ],
  "students": [
    {
      "id": "65656565-aaaa-bbbb-cccc-123456789000",
      "username": "student01",
      "real_name": "學生 A",
      "role": "student"
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

## 課程邀請代碼產生 API

**路徑**：`POST /course/<course_id>/invite-code/`

**說明**：產生指定課程的邀請代碼。僅課程教師本人或系統管理員可執行。

**成功回應 (200 OK)**：

```json
{
  "message": "Success.",
  "data": { "joinCode": "XYZ12AB" },
  "status_code": 200
}
```

**失敗回應**

| 狀況                     | HTTP | 範例訊息                                            |
| ------------------------ | ---- | --------------------------------------------------- |
| 未登入                   | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 非教師/管理員            | 403  | `{ "message": "Forbidden." }`                       |
| 非授課教師操作他人課程   | 403  | `{ "message": "You are not in this course." }`      |
| 課程不存在               | 404  | `{ "message": "Course not found." }`                |

**cURL 測試**：
```bash
curl -X POST http://127.0.0.1:8000/course/42/invite-code/ \
    -H "Authorization: Bearer <access>"
```

---

## 課程邀請代碼刪除 API

**路徑**：`DELETE /course/<course_id>/invite-code/<code>/`

**說明**：刪除指定課程的邀請代碼，使學生無法再透過該代碼加入。僅課程教師本人或系統管理員可執行，代碼不分大小寫。

**路徑參數**

| 參數名        | 型別   | 必填 | 說明                 |
| ------------- | ------ | ---- | -------------------- |
| `course_id`   | int    | ✅   | 課程的流水號 ID      |
| `code`        | string | ✅   | 7 碼英數邀請代碼     |

**成功回應 (200 OK)**：

```json
{ "message": "Success.", "status_code": 200 }
```

**失敗回應**

| 狀況                   | HTTP | 範例訊息                                            |
| ---------------------- | ---- | --------------------------------------------------- |
| 未登入                 | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 非教師/管理員          | 403  | `{ "message": "Forbidden." }`                       |
| 非授課教師操作他人課程 | 403  | `{ "message": "You are not in this course." }`      |
| 課程不存在             | 404  | `{ "message": "Course not found." }`                |
| 邀請代碼錯誤/失效      | 400  | `{ "message": "Invalid join code." }`               |

**cURL 測試**：
```bash
curl -X DELETE http://127.0.0.1:8000/course/42/invite-code/XYZ12AB/ \
    -H "Authorization: Bearer <access>"
```

---

## 課程助教分配 API

**路徑**：`POST /course/<course_id>/assign-ta/`

**說明**：將指定學生設為該課程的助教。僅課程教師本人或系統管理員可操作；教師只能操作自己的課程。

**請求格式 (JSON)**

| 欄位名     | 型別   | 必填 | 說明                           |
| ---------- | ------ | ---- | ------------------------------ |
| `username` | string | ✅   | 要升為助教的學生帳號           |

**成功回應 (200 OK)**

```json
{ "message": "Success.", "status_code": 200 }
```

**失敗回應**

| 狀況                     | HTTP | 範例訊息                                            |
| ------------------------ | ---- | --------------------------------------------------- |
| 未登入                   | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 權限不足（非教師/管理員）| 403  | `{ "message": "Forbidden." }`                       |
| 非授課教師操作他人課程   | 403  | `{ "message": "You are not in this course." }`      |
| 課程不存在               | 404  | `{ "message": "Course not found." }`                |
| 指定帳號不存在           | 404  | `{ "message": "User not found." }`                  |
| 指定帳號不是學生         | 400  | `{ "message": "User is not a student." }`           |

**cURL 測試**：
```bash
curl -X POST http://127.0.0.1:8000/course/42/assign-ta/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access>" \
    -d '{"username": "student01"}'
```

---

## 課程成員調整 API

**路徑**：`PUT /course/<course_id>/`

**說明**：批次調整課程學生（移除與加入）。僅課程教師本人或系統管理員可執行；教師只能操作自己的課程。

**路徑/查詢參數**

| 參數名      | 來源 | 型別 | 必填 | 說明                     |
| ----------- | ---- | ---- | ---- | ------------------------ |
| `course_id` | URL  | int | ✅   | 課程 ID（整數）                  |

**請求格式 (JSON)**

| 欄位名 | 型別 | 必填 | 說明                                 |
| ------ | ---- | ---- | ------------------------------------ |
| `remove` | list | ❌   | 要移除的學生 ID 列表（UUID） |
| `new`    | list | ❌   | 要加入課程的學生 ID 列表（UUID） |

> 備註：`remove`、`new` 皆可省略或給空陣列，代表該方向不異動。

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
| 指定學生不存在或不在該課程內   | 404  | `{ "message": "Student not found." }`    |
| 要加入者不是學生               | 400  | `{ "message": "User is not a student." }` |
| 學生已在課程內                 | 400  | `{ "message": "Student already in this course." }` |
| 已達人數上限                   | 403  | `{ "message": "Course is full." }`       |

**cURL 測試**

```bash
curl -X PUT "http://127.0.0.1:8000/course/<course_id>/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access>" \
    -d '{
    "remove": ["<student_id_to_remove>"],
    "new": ["<student_id_to_add_1>", "<student_id_to_add_2>"]
    }'
```

---

## CSV 批次匯入學生 API

**路徑**：`POST /course/<course_id>/import-csv/`

**說明**：以 CSV 檔批次匯入學生帳號並加入指定課程。僅管理員或授課教師可操作；教師只能匯入自己的課程；檔案大小上限 5MB。

**請求格式 (multipart/form-data)**：

| 欄位    | 必填 | 說明                                                                 |
| ------- | ---- | -------------------------------------------------------------------- |
| `file`  | ✅   | 上傳的 CSV 檔案                                                      |
| `force` | ❌   | 布林，`1/true` 時若帳號已存在會覆寫 email/real_name/student_id，預設為不更新 |

**CSV 欄位**

| 欄位名       | 必填 | 說明                                               |
| ------------ | ---- | -------------------------------------------------- |
| `username`   | ✅   | 學生帳號（全域唯一）                               |
| `email`      | ✅   | 學生 Email（全域唯一）                             |
| `real_name`  | ✅   | 學生姓名                                           |
| `student_id` | ❌   | 學號，若提供會寫入 `UserProfile.student_id`         |
| `password`   | ❌   | 初始密碼，未填時會自動產生隨機密碼                 |

**成功回應 (200 OK)**：

```json
{
  "message": "Success.",
  "status_code": 200,
  "data": {
    "import": {
      "id": "1c9d48e0-7c8d-4f5e-9e6a-12ab34cd56ef",
      "status": "completed",
      "fileName": "students.csv",
      "fileSize": 1240,
      "importResult": true,
      "createdUsers": 2,
      "newMembers": 2,
      "skippedExistingMembers": 0,
      "errorCount": 0,
      "errors": []
    }
  }
}
```

> 備註：若部分列有問題（例如重複帳號、身分非學生、課程人數已滿等），`importResult` 會是 `false`，`errors` 會列出失敗的列號與原因，已通過的列仍會成功匯入。

**失敗回應**

| 狀況                     | HTTP | 範例訊息                                           |
| ------------------------ | ---- | -------------------------------------------------- |
| 未登入                   | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 權限不足                 | 403  | `{ "message": "Forbidden." }`                      |
| 非授課教師操作他人課程   | 403  | `{ "message": "You are not in this course." }`     |
| 課程已達學生上限         | 403  | `{ "message": "Course is full." }`                 |
| 課程不存在               | 404  | `{ "message": "Course not found." }`               |
| 檔案格式錯誤或缺少欄位   | 400  | `{ "message": "Missing required columns: ..." }`   |

**cURL 測試**

```bash
curl -X POST http://127.0.0.1:8000/course/42/import-csv/ \
    -H "Authorization: Bearer <access>" \
    -F "file=@./students.csv" \
    -F "force=1"
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
| `new_title` | string | ❌ | 新標題，若缺省則維持原標題 |
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

---

## 課程計分板 API

**路徑**：`GET /course/<course_id>/scoreboard/`

**說明**：查看課程內指定題目的計分板。需登入且具評分權限（教師、助教或管理員）。

**查詢參數**

| 參數名   | 型別   | 必填 | 說明                                |
| -------- | ------ | ---- | ----------------------------------- |
| `pids`   | string | ✅   | 題目 ID 逗號串，如 `1,2,3`            |
| `start`  | float  | ❌   | 開始時間戳（秒），過濾 >= 該時間的提交 |
| `end`    | float  | ❌   | 結束時間戳（秒），過濾 <= 該時間的提交 |

**成功回應 (200 OK)**：

```json
{
  "message": "Success.",
  "data": {
    "courseId": 24,
    "problemIds": [101, 102],
    "timeRange": { "start": 1735708800.0, "end": null },
    "students": [
      {
        "userId": "d4b8f260-8dcd-4dd2-8c07-8bd6e3c0f001",
        "username": "student01",
        "realName": "學生甲",
        "scores": { "101": 90, "102": 70 },
        "totalScore": 160,
        "submittedCount": 2
      }
    ],
    "problemStats": [
      {
        "problemId": 101,
        "maxScore": 100,
        "averageScore": 95.0,
        "submissionCount": 3,
        "submitterCount": 2,
        "fullScore": 100
      }
    ]
  }
}
```

**失敗回應**

| 狀況                   | HTTP | 範例訊息                                    |
| ---------------------- | ---- | ------------------------------------------- |
| 未登入                 | 401  | `{ "detail": "Authentication credentials were not provided." }` |
| 無評分權限             | 403  | `{ "message": "Permission denied" }`        |
| `pids` 解析錯誤        | 400  | `{ "message": "Error occurred when parsing \`pids\`." }` |
| `start`/`end` 型別錯誤 | 400  | `{ "message": "Type of \`start\` should be float." }` |

**cURL 測試**

```bash
curl "http://127.0.0.1:8000/course/24/scoreboard/?pids=101,102&start=1735708800.0" \
  -H "Authorization: Bearer <access_token>"
```

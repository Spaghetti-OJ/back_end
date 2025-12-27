# Submission API 文檔

**更新日期**: 2025年11月23日  
**API 版本**: v2  
**基礎路徑**: `/submission/`

---

## 目錄

1. [概述](#概述)
2. [通用說明](#通用說明)
3. [API 端點](#api端點)
4. [與 NOJ 的差異](#與noj的差異)
5. [待實作功能](#待實作功能)
6. [錯誤處理](#錯誤處理)

---

## 概述

這是 Spaghetti-OJ 的提交（Submission）API 文檔，提供程式碼提交、查詢、判題等功能。
API 設計遵循 NOJ (Nanjing Online Judge) 的格式標準，確保前後端兼容性。

### 主要功能
- 程式碼提交（兩階段提交：先創建提交，再上傳代碼）
- 提交列表查詢（支援權限過濾）
- 提交詳情查詢
- 程式碼查看
- 標準輸出查看
- 重新判題

### 權限系統

**角色權限總覽**:

**學生**:
- 可查看自己的提交列表和詳情
- 可查看自己的程式碼和輸出
- 可提交程式碼
- 無法查看他人提交

**助教 (TA)**:
- 可查看所屬課程內所有提交
- 可查看課程內所有程式碼和輸出
- 可提交程式碼
- 可對課程內提交進行重新判題

**教師 (Teacher)**:
- 可查看所屬課程內所有提交
- 可查看課程內所有程式碼和輸出
- 可提交程式碼
- 可對課程內提交進行重新判題

**管理員 (Admin)**:
- 可查看所有提交
- 可查看所有程式碼和輸出
- 可對任何提交進行重新判題
- 完全權限

---

## 通用說明

### 資料格式

#### 請求格式
- Content-Type: `application/json`
- 需要在 Header 中攜帶認證 Token

#### 響應格式
所有 API 響應遵循統一的響應格式：

**成功響應**:
```json
{
    "data": {
        /* 實際數據內容 */
    },
    "message": "操作成功訊息",
    "status": "ok"
}
```

**錯誤響應**:
```json
{
    "data": null,
    "message": "錯誤訊息",
    "status": "error"
}
```

**注意**: 部分端點（如創建提交、上傳代碼）仍保留 NOJ 兼容的字串響應格式。

### 語言類型編碼

API 使用整數代表程式語言（與 NOJ 兼容）:

```
0 - C
1 - C++
2 - Python
3 - Java
4 - JavaScript
```

### 判題狀態編碼

```
-2 - Pending before upload (還沒上傳程式碼)
-1 - Pending (等待判題)
0  - Accepted (AC)
1  - Wrong Answer (WA)
2  - Compilation Error (CE)
3  - Time Limit Exceeded (TLE)
4  - Memory Limit Exceeded (MLE)
5  - Runtime Error (RE)
6  - Judge Error (JE)
7  - Output Limit Exceeded (OLE)
```

### 欄位命名慣例

API 使用 **camelCase** 命名慣例（與 NOJ 兼容）:
- `submissionId` (不是 `submission_id`)
- `problemId` (不是 `problem_id`)
- `languageType` (不是 `language_type`)
- `runTime` (不是 `run_time`)
- `memoryUsage` (不是 `memory_usage`)

---

## API 端點

### 1. 創建提交（第一階段）

創建一個新的提交記錄，此時不需要上傳程式碼。

**端點**: `POST /submission/`

**認證**: 必須（Bearer Token）

**請求參數**:
```json
{
    "problemId": 123,
    "languageType": 2
}
```

**參數說明**:
- `problemId` (必填): 題目 ID，整數，最小值為 1
- `languageType` (必填): 程式語言類型，整數 0-4

**成功響應**: HTTP 201
```
"submission recieved.{submission_id}"
```

**錯誤響應**:
- `400 Bad Request`: `"problemId is required!"` - 缺少 problemId
- `400 Bad Request`: `"post data missing!"` - 缺少 languageType
- `403 Forbidden`: `"not allowed language"` - 不支援的語言
- `404 Not Found`: `"Unexisted problem id."` - 題目不存在

**範例**:
```bash
# 請求
curl -X POST http://localhost:8000/submission/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "problemId": 1,
    "languageType": 2
  }'

# 成功響應
"submission recieved.a1b2c3d4-5678-90ab-cdef-1234567890ab"
```

---

### 2. 上傳程式碼（第二階段）

將程式碼上傳到已創建的提交中，上傳後會自動送往判題系統。

**端點**: `PUT /submission/{submissionId}/`

**認證**: 必須（Bearer Token）

**請求參數**:
```json
{
    "source_code": "print('Hello, World!')"
}
```

**參數說明**:
- `source_code` (必填): 程式碼內容，字串，最大 64KB

**成功響應**: HTTP 200
```
"{submission_id} send to judgement."
```

**錯誤響應**:
- `400 Bad Request`: `"can not find the source file"` - 提交不存在
- `400 Bad Request`: `"empty file"` - 程式碼為空
- `403 Forbidden`: `"user not equal!"` - 不是提交者本人
- `403 Forbidden`: `"{submission_id} has finished judgement."` - 已判題完成
- `403 Forbidden`: `"{submission_id} has been uploaded source file!"` - 已上傳過代碼

**範例**:
```bash
# 請求
curl -X PUT http://localhost:8000/submission/a1b2c3d4-5678-90ab-cdef-1234567890ab/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "def solve():\n    print(\"Hello\")\nsolve()"
  }'

# 成功響應
"a1b2c3d4-5678-90ab-cdef-1234567890ab send to judgement."
```

---

### 3. 獲取提交列表

獲取當前用戶有權限查看的提交列表（根據角色過濾）。

**端點**: `GET /submission/`

**認證**: 必須（Bearer Token）

**查詢參數**:
- `page` (可選): 頁碼，預設 1
- `page_size` (可選): 每頁數量，預設 20
- `problem_id` (可選): 篩選特定題目的提交
- `username` (可選): 篩選特定使用者的提交
- `status` (可選): 篩選判題狀態（如 "0"=AC, "1"=WA, "2"=CE, "3"=TLE, "4"=MLE, "5"=RE）
- `course_id` (可選): 篩選特定課程的所有提交
- `language_type` (可選): 篩選程式語言（0=C, 1=C++, 2=Python, 3=Java, 4=JavaScript）
- `before` (可選): 篩選某時間之前的提交（Unix 時間戳記，單位：秒）
- `after` (可選): 篩選某時間之後的提交（Unix 時間戳記，單位：秒）

**權限說明**:
- 學生：只能查看自己的提交
- 教師/助教：可以查看自己所教課程的所有學生提交
- 管理員：可以查看所有提交

**成功響應**: HTTP 200
```json
{
    "data": {
        "results": [
            {
                "submissionId": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                "problemId": 123,
                "user": {
                    "id": "user-uuid",
                    "username": "student01",
                    "real_name": "張三"
                },
                "status": "0",
                "score": 100,
                "runTime": 123,
                "memoryUsage": 2048,
                "languageType": "2",
                "timestamp": "2025-11-09T10:30:00Z",
                "ipAddr": "192.168.1.100"
            }
        ],
        "count": 150
    },
    "message": "here you are, bro",
    "status": "ok"
}
```

**響應欄位說明**:
- `submissionId`: 提交 UUID
- `problemId`: 題目 ID
- `user`: 提交者資訊
  - `id`: 用戶 UUID
  - `username`: 用戶名稱
  - `real_name`: 真實姓名
- `status`: 判題狀態（字串格式的數字）
- `score`: 得分（0-100）
- `runTime`: 執行時間（毫秒），未判題時為 `-`
- `memoryUsage`: 記憶體使用量（KB），未判題時為 `-`
- `languageType`: 語言類型（字串格式的數字）
- `timestamp`: 提交時間（ISO 8601 格式）
- `ipAddr`: 提交 IP

**範例**:
```bash
# 基本查詢
curl -X GET "http://localhost:8000/submission/?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 查詢課程 3 的所有 AC 提交
curl -X GET "http://localhost:8000/submission/?course_id=3&status=0" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 查詢特定使用者用 Python 的提交
curl -X GET "http://localhost:8000/submission/?username=student01&language_type=2" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 查詢特定時間範圍的提交（2025-12-27 00:00:00 到 23:59:59）
curl -X GET "http://localhost:8000/submission/?after=1735286400&before=1735372799" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 組合多個篩選條件
curl -X GET "http://localhost:8000/submission/?problem_id=123&status=0&language_type=2" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 4. 獲取提交詳情

獲取單一提交的詳細資訊（不包含程式碼內容）。

**端點**: `GET /submission/{submissionId}/`

**認證**: 必須（Bearer Token）

**成功響應**: HTTP 200
```json
{
    "data": {
        "submissionId": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
        "problemId": 123,
        "user": {
            "id": "user-uuid",
            "username": "student01",
            "real_name": "張三"
        },
        "timestamp": "2025-11-09T10:30:00Z",
        "lastSend": "2025-11-09T10:30:15Z",
        "status": "0",
        "score": 100,
        "runTime": 123,
        "memoryUsage": 2048,
        "languageType": "2",
        "ipAddr": "192.168.1.100"
    },
    "message": "here you are, bro",
    "status": "ok"
}
```

**新增欄位**:
- `lastSend`: 最後判題時間（ISO 8601 格式），未判題時為 `-`

**錯誤響應**:
- `403 Forbidden`: `"no permission"` - 無權限查看
- `404 Not Found`: `"can not find submission"` - 提交不存在

**範例**:
```bash
# 請求
curl -X GET http://localhost:8000/submission/a1b2c3d4-5678-90ab-cdef-1234567890ab/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 5. 獲取程式碼

獲取提交的原始程式碼內容。

**端點**: `GET /submission/{submissionId}/code/`

**認證**: 必須（Bearer Token）

**成功響應**: HTTP 200
```json
{
    "data": {
        "id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
        "source_code": "def solve():\n    print('Hello')\nsolve()",
        "language_type": 2,
        "created_at": "2025-11-09T10:30:00Z"
    },
    "message": "here you are, bro",
    "status": "ok"
}
```

**響應欄位說明**:
- `id`: 提交 UUID
- `source_code`: 程式碼內容（完整文本）
- `language_type`: 語言類型（整數）
- `created_at`: 創建時間

**錯誤響應**:
- `403 Forbidden`: `"no permission"` - 無權限查看
- `404 Not Found`: `"can not find submission"` - 提交不存在
- `404 Not Found`: `"can not find the source file"` - 程式碼不存在

**範例**:
```bash
# 請求
curl -X GET http://localhost:8000/submission/a1b2c3d4-5678-90ab-cdef-1234567890ab/code/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 6. 獲取標準輸出

獲取提交執行後的標準輸出內容。

**端點**: `GET /submission/{submissionId}/stdout/`

**認證**: 必須（Bearer Token）

**成功響應**: HTTP 200
```json
{
    "data": {
        "stdout": "Test Case 1:\nHello, World!\n\nTest Case 2:\nWelcome\n",
        "submission_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
        "status": "0"
    },
    "message": "here you are, bro",
    "status": "ok"
}
```

**響應欄位說明**:
- `stdout`: 標準輸出內容（合併所有測試案例），未判題時為 `-`
- `submission_id`: 提交 UUID
- `status`: 判題狀態

**錯誤響應**:
- `403 Forbidden`: `"no permission"` - 無權限查看
- `404 Not Found`: `"can not find submission"` - 提交不存在

**範例**:
```bash
# 請求
curl -X GET http://localhost:8000/submission/a1b2c3d4-5678-90ab-cdef-1234567890ab/stdout/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 6.1 獲取單一測資輸出

取得指定提交在某個 subtask 的單一測資（test case）的執行結果與輸出預覽。

**端點**: `GET /submission/{submissionId}/output/{task_no}/{case_no}/`

**認證**: 必須（Bearer Token）

**成功響應**: HTTP 200
```json
{
    "data": {
        "submission_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
        "task_no": 1,
        "case_no": 3,
        "status": "accepted",
        "score": 10,
        "max_score": 10,
        "execution_time": 34,
        "memory_usage": 2048,
        "output": "Hello world\n",
        "error_message": "",
        "judge_message": ""
    },
    "message": "ok",
    "status": "ok"
}
```

**響應欄位說明**:
- `submission_id`: 提交 UUID（字串）
- `task_no`: subtask 編號（整數）
- `case_no`: 測資編號（整數）
- `status`: 該測資狀態（例如 'accepted', 'wrong_answer', 'time_limit_exceeded'）
- `score`: 該測資的得分
- `max_score`: 該測資滿分
- `execution_time`: 執行時間（毫秒，若無則為 null 或 -1）
- `memory_usage`: 記憶體使用（KB，若無則為 null 或 -1）
- `output`: 輸出預覽（可能為部分內容或空字串）
- `error_message`: 判題錯誤訊息（如編譯錯誤等）
- `judge_message`: 判題器回傳之附加訊息（前端顯示前請注意隱私）

**錯誤響應**:
- `401 Unauthorized`: 未提供或無效 token
- `403 Forbidden`: `"no permission"` - 無權查看該提交
- `404 Not Found`: `"submission not found"` / `"task_no not found"` / `"case_no not found"` / `"output not found"`
- `500 Internal Server Error`: 伺服器錯誤

**範例**:
```bash
# 取得 submission 的 subtask=1 case=3 的輸出
curl -X GET \
  "http://localhost:8000/submission/a1b2c3d4-5678-90ab-cdef-1234567890ab/output/1/3/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```


### 7. 重新判題

重新判題已提交的程式（僅限教師/助教/管理員）。

**端點**: `GET /submission/{submissionId}/rejudge/`

**認證**: 必須（Bearer Token）

**權限要求**: 
- 題目所屬課程的教師或助教
- 或系統管理員

**成功響應**: HTTP 200
```
"{submission_id} rejudge successfully."
```

**錯誤響應**:
- `400 Bad Request`: `"can not find the source file"` - 沒有程式碼（status=-2）
- `403 Forbidden`: `"no permission"` - 無權限操作
- `404 Not Found`: `"can not find submission"` - 提交不存在
- `500 Internal Server Error`: `"Some error occurred, please contact the admin"` - 系統錯誤

**行為說明**:
- 重設提交狀態為 `-1` (Pending)
- 清除原有得分、執行時間、記憶體使用量
- 刪除舊的判題結果
- 將提交送回判題系統

**範例**:
```bash
# 請求
curl -X GET http://localhost:8000/submission/a1b2c3d4-5678-90ab-cdef-1234567890ab/rejudge/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 成功響應
"a1b2c3d4-5678-90ab-cdef-1234567890ab rejudge successfully."
```

---

## 與 NOJ 的差異

### 已兼容的部分

1. **URL 結構**: 使用 `/submission/` (單數形式)
2. **響應格式**: 錯誤訊息返回字串，不是 JSON 對象
3. **欄位命名**: 使用 camelCase（submissionId, problemId, languageType 等）
4. **語言編碼**: 整數 0-4 代表不同語言
5. **狀態編碼**: 字串格式的數字 "-2" 到 "7"
6. **兩階段提交**: 先 POST 創建，再 PUT 上傳代碼
7. **錯誤訊息**: 完全使用 NOJ 的原始訊息格式

### 與 NOJ 的主要差異

#### 0. 響應格式（重要）
**NOJ**: 數據直接返回在根層級
```json
{
    "message": "here you are, bro",
    "submissionId": "...",
    "problemId": 123
}
```

**我們**: 數據包裝在 `data` 欄位中
```json
{
    "data": {
        "submissionId": "...",
        "problemId": 123
    },
    "message": "here you are, bro",
    "status": "ok"
}
```

**影響**: 
- 前端需要從 `response.data.data` 獲取實際數據
- 錯誤時 `data` 為 `null`，錯誤訊息在 `message` 中
- 新增 `status` 欄位指示 "ok" 或 "error"
- **例外**: 創建提交（POST）和上傳代碼（PUT）仍返回字串格式以保持 NOJ 兼容

#### 1. 認證方式
**NOJ**: 使用 Session Cookie  
**我們**: 使用 JWT Bearer Token

**影響**: 前端需要在 Header 中攜帶 `Authorization: Bearer {token}`

#### 2. 用戶欄位格式
**NOJ**:
```json
"user": {
    "id": 123,
    "username": "student01"
}
```

**我們**:
```json
"user": {
    "id": "uuid-string",
    "username": "student01",
    "real_name": "張三"
}
```

**影響**: user.id 是 UUID 字串而非整數，新增 real_name 欄位

#### 3. 時間戳格式
**NOJ**: Unix 時間戳（秒）  
**我們**: ISO 8601 格式字串

```json
// NOJ
"timestamp": 1699516200

// 我們
"timestamp": "2025-11-09T10:30:00Z"
```

**影響**: 前端需要使用 `new Date(timestamp)` 而非 `new Date(timestamp * 1000)`

#### 4. 提交 ID 格式
**NOJ**: 整數 ID  
**我們**: UUID 字串

```
// NOJ
submission_id: 12345

// 我們
submissionId: "a1b2c3d4-5678-90ab-cdef-1234567890ab"
```

**影響**: URL 參數和響應中的 ID 都是 UUID 字串

#### 5. 語言類型格式
**API 響應中的差異**:
- NOJ: 返回字串 "2"
- 我們: 返回字串 "2" （兼容）

**API 請求中的差異**:
- NOJ: 接受整數 2 或字串 "2"
- 我們: 只接受整數 2

---

## 待實作功能

以下功能在 NOJ 中存在，但我們尚未實作：

### 1. 提交限制檢查
- [ ] `"problem permission denied"` - 題目權限檢查
- [ ] `"homework hasn't start"` - 作業時間檢查
- [ ] `"Invalid IP address"` - IP 白名單檢查
- [ ] `"you have used all your quotas"` - 配額限制
- [ ] `"Submit too fast!"` - 提交頻率限制（含 `waitFor` 欄位）

### 2. 判題系統整合
- [ ] 實際連接 SandBox 判題系統
- [ ] 支援自訂測試資料


### 3. 過濾與排序
- [ ] 按題目 ID 過濾
- [ ] 按狀態過濾
- [ ] 按語言過濾
- [ ] 按時間排序
- [ ] 按得分排序

### 4. 統計資料
- [ ] 用戶提交統計
- [ ] 題目提交統計
- [ ] 通過率計算
- [ ] 排行榜功能

### 5. 程式碼相似度檢測
- [ ] 抄襲檢測
- [ ] 相似度報告

### 6. 批次操作
- [ ] 批次重新判題
- [ ] 批次匯出提交

---

## 錯誤處理

### HTTP 狀態碼

我們使用標準 HTTP 狀態碼，並遵循明確的語義：

**200 OK**
- 成功取得資源
- 操作成功完成

**201 Created**
- 成功創建新提交

**400 Bad Request**
- 請求參數格式錯誤
- 缺少必填欄位
- 資料驗證失敗

**401 Unauthorized**
- 未提供認證 Token
- Token 已過期
- Token 無效

**403 Forbidden**
- 已認證但無權限執行操作
- 例如: 學生試圖查看他人程式碼

**404 Not Found**
- 請求的資源不存在
- 例如: 提交 ID 不存在

**500 Internal Server Error**
- 伺服器內部錯誤
- 判題系統異常

### 錯誤響應格式

與 NOJ 兼容，錯誤訊息直接返回字串：

```
// 正確格式
"error message here"

// 不是這樣
{
    "error": "error message here"
}
```

### 常見錯誤訊息

**提交創建階段**:
```
"problemId is required!"           - 缺少題目 ID
"post data missing!"                - 缺少語言類型
"not allowed language"              - 不支援的語言
"Unexisted problem id."             - 題目不存在
"invalid data!"                     - 其他資料驗證錯誤
```

**代碼上傳階段**:
```
"can not find the source file"     - 提交不存在或程式碼為空
"empty file"                        - 程式碼內容為空
"user not equal!"                   - 不是提交者本人
"{id} has finished judgement."      - 已判題完成，無法上傳
"{id} has been uploaded source file!" - 已上傳過代碼
```

**查詢階段**:
```
"no permission"                     - 無權限查看
"can not find submission"           - 提交不存在
```

**重新判題階段**:
```
"no permission"                     - 無權限操作
"can not find submission"           - 提交不存在
"can not find the source file"     - 沒有程式碼（status=-2）
"{id} rejudge successfully."        - 重新判題成功
"Some error occurred, please contact the admin" - 系統錯誤
```

---

## 測試指南

### 完整提交流程測試

```bash
# 1. 登入取得 Token
TOKEN="your-jwt-token-here"

# 2. 創建提交
SUBMISSION_ID=$(curl -X POST http://localhost:8000/submission/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"problemId": 1, "languageType": 2}' \
  | grep -o '[0-9a-f-]\{36\}')

echo "Created submission: $SUBMISSION_ID"

# 3. 上傳程式碼
curl -X PUT http://localhost:8000/submission/$SUBMISSION_ID/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_code": "print(\"Hello, World!\")"}'

# 4. 查詢提交詳情
curl -X GET http://localhost:8000/submission/$SUBMISSION_ID/ \
  -H "Authorization: Bearer $TOKEN"

# 5. 查看程式碼
curl -X GET http://localhost:8000/submission/$SUBMISSION_ID/code/ \
  -H "Authorization: Bearer $TOKEN"

# 6. 查看標準輸出
curl -X GET http://localhost:8000/submission/$SUBMISSION_ID/stdout/ \
  -H "Authorization: Bearer $TOKEN"
```

### 權限測試

```bash
# 測試學生無法查看他人提交
curl -X GET http://localhost:8000/submission/other-user-submission-id/ \
  -H "Authorization: Bearer $STUDENT_TOKEN"
# 預期: 403 "no permission"

# 測試教師可以查看課程內提交
curl -X GET http://localhost:8000/submission/student-submission-id/ \
  -H "Authorization: Bearer $TEACHER_TOKEN"
# 預期: 200 成功返回資料
```

---

## 版本歷史

**v1.0 (2025-11-09)**
- 初始版本
- 實作基本提交功能（創建、上傳、查詢）
- 兼容 NOJ 格式標準
- 實作角色權限系統
- 支援重新判題功能
- 166 個測試全部通過

---

## 聯絡資訊

如有問題或建議，請聯絡開發團隊：
- **Repository**: Spaghetti-OJ/back_end
- **Branch**: feat/submission-API
- **作者**: 柯良運
---

**文檔結束**

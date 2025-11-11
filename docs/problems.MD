# 題目（Problems）API 說明

本節說明目前可用的題目 API。後端採用 Django + DRF + Simple JWT，所有請求/回應皆為 JSON。

---

## 權限與可見性

題目有三種可見性（欄位 `is_public`）：
- `public`：所有人可見
- `course`：僅該題目所屬課程（課程成員）與管理者/教師/題目擁有者可見
- `hidden`：僅題目擁有者與管理者/教師可見

另外：
- 建立、管理題目需具備管理員或教師身分。
- 每個題目都必須關聯一個 `course_id`（必填）。
- 標籤（tags）採用嚴格驗證：傳入的所有 tag id 必須存在，否則回傳 400。

---

## 取得題目列表

- 路徑：`GET /problem/`
- 說明：依權限回傳題目列表，支援篩選與分頁。
- 查詢參數：
  - `difficulty`: `easy|medium|hard`
  - `is_public`: `public|course|hidden`
  - `course_id`: 課程 UUID
  - `page`, `page_size`: 分頁參數

成功回應（200 OK，略）：
```json
[
  {
    "id": 1,
    "title": "Two Sum",
    "difficulty": "easy",
    "is_public": "public",
    "course_id": "<uuid>",
    "tags": [
      {"id": 1, "name": "陣列", "usage_count": 10}
    ],
    "created_at": "2025-11-08T06:45:00Z"
  }
]
```

**cURL 測試**：
```bash
curl "http://127.0.0.1:8000/problem/" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 查看題目詳情（學生視角）

- 路徑：`GET /problem/<problem_id>`
- 說明：回傳題目詳情；未登入僅能查看 `public` 題目。對於 `course`/`hidden` 依權限與課程成員資格判斷。

成功回應（200 OK，部分欄位省略）：
```json
{
  "id": 1,
  "title": "Two Sum",
  "difficulty": "easy",
  "is_public": "public",
  "course_id": "<uuid>",
  "tags": [{"id":1, "name":"陣列", "usage_count": 10}],
  "submit_count": 2,
  "high_score": 80
}
```
未登入時 `submit_count`/`high_score` 會為 `null`。

**cURL 測試**：
```bash
curl "http://127.0.0.1:8000/problem/$PROBLEM_ID" \
  -H "Authorization: Bearer $TOKEN"
```

可能錯誤：
- 401 未登入（針對非公開題目）
- 403 非課程成員/非擁有者/非教師管理員（當題目為 `course` 或 `hidden`）
- 404 題目不存在

---

## 取得題目最高分數

- 路徑：`GET /problem/<problem_id>/high-score`
- 權限：需要登入
- 說明：回傳當前使用者在該題目的最高分數。若從未提交過則回傳 0。

成功回應（200 OK）：
```json
{
  "score": 85
}
```

可能錯誤：
- 401 未登入
- 404 題目不存在

**cURL 測試**：
```bash
curl "http://127.0.0.1:8000/problem/$PROBLEM_ID/high-score" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 取得題目統計資訊

- 路徑：`GET /problem/<problem_id>/stats`
- 權限：需要登入
- 說明：回傳該題目的統計資料，包含 AC 用戶數、嘗試用戶數、平均分數、標準差、分數分布、狀態統計、top10 執行時間/記憶體使用。

成功回應範例（200 OK）：
```json
{
  "acUserRatio": [5, 20],
  "triedUserCount": 12,
  "average": 67.5,
  "std": 15.2,
  "scoreDistribution": [
    {"score": 0, "count": 2},
    {"score": 50, "count": 3},
    {"score": 100, "count": 7}
  ],
  "statusCount": {
    "accepted": 7,
    "wrong_answer": 3,
    "runtime_error": 2
  },
  "top10RunTime": [
    {"id": "...", "user": "...", "execution_time": 120, "score": 100, "status": "accepted"}
  ],
  "top10MemoryUsage": [
    {"id": "...", "user": "...", "memory_usage": 1024, "score": 100, "status": "accepted"}
  ]
}
```

**欄位說明**：
- `acUserRatio`: `[AC 用戶數, 總學生數]`，總學生數為該題目所屬課程的學生成員數
- `triedUserCount`: 曾提交過該題目的不重複用戶數
- `average`: 所有提交的平均分數
- `std`: 所有提交分數的標準差
- `scoreDistribution`: 分數分布陣列，每個元素包含 `score` 和 `count`
- `statusCount`: 各提交狀態的統計數量（如 accepted, wrong_answer 等）
- `top10RunTime`: 執行時間最短的前 10 筆提交（只包含 execution_time > 0）
- `top10MemoryUsage`: 記憶體使用最少的前 10 筆提交（只包含 memory_usage > 0）

可能錯誤：
- 401 未登入
- 404 題目不存在

**cURL 測試**：
```bash
curl "http://127.0.0.1:8000/problem/$PROBLEM_ID/stats" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 建立題目（管理）

- 路徑：`POST /problem/manage`
- 權限：教師 / 管理員 / 該課程的 TA（課程成員角色為 `ta`）
- 說明：建立一個新題目；必須指定 `course_id`。可附上 `tags`（id 陣列）。

### 欄位規格一覽（建立 / 更新通用）

| 欄位 | 型別 | 必填 | 預設值 | 說明 |
| ---- | ---- | ---- | ------ | ---- |
| title | string | ✅ | (無) | 題目標題，長度 ≤ 200 |
| description | string | ✅ | (無) | 題目敘述主體內容 |
| course_id | UUID | ✅ | (無) | 所屬課程，必須為存在的課程 UUID |
| difficulty | string | ❌ | `medium` | `easy|medium|hard` |
| is_public | string | ❌ | `hidden` | 可見性：`public|course|hidden` |
| max_score | int | ❌ | `100` | 滿分（評測相關，可保留預設） |
| total_quota | int | ❌ | `-1` | 提交上限；`-1` 代表不限次數 |
| input_description | string/null | ❌ | null | 輸入格式說明 |
| output_description | string/null | ❌ | null | 輸出格式說明 |
| sample_input | string/null | ❌ | null | 樣例輸入 |
| sample_output | string/null | ❌ | null | 樣例輸出 |
| hint | string/null | ❌ | null | 提示文字 |
| subtask_description | string/null | ❌ | null | 子任務敘述（若有 subtasks） |
| supported_languages | array | ❌ | `["c","cpp","java","python"]` | 可提交語言（陣列字串） |
| tags | int[] | ❌ | (無) | 標籤 id 陣列；嚴格驗證全部必須存在 |

備註：
1. 未提供可選欄位則使用預設或留空（null）。
2. `tags` 為寫入用；回傳時使用 `tags` 物件陣列（含 id/name/usage_count）。
3. 不支援在建立時直接寫 `like_count`、`view_count` 等統計欄位。

### 最小可建立 Payload（僅必填）
```json
{
  "title": "Two Sum",
  "description": "Find two numbers.",
  "course_id": "<uuid>"
}
```

### 完整範例 Payload（含全部常用欄位）
```json
{
  "title": "Two Sum",
  "description": "Find two numbers that add to target.",
  "course_id": "<uuid>",
  "difficulty": "easy",
  "is_public": "public",
  "max_score": 100,
  "total_quota": -1,
  "input_description": "n followed by array and target",
  "output_description": "indices i j",
  "sample_input": "5\n2 7 11 15 9\n9",
  "sample_output": "0 1",
  "hint": "使用雜湊表",
  "subtask_description": "Subtask1: n<=1000; Subtask2: n<=1e5",
  "supported_languages": ["c","cpp","python"],
  "tags": [1,2]
}
```

請求（JSON）（一般常見簡化版）：
```json
{
  "title": "Two Sum",
  "description": "...",
  "difficulty": "easy",
  "is_public": "public",
  "course_id": "<uuid>",
  "tags": [1, 2]
}
```

成功回應（201 Created）：
```json
{ "success": true, "problem_id": 1 }
```

錯誤情況：
- 422 驗證錯誤（必填欄位缺失等）
- 400 `tags` 含有不存在的 id（嚴格驗證）
- 403 權限不足（非 admin/teacher 且不是該課程 TA）

### cURL 測試

> 最小建立（僅必填）
```bash
curl -X POST http://127.0.0.1:8000/problem/manage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Two Sum",
    "description": "Find two numbers.",
    "course_id": "'$COURSE_ID'"
  }'
```

> 完整建立（含 tags 與所有可選欄位）
```bash
curl -X POST http://127.0.0.1:8000/problem/manage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Two Sum",
    "description": "Find two numbers that add to target.",
    "course_id": "'$COURSE_ID'",
    "difficulty": "easy",
    "is_public": "public",
    "max_score": 100,
    "total_quota": -1,
    "input_description": "n followed by array and target",
    "output_description": "indices i j",
    "sample_input": "5\n2 7 11 15 9\n9",
    "sample_output": "0 1",
    "hint": "使用雜湊表",
    "subtask_description": "Subtasks explained here",
    "supported_languages": ["c","cpp","python"],
    "tags": [1,2]
  }'
```

> 建立（無效 tag，預期 400）
```bash
curl -X POST http://127.0.0.1:8000/problem/manage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bad Tags",
    "description": "Test invalid tags.",
    "course_id": "'$COURSE_ID'",
    "tags": [99999]
  }'
```

---

## 取得題目管理資訊（管理）

- 路徑：`GET /problem/manage/<problem_id>`
- 權限：教師或管理員（或題目擁有者）
- 說明：回傳完整題目資訊（包含 subtasks/test cases 等管理用欄位）。

成功回應（200 OK）：結構與一般詳情類似，但欄位更完整，略。

---

## 編輯題目（管理）

- 路徑：`PUT /problem/manage/<problem_id>`
- 權限：教師 / 管理員 / 題目擁有者 / 該課程 TA（課程成員角色為 `ta`）
- 說明：可更新標題、描述、可見性、課程、標籤等(理論上所有欄位都可以透過這個編輯，欄位可參考上面的建立題目)。若提供 `tags`，將以提供的 id 陣列覆蓋既有關聯，且會做嚴格驗證。

請求（JSON）：
```json
{
  "title": "Two Sum v2",
  "is_public": "course",
  "tags": [2, 3]
}
```

成功回應（200 OK）：
```json
{ "success": true, "problem_id": 1 }
```

錯誤情況：
- 422 驗證錯誤
- 400 `tags` 中有不存在的 id
- 403 權限不足
- 404 題目不存在

### cURL 測試

> 更新部分欄位（改可見性 + 覆蓋 tags）
```bash
curl -X PUT http://127.0.0.1:8000/problem/manage/$PROBLEM_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_public": "course",
    "tags": [2,3]
  }'
```

> 更新補充描述欄位
```bash
curl -X PUT http://127.0.0.1:8000/problem/manage/$PROBLEM_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hint": "嘗試使用雙指針",
    "sample_input": "4\n1 2 3 4\n5",
    "sample_output": "1 3"
  }'
```

> 無效 tag 更新（預期 400）
```bash
curl -X PUT http://127.0.0.1:8000/problem/manage/$PROBLEM_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tags": [2,99999]
  }'
```

---

## 刪除題目（管理）

- 路徑：`DELETE /problem/manage/<problem_id>`
- 權限：教師或管理員（或題目擁有者）
- 成功回應：`204 No Content`

> 範例curl
```bash
curl -X DELETE http://127.0.0.1:8000/problem/manage/$PROBLEM_ID \
  -H "Authorization: Bearer $TOKEN"
```

---










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

## 按讚題目

- 路徑：`POST /problem/<problem_id>/like`
- 權限：需要登入
- 說明：對指定題目按讚。若已按讚過則回傳 400 錯誤。

成功回應（201 Created）：
```json
{
  "detail": "Liked",
  "likes_count": 15
}
```

可能錯誤：
- 400 已按過讚（`You already liked this problem.`）
- 401 未登入
- 404 題目不存在
- 500 操作失敗

**cURL 測試**：
```bash
curl -X POST "http://127.0.0.1:8000/problem/$PROBLEM_ID/like" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 取消按讚題目

- 路徑：`DELETE /problem/<problem_id>/like`
- 權限：需要登入
- 說明：取消對指定題目的按讚。若尚未按讚則回傳 400 錯誤。

成功回應（200 OK）：
```json
{
  "detail": "Unliked",
  "likes_count": 14
}
```

可能錯誤：
- 400 尚未按讚（`You have not liked this problem.`）
- 401 未登入
- 404 題目不存在
- 500 操作失敗

**cURL 測試**：
```bash
curl -X DELETE "http://127.0.0.1:8000/problem/$PROBLEM_ID/like" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 取得題目按讚數

- 路徑：`GET /problem/<problem_id>/likes`
- 權限：無需登入
- 說明：回傳指定題目的按讚總數（`like_count` 欄位）。

成功回應（200 OK）：
```json
{
  "likes_count": 42
}
```

可能錯誤：
- 404 題目不存在

**cURL 測試**：
```bash
curl "http://127.0.0.1:8000/problem/$PROBLEM_ID/likes"
```

---

## 取得我按過讚的題目列表

- 路徑：`GET /problem/liked`
- 權限：需要登入
- 說明：回傳當前使用者按讚過的所有題目（依建立時間倒序）。回傳格式與題目列表相同，包含每個題目的 `is_liked_by_user`（恆為 `true`）、`submit_count`、`high_score` 等個人化欄位。

成功回應（200 OK）：
```json
[
  {
    "id": 3,
    "title": "Binary Search",
    "difficulty": "medium",
    "is_public": "public",
    "course_id": "<uuid>",
    "tags": [{"id": 1, "name": "搜尋", "usage_count": 5}],
    "submit_count": 10,
    "high_score": 100,
    "is_liked_by_user": true,
    "created_at": "2025-11-10T08:00:00Z"
  },
  {
    "id": 1,
    "title": "Two Sum",
    "difficulty": "easy",
    "is_public": "public",
    "course_id": "<uuid>",
    "tags": [{"id": 2, "name": "陣列", "usage_count": 12}],
    "submit_count": 5,
    "high_score": 80,
    "is_liked_by_user": true,
    "created_at": "2025-11-08T06:45:00Z"
  }
]
```

可能錯誤：
- 401 未登入

**cURL 測試**：
```bash
curl "http://127.0.0.1:8000/problem/liked" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 標籤（Tags）API

提供四個操作：
1. 取得所有標籤：`GET /problem/tags`
2. 建立新標籤：`POST /problem/tags`
3. 新增標籤到題目：`POST /problem/<problem_id>/tags`
4. 從題目移除標籤：`DELETE /problem/<problem_id>/tags/<tag_id>`

> 注意：舊版路徑 `/problem/router/tags/` 已淘汰，現在統一使用上述格式方便前端整合。

### 1. 取得所有標籤
- 路徑：`GET /problem/tags`
- 權限：公開（可匿名）

成功回應：
```json
[
  {"id":1, "name":"陣列", "usage_count":12},
  {"id":2, "name":"字串", "usage_count":7}
]
```

**cURL**
```bash
curl "http://127.0.0.1:8000/problem/tags" | jq
```

### 2. 建立新標籤
- 路徑：`POST /problem/tags`
- 權限：需要登入（建議僅教師/管理員；目前後端未限制）
- Body：`{"name": "圖論"}`

成功回應（201）：
```json
{"id":5, "name":"圖論", "usage_count":0}
```

錯誤：
- 422 驗證失敗（名稱空白或重複）
- 401 未登入

**cURL**
```bash
curl -X POST "http://127.0.0.1:8000/problem/tags" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"圖論"}' | jq
```

### 3. 新增標籤到題目
- 路徑：`POST /problem/<problem_id>/tags`
- 權限：題目擁有者 / 課程 TA / 教師 / 管理員
- Body：`{"tag_id": 1}`（也支援 `tagId`）

成功回應（201）：
```json
{
  "detail": "Tag added",
  "tag": {"id":1, "name":"陣列", "usage_count":13}
}
```

錯誤：
- 400 缺少或無效的 `tag_id` / 標籤已存在於題目
- 404 題目不存在 / 標籤不存在
- 403 權限不足

**cURL**
```bash
curl -X POST "http://127.0.0.1:8000/problem/$PROBLEM_ID/tags" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tag_id":1}' | jq
```

### 4. 從題目移除標籤
- 路徑：`DELETE /problem/<problem_id>/tags/<tag_id>`
- 權限：題目擁有者 / 課程 TA / 教師 / 管理員

成功回應（200）：
```json
{
  "detail": "Tag removed",
  "tag": {"id":1, "name":"陣列", "usage_count":12}
}
```

錯誤：
- 404 題目不存在 / 標籤不存在 / 關聯不存在
- 403 權限不足
- 400 無效 tag_id 格式

**cURL**
```bash
curl -X DELETE "http://127.0.0.1:8000/problem/$PROBLEM_ID/tags/1" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 使用計數（usage_count）說明
`usage_count` 代表目前有多少題目關聯此標籤：
- 新增標籤到題目會遞增。
- 從題目移除標籤會遞減。
- 無論是透過增/刪標籤 API，或是在建立/編輯題目時傳 `tags` 陣列，`usage_count` 都會即時正確更新。

---

## 完整測試流程範例（點讚功能）

```bash
# 1. 取得 JWT token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/session/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}' | jq -r '.access')

# 2. 設定題目 ID（假設為 1）
PROBLEM_ID=1

# 3. 查看題目詳情（含 is_liked_by_user 欄位）
curl "http://127.0.0.1:8000/problem/$PROBLEM_ID" \
  -H "Authorization: Bearer $TOKEN" | jq

# 4. 按讚
curl -X POST "http://127.0.0.1:8000/problem/$PROBLEM_ID/like" \
  -H "Authorization: Bearer $TOKEN" | jq

# 5. 查看按讚數
curl "http://127.0.0.1:8000/problem/$PROBLEM_ID/likes" | jq

# 6. 查看我按讚過的題目列表
curl "http://127.0.0.1:8000/problem/liked" \
  -H "Authorization: Bearer $TOKEN" | jq

# 7. 取消按讚
curl -X DELETE "http://127.0.0.1:8000/problem/$PROBLEM_ID/like" \
  -H "Authorization: Bearer $TOKEN" | jq

# 8. 再次查看按讚數（應減少 1）
curl "http://127.0.0.1:8000/problem/$PROBLEM_ID/likes" | jq
```

---










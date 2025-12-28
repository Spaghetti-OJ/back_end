# 題目（Problems）API 說明

本節說明目前可用的題目 API。後端採用 Django + DRF + Simple JWT，所有請求/回應皆為 JSON。

## 查看題目詳情（學生/一般）

- 路徑：`GET /problem/<problem_id>`
- 未登入僅能看到 `public` 題目；`course` / `hidden` 需題目擁有者、課程成員或有管理權限。

成功回應（200 OK 新格式；部分欄位視登入與資料情況可能為 null）：
```json
{
  "data": {
    "problemName": "Two Sum",
    "description": {
      "description": "找出兩數之和等於 target。",
      "input": "第一行 n，第二行 n 個數字，第三行 target",
      "output": "輸出兩個索引 i j",
      "hint": "可以使用雜湊表降低時間複雜度",
      "sampleInput": ["5", "2 7 11 15 9", "9"],
      "sampleOutput": ["0 1"]
    },
    "owner": {
      "id": "6420753c-9e51-42a0-8349-ef79b2e70787",
      "username": "admin",
      "real_name": ""
    },
    "tags": [
      {"id": 2, "name": "array", "usage_count": 10}
    ],
    "allowedLanguage": 15,
    "courses": [
      {"id": 1, "name": "演算法課程"}
    ],
    "quota": -1,
    "defaultCode": {"c": "", "cpp": "", "java": "", "python": ""},
    "status": "public",
    "type": 0,
    "testCase": [
      {"no": 1, "stem": "0001", "in": "0001.in", "out": "0001.out"}
    ],
    "fillInTemplate": null,
    "submitCount": 2,
    "highScore": 80,
    "static_analysis_rules": ["forbid-loops"],
    "forbidden_functions": [],
    "use_static_analysis": true,
    "static_analysis_config": {
      "enabled": true,
      "rules": ["forbid-loops"]
    }
  },
  "message": "Problem can view.",
  "status": "200"
}
```
欄位說明補充：
- `description.sampleInput` / `description.sampleOutput`：後端已將原始換行字串依行切割為陣列；若為空字串則回傳 `[]`。
- `allowedLanguage`：語言遮罩（c=1, cpp=2, java=4, python=8；相加形成整數）。
- `testCase`：僅在題目已有上傳測資 zip 且解析成功時出現。沒有則為空陣列。
- `static_analysis_rules`：靜態分析規則列表，可選值：`forbid-loops`、`forbid-arrays`、`forbid-stl`、`forbid-functions`。空陣列表示不使用靜態分析。
- `forbidden_functions`：禁止使用的函數名稱列表。當 `static_analysis_rules` 包含 `forbid-functions` 時會有值。
- `use_static_analysis`：布林值，表示是否啟用靜態分析（根據 `static_analysis_rules` 自動計算）。
- `static_analysis_config`：完整的靜態分析配置物件（供 Sandbox 使用）。
未登入或無權限時可能回 403；若是舊邏輯隱藏題目也可能視需求回 404。

**cURL**
```bash
curl "http://127.0.0.1:8000/problem/1" -H "Authorization: Bearer $TOKEN"
```

---

## 題目最高分資訊

- 路徑：`GET /problem/<problem_id>/high-score`
- 回傳目前使用者或全域的最高分（依後端邏輯）。未登入可能為 null。

成功回應（200 OK）：
```json
{
  "data": { "score": 85 },
  "message": "OK",
  "status": "200"
}
```

**cURL**
```bash
curl "http://127.0.0.1:8000/problem/1/high-score" -H "Authorization: Bearer $TOKEN"
```

---

## 題目測資（Test Cases）上傳／下載（題目層級）

後端採「三端點」模式（取消舊的分片 PUT 端點）：
1. 初始化上傳：`POST /problem/<problem_id>/initiate-test-case-upload`
2. 完成上傳：`POST /problem/<problem_id>/complete-test-case-upload`
3. 下載測資：`GET /problem/<problem_id>/test-case`

權限：題目擁有者 / 課程 TA / 教師 / 管理員（`_has_problem_manage_permission` 包含 TA）。

檔名配對驗證：上傳的 zip 內容需包含四位數成對檔名，例如 `0001.in` 與 `0001.out`；若有缺失或不對稱回 400。

### 1) 初始化上傳
`POST /problem/<pid>/initiate-test-case-upload`

Body 範例：
```json
{ "length": 123456, "part_size": 1048576 }
```
回傳一組 `upload_id` 與暫存 TTL。`part_endpoint` 為佔位（本地不使用實際分片上傳）。

成功回應（200 OK）：
```json
{
  "data": { "upload_id": "<uuid>", "ttl": 600, "part_endpoint": "/problem/1/test-case-upload-part" },
  "message": "Upload initiated",
  "status": "200"
}
```

### 2) 完成上傳
`POST /problem/<pid>/complete-test-case-upload`

Body：
```json
{ "upload_id": "<uuid>", "parts": [ { "PartNumber": 1, "ETag": "..." } ] }
```
後端會拼合暫存分片并讀取 zip，驗證成對檔名。

成功回應（201 Created）：
```json
{
  "data": { "path": "testcases/p<pid>/problem.zip" },
  "message": "Upload completed",
  "status": "201"
}
```

### 3) 下載測資
`GET /problem/<pid>/test-case`

成功：直接回傳二進位串流（`Content-Disposition: attachment`）。例外：測資不存在回 404；權限不足 403。

**cURL（下載）**
```bash
curl "http://127.0.0.1:8000/problem/30/test-case" -H "Authorization: Bearer $TOKEN" -o problem-30-testcases.zip
```

### Sandbox 專用：測資校驗與結構

沙盒在判題前會：
1. 下載 zip 檔案。
2. 呼叫 checksum 端點確認 SHA256 是否一致（避免網路傳輸損毀）。
3. 呼叫 meta 端點取得測資對列表（in/out）以便依序執行。

安全驗證：使用 query string `token` 與後端設定的 `SANDBOX_TOKEN` 比對；不需一般登入權限。若 token 缺失或不符 → 401。

#### 1) 取得 SHA256 校驗和
- 路徑：`GET /problem/<problem_id>/checksum?token=<sandbox_token>`
- 成功回應：
```json
{
  "data": { "checksum": "EXAMPLE_SHA256_CHECKSUM" },
  "message": "OK",
  "status": "200"
}
```
錯誤：401 Invalid sandbox token；404 題目或測資不存在。

**cURL**
```bash
curl "http://127.0.0.1:8000/problem/30/checksum?token=$SANDBOX_TOKEN"
```

#### 2) 取得測資元資料
- 路徑：`GET /problem/<problem_id>/meta?token=<sandbox_token>`
- 回傳欄位：
  - `checksum`: 與 /checksum 相同 SHA256（方便比對）
  - `task_count`: 總測試對數量
  - `missing_pairs`: 缺失配對的 stem 列表（理想應為空）
  - `tasks`: 陣列，每項包含 `no`, `stem`, `in`, `out`

成功回應（範例）：
```json
{
  "data": {
    "checksum": "a3f2b8c9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
    "task_count": 2,
    "missing_pairs": [],
    "tasks": [
      { "no": 1, "stem": "0001", "in": "0001.in", "out": "0001.out" },
      { "no": 2, "stem": "0002", "in": "0002.in", "out": "0002.out" }
    ]
  },
  "message": "OK",
  "status": "200"
}
```
錯誤：401 Invalid sandbox token；404 測資不存在；500 zip 損毀。

**cURL**
```bash
curl "http://127.0.0.1:8000/problem/30/meta?token=$SANDBOX_TOKEN" | jq
```

#### 3) 下載測資包（Sandbox 專用）
- 路徑：`GET /problem/<problem_id>/testdata?token=<sandbox_token>`
- 目的：提供 Sandbox 下載該題目的完整測資包（.zip 檔案）
- 驗證：使用 query string `token` 與後端設定的 `SANDBOX_TOKEN` 比對
- 回傳：`application/zip` 二進位檔案流

此端點與 `/test-case` 下載端點的差異：
- `/test-case`：需要一般使用者登入驗證（JWT），供題目管理者下載
- `/testdata`：使用 Sandbox Token 驗證，專門供 Sandbox 環境下載判題測資

成功回應（200 OK）：
- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename="problem-<problem_id>-package.zip"`
- Body: 測資 zip 檔案的二進位內容

錯誤情況：
- 401 Invalid sandbox token（token 缺失、不正確或 SANDBOX_TOKEN 未設定）
- 404 題目不存在或測資檔案不存在

**cURL**
```bash
# 下載測資包
curl "http://127.0.0.1:8000/problem/30/testdata?token=$SANDBOX_TOKEN" -o problem-30-testdata.zip

# 驗證下載的 zip 檔案
unzip -l problem-30-testdata.zip
```

**典型 Sandbox 工作流程**
```bash
# 1. 下載測資包
curl "http://127.0.0.1:8000/problem/30/testdata?token=$SANDBOX_TOKEN" -o testdata.zip

# 2. 取得 checksum 並驗證完整性
CHECKSUM=$(curl -s "http://127.0.0.1:8000/problem/30/checksum?token=$SANDBOX_TOKEN" | jq -r '.data.checksum')
echo "$CHECKSUM  testdata.zip" | sha256sum -c

# 3. 取得測資結構資訊
curl "http://127.0.0.1:8000/problem/30/meta?token=$SANDBOX_TOKEN" | jq '.data.tasks'

# 4. 解壓並執行判題
unzip -q testdata.zip -d testcases/
# ... 執行使用者程式並比對 .in/.out 檔案
```

---

## 題目巢狀「測資資料表」CRUD（Test_cases）

此段為「資料表層級」管理子題底下的個別測資（與上面的題目層級 Zip 機制並行）。

- 路徑：
  - `GET /problem/<problem_id>/test-cases` — 取得此題目所有子題的測資清單
  - `POST /problem/<problem_id>/test-cases` — 新增測資（需提供 `subtask_id` 且必須隸屬此題目）
  - `PUT /problem/<problem_id>/test-cases/<case_id>` — 修改測資
  - `DELETE /problem/<problem_id>/test-cases/<case_id>` — 刪除測資

- 權限：
  - `GET` 允許匿名，但僅在題目對該使用者可見時返回（與題目詳情相同可視規則）。
  - `POST/PUT/DELETE` 需要題目擁有者 / 課程 TA / 教師 / 管理員。

- 驗證重點：
  - `POST` 時必須提供 `subtask_id`（或 `subtaskId`），且該子題必須屬於此題目；否則回 404。
  - `PUT/DELETE` 時會驗證該測資所屬子題是否隸屬此題目；不符則回 404。

**cURL 範例**

取得測資列表：
```bash
curl "http://127.0.0.1:8000/problem/2/test-cases"
```

新增測資到指定子題（需登入與權限）：
```bash
curl -X POST "http://127.0.0.1:8000/problem/2/test-cases" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subtask_id": 3,
    "idx": 1,
    "input_path": "0001.in",
    "output_path": "0001.out",
    "status": "ready"
  }'
```

修改測資：
```bash
curl -X PUT "http://127.0.0.1:8000/problem/2/test-cases/10" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "status": "disabled" }'
```

刪除測資：
```bash
curl -X DELETE "http://127.0.0.1:8000/problem/2/test-cases/10" \
  -H "Authorization: Bearer $TOKEN"
```

> 備註：題目層級 Zip（`/initiate-test-case-upload`、`/complete-test-case-upload`、`/test-case`）提供給 Sandbox 與下載使用；資料表 CRUD 用於後台維護子題級測資。兩者並行，不互相覆蓋。

---

## 建立題目（管理）

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

成功回應（200 OK，分頁包裝）：
```json
{
  "data": {
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": 1,
        "title": "Two Sum",
        "difficulty": "easy",
        "is_public": "public",
        "course_id": "<uuid>",
        "tags": [{"id": 1, "name": "陣列", "usage_count": 10}],
        "created_at": "2025-11-08T06:45:00Z"
      }
    ]
  },
  "message": "OK",
  "status": "200"
}

---

## 取得題目統計資訊

- 路徑：`GET /problem/<problem_id>/stats`
- 權限：需要登入
- 說明：回傳該題目的統計資料，包含 AC 用戶數、嘗試用戶數、平均分數、標準差、分數分布、狀態統計、top10 執行時間/記憶體使用。

成功回應範例（200 OK）：
```json
{
  "data": {
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
  },
  "message": "OK",
  "status": "200"
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
| static_analysis_rules | string[] | ❌ | `[]` | 靜態分析規則列表，可選值見下方說明 |
| forbidden_functions | string[] | ❌ | `[]` | 禁止使用的函數名稱列表（當啟用 `forbid-functions` 規則時必填且至少一個） |
| tags | int[] | ❌ | (無) | 標籤 id 陣列；嚴格驗證全部必須存在 |

備註：
1. 未提供可選欄位則使用預設或留空（null）。
2. `tags` 為寫入用；回傳時使用 `tags` 物件陣列（含 id/name/usage_count）。
3. 不支援在建立時直接寫 `like_count`、`view_count` 等統計欄位。

### 靜態分析規則說明

`static_analysis_rules` 可選用以下規則（可多選組合）：

| 規則 | 說明 | 適用情境 |
| ---- | ---- | -------- |
| `forbid-loops` | 禁止使用迴圈（for、while、do-while） | 遞迴練習題 |
| `forbid-arrays` | 禁止使用陣列 | 指標練習題 |
| `forbid-stl` | 禁止使用 STL 容器和演算法 | 資料結構實作題 |
| `forbid-functions` | 禁止使用特定函數 | 演算法實作題（禁用內建排序等） |

**驗證規則**：
- 當 `static_analysis_rules` 包含 `forbid-functions` 時，`forbidden_functions` 必須提供且至少包含一個函數名稱。
- 函數名稱不能為空字串。

**回應中的額外欄位**：
- `use_static_analysis`（boolean）：是否啟用靜態分析，根據 `static_analysis_rules` 是否為空自動計算。
- `static_analysis_config`（object）：完整配置，供 Sandbox 判題使用，格式如下：
```json
{
  "enabled": true,
  "rules": ["forbid-functions", "forbid-stl"],
  "forbidden_functions": ["sort", "qsort"]
}
```

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
  "static_analysis_rules": ["forbid-functions"],
  "forbidden_functions": ["sort", "qsort"],
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
{
  "data": { "problem_id": 1 },
  "message": "題目建立成功",
  "status": "201"
}
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

成功回應（200 OK）：結構與一般詳情類似，但欄位更完整，略。統一包裝：
```json
{
  "data": { /* 管理詳情 payload */ },
  "message": "取得題目（管理）成功",
  "status": "200"
}
```

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
{
  "data": { "problem_id": 1 },
  "message": "題目更新成功",
  "status": "200"
}
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

### 靜態分析設定範例

> 啟用禁止迴圈和陣列（遞迴練習）
```bash
curl -X PUT http://127.0.0.1:8000/problem/manage/$PROBLEM_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "static_analysis_rules": ["forbid-loops", "forbid-arrays"]
  }'
```

> 啟用禁止特定函數（演算法實作）
```bash
curl -X PUT http://127.0.0.1:8000/problem/manage/$PROBLEM_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "static_analysis_rules": ["forbid-functions", "forbid-stl"],
    "forbidden_functions": ["sort", "qsort", "stable_sort", "nth_element"]
  }'
```

> 停用靜態分析
```bash
curl -X PUT http://127.0.0.1:8000/problem/manage/$PROBLEM_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "static_analysis_rules": []
  }'
```

> 靜態分析驗證錯誤（啟用 forbid-functions 但未提供函數列表，預期 400）
```bash
curl -X PUT http://127.0.0.1:8000/problem/manage/$PROBLEM_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "static_analysis_rules": ["forbid-functions"]
  }'
# 回應：{"forbidden_functions": ["當啟用 forbid-functions 規則時，必須至少指定一個禁止使用的函數。"]}
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
  "data": { "likes_count": 15 },
  "message": "Liked",
  "status": "201"
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
  "data": { "likes_count": 14 },
  "message": "Unliked",
  "status": "200"
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
  "data": { "likes_count": 42 },
  "message": "OK",
  "status": "200"
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

成功回應（200 OK，分頁包裝）：
```json
{
  "data": {
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
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
  },
  "message": "OK",
  "status": "200"
}
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

### 1. 取得所有標籤
- 路徑：`GET /problem/tags`
- 權限：公開（可匿名）

成功回應（200 OK）：
```json
{
  "data": [
    {"id":1, "name":"陣列", "usage_count":12},
    {"id":2, "name":"字串", "usage_count":7}
  ],
  "message": "取得標籤列表成功",
  "status": "200"
}
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
{
  "data": {"id":5, "name":"圖論", "usage_count":0},
  "message": "Tag created",
  "status": "201"
}
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

---

## 複製題目（管理）

- 路徑：`POST /problem/clone`
- 權限：系統管理員或目標課程教師 / TA
- 功能：複製指定題目到目標課程，複製其 tags、subtasks、test cases；統計欄位（提交次數、讚數、瀏覽、AC 率等）會歸零。
- 支援 `status` 欄位（可選）：接受 `0|1|2` 或 `hidden|course|public`；未提供則沿用原題目狀態。
- 支援 `dry_run`（布林，可選）：若為 `true`，只建立題目本體，不複製關聯資料（用於除錯）。

請求（JSON 範例）：
```json
{
  "problem_id": 2,
  "target": "作業系統",
  "status": "public"
}
```

成功回應（200 OK）：
```json
{
  "data": { "problemId": 99 },
  "message": "Success.",
  "status": "200"
}
```

`dry_run: true` 範例成功回應：
```json
{
  "data": { "problemId": 100 },
  "message": "Success (dry_run: only problem created).",
  "status": "200"
}
```

可能錯誤：
- 400 缺少 `problem_id` 或 `target`
- 403 `Problem can not view.`（來源題目不可視） / `Permission denied`（無權在目標課程建立）
- 404 `Problem not found` / `Target course not found`

**cURL（一般複製）**
```bash
curl -X POST "http://127.0.0.1:8000/problem/clone" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "problem_id": 2, "target": "作業系統", "status": "public" }'
```

**cURL（dry_run 只建立題目本體(除錯用)）**
```bash
curl -X POST "http://127.0.0.1:8000/problem/clone" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "problem_id": 2, "target": "作業系統", "status": "public", "dry_run": true }'
```


### 3. 新增標籤到題目
- 路徑：`POST /problem/<problem_id>/tags`
- 權限：題目擁有者 / 課程 TA / 教師 / 管理員
- Body：`{"tag_id": 1}`（也支援 `tagId`）

成功回應（201）：
```json
{
  "data": {"tag": {"id":1, "name":"陣列", "usage_count":13}},
  "message": "Tag added",
  "status": "201"
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
  "data": {"tag": {"id":1, "name":"陣列", "usage_count":12}},
  "message": "Tag removed",
  "status": "200"
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











## 子題（Subtasks）API

提供四個操作，皆採統一回傳包裝（`data/message/status`）：

1. 取得子題列表：`GET /problem/<problem_id>/subtasks`
2. 新增子題：`POST /problem/<problem_id>/subtasks`
3. 修改子題：`PUT /problem/<problem_id>/subtasks/<subtask_id>`
4. 刪除子題：`DELETE /problem/<problem_id>/subtasks/<subtask_id>`

權限說明：
- GET：公開題可匿名；若為 `course`/`hidden` 題目則需具備觀看權限（課程成員/擁有者/教師/管理員）。
- POST/PUT/DELETE：題目擁有者、課程 TA、教師、管理員。

資料結構（`SubtaskSerializer`）：
```json
{
  "id": 12,
  "problem_id": 30,
  "subtask_no": 1,
  "weight": 20,
  "time_limit_ms": 1000,
  "memory_limit_mb": 256,
  "created_at": "2025-11-28T01:23:45Z",
  "updated_at": "2025-11-28T01:23:45Z",
  "test_cases": [
    {
      "id": 101,
      "subtask_id": 12,
      "idx": 1,
      "input_path": "...",
      "output_path": "...",
      "input_size": 123,
      "output_size": 45,
      "checksum_in": "...",
      "checksum_out": "...",
      "status": "ready",
      "created_at": "2025-11-28T01:23:45Z"
    }
  ]
}
```

### 1) 取得子題列表
- 路徑：`GET /problem/<problem_id>/subtasks`

成功回應（200 OK）：
```json
{
  "data": [ { /* SubtaskSerializer */ } ],
  "message": "OK",
  "status": "200"
}
```

**cURL**
```bash
curl "http://127.0.0.1:8000/problem/30/subtasks" | jq
```

### 2) 新增子題
- 路徑：`POST /problem/<problem_id>/subtasks`
- 權限：題目擁有者 / 課程 TA / 教師 / 管理員
- Body 範例：
```json
{
  "subtask_no": 2,
  "weight": 30,
  "time_limit_ms": 1500,
  "memory_limit_mb": 256
}
```

成功回應（201 Created）：
```json
{
  "data": { /* SubtaskSerializer */ },
  "message": "Subtask created",
  "status": "201"
}
```

**cURL**
```bash
curl -X POST "http://127.0.0.1:8000/problem/30/subtasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subtask_no": 2,
    "weight": 30,
    "time_limit_ms": 1500,
    "memory_limit_mb": 256
  }'
```

### 3) 修改子題
- 路徑：`PUT /problem/<problem_id>/subtasks/<subtask_id>`
- 權限：題目擁有者 / 課程 TA / 教師 / 管理員
- Body（部分欄位即可）：
```json
{
  "weight": 25,
  "time_limit_ms": 1200
}
```

成功回應（200 OK）：
```json
{
  "data": { /* SubtaskSerializer */ },
  "message": "Subtask updated",
  "status": "200"
}
```

**cURL**
```bash
curl -X PUT "http://127.0.0.1:8000/problem/30/subtasks/12" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "weight": 25,
    "time_limit_ms": 1200
  }'
```

### 4) 刪除子題
- 路徑：`DELETE /problem/<problem_id>/subtasks/<subtask_id>`
- 權限：題目擁有者 / 課程 TA / 教師 / 管理員

成功回應（204 No Content）：
```json
{
  "data": null,
  "message": "Subtask deleted",
  "status": "204"
}
```

**cURL**
```bash
curl -X DELETE "http://127.0.0.1:8000/problem/30/subtasks/12" \
  -H "Authorization: Bearer $TOKEN"
```










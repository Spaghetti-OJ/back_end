# Editor API 文檔

**更新日期**: 2025年11月23日  
**API 版本**: v1  
**基礎路徑**: `/editor/`

---

## 目錄

1. [概述](#概述)
2. [通用說明](#通用說明)
3. [API 端點](#api端點)
4. [使用場景](#使用場景)
5. [錯誤處理](#錯誤處理)

---

## 概述

這是 Spaghetti-OJ 的代碼編輯器（Editor）API 文檔，提供代碼草稿的保存、載入、刪除功能。
編輯器草稿與提交（Submission）分離，允許用戶在提交前保存和編輯代碼。

### 主要功能
- 代碼草稿自動保存
- 代碼草稿載入
- 代碼草稿刪除
- 支援多種程式語言
- 每個題目僅保存最新草稿

### 權限系統

所有 Editor API 端點都需要用戶認證：
- 用戶只能操作自己的草稿
- 每個用戶對每個題目只有一個草稿
- 草稿與提交獨立，互不影響

---

## 通用說明

### 資料格式

#### 請求格式
- Content-Type: `application/json`
- 需要在 Header 中攜帶認證 Token

#### 響應格式
所有 API 響應遵循統一格式：

**成功響應**:
```json
{
    "data": {...},
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

### 語言類型編碼

API 使用整數代表程式語言（與 Submission API 兼容）:

```
0 - C
1 - C++
2 - Python
3 - Java
4 - JavaScript
```

### 欄位命名慣例

API 使用 **snake_case** 命名慣例:
- `problem_id`
- `assignment_id`
- `language_type`
- `source_code`
- `created_at`
- `updated_at`

---

## API 端點

### 1. 載入草稿

載入指定題目的代碼草稿。

**端點**: `GET /editor/draft/{problem_id}/`

**認證**: 必須（Bearer Token）

**路徑參數**:
- `problem_id` (必填): 題目 ID，整數

**成功響應**: HTTP 200
```json
{
    "data": {
        "id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
        "user": {
            "id": "user-uuid",
            "username": "student001",
            "email": "student@example.com"
        },
        "problem_id": 123,
        "assignment_id": null,
        "language_type": 2,
        "source_code": "def solution():\n    pass",
        "title": "My Draft",
        "auto_saved": true,
        "created_at": "2025-11-23T10:30:00Z",
        "updated_at": "2025-11-23T10:35:00Z"
    },
    "message": "草稿載入成功",
    "status": "ok"
}
```

**回應欄位說明**:
- `id`: 草稿 UUID（唯一識別碼）
- `user`: 用戶資訊（id, username, email）
- `problem_id`: 題目 ID
- `assignment_id`: 作業 ID（可為 null）
- `language_type`: 程式語言類型（0-4）
- `source_code`: 代碼內容
- `title`: 草稿標題（可為 null）
- `auto_saved`: 是否為自動保存
- `created_at`: 創建時間（ISO 8601 格式）
- `updated_at`: 最後更新時間（ISO 8601 格式）

**錯誤響應**:
- `401 Unauthorized`: 未提供認證 Token
```json
{
    "detail": "Authentication credentials were not provided."
}
```

- `404 Not Found`: 草稿不存在
```json
{
    "data": null,
    "message": "找不到草稿",
    "status": "error"
}
```

**範例**:
```bash
# 請求
curl -X GET http://localhost:8000/editor/draft/123/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 成功響應（略，見上方）
```

---

### 2. 保存/更新草稿

保存或更新代碼草稿。如果該題目的草稿已存在則更新，否則創建新草稿。

**端點**: `PUT /editor/draft/{problem_id}/`

**認證**: 必須（Bearer Token）

**路徑參數**:
- `problem_id` (必填): 題目 ID，整數

**請求參數**:
```json
{
    "language_type": 2,
    "source_code": "def solution():\n    return 42",
    "assignment_id": 456,
    "title": "My Solution Draft",
    "auto_saved": true
}
```

**參數說明**:
- `language_type` (必填): 程式語言類型，整數 0-4
- `source_code` (必填): 代碼內容，字串，不可為空
- `assignment_id` (可選): 作業 ID，整數
- `title` (可選): 草稿標題，字串，最大 255 字元
- `auto_saved` (可選): 是否為自動保存，布林值，預設 false

**成功響應**: HTTP 200
```json
{
    "data": {
        "id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
        "user": {
            "id": "user-uuid",
            "username": "student001",
            "email": "student@example.com"
        },
        "problem_id": 123,
        "assignment_id": 456,
        "language_type": 2,
        "source_code": "def solution():\n    return 42",
        "title": "My Solution Draft",
        "auto_saved": true,
        "created_at": "2025-11-23T10:30:00Z",
        "updated_at": "2025-11-23T10:40:00Z"
    },
    "message": "草稿保存成功",
    "status": "ok"
}
```

**錯誤響應**:
- `401 Unauthorized`: 未提供認證 Token
```json
{
    "detail": "Authentication credentials were not provided."
}
```

- `400 Bad Request`: 參數驗證失敗
```json
{
    "data": {
        "language_type": [
            "Invalid language type. Must be one of: [0, 1, 2, 3, 4]"
        ]
    },
    "message": "草稿保存失敗",
    "status": "error"
}
```

```json
{
    "data": {
        "source_code": [
            "Source code cannot be empty"
        ]
    },
    "message": "草稿保存失敗",
    "status": "error"
}
```

```json
{
    "data": {
        "source_code": [
            "Source code too large. Maximum size is 65535 bytes (64KB), but got 70000 bytes"
        ]
    },
    "message": "草稿保存失敗",
    "status": "error"
}
```

**範例**:
```bash
# 請求 - 創建新草稿
curl -X PUT http://localhost:8000/editor/draft/123/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "language_type": 2,
    "source_code": "def solution():\n    return 42",
    "title": "My Draft",
    "auto_saved": false
  }'

# 請求 - 更新現有草稿（相同的 problem_id）
curl -X PUT http://localhost:8000/editor/draft/123/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "language_type": 2,
    "source_code": "def solution():\n    return 100",
    "auto_saved": true
  }'
```

**重要提示**:
- PUT 操作是冪等的，多次調用結果相同
- 每個用戶對每個題目只保存一個草稿
- 更新草稿時會自動更新 `updated_at` 時間戳
- 如果只傳部分欄位，其他欄位保持不變（部分更新）

---

### 3. 刪除草稿

刪除指定題目的代碼草稿。

**端點**: `DELETE /editor/draft/{problem_id}/`

**認證**: 必須（Bearer Token）

**路徑參數**:
- `problem_id` (必填): 題目 ID，整數

**成功響應**: HTTP 200
```json
{
    "data": null,
    "message": "草稿刪除成功",
    "status": "ok"
}
```

**錯誤響應**:
- `401 Unauthorized`: 未提供認證 Token
```json
{
    "detail": "Authentication credentials were not provided."
}
```

- `404 Not Found`: 草稿不存在
```json
{
    "data": null,
    "message": "找不到草稿",
    "status": "error"
}
```

**範例**:
```bash
# 請求
curl -X DELETE http://localhost:8000/editor/draft/123/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 成功響應
{
    "data": null,
    "message": "草稿刪除成功",
    "status": "ok"
}
```

---

## 使用場景

### 場景 1: 用戶開始寫代碼

1. 用戶打開題目頁面
2. 前端嘗試載入草稿: `GET /editor/draft/{problem_id}/`
3. 如果返回 404，表示沒有草稿，使用預設代碼模板
4. 如果返回 200，使用草稿內容填充編輯器

### 場景 2: 自動保存草稿

1. 用戶在編輯器中輸入代碼
2. 前端每隔一定時間（如 30 秒）自動保存
3. 調用 `PUT /editor/draft/{problem_id}/` 並設置 `auto_saved: true`
4. 無論草稿是否存在，都可以直接 PUT（冪等操作）

### 場景 3: 手動保存草稿

1. 用戶點擊「保存」按鈕
2. 調用 `PUT /editor/draft/{problem_id}/` 並設置 `auto_saved: false`
3. 顯示保存成功提示

### 場景 4: 提交代碼

1. 用戶點擊「提交」按鈕
2. 先保存草稿: `PUT /editor/draft/{problem_id}/`
3. 再創建提交: `POST /submission/` 和 `PUT /submission/{submission_id}/`
4. 提交成功後可選擇是否保留草稿

### 場景 5: 切換題目

1. 用戶從題目 A 切換到題目 B
2. 保存題目 A 的草稿: `PUT /editor/draft/{problem_id_A}/`
3. 載入題目 B 的草稿: `GET /editor/draft/{problem_id_B}/`

### 場景 6: 切換程式語言

1. 用戶在編輯器中切換程式語言
2. 前端可以選擇：
   - 方案 A: 清空編輯器，使用新語言的模板
   - 方案 B: 先保存當前草稿，再切換語言
3. 建議實作語言切換確認對話框

### 場景 7: 刪除草稿

1. 用戶想要重新開始
2. 點擊「刪除草稿」按鈕
3. 調用 `DELETE /editor/draft/{problem_id}/`
4. 編輯器恢復為預設模板

---

## 錯誤處理

### 常見錯誤碼

| HTTP 狀態碼 | 說明 | 處理建議 |
|-----------|------|---------|
| 200 | 成功 | 正常處理響應數據 |
| 400 | 請求參數錯誤 | 檢查請求參數格式和內容 |
| 401 | 未認證 | 提示用戶登入 |
| 404 | 草稿不存在 | 使用預設模板或提示用戶 |
| 500 | 伺服器錯誤 | 提示用戶稍後重試 |

### 前端錯誤處理建議

#### 1. 載入草稿失敗
```javascript
try {
    const response = await fetch(`/editor/draft/${problemId}/`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.status === 404) {
        // 沒有草稿，使用預設模板
        loadDefaultTemplate(languageType);
    } else if (response.ok) {
        const result = await response.json();
        loadDraft(result.data);
    } else {
        // 其他錯誤
        showError('載入草稿失敗');
    }
} catch (error) {
    showError('網絡錯誤');
}
```

#### 2. 保存草稿失敗
```javascript
try {
    const response = await fetch(`/editor/draft/${problemId}/`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            language_type: languageType,
            source_code: code,
            auto_saved: true
        })
    });
    
    if (response.ok) {
        // 保存成功，更新 UI
        showSuccess('草稿已保存');
    } else {
        const result = await response.json();
        if (result.status === 'error') {
            // 顯示具體錯誤訊息
            showError(result.message);
        }
    }
} catch (error) {
    // 網絡錯誤，可以稍後重試
    retryLater();
}
```

#### 3. 離線處理
```javascript
// 檢測網絡狀態
if (!navigator.onLine) {
    // 離線時保存到本地存儲
    localStorage.setItem(`draft_${problemId}`, JSON.stringify({
        language_type: languageType,
        source_code: code,
        timestamp: Date.now()
    }));
    showInfo('離線模式：草稿已保存到本地');
}

// 網絡恢復時同步
window.addEventListener('online', () => {
    syncLocalDrafts();
});
```

### 數據驗證

#### language_type 驗證
- 必須是整數 0-4
- 對應語言: 0=C, 1=C++, 2=Python, 3=Java, 4=JavaScript

#### source_code 驗證
- 不可為空字串
- 不可只包含空白字元
- **最大大小：64KB（65535 bytes）**
  - 使用 UTF-8 編碼計算字節數
  - 超過限制返回 400 錯誤
  - 前端建議在用戶輸入時提示當前大小
  - 防止超大文件 DoS 攻擊

#### problem_id 驗證
- 必須是正整數
- 題目必須存在（由 Submission API 驗證）

---

## 與 Submission API 的關係

### 相同點
- 都使用相同的 `language_type` 編碼
- 都需要 `problem_id` 和 `source_code`
- 都需要用戶認證

### 不同點

| 特性 | Editor API | Submission API |
|-----|-----------|---------------|
| 目的 | 保存編輯中的代碼 | 提交代碼進行判題 |
| 數量限制 | 每個題目一個草稿 | 無限制提交次數 |
| 是否判題 | 否 | 是 |
| 數據持久性 | 可刪除 | 永久保存 |
| 響應格式 | 統一 JSON 格式 | NOJ 兼容格式 |
| 命名慣例 | snake_case | camelCase |

### 使用流程

典型的用戶使用流程：

1. 載入草稿（Editor API）
   ```
   GET /editor/draft/123/
   ```

2. 編輯代碼（前端）
   - 用戶在編輯器中輸入代碼

3. 自動保存（Editor API）
   ```
   PUT /editor/draft/123/
   ```

4. 提交代碼（Submission API）
   ```
   POST /submission/
   PUT /submission/{submission_id}/
   ```

5. 查看結果（Submission API）
   ```
   GET /submission/{submission_id}/
   ```

---

## 最佳實踐

### 前端實作建議

1. **自動保存間隔**: 建議 30-60 秒
2. **手動保存**: 提供明確的保存按鈕
3. **離線支援**: 使用 localStorage 作為備份
4. **衝突處理**: 比較本地和伺服器時間戳
5. **載入指示**: 顯示載入和保存狀態
6. **錯誤重試**: 網絡錯誤時自動重試

### 性能優化

1. **節流（Throttle）**: 限制保存請求頻率
2. **防抖（Debounce）**: 用戶停止輸入後再保存
3. **差異更新**: 只在代碼改變時保存
4. **壓縮傳輸**: 大型代碼可以壓縮

### 安全考慮

1. **認證**: 所有請求必須攜帶有效 Token
2. **授權**: 用戶只能操作自己的草稿
   - 每個用戶只能查看、修改、刪除自己的草稿
   - URL 中的 problem_id 配合 request.user 確保數據隔離
   - 即使知道其他用戶的草稿存在，也無法訪問或修改
3. **輸入驗證**: 前後端都要驗證輸入
   - language_type 必須在 0-4 範圍內
   - source_code 不可為空
4. **大小限制**: 代碼文件最大 64KB（65535 bytes）
   - 防止 DoS 攻擊（超大文件消耗伺服器資源）
   - 與 Submission API 保持一致
   - 超過限制會返回 400 錯誤
5. **數據庫隔離**: 使用 user + problem_id 的組合索引確保查詢效率和數據隔離

---

## 測試範例

### 完整測試流程

```bash
# 1. 設置變量
TOKEN="your_jwt_token_here"
PROBLEM_ID=123

# 2. 嘗試載入草稿（預期 404）
curl -X GET "http://localhost:8000/editor/draft/${PROBLEM_ID}/" \
  -H "Authorization: Bearer ${TOKEN}"

# 3. 創建新草稿
curl -X PUT "http://localhost:8000/editor/draft/${PROBLEM_ID}/" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "language_type": 2,
    "source_code": "def solution():\n    return 42",
    "title": "Test Draft",
    "auto_saved": false
  }'

# 4. 載入草稿（預期成功）
curl -X GET "http://localhost:8000/editor/draft/${PROBLEM_ID}/" \
  -H "Authorization: Bearer ${TOKEN}"

# 5. 更新草稿
curl -X PUT "http://localhost:8000/editor/draft/${PROBLEM_ID}/" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "def solution():\n    return 100",
    "auto_saved": true
  }'

# 6. 刪除草稿
curl -X DELETE "http://localhost:8000/editor/draft/${PROBLEM_ID}/" \
  -H "Authorization: Bearer ${TOKEN}"

# 7. 確認刪除（預期 404）
curl -X GET "http://localhost:8000/editor/draft/${PROBLEM_ID}/" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## 常見問題

### Q1: 為什麼使用 PUT 而不是 POST 創建草稿？

A: PUT 是冪等操作，無論草稿是否存在都可以直接調用。這簡化了前端邏輯，不需要先判斷草稿是否存在。

### Q2: 可以保存多個草稿嗎？

A: 目前每個用戶對每個題目只能保存一個草稿。如果需要保存多個版本，建議使用 Submission API 進行提交。

### Q3: 草稿會過期嗎？

A: 目前草稿不會自動過期，除非用戶主動刪除。未來可能會實作草稿清理政策。

### Q4: 草稿大小有限制嗎？

A: 目前沒有硬性限制，但建議代碼大小不超過 64KB。過大的代碼可能影響性能。

### Q5: 可以查看所有草稿列表嗎？

A: 目前不提供草稿列表 API。用戶只能通過 problem_id 查詢特定題目的草稿。

### Q6: 草稿和提交有什麼關係？

A: 草稿和提交是獨立的。草稿用於編輯過程中的保存，提交用於正式判題。提交時不會自動刪除草稿。

### Q7: 切換語言時會怎樣？

A: 每個草稿包含 language_type 欄位。切換語言時，前端可以選擇保存當前草稿或直接切換。建議實作確認對話框。

### Q8: 離線時可以使用嗎？

A: API 需要網絡連接。建議前端實作本地存儲作為離線備份，網絡恢復時再同步到伺服器。

---

## 更新歷史

- **2025年11月23日**: 初始版本
  - 創建 Editor API 文檔
  - 定義草稿 CRUD 端點
  - 說明與 Submission API 的關係

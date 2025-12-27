# Editorial API 文檔

## 概述
本文檔描述了題解系統的四個核心API端點，用於管理問題的題解內容。所有 Editorial API 使用 `/editorials/` 前綴。

## URL 結構說明
**重要變更**：Editorial API 已從 `/submissions/` 遷移到 `/editorials/` 前綴：
- 新的正確URL：`/editorials/problem/{problemId}/solution/`
- 舊的廢棄URL：`/submissions/problem/{problemId}/solution/` (不再可用)

這個變更讓 API 結構更清楚地區分了題解管理(`editorials`)和程式碼提交(`submissions`)的功能。

## 認證
所有API都需要JWT認證，請在請求頭中包含：
```
Authorization: Bearer <your_jwt_token>
```

## API 端點

### 1. 發布題解
**POST** `/editorials/problem/{problemId}/solution/`

創建新的題解。只有課程老師或TA可以發布題解。

#### 請求參數
- `problemId` (路徑參數): 問題ID

#### 請求體
```json
{
    "title": "題解標題",
    "content": "題解內容",
    "difficulty_rating": 3.5,
    "is_official": true
}
```

#### 請求體字段說明
- `title` (必填): 題解標題，最大255字元
- `content` (必填): 題解內容，不能為空
- `difficulty_rating` (可選): 難度評級，範圍 0.0 ~ 99.9，精確到一位小數（例如：3.5）
- `is_official` (可選): 是否為官方題解，默認false

#### 成功響應 (201 Created)
```json
{
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "author_username": "teacher1",
        "is_liked_by_user": false,
        "problem_id": 1,
        "title": "題解標題",
        "content": "題解內容",
        "difficulty_rating": "3.5",
        "likes_count": 0,
        "views_count": 0,
        "status": "published",
        "is_official": true,
        "created_at": "2025-11-02T08:00:00Z",
        "updated_at": "2025-11-02T08:00:00Z",
        "published_at": "2025-11-02T08:00:00Z",
        "author": "550e8400-e29b-41d4-a716-446655440001"
    },
    "message": "OK",
    "status": "ok"
}
```

#### 錯誤響應
- **400 Bad Request**: 請求數據驗證失敗
- **401 Unauthorized**: 未認證或認證失敗
- **403 Forbidden**: 沒有權限發布題解（不是課程老師/TA）
- **404 Not Found**: 問題不存在

---

### 2. 取得題解列表
**GET** `/editorials/problem/{problemId}/solution/`

獲取指定問題的所有已發布題解列表。

#### 請求參數
- `problemId` (路徑參數): 問題ID

#### 成功響應 (200 OK)
```json
{
    "data": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "author_username": "teacher1",
            "is_liked_by_user": true,
            "problem_id": 1,
            "title": "官方題解",
            "content": "這是官方題解內容...",
            "difficulty_rating": "3.5",
            "likes_count": 15,
            "views_count": 234,
            "status": "published",
            "is_official": true,
            "created_at": "2025-11-01T08:00:00Z",
            "updated_at": "2025-11-01T08:00:00Z",
            "published_at": "2025-11-01T08:00:00Z",
            "author": "550e8400-e29b-41d4-a716-446655440001"
        }
    ],
    "message": "OK",
    "status": "ok"
}
```

#### 錯誤響應
- **401 Unauthorized**: 未認證
- **404 Not Found**: 問題不存在

#### 排序規則
題解按以下順序排列：
1. 官方題解優先 (`is_official=true`)
2. 按讚數量降序
3. 創建時間降序

---

### 3. 修改題解
**PUT** `/editorials/problem/{problemId}/solution/{solutionId}/`

修改指定的題解。只有課程老師或TA可以修改題解。

#### 請求參數
- `problemId` (路徑參數): 問題ID
- `solutionId` (路徑參數): 題解ID (UUID格式)

#### 請求體
```json
{
    "title": "更新後的題解標題",
    "content": "更新後的題解內容",
    "difficulty_rating": 4.0,
    "is_official": false
}
```

#### 成功響應 (200 OK)
```json
{
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "author_username": "teacher1",
        "is_liked_by_user": true,
        "problem_id": 1,
        "title": "更新後的題解標題",
        "content": "更新後的題解內容",
        "difficulty_rating": "4.0",
        "likes_count": 15,
        "views_count": 234,
        "status": "published",
        "is_official": false,
        "created_at": "2025-11-01T08:00:00Z",
        "updated_at": "2025-11-02T08:00:00Z",
        "published_at": "2025-11-01T08:00:00Z",
        "author": "550e8400-e29b-41d4-a716-446655440001"
    },
    "message": "OK",
    "status": "ok"
}
```

#### 錯誤響應
- **400 Bad Request**: 請求數據驗證失敗
- **401 Unauthorized**: 未認證或認證失敗
- **403 Forbidden**: 沒有權限修改題解（不是課程老師/TA）
- **404 Not Found**: 問題或題解不存在

---

### 4. 刪除題解
**DELETE** `/editorials/problem/{problemId}/solution/{solutionId}/`

刪除指定的題解。只有課程老師或TA可以刪除題解。

#### 請求參數
- `problemId` (路徑參數): 問題ID
- `solutionId` (路徑參數): 題解ID (UUID格式)

#### 成功響應 (204 No Content)
無響應內容

#### 錯誤響應
- **401 Unauthorized**: 未認證或認證失敗
- **403 Forbidden**: 沒有權限刪除題解（不是課程老師/TA）
- **404 Not Found**: 問題或題解不存在

---

## 測試結果分析

### 已驗證正常工作的功能：
1. **JWT認證系統** - 令牌獲取和驗證正常
2. **POST創建題解** - 成功創建並返回完整資料
3. **GET獲取題解列表** - 正確返回題解列表，按官方優先排序
4. **PUT修改題解** - 成功更新題解內容
5. **DELETE刪除題解** - 正確返回204狀態碼
6. **數據驗證** - 標題長度等驗證規則生效
7. **權限控制** - 無認證請求被正確拒絕

### 已修復的問題：
1. **UUID格式驗證** - 現在返回JSON錯誤而非HTML 404頁面
2. **問題存在性檢查** - 不存在的問題ID現在返回404而非空數組
3. **錯誤響應格式** - 統一使用JSON格式返回錯誤信息

### 實際測試結果示例：

#### 成功創建題解：
```json
{
    "id": "fefbcf77-2df6-40aa-aa39-587b7c3b30c0",
    "author_username": "teacher1",
    "is_liked_by_user": false,
    "problem_id": 1,
    "title": "動態規劃解法",
    "content": "這個問題可以使用動態規劃來解決...",
    "difficulty_rating": "3.5",
    "likes_count": 0,
    "views_count": 0,
    "status": "published",
    "is_official": true,
    "created_at": "2025-11-01T16:22:17.124771Z",
    "updated_at": "2025-11-01T16:22:17.124793Z",
    "published_at": "2025-11-01T16:22:17.124534Z",
    "author": "91ed4f45-ddaf-40da-a821-cec5ab1d4ea9"
}
```

#### 錯誤處理示例：
- **無效UUID**: `{"error": "無效的題解ID格式"}`
- **未認證**: `{"detail": "Authentication credentials were not provided."}`
- **驗證失敗**: `{"title": ["標題長度不能超過 255 字元"]}`
- **問題不存在**: `{"error": "問題不存在"}`

## 錯誤碼說明

### HTTP 狀態碼
- **200 OK**: 請求成功
- **201 Created**: 資源創建成功
- **204 No Content**: 刪除成功
- **400 Bad Request**: 請求數據格式錯誤或驗證失敗
- **401 Unauthorized**: 未認證或認證令牌無效
- **403 Forbidden**: 已認證但沒有執行操作的權限
- **404 Not Found**: 請求的資源不存在
- **500 Internal Server Error**: 伺服器內部錯誤

### 常見錯誤響應格式
```json
{
    "data": null,
    "message": "錯誤描述信息",
    "status": "error"
}
```

或字段驗證錯誤：
```json
{
    "data": {
        "title": ["標題長度不能超過 255 字元"],
        "content": ["內容至少需要 10 個字元"]
    },
    "message": "驗證失敗",
    "status": "error"
}
```

## 額外功能

### 題解按讚功能
雖然不在核心四個API中，但系統還提供按讚功能：

**POST** `/editorials/problem/{problemId}/solution/{solutionId}/like/` - 按讚
**DELETE** `/editorials/problem/{problemId}/solution/{solutionId}/like/` - 取消按讚

## 權限說明

### 題解管理權限
只有以下用戶可以創建、修改、刪除題解：
1. 問題所屬課程的主要老師 (`course.teacher_id`)
2. 問題所屬課程的老師成員 (`Course_members.role = 'teacher'`)
3. 問題所屬課程的TA成員 (`Course_members.role = 'ta'`)

### 題解查看權限
所有已認證用戶都可以查看已發布的題解。

## 注意事項

1. **UUID格式**: `solutionId` 必須是有效的UUID格式
2. **內容長度**: 題解內容不能為空
3. **標題長度**: 標題最多255個字元
4. **難度評級**: `difficulty_rating` 的範圍是 0.0 ~ 99.9，必須是一位小數（如：1.0, 5.5, 99.9）
5. **問題關聯**: 題解必須關聯到存在的問題
6. **課程權限**: 問題必須屬於某個課程，且操作者必須是該課程的教學人員
7. **狀態管理**: 創建的題解自動設為"已發布"狀態
8. **統計更新**: 查看題解時會自動增加瀏覽次數
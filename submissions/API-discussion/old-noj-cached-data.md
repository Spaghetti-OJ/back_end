# 舊 NOJ 系統實際快取的資料清單

## 概述

基於對原有 NOJ 系統程式碼的分析，以下是實際放在 Redis 快取中的資料類型和用途。

## 實際快取的資料

### 1. 提交列表查詢結果
**位置**: `model/submission.py` - `get_submission_list()`
```python
cache_key = f'SUBMISSION_LIST_API_{user}_{problem_id}_{username}_{status}_{language_type}_{course}_{offset}_{count}_{before}_{after}'

# 快取內容
{
    "submissions": [
        {
            "submissionId": "507f1f77bcf86cd799439011",
            "problemId": 123,
            "user": {"username": "alice", ...},
            "timestamp": 1640995200.0,
            "status": 0,
            "score": 100,
            "language": 1,
            "ipAddr": "192.168.1.1"
        }
    ],
    "submission_count": 150
}

# 過期時間: 15秒
```

### 2. 用戶題目高分
**位置**: `mongo/problem/problem.py` - `get_high_score()`
```python
cache_key = f'high_score_{problem_id}_{user_id}'

# 快取內容: 純數值
87  # 用戶在該題目的最高分

# 過期時間: 600秒 (10分鐘)
```

### 3. 提交權限檢查結果
**位置**: `mongo/submission.py` - `own_permission()`
```python
cache_key = f'SUBMISSION_PERMISSION_{submission_id}_{user_id}_{problem_id}'

# 快取內容: 權限等級數值
3  # 對應 Permission 枚舉值
   # 0: 無權限, 1: OTHER, 2: STUDENT, 3: MANAGER

# 過期時間: 60秒 (1分鐘)
```

### 4. 提交驗證 Token (安全用途)
**位置**: `mongo/submission.py` - `assign_token()` / `verify_token()`
```python
cache_key = f'stoekn_{submission_id}'  # 注意: 原代碼拼寫錯誤

# 快取內容: 隨機生成的 Token 字串
"KoNoSandboxDa_random_token_string"

# 特殊處理: 
# - 無固定過期時間
# - 驗證後立即刪除 (一次性使用)
# - 用於 Sandbox 與後端的安全通信
```

## **沒有** 快取的資料

### 原系統中這些資料都**不在**快取中：

#### 1. 用戶基本資料
```python
# 每次都從 MongoDB 查詢
user = User.objects.get(username='alice')
user.email, user.role, user.profile  # 沒有快取
```

#### 2. 題目資料
```python
# 每次都從 MongoDB 查詢  
problem = Problem.objects.get(id=123)
problem.title, problem.description  # 沒有快取
```

#### 3. 課程資料
```python
# 每次都從 MongoDB 查詢
course = Course.objects.get(name='演算法')
course.members, course.assignments  # 沒有快取
```

#### 4. 提交的程式碼內容
```python
# 每次都從 GridFS 或 MinIO 讀取
submission.get_main_code()  # 沒有快取
submission.get_code('main.cpp')  # 沒有快取
```

#### 5. 提交的執行結果
```python
# 每次都從檔案系統讀取
submission.get_single_output(task_no, case_no)  # 沒有快取
submission.get_detailed_result()  # 沒有快取
```

#### 6. 統計資料
```python
# 每次都重新計算
problem.get_submission_count()  # 沒有快取
user.get_solved_problem_count()  # 沒有快取
course.get_student_progress()  # 沒有快取
```

#### 7. 排行榜資料
```python
# 每次都重新查詢和計算
get_global_ranking()  # 沒有快取
get_course_ranking()  # 沒有快取
```

## 快取使用統計

| 資料類型 | 是否快取 | 快取時間 | 原因 |
|---------|---------|---------|------|
| **提交列表查詢** | O | 15秒 | 高頻查詢，短期快取減少 DB 負載 |
| **用戶題目高分** | O | 10分鐘 | 計算成本高，允許稍長快取 |
| **提交權限** | O | 1分鐘 | 複雜權限計算，短期快取 |
| **驗證 Token** | O | 用後即刪 | 安全考量，一次性使用 |
| 用戶基本資料 | X | - | 變更頻繁，保證一致性 |
| 題目內容 | X | - | 變更時需立即生效 |
| 程式碼內容 | X | - | 檔案讀取，不適合記憶體快取 |
| 執行結果 | X | - | 檔案讀取，不適合記憶體快取 |
| 統計資料 | X | - | 計算邏輯簡單，不需快取 |
| 排行榜 | X | - | 沒有實作快取機制 |

## 舊系統快取策略特點

### 1. **極度保守**
- 只快取 4 種資料類型
- 快取時間都很短 (15秒 - 10分鐘)
- 大部分資料都不快取

### 2. **查詢結果導向**
- 主要快取資料庫查詢結果
- 不快取原始資料或檔案內容
- 重點解決高頻查詢的效能問題

### 3. **安全優先**
- 權限相關快取時間極短 (1分鐘)
- Token 使用後立即刪除
- 寧可犧牲效能也要保證安全

### 4. **簡單的失效策略**
- 主要依賴 TTL 自動過期
- 沒有複雜的主動失效機制
- 避免快取一致性的複雜問題

## 對新系統的啟示

### 可以學習的部分
1. **保守的快取時間**：避免資料不一致問題
2. **權限快取**：複雜的權限計算確實值得快取
3. **安全 Token 處理**：一次性使用的安全設計
4. **查詢結果快取**：針對高頻查詢進行最佳化

### 可以改進的部分
1. **統計資料快取**：排行榜、用戶統計等可以快取
2. **程式碼內容快取**：常用程式碼模板可以快取
3. **主動失效機制**：資料更新時主動清除相關快取
4. **快取時間調整**：某些資料可以接受更長的快取時間

---

**總結**：舊 NOJ 系統只快取了 4 種核心資料，採用非常保守的策略。新系統可以在保持安全性的前提下，擴展快取的使用範圍以提升效能。
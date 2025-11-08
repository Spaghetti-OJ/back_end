# 原有 NOJ 系統快取使用分析報告

## 概述

本文件純粹分析原有 NOJ 系統如何使用 Redis 快取，不涉及新系統建議，僅供參考和決策依據。

## 原有系統快取使用模式

### 1. 提交列表查詢快取

**位置**: `model/submission.py` 的 `get_submission_list()` 函數

**快取策略**:
```python
# 快取鍵組成
cache_key = '_'.join(map(str, (
    'SUBMISSION_LIST_API',
    user,                # 用戶物件
    problem_id,          # 題目ID
    username,            # 用戶名
    status,              # 提交狀態
    language_type,       # 程式語言
    course,              # 課程
    offset,              # 分頁偏移
    count,               # 每頁數量
    before,              # 時間範圍(前)
    after,               # 時間範圍(後)
)))

# 快取內容
cached_data = {
    'submissions': [submission_list],
    'submission_count': total_count
}

# 快取設定
cache.set(cache_key, json.dumps(cached_data), 15)  # 15秒過期
```

**特點**:
- 非常短的快取時間 (15秒)
- 快取完整的查詢結果和總數
- 根據所有查詢參數生成唯一鍵

### 2. 用戶題目高分快取

**位置**: `mongo/problem/problem.py` 的 `get_high_score()` 方法

**快取策略**:
```python
# 快取鍵生成
def high_score_key(self, user: User) -> str:
    return f'high_score_{self.id}_{user.id}'

# 快取邏輯
cache = RedisCache()
key = self.high_score_key(user=user)
if (val := cache.get(key)) is not None:
    return int(val.decode())

# 計算並快取
high_score = max(submissions[0].score, 0)
cache.set(key, high_score, ex=600)  # 10分鐘過期
```

**特點**:
- 中等長度快取時間 (10分鐘)
- 快取純數值結果
- 按用戶和題目分別快取

### 3. 提交權限快取

**位置**: `mongo/submission.py` 的 `own_permission()` 方法

**快取策略**:
```python
# 快取鍵格式
key = f'SUBMISSION_PERMISSION_{self.id}_{user.id}_{self.problem.id}'

# 快取檢查
cache = RedisCache()
if (v := cache.get(key)) is not None:
    return self.Permission(int(v))

# 計算權限後快取
cache.set(key, cap.value, 60)  # 1分鐘過期
```

**特點**:
- 短快取時間 (1分鐘)
- 快取權限枚舉值
- 包含提交、用戶、題目三重ID

### 4. 提交驗證 Token 快取

**位置**: `mongo/submission.py` 的 `assign_token()` 和 `verify_token()` 方法

**快取策略**:
```python
# Token 生成和存儲
def assign_token(cls, submission_id, token=None):
    if token is None:
        token = gen_token()
    RedisCache().set(gen_key(submission_id), token)
    return token

# Token 驗證和清除
def verify_token(cls, submission_id, token):
    cache = RedisCache()
    key = gen_key(submission_id)
    s_token = cache.get(key)
    if s_token is None:
        return False
    s_token = s_token.decode('ascii')
    valid = secrets.compare_digest(s_token, token)
    if valid:
        cache.delete(key)  # 使用後立即刪除
    return valid

# Token 鍵格式
def gen_key(_id):
    return f'stoekn_{_id}'  # 注意: 原代碼有拼寫錯誤 "stoekn"
```

**特點**:
- 無明確過期時間 (依賴手動刪除)
- 一次性使用 (驗證後立即刪除)
- 用於 Sandbox 和後端的安全通信

## 原系統快取分類總結

### 按快取時間分類

| 快取類型 | 過期時間 | 用途 |
|---------|---------|------|
| 提交列表查詢 | 15秒 | 避免頻繁查詢資料庫 |
| 提交權限 | 60秒 | 減少權限計算開銷 |
| 用戶高分 | 600秒 (10分鐘) | 統計數據快取 |
| 驗證 Token | 無期限 | 安全驗證，用後即刪 |

### 按資料類型分類

| 資料類型 | 範例 | 特點 |
|---------|------|------|
| 查詢結果 | 提交列表 | JSON 序列化存儲 |
| 統計數據 | 用戶高分 | 簡單數值 |
| 權限資料 | 權限等級 | 枚舉值 |
| 安全 Token | 驗證密鑰 | 字串，一次性使用 |

### 按快取策略分類

| 策略類型 | 說明 | 應用場景 |
|---------|------|---------|
| **Cache-Aside** | 先查快取，miss 時查 DB 並回寫 | 提交列表、用戶高分 |
| **Write-Behind** | 使用後刪除，不回寫 | 驗證 Token |
| **TTL-Based** | 依賴過期時間自動失效 | 大部分查詢快取 |

## 原系統設計哲學

### 1. 保守的快取策略
- **短過期時間**: 大部分快取只有 15-60 秒
- **避免資料不一致**: 寧可多查詢，也不要過期資料
- **簡單的失效機制**: 主要依賴 TTL，很少主動失效

### 2. 效能 vs 一致性的權衡
- **高頻查詢**: 提交列表只快取 15 秒，但能顯著減少 DB 負載
- **統計資料**: 用戶高分可以接受 10 分鐘的延遲
- **安全資料**: Token 類資料優先保證安全性

### 3. 快取鍵設計模式
```python
# 模式 1: 功能_參數1_參數2_參數N
'SUBMISSION_LIST_API_user_problem_status_...'

# 模式 2: 資料類型_ID1_ID2
'high_score_{problem_id}_{user_id}'

# 模式 3: 功能_主鍵
'stoekn_{submission_id}'
```

## 從原系統學到的經驗

### 好的做法
1. **權限快取**: 複雜的權限計算結果值得快取
2. **查詢結果快取**: 即使很短時間也能顯著提升效能
3. **安全優先**: Token 使用後立即刪除
4. **簡單的鍵設計**: 容易理解和除錯

### 可能的改進點
1. **過短的快取時間**: 15秒可能過於保守
2. **缺乏主動失效**: 資料更新時沒有清除相關快取
3. **拼寫錯誤**: `stoekn` 應該是 `token`
4. **快取策略單一**: 大部分都是 Cache-Aside 模式

---

**總結**: 原系統採用非常保守但安全的快取策略，優先保證資料一致性而非效能最佳化。新系統可以參考其安全性考量，但在效能最佳化方面有改進空間。
# 資料存儲策略設計文件

## 概述

本文件分析原有 NOJ 系統的快取使用模式，並定義在新 Submissions 系統中，哪些資料應該存放在資料庫(PostgreSQL)，哪些資料應該存放在快取(Redis)，以及相應的存取策略和快取失效機制。

## 原有 NOJ 系統快取分析

### 實際使用的快取策略

基於對原有系統的分析，發現以下快取使用模式：

#### 1. 提交列表查詢快取
```python
# 位置：model/submission.py get_submission_list()
cache_key = '_'.join(map(str, (
    'SUBMISSION_LIST_API',
    user, problem_id, username, status, 
    language_type, course, offset, count, before, after
)))

# 快取內容：查詢結果 + 總數
{
    'submissions': [...],
    'submission_count': 150
}

# 快取時間：15秒 (非常短)
cache.set(cache_key, json.dumps(data), 15)
```

#### 2. 用戶高分快取 
```python
# 位置：mongo/problem/problem.py get_high_score()
cache_key = f'high_score_{problem_id}_{user_id}'

# 快取內容：用戶在特定題目的最高分
high_score = 87

# 快取時間：600秒 (10分鐘)
cache.set(key, high_score, ex=600)
```

#### 3. 提交權限快取
```python
# 位置：mongo/submission.py own_permission()
cache_key = f'SUBMISSION_PERMISSION_{submission_id}_{user_id}_{problem_id}'

# 快取內容：權限等級 (數字)
permission_level = 3  # MANAGER, STUDENT, OTHER, etc.

# 快取時間：60秒 (1分鐘)
cache.set(key, permission_level, 60)
```

#### 4. 提交 Token 快取 (安全用途)
```python
# 位置：mongo/submission.py assign_token/verify_token
cache_key = f'stoekn_{submission_id}'

# 快取內容：一次性驗證 token
token = 'KoNoSandboxDa'

# 特點：驗證後立即刪除 (一次性使用)
cache.delete(key)  # 使用後刪除
```

### 原系統快取特點總結

1. **極短快取時間**：多數快取只有 15-60 秒，避免資料不一致
2. **查詢結果導向**：主要快取資料庫查詢結果，不快取原始資料
3. **安全優先**：權限和 token 相關快取都有短過期時間
4. **簡單的失效策略**：主要依賴 TTL，沒有複雜的主動失效

## 資料庫存儲 (PostgreSQL)

### 永久性資料 - 必須存資料庫

#### 1. 核心業務資料 (保持與原系統一致)
```sql
-- submissions 表：提交記錄
- id, problem_id, user_id, language_type
- source_code, status, score, ip_address  
- created_at, updated_at, judged_at
- execution_time, memory_usage

-- submission_results 表：測試結果詳情  
- submission_id, task_id, case_id
- status, execution_time, memory_usage
- output_minio_path (檔案存儲路徑)

-- user_problem_stats 表：用戶統計
- user_id, problem_id, best_score
- attempt_count, solved_status, first_solved_at

-- custom_tests 表：自定義測試
- user_id, problem_id, language_type
- source_code, input_data, expected_output
- result, created_at

-- code_drafts 表：程式碼草稿
- user_id, problem_id, language_type  
- source_code, title, last_modified

-- editorials 表：題解
- problem_id, author_id, title, content
- difficulty_rating, is_official, created_at

-- editorial_likes 表：題解點讚
- editorial_id, user_id, created_at
```
-- submissions 表：提交記錄
- id, problem_id, user_id, language_type
- source_code, status, score, ip_address
- created_at, updated_at, judged_at

-- submission_results 表：測試結果
- submission_id, task_id, case_id
- status, execution_time, memory_usage
- input_data, expected_output, actual_output

-- user_problem_stats 表：用戶統計
- user_id, problem_id, best_score
- attempt_count, solved_status, first_solved_at

-- custom_tests 表：自定義測試
- user_id, problem_id, language_type
- source_code, input_data, expected_output
- result, created_at

-- code_drafts 表：程式碼草稿
- user_id, problem_id, language_type
- source_code, title, last_modified

-- editorials 表：題解
- problem_id, author_id, title, content
- difficulty_rating, is_official, created_at

-- editorial_likes 表：題解點讚
- editorial_id, user_id, created_at
```

#### 2. 用戶認證與權限資料
```sql
-- 用戶基本資料
- user_id, username, email, role
- last_login, is_active, created_at

-- 權限與角色資料
- permissions, group_memberships
- course_enrollments, problem_access
```

#### 3. 系統配置資料
```sql
-- 系統設定
- rate_limit_settings, sandbox_configurations
- judging_configurations, scoring_rules

-- 審計日誌
- user_actions, api_access_logs
- security_events, error_logs
```

**為什麼要放資料庫？**
- **資料一致性**：ACID 特性保證資料完整性
- **持久性**：重要業務資料不能遺失
- **複雜查詢**：支援 SQL 複雜查詢和聚合
- **關聯性**：支援表格間的關聯查詢
- **備份恢復**：完整的備份和恢復機制

## 快取存儲 (Redis)

### 1. 查詢結果快取

#### 提交列表快取
```python
# 快取鍵格式
cache_key = f"submissions:list:{user_id}:{filters_hash}:{page}"

# 快取內容
{
    "submissions": [
        {
            "id": 1234,
            "problem_title": "Two Sum",
            "status": "AC",
            "score": 100,
            "created_at": "2025-10-21T10:30:00Z"
        }
    ],
    "total_count": 150,
    "has_next": true
}

# 快取時間：15分鐘
# 失效條件：用戶新提交時清除該用戶相關快取
```

#### 用戶統計快取
```python
# 快取鍵格式  
cache_key = f"stats:user:{user_id}"

# 快取內容
{
    "total_submissions": 234,
    "solved_problems": 45,
    "accuracy_rate": 0.76,
    "rank": 128,
    "recent_activities": [...],
    "language_stats": {...}
}

# 快取時間：1小時
# 失效條件：用戶提交新作業時更新
```

#### 題目統計快取
```python
# 快取鍵格式
cache_key = f"stats:problem:{problem_id}"

# 快取內容
{
    "total_submissions": 1500,
    "accepted_count": 750,
    "acceptance_rate": 0.50,
    "difficulty_rating": 3.2,
    "language_distribution": {...},
    "top_solutions": [...]
}

# 快取時間：30分鐘
# 失效條件：有新提交時異步更新
```

#### 排行榜快取
```python
# 快取鍵格式
cache_key = f"ranking:global:{time_range}"

# 快取內容
{
    "rankings": [
        {
            "rank": 1,
            "user_id": 123,
            "username": "alice",
            "solved_count": 89,
            "total_score": 8900
        }
    ],
    "last_updated": "2025-10-21T11:00:00Z"
}

# 快取時間：1小時
# 更新策略：每小時重算一次
```

### 2. 會話和臨時資料

#### 用戶會話資料
```python
# 快取鍵格式
cache_key = f"session:{session_id}"

# 快取內容
{
    "user_id": 123,
    "permissions": ["submit", "view_stats"],
    "last_activity": "2025-10-21T11:30:00Z",
    "ip_address": "192.168.1.100"
}

# 快取時間：2小時(滑動過期)
# 失效條件：用戶登出或逾時
```

#### API 限流資料
```python
# 快取鍵格式
cache_key = f"rate_limit:{user_id}:{endpoint}"

# 快取內容
{
    "requests_count": 45,
    "window_start": "2025-10-21T11:00:00Z",
    "blocked_until": null
}

# 快取時間：根據限流視窗(如1分鐘、1小時)
# 重置條件：時間視窗結束時自動重置
```

#### 自定義測試結果
```python
# 快取鍵格式
cache_key = f"custom_test:{user_id}:{hash}"

# 快取內容
{
    "source_code": "print('hello')",
    "input_data": "test input",
    "output": "hello\n",
    "execution_time": "120ms",
    "memory_usage": "2MB",
    "status": "success"
}

# 快取時間：1小時
# 清理策略：LRU 自動清理舊結果
```

### 3. 預運算資料

#### 題解推薦快取
```python
# 快取鍵格式
cache_key = f"editorials:recommended:{problem_id}"

# 快取內容
{
    "official_editorial": {...},
    "top_community_editorials": [...],
    "related_editorials": [...],
    "computed_at": "2025-10-21T10:00:00Z"
}

# 快取時間：6小時
# 更新策略：有新題解發布時異步更新
```

#### 搜尋結果快取
```python
# 快取鍵格式
cache_key = f"search:{query_hash}:{filters_hash}"

# 快取內容
{
    "results": [...],
    "total_hits": 45,
    "search_time": "15ms",
    "facets": {...}
}

# 快取時間：30分鐘
# 失效條件：相關資料更新時清除
```

## 快取策略與失效機制

### 1. 快取更新策略

#### Cache-Aside 模式(推薦)
```python
def get_user_stats(user_id):
    # 1. 先查快取
    cache_key = f"stats:user:{user_id}"
    cached_data = redis.get(cache_key)
    
    if cached_data:
        return json.loads(cached_data)
    
    # 2. 快取miss，查資料庫
    stats = calculate_user_stats_from_db(user_id)
    
    # 3. 寫入快取
    redis.setex(cache_key, 3600, json.dumps(stats))
    
    return stats

def invalidate_user_stats(user_id):
    # 用戶有新提交時清除快取
    cache_key = f"stats:user:{user_id}"
    redis.delete(cache_key)
```

#### Write-Through 模式(部分資料)
```python
def update_submission_score(submission_id, score):
    # 1. 更新資料庫
    submission = Submission.objects.get(id=submission_id)
    submission.score = score
    submission.save()
    
    # 2. 同時更新快取
    cache_key = f"submission:{submission_id}"
    cached_submission = submission.to_dict()
    redis.setex(cache_key, 1800, json.dumps(cached_submission))
```

### 2. 快取失效機制

#### 基於事件的失效
```python
# Django signals 觸發快取失效
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Submission)
def invalidate_submission_caches(sender, instance, **kwargs):
    # 清除用戶相關快取
    redis.delete(f"stats:user:{instance.user_id}")
    redis.delete(f"submissions:list:{instance.user_id}:*")
    
    # 清除題目相關快取
    redis.delete(f"stats:problem:{instance.problem_id}")
    
    # 清除排行榜快取
    redis.delete("ranking:global:*")
```

#### 基於 TTL 的自動失效
```python
# 設定不同資料的快取時間
CACHE_TIMEOUTS = {
    'user_stats': 3600,      # 1小時
    'problem_stats': 1800,   # 30分鐘  
    'submission_list': 900,  # 15分鐘
    'ranking': 3600,         # 1小時
    'search_results': 1800,  # 30分鐘
}
```

#### 基於版本的失效
```python
# 使用版本號控制快取失效
def get_problem_stats(problem_id):
    version = redis.get(f"version:problem:{problem_id}") or "1"
    cache_key = f"stats:problem:{problem_id}:v{version}"
    
    cached_data = redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # 重新計算並快取
    stats = calculate_problem_stats(problem_id)
    redis.setex(cache_key, 1800, json.dumps(stats))
    return stats

def invalidate_problem_stats(problem_id):
    # 增加版本號，讓舊快取自然失效
    redis.incr(f"version:problem:{problem_id}")
```

## 效能考量與最佳實踐

### 1. 快取大小控制

#### 記憶體使用限制
```python
# Redis 記憶體配置
REDIS_CONFIG = {
    'maxmemory': '2gb',
    'maxmemory-policy': 'allkeys-lru',  # LRU 淘汰策略
    'maxmemory-samples': 5
}

# 大物件壓縮存儲
import gzip
import json

def cache_large_object(key, data, timeout):
    compressed_data = gzip.compress(json.dumps(data).encode())
    redis.setex(f"gz:{key}", timeout, compressed_data)

def get_large_object(key):
    compressed_data = redis.get(f"gz:{key}")
    if compressed_data:
        return json.loads(gzip.decompress(compressed_data).decode())
    return None
```

#### 批量操作最佳化
```python
# 批量查詢快取
def get_multiple_submissions(submission_ids):
    cache_keys = [f"submission:{sid}" for sid in submission_ids]
    cached_results = redis.mget(cache_keys)
    
    # 找出 cache miss 的 IDs
    missing_ids = []
    results = {}
    
    for i, result in enumerate(cached_results):
        if result:
            results[submission_ids[i]] = json.loads(result)
        else:
            missing_ids.append(submission_ids[i])
    
    # 只查詢 cache miss 的資料
    if missing_ids:
        db_results = Submission.objects.filter(id__in=missing_ids)
        for submission in db_results:
            results[submission.id] = submission.to_dict()
            # 回寫快取
            redis.setex(f"submission:{submission.id}", 1800, 
                       json.dumps(submission.to_dict()))
    
    return results
```

### 2. 監控與警報

#### 快取命中率監控
```python
def cache_hit_rate_middleware(get_response):
    def middleware(request):
        # 記錄快取存取統計
        cache_stats = {
            'hits': 0,
            'misses': 0,
            'operations': []
        }
        
        response = get_response(request)
        
        # 記錄到監控系統
        hit_rate = cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses'])
        if hit_rate < 0.8:  # 命中率低於 80% 時警報
            logger.warning(f"Low cache hit rate: {hit_rate:.2%}")
        
        return response
    return middleware
```

#### 記憶體使用監控
```python
def monitor_redis_memory():
    info = redis.info('memory')
    used_memory = info['used_memory']
    max_memory = info.get('maxmemory', 0)
    
    if max_memory > 0:
        usage_percent = (used_memory / max_memory) * 100
        if usage_percent > 90:
            logger.critical(f"Redis memory usage: {usage_percent:.1f}%")
        elif usage_percent > 80:
            logger.warning(f"Redis memory usage: {usage_percent:.1f}%")
```

## 安全性考量

### 1. 快取資料安全
```python
# 敏感資料不放快取，或加密存儲
def cache_sensitive_data(key, data, timeout):
    # 加密敏感資料
    encrypted_data = encrypt(json.dumps(data))
    redis.setex(f"secure:{key}", timeout, encrypted_data)

def get_sensitive_data(key):
    encrypted_data = redis.get(f"secure:{key}")
    if encrypted_data:
        return json.loads(decrypt(encrypted_data))
    return None
```

### 2. 快取隔離
```python
# 用戶資料隔離
def get_user_cache_key(user_id, key_type, *args):
    # 確保用戶只能存取自己的快取
    return f"user:{user_id}:{key_type}:{':'.join(map(str, args))}"

# 權限檢查
def get_cached_data_with_permission(user, cache_key):
    if not user.has_permission_for_cache(cache_key):
        raise PermissionError("Access denied")
    return redis.get(cache_key)
```

## 總結

### 資料庫 vs 快取決策準則

| 特性 | 資料庫 | 快取 |
|-----|--------|------|
| **資料重要性** | 核心業務資料、不可遺失 | 可重建的查詢結果 |
| **存取頻率** | 各種頻率 | 高頻存取 |
| **資料大小** | 任意大小 | 相對較小 |
| **查詢複雜度** | 複雜 SQL 查詢 | 簡單 key-value 查詢 |
| **一致性要求** | 強一致性 | 最終一致性可接受 |
| **持久性要求** | 永久保存 | 臨時存儲 |

### 實作建議
1. **優先原則**：重要資料先存資料庫，效能瓶頸再加快取
2. **監控優先**：建立完善的快取監控機制
3. **漸進式導入**：從高頻查詢開始加入快取
4. **定期清理**：建立快取清理和維護機制

---

**文件版本**: v1.0  
**最後更新**: 2025年10月21日  
**維護者**: Backend Team
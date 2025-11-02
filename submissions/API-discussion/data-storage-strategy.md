# 資料存儲策略設計文件

> ** 保守策略說明**
> - 本文件採用**選擇性快取**策略：只在極高頻操作和對用戶體驗關鍵的地方設計 cache
> - 沿用舊 NOJ 已驗證的快取策略（提交列表、用戶高分、權限檢查、Token）
> - 必須實作**布隆過濾器**（防止快取穿透）和**分散式鎖**（防止快取擊穿）
> - TTL 時間參考舊 NOJ（30秒 - 10分鐘），優先保證資料一致性
> - **重點優化**: 查看 ranking 和提交詳情的用戶體驗

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

## 快取存儲 (Redis) - 保守策略實作

### 1. 極高頻查詢快取

#### 1.1 提交列表快取  必須實作
**API**: `GET /submission/`  
**原因**: 學生會反覆刷新查看判題結果，超高頻查詢

```python
# 快取鍵格式
cache_key = f"SUBMISSION_LIST:{user_id}:{problem_id}:{status}:{language}:{offset}:{limit}"

# 快取內容
{
    "submissions": [
        {
            "id": "507f1f77-bcf8-6cd7-9943-9011",
            "problem_id": 42,
            "status": "accepted",
            "score": 100,
            "language_type": "python",
            "created_at": "2025-11-02T10:30:00Z"
        }
    ],
    "total_count": 150,
    "cached_at": "2025-11-02T10:30:00Z"
}

# 快取時間：30秒（參考舊 NOJ 的 15秒，稍微延長）
# 失效條件：
# 1. TTL 自動過期（主要策略）
# 2. 用戶新提交時主動清除（pattern: SUBMISSION_LIST:{user_id}:*）
```

#### 1.2 用戶統計快取  必須實作

**API**: `GET /stats/user/{userId}`  
**原因**: 計算密集（聚合查詢），個人頁面和排行榜會頻繁查詢

```python
# 快取鍵格式  
cache_key = f"USER_STATS:{user_id}"

# 快取內容
{
    "user_id": "123e4567...",
    "total_submissions": 234,
    "solved_problems": 45,
    "accepted_count": 89,
    "accuracy_rate": 0.76,
    "best_scores": {...},  # problem_id -> score
    "recent_activities": [...],
    "language_distribution": {...}
}

# 快取時間：5分鐘（允許統計資料短期延遲）
# 失效條件：
# 1. TTL 自動過期（主要策略）
# 2. 用戶新提交時主動清除
# 安全機制：使用分散式鎖防止重複計算
```

#### 1.3 提交詳情快取  必須實作

**API**: `GET /submission/<submission>`  
**原因**: 查看判題結果和程式碼，熱門 AC 提交被頻繁查看

```python
# 快取鍵格式
cache_key = f"SUBMISSION_DETAIL:{submission_id}"

# 快取內容
{
    "id": "507f1f77...",
    "user": {"id": "...", "username": "alice"},
    "problem_id": 42,
    "status": "accepted",
    "score": 100,
    "execution_time": 1234,
    "memory_usage": 5678,
    "language_type": "python",
    "created_at": "2025-11-02T10:30:00Z",
    "results": [...]  # 包含測試結果
}

# 快取時間：2分鐘
# 快取條件：只快取已判題完成的提交（status != 'pending'）
# 失效條件：TTL 自動過期
# 安全機制：使用布隆過濾器防止查詢不存在的 submission_id
```

---

### 2. 舊 NOJ 已驗證快取（沿用）

#### 2.1 用戶題目高分快取  沿用舊 NOJ

**來源**: 舊 NOJ `get_high_score()`  
**原因**: 計算成本高，舊系統已驗證有效

```python
# 快取鍵格式
cache_key = f"HIGH_SCORE:{problem_id}:{user_id}"

# 快取內容
{
    "user_id": "123e4567...",
    "problem_id": 42,
    "best_score": 87,
    "best_submission_id": "507f1f77...",
    "cached_at": "2025-11-02T10:30:00Z"
}

# 快取時間：10分鐘（沿用舊 NOJ 設定）
# 失效條件：TTL 自動過期 + 用戶新提交該題時清除
```

#### 2.2 提交權限快取  沿用舊 NOJ

**來源**: 舊 NOJ `own_permission()`  
**原因**: 複雜的權限計算，短期快取提升效能

```python
# 快取鍵格式
cache_key = f"SUBMISSION_PERMISSION:{submission_id}:{user_id}"

# 快取內容
{
    "can_view": true,
    "can_edit": false,
    "can_delete": false,
    "is_owner": true,
    "is_course_staff": false
}

# 快取時間：1分鐘（沿用舊 NOJ，安全優先）
# 失效條件：TTL 自動過期
```

#### 2.3 驗證 Token 快取  沿用舊 NOJ

**來源**: 舊 NOJ `assign_token()` / `verify_token()`  
**原因**: Sandbox 與後端的安全通信機制

```python
# 快取鍵格式
cache_key = f"TOKEN:{submission_id}"

# 快取內容
"random_token_string_for_sandbox"

# 特殊處理：
# - 無固定過期時間
# - 驗證後立即刪除（一次性使用）
# - 用於 Sandbox 回傳判題結果時的身份驗證
```

---

### 3. 用戶體驗優化快取

#### 3.1 排行榜快取  體驗優化

**API**: `GET /ranking`  
**原因**: 用戶體驗要求，避免每次都重新計算排名

```python
# 快取鍵格式
cache_key = f"RANKING:{scope}:{time_range}"
# 範例: RANKING:global:all_time
# 範例: RANKING:course:123:this_week

# 快取內容
{
    "rankings": [
        {
            "rank": 1,
            "user_id": "123e4567...",
            "username": "alice",
            "solved_count": 89,
            "total_score": 8900,
            "accepted_rate": 0.85
        }
    ],
    "total_users": 500,
    "last_updated": "2025-11-02T11:00:00Z"
}

# 快取時間：5分鐘（平衡即時性與效能）
# 失效條件：
# 1. TTL 自動過期（主要策略）
# 2. 可選：背景任務定期更新
# 安全機制：使用分散式鎖防止重複計算
```

---

### 4. 暫不快取的資料（未來擴展）

以下資料在保守策略中**不快取**，待系統規模擴大後再考慮：

#### 會話資料
- 使用 Django Session 框架處理
- 不額外快取到 Redis

#### API 限流資料  
- 使用 Django REST Framework 的 throttling 機制
- 或使用 Nginx 層面的限流

#### 自定義測試結果
- 臨時資料，執行完即可丟棄
- 不需要快取

#### 題解相關
- 讀取頻率不高
- 資料變更頻率低
- 不是核心功能

#### 搜尋結果
- 查詢條件多樣，快取命中率低
- 直接查詢資料庫或使用專用搜尋引擎

## 快取策略與失效機制（保守策略實作）

### 1. Cache-Aside 模式（主要採用）

```python
from django.core.cache import cache

def get_user_stats(user_id):
    """使用 Cache-Aside 模式獲取用戶統計"""
    # 1. 先查快取
    cache_key = f"USER_STATS:{user_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    # 2. 快取 miss，使用分散式鎖防止擊穿
    lock_key = f"lock:{cache_key}"
    lock = acquire_distributed_lock(lock_key, timeout=5)
    
    try:
        # 雙重檢查
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # 3. 查資料庫並計算
        stats = calculate_user_stats_from_db(user_id)
        
        # 4. 寫入快取（5分鐘）
        cache.set(cache_key, stats, 300)
        
        return stats
    finally:
        release_distributed_lock(lock_key, lock)

def invalidate_user_stats(user_id):
    """用戶有新提交時清除快取"""
    cache_key = f"USER_STATS:{user_id}"
    cache.delete(cache_key)
```

### 2. 防止快取穿透（布隆過濾器） 必須實作

```python
from pybloom_live import BloomFilter

class CachePenetrationProtection:
    def __init__(self):
        # 初始化布隆過濾器（100萬容量，0.1% 誤判率）
        self.bloom_filter = BloomFilter(capacity=1000000, error_rate=0.001)
        self._init_bloom_filter()
    
    def _init_bloom_filter(self):
        """啟動時將所有 submission_id 加入布隆過濾器"""
        submission_ids = Submission.objects.values_list('id', flat=True)
        for sid in submission_ids:
            self.bloom_filter.add(str(sid))
    
    def add_submission(self, submission_id):
        """新提交時加入布隆過濾器"""
        self.bloom_filter.add(str(submission_id))
    
    def might_exist(self, submission_id):
        """檢查提交是否可能存在"""
        return str(submission_id) in self.bloom_filter
    
    def get_submission_safe(self, submission_id):
        """安全獲取提交，防止穿透"""
        # 1. 檢查布隆過濾器
        if not self.might_exist(submission_id):
            # 確定不存在，直接返回 404
            raise Http404("Submission not found")
        
        # 2. 檢查快取
        cache_key = f"SUBMISSION_DETAIL:{submission_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # 3. 查詢資料庫
        try:
            submission = Submission.objects.get(id=submission_id)
            submission_data = SubmissionSerializer(submission).data
            
            # 4. 只快取已判題完成的提交
            if submission.status != 'pending':
                cache.set(cache_key, submission_data, 120)  # 2分鐘
            
            return submission_data
            
        except Submission.DoesNotExist:
            # 布隆過濾器誤判，快取空值防止重複查詢
            cache.set(cache_key, None, 60)
            raise Http404("Submission not found")

# 全域實例
penetration_protection = CachePenetrationProtection()
```

### 3. 防止快取擊穿（分散式鎖） 必須實作

```python
import redis
import uuid
import time
from django.core.cache import cache

class RedisDistributedLock:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def acquire(self, key, expire=10, timeout=5):
        """
        獲取分散式鎖（帶超時機制）
        
        Args:
            key: 鎖的鍵
            expire: 鎖的過期時間（秒）
            timeout: 獲取鎖的超時時間（秒）
        
        Returns:
            identifier 或 None
        """
        identifier = str(uuid.uuid4())
        lock_key = f"lock:{key}"
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            # 嘗試獲取鎖（NX: 不存在才設定，EX: 過期時間）
            if self.redis.set(lock_key, identifier, nx=True, ex=expire):
                return identifier
            time.sleep(0.01)  # 10ms 後重試
        
        # 超時未獲取到鎖
        return None
    
    def release(self, key, identifier):
        """釋放分散式鎖（Lua 腳本確保原子性）"""
        lock_key = f"lock:{key}"
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        return self.redis.eval(lua_script, 1, lock_key, identifier)

# 使用範例：防止排行榜被重複計算（帶超時降級）
def get_ranking_safe(scope, time_range):
    cache_key = f"RANKING:{scope}:{time_range}"
    
    # 1. 檢查快取
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # 2. 獲取分散式鎖（最多等待 3 秒）
    lock = distributed_lock.acquire(cache_key, expire=30, timeout=3)
    if not lock:
        # 超時降級策略：直接查詢資料庫，不等待
        logger.warning(f"Failed to acquire lock for {cache_key}, falling back to direct query")
        return calculate_ranking(scope, time_range)
    
    try:
        # 3. 雙重檢查
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # 4. 計算排行榜（計算密集）
        ranking_data = calculate_ranking(scope, time_range)
        
        # 5. 寫入快取（5分鐘）
        cache.set(cache_key, ranking_data, 300)
        
        return ranking_data
    finally:
        # 6. 釋放鎖
        distributed_lock.release(cache_key, lock)

# Redis 客戶端
from django_redis import get_redis_connection
redis_client = get_redis_connection("default")
distributed_lock = RedisDistributedLock(redis_client)
```

### 4. 快取失效機制（簡化版）

#### TTL 自動過期（主要策略）

```python
# 保守策略的快取時間配置
CACHE_TIMEOUTS = {
    'submission_list': 30,        # 30秒（參考舊 NOJ）
    'user_stats': 300,            # 5分鐘
    'submission_detail': 120,     # 2分鐘
    'high_score': 600,            # 10分鐘（沿用舊 NOJ）
    'permission': 60,             # 1分鐘（沿用舊 NOJ）
    'ranking': 300,               # 5分鐘
}

# TTL 保證最終一致性：
# - 即使 signals 失效或延遲，快取最多在 TTL 時間後會自動過期
# - 優先使用 signals 主動清除，TTL 作為兜底機制
```

#### 基於事件的失效（最小化）

```python
# Django signals 觸發快取失效
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Submission)
def invalidate_submission_caches(sender, instance, created, **kwargs):
    """提交建立後清除相關快取"""
    if not created:
        return
    
    user_id = instance.user.id
    problem_id = instance.problem_id
    
    # 1. 清除用戶提交列表快取（模式匹配）
    pattern = f"SUBMISSION_LIST:{user_id}:*"
    delete_cache_pattern(pattern)
    
    # 2. 清除用戶統計快取
    cache.delete(f"USER_STATS:{user_id}")
    
    # 3. 清除用戶題目高分快取
    cache.delete(f"HIGH_SCORE:{problem_id}:{user_id}")
    
    # 4. 清除排行榜快取（延遲5秒，避免頻繁清除）
    from django_rq import enqueue
    enqueue(invalidate_ranking_cache, delay=5)
    
    # 5. 將新 submission_id 加入布隆過濾器
    penetration_protection.add_submission(instance.id)

def delete_cache_pattern(pattern):
    """刪除符合模式的所有快取"""
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        keys = conn.keys(pattern)
        if keys:
            conn.delete(*keys)
    except Exception as e:
        logger.error(f"Cache pattern delete failed: {e}")

def invalidate_ranking_cache():
    """清除所有排行榜快取"""
    pattern = "RANKING:*"
    delete_cache_pattern(pattern)

### Redis 超時與降級處理（防止阻塞） 必須實作

```python
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class CacheWithFallback:
    """帶降級機制的快取操作"""
    
    def __init__(self, timeout=0.5):
        """
        Args:
            timeout: Redis 操作超時時間（秒），預設 0.5 秒
        """
        self.timeout = timeout
    
    def get_safe(self, key, fetch_function=None):
        """
        安全獲取快取，Redis 故障時降級到資料庫
        
        Args:
            key: 快取鍵
            fetch_function: Redis 失敗時的降級函數
        
        Returns:
            快取資料或資料庫查詢結果
        """
        try:
            # 嘗試從 Redis 獲取（帶超時）
            result = cache.get(key, default=None)
            if result is not None:
                return result
            
            # 快取 miss，但 Redis 正常
            if fetch_function:
                result = fetch_function()
                # 嘗試寫入快取
                try:
                    cache.set(key, result, 300)
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")
                return result
            
            return None
            
        except Exception as e:
            # Redis 故障，降級到資料庫
            logger.error(f"Redis get failed for {key}: {e}")
            if fetch_function:
                return fetch_function()
            return None
    
    def set_safe(self, key, value, timeout=300):
        """
        安全寫入快取，失敗不阻塞主流程
        
        Args:
            key: 快取鍵
            value: 快取值
            timeout: TTL（秒）
        
        Returns:
            True/False 表示是否成功
        """
        try:
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            # Redis 故障，記錄日誌但不拋出異常
            logger.error(f"Redis set failed for {key}: {e}")
            return False

# 全域實例
cache_fallback = CacheWithFallback(timeout=0.5)

# 使用範例：用戶統計查詢
def get_user_stats_with_fallback(user_id):
    """獲取用戶統計，Redis 故障時直接查詢資料庫"""
    cache_key = f"USER_STATS:{user_id}"
    
    return cache_fallback.get_safe(
        cache_key,
        fetch_function=lambda: calculate_user_stats_from_db(user_id)
    )

# 使用範例：提交列表查詢
def get_submission_list_safe(user_id, **filters):
    """獲取提交列表，Redis 故障時降級"""
    cache_key = f"SUBMISSION_LIST:{user_id}:{hash(str(filters))}"
    
    def fetch_from_db():
        submissions = Submission.objects.filter(user_id=user_id, **filters)
        return list(submissions.values())
    
    return cache_fallback.get_safe(cache_key, fetch_from_db)
```
```

## 效能考量與最佳實踐

### 1. 快取大小控制與內存管理 必須實作

#### Redis 記憶體配置
```python
# redis.conf 或 Docker 環境變數配置
REDIS_CONFIG = {
    'maxmemory': '2gb',                    # 最大記憶體限制
    'maxmemory-policy': 'allkeys-lru',     # LRU 淘汰策略
    'maxmemory-samples': 5,                # LRU 採樣數量
}

# 淘汰策略說明：
# - allkeys-lru: 從所有 key 中淘汰最少使用的（推薦）
# - volatile-lru: 只從設定過期時間的 key 中淘汰
# - allkeys-lfu: 從所有 key 中淘汰訪問頻率最低的
# - volatile-ttl: 優先淘汰 TTL 最短的 key
# - noeviction: 記憶體滿時拒絕寫入（不推薦）

# Docker Compose 配置範例
"""
services:
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
      --maxmemory-samples 5
    ports:
      - "6379:6379"
"""

#### 記憶體監控與警報 必須實作

```python
from django_redis import get_redis_connection
import logging

logger = logging.getLogger(__name__)

class RedisMemoryMonitor:
    """Redis 記憶體監控"""
    
    def __init__(self, warning_threshold=0.8, critical_threshold=0.9):
        """
        Args:
            warning_threshold: 警告閾值（80%）
            critical_threshold: 嚴重閾值（90%）
        """
        self.redis = get_redis_connection("default")
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    def get_memory_info(self):
        """獲取 Redis 記憶體使用情況"""
        try:
            info = self.redis.info('memory')
            used_memory = info['used_memory']
            max_memory = info.get('maxmemory', 0)
            
            if max_memory == 0:
                logger.warning("Redis maxmemory not set!")
                return None
            
            usage_ratio = used_memory / max_memory
            
            return {
                'used_memory_mb': used_memory / (1024 * 1024),
                'max_memory_mb': max_memory / (1024 * 1024),
                'usage_ratio': usage_ratio,
                'status': self._get_status(usage_ratio)
            }
        except Exception as e:
            logger.error(f"Failed to get Redis memory info: {e}")
            return None
    
    def _get_status(self, usage_ratio):
        """判斷記憶體使用狀態"""
        if usage_ratio >= self.critical_threshold:
            return 'CRITICAL'
        elif usage_ratio >= self.warning_threshold:
            return 'WARNING'
        else:
            return 'OK'
    
    def check_and_alert(self):
        """檢查並發送警報"""
        info = self.get_memory_info()
        if not info:
            return
        
        status = info['status']
        usage = info['usage_ratio']
        
        if status == 'CRITICAL':
            logger.critical(
                f"Redis memory CRITICAL: {usage:.1%} used "
                f"({info['used_memory_mb']:.1f}MB / {info['max_memory_mb']:.1f}MB)"
            )
            # TODO: 發送緊急通知（Email/Slack）
            
        elif status == 'WARNING':
            logger.warning(
                f"Redis memory WARNING: {usage:.1%} used "
                f"({info['used_memory_mb']:.1f}MB / {info['max_memory_mb']:.1f}MB)"
            )
        else:
            logger.info(f"Redis memory OK: {usage:.1%} used")
        
        return info

# 全域監控實例
memory_monitor = RedisMemoryMonitor()

# Django Management Command: 監控 Redis 記憶體
# python manage.py monitor_redis_memory
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Monitor Redis memory usage'
    
    def handle(self, *args, **options):
        info = memory_monitor.check_and_alert()
        if info:
            self.stdout.write(
                f"Memory: {info['used_memory_mb']:.1f}MB / "
                f"{info['max_memory_mb']:.1f}MB ({info['usage_ratio']:.1%})"
            )
```

#### 大物件壓縮存儲（選用）

```python
import gzip
import json

def cache_large_object(key, data, timeout):
    """壓縮大型資料後快取（節省 50-70% 記憶體）"""
    compressed_data = gzip.compress(json.dumps(data).encode())
    cache.set(f"gz:{key}", compressed_data, timeout)

def get_large_object(key):
    """獲取壓縮快取資料"""
    compressed_data = cache.get(f"gz:{key}")
    if compressed_data:
        return json.loads(gzip.decompress(compressed_data).decode())
    return None

# 使用範例：排行榜資料較大時
def cache_ranking_compressed(scope, ranking_data):
    cache_key = f"RANKING:{scope}"
    cache_large_object(cache_key, ranking_data, 300)
```

#### 快取大小限制（保守策略）

```python
# 保守策略的快取大小控制
MAX_CACHE_SIZES = {
    'submission_list': 100,       # 最多 100 筆提交記錄
    'ranking': 500,               # 最多 500 名用戶排名
    'user_stats': None,           # 無限制（單個物件小）
}

def cache_submission_list_limited(cache_key, submissions, timeout=30):
    """限制提交列表快取大小"""
    # 只快取前 100 筆
    limited_data = submissions[:MAX_CACHE_SIZES['submission_list']]
    cache.set(cache_key, limited_data, timeout)
```
```

### 2. 監控和警報系統 必須實作

#### 快取命中率監控（簡化版）

```python
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class CacheHitRateMonitor:
    """快取命中率監控"""
    
    def __init__(self):
        self.stats = defaultdict(lambda: {'hits': 0, 'misses': 0})
    
    def record_hit(self, cache_type):
        """記錄快取命中"""
        self.stats[cache_type]['hits'] += 1
    
    def record_miss(self, cache_type):
        """記錄快取未命中"""
        self.stats[cache_type]['misses'] += 1
    
    def get_hit_rate(self, cache_type):
        """計算命中率"""
        stats = self.stats[cache_type]
        total = stats['hits'] + stats['misses']
        if total == 0:
            return 0.0
        return stats['hits'] / total
    
    def report(self):
        """生成監控報告"""
        for cache_type, stats in self.stats.items():
            total = stats['hits'] + stats['misses']
            if total == 0:
                continue
            
            hit_rate = self.get_hit_rate(cache_type)
            status = '✅' if hit_rate >= 0.7 else '⚠️' if hit_rate >= 0.5 else '🔴'
            
            logger.info(
                f"{status} Cache[{cache_type}]: "
                f"Hit Rate {hit_rate:.1%} ({stats['hits']}/{total})"
            )
            
            # 低命中率警報
            if hit_rate < 0.5 and total > 100:
                logger.warning(f"Low hit rate for {cache_type}: {hit_rate:.1%}")

# 全域監控實例
hit_rate_monitor = CacheHitRateMonitor()

# 使用範例
def get_user_stats_monitored(user_id):
    cache_key = f"USER_STATS:{user_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        hit_rate_monitor.record_hit('user_stats')
        return cached_data
    
    hit_rate_monitor.record_miss('user_stats')
    stats = calculate_user_stats_from_db(user_id)
    cache.set(cache_key, stats, 300)
    return stats
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

### 保守策略快取清單

| 資料類型 | Cache Key | TTL | 來源 | 安全機制 |
|---------|-----------|-----|------|---------|
| 提交列表 | `SUBMISSION_LIST:{user_id}:{problem_id}:{status}:{offset}:{limit}` | 30秒 | 極高頻 | 超時降級 |
| 用戶統計 | `USER_STATS:{user_id}` | 5分鐘 | 極高頻 | 分散式鎖 + 超時降級 |
| 提交詳情 | `SUBMISSION_DETAIL:{submission_id}` | 2分鐘 | 極高頻 | 布隆過濾器 + 超時降級 |
| 用戶題目高分 | `HIGH_SCORE:{problem_id}:{user_id}` | 10分鐘 | 舊 NOJ | 超時降級 |
| 提交權限 | `SUBMISSION_PERMISSION:{submission_id}:{user_id}` | 1分鐘 | 舊 NOJ | 超時降級 |
| 驗證 Token | `TOKEN:{submission_id}` | 一次性 | 舊 NOJ | 使用後刪除 |
| 排行榜 | `RANKING:{scope}:{time_range}` | 5分鐘 | 體驗優化 | 分散式鎖 + 超時降級 |

### 必須實作的核心機制

#### 1. 布隆過濾器（防止快取穿透）
- 防止查詢不存在的 `submission_id`
- 100萬容量，0.1% 誤判率
- 啟動時載入所有 ID
- 新提交時動態加入

#### 2. 分散式鎖（防止快取擊穿）
- 防止統計資料和排行榜的重複計算
- 使用 Redis SET NX EX
- Lua 腳本確保原子性釋放
- **帶超時機制**：最多等待 3-5 秒

#### 3. 超時降級（防止 Redis 阻塞）
- Redis 操作超時（0.5 秒）自動降級
- 降級策略：直接查詢資料庫
- 快取寫入失敗不阻塞主流程
- 記錄日誌但不拋出異常

#### 4. 內存管理（防止記憶體爆滿）
- Redis `maxmemory` 限制：2GB
- 淘汰策略：`allkeys-lru`
- 記憶體監控：80% 警告，90% 嚴重
- 定期監控任務：`python manage.py monitor_redis_memory`

#### 5. 快取一致性（防止資料不一致）
- Django signals 主動清除快取
- TTL 自動過期作為兜底機制
- 最大不一致時間：5 分鐘（排行榜）
- 關鍵資料（權限）：1 分鐘 TTL

#### 6. 監控與警報（發現問題）
- 快取命中率監控：目標 ≥ 70%
- Redis 記憶體監控：80% 警告
- Redis 連線狀態檢查
- Management Command：`python manage.py cache_stats`


### 資料庫 vs 快取決策準則

| 特性 | 資料庫 | 快取 |
|-----|--------|------|
| **資料重要性** | 核心業務資料、不可遺失 | 可重建的查詢結果 |
| **存取頻率** | 各種頻率 | 極高頻（提交列表、統計） |
| **資料大小** | 任意大小 | 相對較小 |
| **查詢複雜度** | 複雜 SQL 查詢 | 簡單 key-value 查詢 |
| **一致性要求** | 強一致性 | 最終一致性可接受（≤30秒） |
| **持久性要求** | 永久保存 | 臨時存儲 |

### 實作優先級

#### 第一階段（核心功能 - 必須完成）
1. **Redis 基礎配置**
   ```bash
   pip install django-redis pybloom-live redis
   ```
   - 配置 Django settings
   - 設定 `maxmemory=2gb` 和 `maxmemory-policy=allkeys-lru`
   - Docker Compose 配置

2. **安全機制實作**
   - `CachePenetrationProtection`（布隆過濾器）
   - `RedisDistributedLock`（分散式鎖）
   - `CacheWithFallback`（超時降級）

3. **極高頻快取**
   - 提交列表快取（30秒 TTL）
   - 用戶統計快取（5分鐘 TTL）
   - Django signals 清除機制

#### 第二階段（優化體驗）
1. **用戶體驗優化**
   - 提交詳情快取（2分鐘 TTL）
   - 排行榜快取（5分鐘 TTL）

2. **沿用舊 NOJ**
   - 用戶題目高分快取（10分鐘 TTL）
   - 提交權限快取（1分鐘 TTL）
   - 驗證 Token 機制

#### 第三階段（監控完善）
1. **監控系統**
   - `CacheHitRateMonitor`（命中率監控）
   - `RedisMemoryMonitor`（記憶體監控）
   - Management Commands (`cache_stats`, `monitor_redis_memory`)

2. **警報與優化**
   - 低命中率警報（< 70%）
   - 記憶體警報（> 80%）
   - 效能調優與壓縮

### 三大關鍵問題解決方案總結

| 問題 | 解決方案 | 實作複雜度 | 必須實作 |
|------|---------|----------|---------|
| **1. 緩存與資料庫不一致** | Django signals 主動清除 + TTL 兜底 | 簡單 | 是 |
| **2. Redis 查詢阻塞** | 超時降級（0.5秒）+ 分散式鎖超時（3秒） | 中等 | 是 |
| **3. 內存爆滿** | `maxmemory=2gb` + LRU 淘汰 + 監控警報 | 簡單 | 是 |

**關鍵設計原則**：
1. **寧可慢，不可錯**：Redis 故障時降級到資料庫，保證服務可用
2. **TTL 是保險**：即使 signals 失效，快取最多延遲 5 分鐘
3. **監控是眼睛**：快取命中率和記憶體使用必須可觀測
4. **超時是底線**：所有 Redis 操作都有超時，不能無限等待

### 實作建議

1. **保守優先**：只快取極高頻和對體驗關鍵的資料
2. **安全第一**：必須實作布隆過濾器、分散式鎖、超時降級
3. **參考舊 NOJ**：沿用已驗證的 TTL 時間
4. **簡化失效**：主要依賴 TTL 自動過期
5. **監控必備**：追蹤 cache hit rate 和記憶體使用

---

**文件版本**: v2.0（保守策略 + 完整容錯）  
**最後更新**: 2025年11月2日  
**維護者**: Backend Team
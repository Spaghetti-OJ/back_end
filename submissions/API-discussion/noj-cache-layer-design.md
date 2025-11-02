# Submissions 快取實作架構參考

> ** 文件狀態**
> - 本文件為架構參考，非完整實作指南
> - 實作細節請參考 [data-storage-strategy.md](./data-storage-strategy.md)
> - 保守策略採用簡化的實作方式

---

## 保守策略架構

基於保守策略，我們採用簡化的快取架構：

### 目錄結構

```
submissions/
├── cache/
│   ├── __init__.py          # 模組匯出
│   ├── keys.py              # 快取鍵管理
│   ├── protection.py        # 布隆過濾器
│   ├── lock.py              # 分散式鎖
│   ├── fallback.py          # 降級機制
│   ├── monitoring.py        # 監控系統
│   ├── signals.py           # Django 信號
│   └── utils.py             # 工具函數
├── management/commands/
│   ├── cache_stats.py       # 快取統計命令
│   └── monitor_redis_memory.py  # 記憶體監控命令
├── test_file/
│   └── test_redis_cache.py  # 快取測試
└── test_logs/
    └── redis-cache-testing-log-2025-11-02.md
```

### Cache Key 生成器 (`cache/keys.py`)

```python
class CacheKeys:
    """統一管理所有 Cache Key 的生成"""
    
    @staticmethod
    def submission_list(user_id, problem_id=None, status=None, 
                       language=None, offset=0, limit=20):
        params = [
            'SUBMISSION_LIST',
            str(user_id),
            str(problem_id) if problem_id else 'all',
            status or 'all',
            language or 'all',
            str(offset),
            str(limit)
        ]
        return ':'.join(params)
    
    @staticmethod
    def user_stats(user_id):
        return f'USER_STATS:{user_id}'
    
    @staticmethod
    def submission_detail(submission_id):
        return f'SUBMISSION_DETAIL:{submission_id}'
    
    @staticmethod
    def high_score(problem_id, user_id):
        return f'HIGH_SCORE:{problem_id}:{user_id}'
    
    @staticmethod
    def submission_permission(submission_id, user_id):
        return f'SUBMISSION_PERMISSION:{submission_id}:{user_id}'
    
    @staticmethod
    def ranking(scope, time_range):
        return f'RANKING:{scope}:{time_range}'
```

### 安全機制 (`cache/protection.py`)

```python
from pybloom_live import BloomFilter
import redis
import uuid

class CachePenetrationProtection:
    """布隆過濾器防穿透"""
    def __init__(self):
        self.bloom_filter = BloomFilter(capacity=1000000, error_rate=0.001)
        self._init_bloom_filter()
    
    def _init_bloom_filter(self):
        # 載入所有 submission_id
        pass
    
    def might_exist(self, submission_id):
        return str(submission_id) in self.bloom_filter
    
    def add_submission(self, submission_id):
        self.bloom_filter.add(str(submission_id))

class RedisDistributedLock:
    """分散式鎖防擊穿"""
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def acquire(self, key, expire=10):
        identifier = str(uuid.uuid4())
        lock_key = f"lock:{key}"
        if self.redis.set(lock_key, identifier, nx=True, ex=expire):
            return identifier
        return None
    
    def release(self, key, identifier):
        # Lua 腳本釋放
        pass
```

### 使用範例 (在 Views 中)

```python
from django.core.cache import cache
from .cache.keys import CacheKeys
from .cache.protection import penetration_protection, distributed_lock

class SubmissionListView(generics.ListAPIView):
    def get_queryset(self):
        user = self.request.user
        problem_id = self.request.query_params.get('problem_id')
        
        # 生成 cache key
        cache_key = CacheKeys.submission_list(
            user_id=user.id,
            problem_id=problem_id,
            offset=0,
            limit=20
        )
        
        # 檢查快取
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # 查詢資料庫
        queryset = Submission.objects.filter(user=user)
        if problem_id:
            queryset = queryset.filter(problem_id=problem_id)
        
        # 寫入快取（30秒）
        cache.set(cache_key, list(queryset), 30)
        
        return queryset
```

---

## 完整實作指南

詳細的實作細節、安全機制和程式碼範例，請參考：
- **[data-storage-strategy.md](./data-storage-strategy.md)** - 完整快取策略和實作

---

**文件版本**: v2.0（保守策略）  
**最後更新**: 2025年11月2日
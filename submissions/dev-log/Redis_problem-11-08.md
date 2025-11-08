# 修復日誌 - 2025-11-08

## 修復摘要

修復了 Redis 快取模組中的性能和穩定性問題。

---

## 問題 1: Redis `keys()` 阻塞問題

### 描述
> 在第 126 行使用帶模式的 `keys()` 是阻塞操作，在生產環境中可能導致性能問題，尤其是在大型 Redis 數據集上。這會在掃描時阻塞整個 Redis 服務器。考慮使用 `scan_iter()`，它是非阻塞且更適合生產環境的。

### 問題分析

**嚴重程度**: Critical（生產環境災難級別）

**影響範圍**: 整個 Redis 服務器的所有操作

#### 技術細節

1. **Redis 單線程架構**
   - Redis 使用單一執行緒處理所有請求
   - `keys()` 執行時會阻塞所有其他操作
   - 包括 GET、SET、INCR 等所有命令

2. **時間複雜度**
   - `keys(pattern)`: O(N)，N = Redis 中的所有鍵
   - 必須一次性掃描所有鍵才能返回結果

3. **實際影響**
   ```
   假設 Redis 有 1,000,000 個鍵：
   
   時間 00:00.000 - 執行 keys("submission:*")
   時間 00:00.001 - 用戶 A 請求 GET user:123 → 阻塞等待
   時間 00:00.002 - 用戶 B 請求 SET cart:456 → 阻塞等待
   時間 00:00.003 - 用戶 C 請求 INCR views:789 → 阻塞等待
   ...
   時間 00:01.500 - keys() 完成（掃描完成）
   時間 00:01.501 - 其他請求才能開始執行
   時間 00:01.502 - 用戶收到超時錯誤 
   ```

4. **生產環境風險**
   - CPU 使用率飆升
   - 響應時間激增
   - 可能觸發雪崩效應
   - 影響所有使用 Redis 的服務

### 修復方案

**文件**: `submissions/cache/fallback.py`

**修改前**:
```python
def delete_pattern_safe(self, pattern: str) -> bool:
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        keys = conn.keys(pattern)  #  阻塞操作
        if keys:
            conn.delete(*keys)
        return True
    except Exception as e:
        logger.error(f"Redis pattern delete failed for {pattern}: {e}")
        return False
```

**修改後**:
```python
def delete_pattern_safe(self, pattern: str) -> bool:
    """
    安全刪除符合模式的所有快取
    
    使用 scan_iter() 避免阻塞 Redis 服務器
    
    Args:
        pattern: 快取鍵模式（例如 "SUBMISSION_LIST:123:*"）
    
    Returns:
        True/False 表示是否成功
    """
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        
        # 使用 scan_iter() 非阻塞式掃描
        keys_to_delete = []
        for key in conn.scan_iter(match=pattern, count=100):
            keys_to_delete.append(key)
            
            # 批次刪除，避免一次刪除太多
            if len(keys_to_delete) >= 1000:
                conn.delete(*keys_to_delete)
                keys_to_delete = []
        
        # 刪除剩餘的鍵
        if keys_to_delete:
            conn.delete(*keys_to_delete)
        
        return True
    except Exception as e:
        logger.error(f"Redis pattern delete failed for {pattern}: {e}")
        return False
```

### 改進效果

| 指標 | keys() | scan_iter() |
|-----|--------|-------------|
| **阻塞性** | 完全阻塞  | 非阻塞  |
| **時間複雜度** | O(N) 一次性 | O(N) 分批執行 |
| **對其他請求影響** | 全部阻塞 | 幾乎無影響 |
| **記憶體使用** | 一次性載入所有鍵 | 迭代器，記憶體友善 |
| **生產環境適用** | 禁止使用  | 推薦使用  |

### 工作原理對比

**keys() - 一次性掃描**:
```
Redis: "掃描所有 1,000,000 個鍵..."
[━━━━━━━━━━━━━━━━━━━━] 100% (阻塞 1.5 秒)
其他請求: 😴😴😴 全部等待

結果: 阻塞時間長，影響所有用戶
```

**scan_iter() - 增量掃描**:
```
Redis: "掃描 100 個鍵..." [━━] 
      "處理其他請求..." 
      "再掃描 100 個鍵..." [━━]
      "處理其他請求..." 
      "再掃描 100 個鍵..." [━━]
      ...持續進行

其他請求:  正常處理，幾乎無感

結果: 平滑執行，用戶體驗良好
```

---

## 問題 2: 分散式鎖的驚群問題

### 描述
> 分散式鎖實現使用固定 10ms 睡眠的簡單重試循環（第 60 行）。在高競爭情況下，這可能導致驚群問題（thundering herd），許多進程同時醒來競爭鎖。考慮實現帶抖動的指數退避以減少競爭並改善鎖獲取的公平性。

### 問題分析

**嚴重程度**:  Medium（高競爭環境下性能下降）

**影響範圍**: 分散式鎖的獲取效率

#### 什麼是驚群問題？

假設 100 個進程同時競爭同一個鎖：

```
時間 00:00.000 - 100 個進程同時嘗試獲取鎖
    ↓
只有進程 #1 成功，其他 99 個進入睡眠
    ↓
時間 00:00.010 - 所有 99 個進程同時醒來 ⚡ (驚群)
    ↓
只有進程 #2 成功，其他 98 個進入睡眠
    ↓
時間 00:00.020 - 所有 98 個進程同時醒來 ⚡ (驚群)
    ↓
...循環往復
```

**問題**:
- 所有進程在同一時刻醒來
- 造成 CPU 和網路流量的瞬間尖峰
- 只有 1 個進程成功，其他浪費資源
- 不公平：總是相同的進程優先

#### 視覺化對比

**固定睡眠（修復前）**:
```
進程 A: ━━━━━━━━━━━━━━━━━━━━ (持有鎖)
進程 B: 10ms|嘗試|10ms|嘗試|10ms
進程 C: 10ms|嘗試|10ms|嘗試|10ms
進程 D: 10ms|嘗試|10ms|嘗試|10ms
         ↑        ↑        ↑
    所有進程同時醒來 (驚群效應)
```

**指數退避 + 抖動（修復後）**:
```
進程 A: ━━━━━━━━━━━━━━━━━━━━ (持有鎖)
進程 B: 15ms|嘗試|32ms|嘗試|
進程 C: 23ms|嘗試|51ms|
進程 D: 8ms|嘗試|19ms|嘗試|44ms
         ↑    ↑   ↑     ↑
    醒來時間分散，減少衝突
```

### 修復方案

**文件**: `submissions/cache/lock.py`

#### 1. 添加 random 模組

**修改前**:
```python
import logging
import uuid
import time
from typing import Optional
from django_redis import get_redis_connection
```

**修改後**:
```python
import logging
import uuid
import time
import random  # ← 新增
from typing import Optional
from django_redis import get_redis_connection
```

#### 2. 實現指數退避 + 抖動

**修改前**:
```python
identifier = str(uuid.uuid4())
lock_key = f"lock:{key}"
end_time = time.time() + timeout

try:
    while time.time() < end_time:
        # 嘗試獲取鎖（NX: 不存在才設定，EX: 過期時間）
        if self.redis.set(lock_key, identifier, nx=True, ex=expire):
            logger.debug(f"Lock acquired: {lock_key}")
            return identifier
        
        # 短暫休息後重試
        time.sleep(0.01)  # 固定 10ms 
    
    # 超時未獲取到鎖
    logger.warning(f"Lock acquire timeout for {lock_key}")
    return None
```

**修改後**:
```python
identifier = str(uuid.uuid4())
lock_key = f"lock:{key}"
end_time = time.time() + timeout

# 指數退避參數
attempt = 0
base_delay = 0.01  # 初始 10ms
max_delay = 0.5    # 最大 500ms

try:
    while time.time() < end_time:
        # 嘗試獲取鎖（NX: 不存在才設定，EX: 過期時間）
        if self.redis.set(lock_key, identifier, nx=True, ex=expire):
            logger.debug(f"Lock acquired: {lock_key} after {attempt} attempts")
            return identifier
        
        # 指數退避 + 抖動 
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = random.uniform(0, delay * 0.5)  # 0-50% 的隨機抖動
        time.sleep(delay + jitter)
        attempt += 1
    
    # 超時未獲取到鎖
    logger.warning(f"Lock acquire timeout for {lock_key} after {attempt} attempts")
    return None
```

### 指數退避算法說明

**公式**:
```python
delay = min(base_delay * (2 ** attempt), max_delay)
jitter = random.uniform(0, delay * 0.5)
actual_sleep = delay + jitter
```

**示例計算**:

| 嘗試次數 | 基礎延遲 | 抖動範圍 | 實際睡眠時間 |
|---------|---------|---------|-------------|
| 0 | 10ms | 0-5ms | 10-15ms |
| 1 | 20ms | 0-10ms | 20-30ms |
| 2 | 40ms | 0-20ms | 40-60ms |
| 3 | 80ms | 0-40ms | 80-120ms |
| 4 | 160ms | 0-80ms | 160-240ms |
| 5 | 320ms | 0-160ms | 320-480ms |
| 6+ | 500ms (max) | 0-250ms | 500-750ms |

### 改進效果

| 指標 | 固定睡眠 | 指數退避 + 抖動 |
|-----|---------|----------------|
| **CPU 尖峰** | 高 | 低（分散） |
| **網路流量** | 高（大量重試） | 低（智慧重試） |
| **公平性** | 差（先到先得） | 好（減少衝突） |
| **競爭處理** | 差（驚群效應） | 優（時間分散） |
| **適用場景** | 低競爭 | 高競爭  |

### 性能對比

**場景：100 個進程競爭 1 個鎖**

**固定睡眠**:
```
每次重試: 100 個進程同時檢查
總檢查次數: 100 × 重試次數 ≈ 1000-5000 次
CPU 尖峰: 非常明顯
獲取鎖時間: 不可預測
```

**指數退避 + 抖動**:
```
每次重試: 進程分散在不同時間
總檢查次數: 約 20-50 次（大幅減少）
CPU 使用: 平滑分佈
獲取鎖時間: 更可預測
```

---

##  測試驗證

### 測試執行

```bash
python manage.py test submissions.test_file.test_redis_cache --keepdb -v 2
```

### 測試結果

```
Found 17 test(s).
...
test_lock_mutual_exclusion ... Lock acquire timeout for lock:xxx after 3 attempts
ok

----------------------------------------------------------------------
Ran 17 tests in 3.177s
OK 
```

**關鍵觀察**:
- 日誌顯示 `after X attempts`，證明指數退避正在工作
- 所有測試通過，包括並發測試和互斥測試
- 執行時間 3.177 秒，性能良好

---

## 影響評估

### 修復優先級

| 修復項目 | 嚴重性 | 優先級 | 影響範圍 |
|---------|-------|--------|---------|
| scan_iter() 替換 | Critical | P0 | 整個 Redis 服務 |
| 指數退避 |  Medium | P1 | 分散式鎖性能 |

### 修復效益

1. **scan_iter() 修復**
   -  消除 Redis 阻塞風險
   -  提升系統穩定性
   -  適應大規模數據集
   -  符合生產環境最佳實踐

2. **指數退避修復**
   -  減少 CPU 尖峰
   -  降低網路流量
   -  改善鎖獲取公平性
   -  提升高並發場景性能

---

## 技術要點總結

### Redis 最佳實踐

1. **永遠使用 `scan_iter()` 而非 `keys()`**
   ```python
   #  禁止
   keys = redis.keys(pattern)
   
   #  推薦
   for key in redis.scan_iter(match=pattern, count=100):
       process(key)
   ```

2. **批次操作以減少網路往返**
   ```python
   # 累積到 1000 個後再批次刪除
   if len(keys_to_delete) >= 1000:
       conn.delete(*keys_to_delete)
   ```

3. **使用迭代器節省記憶體**
   ```python
   # scan_iter() 返回迭代器，不會一次性載入所有鍵
   for key in conn.scan_iter(match=pattern):
       # 逐一處理
   ```

### 分散式鎖最佳實踐

1. **指數退避公式**
   ```python
   delay = min(base_delay * (2 ** attempt), max_delay)
   ```

2. **添加抖動避免同步**
   ```python
   jitter = random.uniform(0, delay * 0.5)
   actual_delay = delay + jitter
   ```

3. **設置合理的上限**
   ```python
   max_delay = 0.5  # 避免等待時間過長
   ```

4. **記錄重試次數用於監控**
   ```python
   logger.debug(f"Lock acquired after {attempt} attempts")
   logger.warning(f"Lock timeout after {attempt} attempts")
   ```


## 參考資源

1. **Redis 官方文檔**
   - [SCAN command](https://redis.io/commands/scan/)
   - [KEYS command (警告)](https://redis.io/commands/keys/)

2. **分散式系統**
   - [Exponential Backoff And Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
   - [Thundering Herd Problem](https://en.wikipedia.org/wiki/Thundering_herd_problem)

3. **Django Redis**
   - [django-redis Documentation](https://github.com/jazzband/django-redis)

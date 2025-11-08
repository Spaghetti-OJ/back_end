# Submissions 快取系統使用指南

## 概述

已實作完整的 Redis 快取系統，包含以下核心功能：

- **布隆過濾器**（防止快取穿透）
- **分散式鎖**（防止快取擊穿）
- **超時降級**（防止 Redis 阻塞）
- **記憶體管理**（LRU 淘汰策略）
- **監控系統**（命中率和記憶體使用）
- **自動失效**（Django signals）

---

## 快速開始

### 1. 啟動 Redis

使用 Docker Compose：

```bash
cd back_end
docker-compose -f docker-compose.redis.yml up -d
docker-compose -f docker-compose.redis.yml down -v (關掉)
```

或手動啟動 Redis：

```bash
redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

### 2. 確認 Redis 連線

```bash
python manage.py check
```

### 3. 查看快取統計

```bash
# 查看快取命中率
python manage.py cache_stats

# 監控 Redis 記憶體使用
python manage.py monitor_redis_memory
```

---

## 已實作的快取類型

| 快取類型 | TTL | 用途 | 安全機制 |
|---------|-----|------|---------|
| 提交列表 | 30秒 | 用戶查看自己的提交記錄 | 超時降級 |
| 用戶統計 | 5分鐘 | 個人頁面統計資料 | 分散式鎖 + 超時降級 |
| 提交詳情 | 2分鐘 | 查看單個提交的詳細資訊 | 布隆過濾器 + 超時降級 |
| 用戶高分 | 10分鐘 | 用戶在特定題目的最高分 | 超時降級 |
| 提交權限 | 1分鐘 | 檢查用戶對提交的權限 | 超時降級 |
| 排行榜 | 5分鐘 | 全域或課程排行榜 | 分散式鎖 + 超時降級 |

---
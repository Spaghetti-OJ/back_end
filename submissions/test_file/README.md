# Sandbox 整合測試工具

這個目錄包含用於測試 Backend 與 Sandbox 判題系統整合的測試腳本。

## 文件說明

### 1. `get_test_token.py`
創建測試用戶並獲取 JWT Token。

**使用方式:**
```bash
cd /Users/keliangyun/Desktop/software_engineering/back_end
python submissions/test_file/get_test_token.py
```

**功能:**
- 創建或獲取測試用戶 `test_sandbox`
- 生成 JWT Access Token 和 Refresh Token
- 顯示用戶資訊和使用方式

---

### 2. `create_test_problem.py`
創建測試用的 Problem、Subtask 和 Test Case。

**使用方式:**
```bash
cd /Users/keliangyun/Desktop/software_engineering/back_end
python submissions/test_file/create_test_problem.py
```

**功能:**
- 創建 Problem ID 1 (A + B Problem)
- 創建 Subtask 1 (時間限制 1s, 記憶體限制 256MB)
- 創建 Test Case 1 (輸入: "1 2\n", 輸出: "3\n")

**注意:** 
- 需要資料庫中至少有一個用戶
- Problem 需要關聯到 Course (目前會失敗，需要先創建 Course)

---

### 3. `test_sandbox_celery.py`
測試 Sandbox API 連通性、Celery 任務發現和執行。

**使用方式:**
```bash
cd /Users/keliangyun/Desktop/software_engineering/back_end
python submissions/test_file/test_sandbox_celery.py
```

**測試項目:**
1. Sandbox API 連通性測試
2. Sandbox Client 函數測試 (可選)
3. Celery 任務發現測試
4. Celery 任務執行測試 (可選)

**前置條件:**
- Redis 必須運行中
- Celery Worker 必須運行中 (用於測試 4)

---

### 4. `test_sandbox_integration.py`
完整的端到端整合測試，測試從提交到判題的完整流程。

**使用方式:**
```bash
cd /Users/keliangyun/Desktop/software_engineering/back_end
python submissions/test_file/test_sandbox_integration.py
```

**測試流程:**
1. 測試 Sandbox API 連通性
2. 使用 Token 創建提交
3. 上傳程式碼並觸發 Celery 任務
4. 查詢提交狀態
5. (可選) 測試重新判題功能

**前置條件:**
- Redis 運行中
- Celery Worker 運行中
- Django Server 運行中
- 有有效的 JWT Token
- 資料庫中有測試用的 Problem

---

## 完整測試流程

### 步驟 1: 啟動必要的服務

```bash
# 終端 1: 啟動 Redis (使用 Docker)
cd /Users/keliangyun/Desktop/software_engineering/back_end
docker-compose -f docker-compose.redis.yml up -d

# 終端 2: 啟動 Celery Worker
cd /Users/keliangyun/Desktop/software_engineering/back_end
celery -A back_end worker -l info

# 終端 3: 啟動 Django Server
cd /Users/keliangyun/Desktop/software_engineering/back_end
python manage.py runserver
```

### 步驟 2: 獲取測試 Token

```bash
# 終端 4: 執行測試腳本
cd /Users/keliangyun/Desktop/software_engineering/back_end
python submissions/test_file/get_test_token.py
```

複製顯示的 Access Token。

### 步驟 3: 測試 Celery 和 Sandbox 連通性

```bash
python submissions/test_file/test_sandbox_celery.py
```

確認:
- Sandbox API 可訪問
- Celery 任務已註冊

### 步驟 4: (可選) 創建測試 Problem

```bash
python submissions/test_file/create_test_problem.py
```

**注意:** 如果失敗，需要先在資料庫中創建 Course 和相關資料。

### 步驟 5: 執行完整整合測試

```bash
python submissions/test_file/test_sandbox_integration.py
```

當提示輸入 Token 時，貼上步驟 2 獲取的 Token。

---

## 預期結果

### 成功的測試應該顯示:

1. **Sandbox API 連通性**: 通過
2. **創建提交**: 提交已創建 (顯示 submission_id)
3. **上傳程式碼**: 程式碼已上傳，應已觸發 Celery 任務
4. **Celery Worker 日誌**: 顯示任務被接收並執行
5. **查詢提交狀態**: 狀態從 `-1` (Pending) 變化

### Celery Worker 日誌中應該看到:

```
[INFO/MainProcess] Task submissions.tasks.submit_to_sandbox_task[...] received
[INFO/ForkPoolWorker-1] Submitting to Sandbox: submission_id=..., problem_id=...
[INFO/ForkPoolWorker-1] Sandbox response: {...}
[INFO/ForkPoolWorker-1] Task submissions.tasks.submit_to_sandbox_task[...] succeeded
```

---

## 故障排除

### 問題 1: "Redis connection failed"
**解決方案:**
```bash
# 檢查 Redis 是否運行
docker ps | grep redis

# 如果沒有運行，啟動它
docker-compose -f docker-compose.redis.yml up -d
```

### 問題 2: "Celery 任務沒有被發現"
**解決方案:**
1. 確認 Celery Worker 正在運行
2. 檢查啟動日誌中是否有 `submissions.tasks.submit_to_sandbox_task`
3. 重啟 Celery Worker

### 問題 3: "Problem not found"
**解決方案:**
1. 確認資料庫中有對應的 Problem
2. 或者先創建 Course，再創建 Problem

### 問題 4: "Sandbox API 連接失敗"
**解決方案:**
1. 檢查網絡連接
2. 確認 Sandbox API URL 正確: `http://34.81.90.111:8000`
3. 檢查是否有防火牆限制

---

## 重要提示

1. **環境變數**: 所有腳本都需要在專案根目錄 (`back_end/`) 執行
2. **測試數據**: 測試腳本會創建真實的資料庫記錄
3. **Sandbox API**: 測試會發送真實的 HTTP 請求到 Sandbox
4. **Token 過期**: JWT Token 有效期有限，如果過期需要重新獲取
5. **Celery 日誌**: 務必查看 Celery Worker 終端的日誌以確認任務執行情況

---

## 快速測試命令

```bash
# 一鍵檢查所有組件狀態
cd /Users/keliangyun/Desktop/software_engineering/back_end

# 檢查 Redis
docker ps | grep redis

# 測試 Sandbox 連通性和 Celery
python submissions/test_file/test_sandbox_celery.py

# 獲取 Token 並測試完整流程
python submissions/test_file/get_test_token.py
python back_end/submissions/test_file/test_sandbox_direct.py
```

---

## 相關文檔

- [Sandbox API 文檔](../../docs/submissions.MD)
- [開發者指南](../../docs/developers.MD)
- [快取使用指南](../../cache_usage.md)

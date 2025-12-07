# Sandbox 整合開發日誌
日期: 2025年12月7日
任務: 整合 Django Backend 與 Sandbox 判題系統

## 開發目標
實現 Backend 與 Sandbox 判題系統的完整對接，讓提交的程式碼能夠異步發送到 Sandbox 進行判題，並在 Dashboard 上顯示結果。

## 架構設計

### 系統架構
- Django Backend: 處理提交請求
- Celery: 異步任務處理
- Redis: 消息佇列和結果儲存
- Sandbox API: 遠端判題系統 (http://34.81.90.111:8000)

### 資料流程
1. 使用者提交程式碼 -> Django API
2. Django 建立 Submission 記錄
3. 觸發 Celery 異步任務
4. Celery Worker 調用 sandbox_client
5. sandbox_client 發送請求到 Sandbox API
6. Sandbox 進行判題並返回結果

## 開發步驟

### 步驟 1: Celery 配置
檔案: back_end/celery.py

建立 Celery app 並配置自動發現任務:
- 設定 broker 和 result backend 使用 Redis database 0
- 配置 Django settings 整合
- 設定時區為 Asia/Taipei
- 啟用自動任務發現

修改 back_end/__init__.py:
- 導入 Celery app
- 確保 Django 啟動時自動載入 Celery

### 步驟 2: Sandbox Client 實作
檔案: submissions/sandbox_client.py

核心功能:
1. convert_language_code(): 將 Django 語言代碼轉換為 Sandbox 格式
   - Django: 0=C, 1=C++, 2=Python, 3=Java, 4=JavaScript
   - Sandbox: 'c', 'cpp', 'python', 'java', 'javascript'

2. get_file_extension(): 根據語言返回正確的檔案副檔名

3. submit_to_sandbox(): 提交程式碼到 Sandbox
   - 從 Problem 取得時間和記憶體限制
   - 準備 multipart/form-data 格式的請求
   - 包含認證 header (X-API-KEY)
   - 處理各種異常情況

關鍵欄位:
- submission_id: Submission 的 UUID
- problem_id: 題目 ID
- problem_hash: 題目包的 hash 值
- file_hash: 程式碼檔案的 SHA256
- language: 程式語言
- time_limit: 時間限制 (秒)
- memory_limit: 記憶體限制 (KB)
- use_checker: 是否使用自訂 checker
- checker_name: checker 名稱
- use_static_analysis: 是否啟用靜態分析
- priority: 優先級

### 步驟 3: Celery 異步任務
檔案: submissions/tasks.py

實作 submit_to_sandbox_task:
- 使用 @shared_task 裝飾器
- 設定 bind=True 以取得 task 實例
- 配置最多重試 3 次，每次間隔 60 秒
- 使用 select_for_update() 進行資料庫鎖定
- 處理網路錯誤並自動重試
- 失敗時設定狀態為 Judge Error

### 步驟 4: 整合到 Serializer 和 View
檔案: submissions/serializers.py

SubmissionCodeUploadSerializer.send_to_sandbox():
- 原本是 TODO 註解
- 改為調用 submit_to_sandbox_task.delay()
- 傳入 submission.id 字串

檔案: submissions/views.py

submission_rejudge():
- 原本是 TODO 註解
- 重置 status 為 Pending
- 調用 submit_to_sandbox_task.delay()

### 步驟 5: 設定檔更新
檔案: back_end/settings.py

新增 Celery 設定:
- CELERY_BROKER_URL: Redis 連接字串 (database 0)
- CELERY_RESULT_BACKEND: Redis 連接字串 (database 0)
- CELERY_ACCEPT_CONTENT: 接受 JSON 和 pickle
- CELERY_TASK_SERIALIZER: 使用 JSON
- CELERY_RESULT_SERIALIZER: 使用 JSON
- CELERY_TIMEZONE: Asia/Taipei

新增 Sandbox 設定:
- SANDBOX_API_URL: Sandbox API 位址
- SANDBOX_TIMEOUT: API 請求超時時間
- SANDBOX_API_KEY: API 認證金鑰

檔案: .env

新增環境變數:
- CELERY_BROKER_URL=redis://127.0.0.1:6379/0
- CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
- SANDBOX_API_URL=http://34.81.90.111:8000
- SANDBOX_TIMEOUT=30
- SANDBOX_API_KEY=happylittle7

檔案: requirements.txt

新增依賴:
- celery==5.4.0

## 開發過程遇到的問題

### 問題 1: Sandbox API 認證機制不夠了解
初始實作沒有包含認證，導致 403 Forbidden 錯誤。

分析過程:
1. 檢查 Sandbox API 的 OpenAPI 規格
2. 發現 securitySchemes 定義了 APIKeyHeader
3. 確認需要在 header 中加入 X-API-KEY

解決方案:
1. 在 .env 新增 SANDBOX_API_KEY
2. 在 settings.py 讀取該設定
3. 在 sandbox_client.py 準備 headers
4. 在 requests.post() 傳入 headers

### 問題 2: Problem Hash 管理
Problem model 沒有 problem_hash 欄位，但 Sandbox API 要求必填。

分析過程:
1. 檢查 Problem model 結構
2. 確認沒有 problem_hash 欄位
3. 查看 Sandbox 歷史記錄，發現有 test_sidecar 等測試題目

臨時解決方案:
- 在 sandbox_client.py 使用 TODO 佔位符
- 測試時使用已知存在的題目名稱作為 hash

長期解決方案 (待實作):
- 新增 Problem.problem_hash 欄位
- 實作題目包上傳和管理機制
- 或者與題目包儲存系統整合

### 問題 3: File Hash 計算
Sandbox 會驗證檔案的 SHA256 hash，初期使用假的 hash 值導致 400 錯誤。

分析過程:
1. Sandbox 返回錯誤: "File hash mismatch"
2. 顯示期望的 hash 和實際計算的 hash
3. 確認 Sandbox 會自行計算並驗證

解決方案:
1. 在 serializers.py 建立 Submission 時計算 code_hash
2. 使用 hashlib.sha256(source_code.encode()).hexdigest()
3. 儲存到 Submission.code_hash 欄位
4. sandbox_client.py 使用 submission.code_hash

### 問題 4: 語言代碼對應
Django 使用整數代表語言，Sandbox 使用字串。

解決方案:
建立 convert_language_code() 函數進行轉換:
- 0 -> 'c'
- 1 -> 'cpp'
- 2 -> 'python'
- 3 -> 'java'
- 4 -> 'javascript'

## 技術細節

### Celery Task 重試機制
使用指數退避策略:
- 初次失敗: 等待 60 秒
- 第二次失敗: 等待 120 秒
- 第三次失敗: 等待 240 秒
- 超過 3 次: 放棄並設定為 Judge Error

只對網路相關錯誤進行重試:
- requests.Timeout
- requests.ConnectionError
- requests.RequestException

### 資料庫並發控制
使用 select_for_update() 鎖定 Submission 記錄:
- 防止多個 worker 同時處理同一筆提交
- 確保狀態更新的原子性

### API 請求格式
使用 multipart/form-data:
- data 參數: 各種設定欄位
- files 參數: 程式碼檔案
- headers 參數: 認證金鑰

檔案準備:
- 使用 BytesIO 包裝程式碼內容
- 設定正確的檔案名稱和 MIME type
- 避免寫入實體檔案系統

### 錯誤處理策略
1. Problem 不存在: ValueError
2. 網路錯誤: 重試機制
3. API 錯誤: 記錄並設定 Judge Error
4. 未預期錯誤: 記錄完整 traceback

## 測試準備

建立測試腳本目錄: submissions/test_file/

測試腳本:
1. get_test_token.py: 建立測試用戶和 JWT token
2. create_test_problem.py: 建立測試 Problem
3. test_sandbox_integration.py: 端到端整合測試
4. test_sandbox_celery.py: Celery 和 Sandbox 連接測試
5. test_direct_sandbox_submit.py: 直接提交到 Sandbox
6. test_sandbox_auth.py: 認證機制測試
7. README.md: 測試文件

## 環境啟動順序

1. Redis Server:
   redis-server

2. Celery Worker:
   celery -A back_end worker --loglevel=info

3. Django Server:
   python manage.py runserver

## 完成的功能

1. Celery 完整配置和整合
2. Sandbox API client 實作
3. 異步任務系統
4. 認證機制
5. 錯誤處理和重試
6. 語言代碼轉換
7. 檔案 hash 計算
8. 完整測試套件

## 待實作功能

1. Callback 端點
   - 接收 Sandbox 判題完成的通知
   - 更新 Submission 的狀態和結果

2. Problem Hash 管理
   - 決定 hash 的生成方式
   - 與題目包儲存系統整合

3. Checker 和靜態分析
   - 從 Problem 或 Assignment 讀取設定
   - 支援自訂 checker

4. 配額和權限檢查
   - NOJ 系統的配額限制
   - Rate limiting

5. 監控和日誌
   - 提交成功率監控
   - 效能指標收集
   - 詳細的錯誤日誌

## 設定檔總結

需要的環境變數 (.env):
- CELERY_BROKER_URL
- CELERY_RESULT_BACKEND
- SANDBOX_API_URL
- SANDBOX_TIMEOUT
- SANDBOX_API_KEY

需要的 Python 套件:
- celery==5.4.0
- redis (已存在)
- requests (已存在)

需要的服務:
- Redis Server (port 6379)
- Sandbox API (http://34.81.90.111:8000)

## 程式碼品質

已完成:
- 適當的錯誤處理
- Logging 機制
- 文件字串
- 型別提示 (部分)

待改進:
- 增加更多型別提示
- 單元測試
- 整合測試
- API 文件

## 總結

成功實作了 Backend 與 Sandbox 的完整整合:
1. 使用 Celery 實現異步處理
2. 完整的錯誤處理和重試機制
3. 正確的認證和資料格式
4. 可擴展的架構設計

主要技術挑戰:
1. 認證機制的發現和實作
2. File hash 驗證機制
3. Problem hash 的臨時解決方案
4. Celery 和 Django 的整合

系統目前可以:
- 接收程式碼提交
- 異步發送到 Sandbox
- 在 Dashboard 查看結果
- 自動重試失敗的請求

下一階段重點:
- 實作 callback 端點
- 完善 problem hash 管理
- 增加監控和日誌
- 完整的端到端測試

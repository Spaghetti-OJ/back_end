# Custom Test 測試文件說明

測試 Custom Test (自定義測試) 功能的測試套件。

## 測試文件

### 1. `test_custom_test.py` - 整合測試腳本
完整的端到端整合測試，測試整個流程。

**功能：**
- 測試 Custom Test API 端點
- 測試 Celery 異步任務
- 測試 Redis 快取機制
- 測試查詢測試結果
- 測試錯誤處理

**執行方式：**
```bash
cd /Users/keliangyun/Desktop/software_engineering/back_end
python submissions/test_file/test_custom_test.py
```

**前置需求：**
- Django 開發伺服器運行中 (`python manage.py runserver`)
- Celery worker 運行中 (`celery -A back_end worker -l info`)
- Redis 運行中 (`redis-server`)
- 資料庫中至少有一個 Problem

### 2. `test_custom_test_unit.py` - 單元測試
使用 pytest 框架的單元測試，測試個別功能。

**測試類別：**
- `TestCustomTestAPI` - API 端點測試
- `TestSandboxClient` - Sandbox client 函數測試
- `TestCeleryTasks` - Celery 任務測試
- `TestValidation` - 驗證邏輯測試
- `TestCustomTestIntegration` - 整合測試（需要真實服務）

**執行方式：**
```bash
# 執行所有測試
pytest back_end/submissions/test_file/test_custom_test_unit.py -v

# 執行特定測試類別
pytest back_end/submissions/test_file/test_custom_test_unit.py::TestCustomTestAPI -v

# 執行特定測試
pytest back_end/submissions/test_file/test_custom_test_unit.py::TestCustomTestAPI::test_submit_custom_test_success -v

# 顯示詳細輸出
pytest back_end/submissions/test_file/test_custom_test_unit.py -v -s

# 產生覆蓋率報告
pytest back_end/submissions/test_file/test_custom_test_unit.py --cov=submissions --cov-report=html
```

**前置需求：**
- 安裝 pytest: `pip install pytest pytest-django`
- 配置 pytest.ini（已在專案根目錄配置）

## 測試場景

### API 測試
1. 成功提交自定義測試
2. 缺少必要欄位 (source_code)
3. 無效的語言類型
4. 題目不存在
5. 未認證的請求
6. 空的 stdin
7. 長程式碼提交

### 查詢測試
1. 查詢不存在的測試結果
2. 查詢成功的測試結果

### Sandbox Client 測試
1. 語言代碼轉換
2. 檔案副檔名取得
3. 提交到 Sandbox

### Celery 任務測試
1. 異步任務執行
2. Redis 快取更新
3. 錯誤處理和重試

## 快速開始

### 1. 準備環境
```bash
# 啟動 Redis
redis-server

# 啟動 Django 開發伺服器（終端機 1）
cd /Users/keliangyun/Desktop/software_engineering/back_end
python manage.py runserver

# 啟動 Celery worker（終端機 2）
cd /Users/keliangyun/Desktop/software_engineering/back_end
celery -A back_end worker -l info
```

### 2. 執行測試

**方式 A：執行整合測試腳本（推薦新手）**
```bash
python submissions/test_file/test_custom_test.py
```

**方式 B：執行單元測試（推薦開發時）**
```bash
pytest submissions/test_file/test_custom_test_unit.py -v
```

## 測試結果範例

### 成功的測試輸出
```
╔══════════════════════════════════════════════════════════════════╗
║              Custom Test (自定義測試) 功能測試                  ║
║        測試 Backend → Celery → Redis → Sandbox 整合            ║
╚══════════════════════════════════════════════════════════════════╝

======================================================================
  環境準備
======================================================================

1. 檢查用戶...
使用現有用戶: test_custom_test

2. 檢查題目...
找到題目: Test Problem (ID: 1)

3. 檢查 Backend 服務...
Backend 服務運行中 (狀態碼: 200)

4. 檢查 Sandbox API...
Sandbox API 可訪問

======================================================================
  測試 1: 提交 Custom Test
======================================================================

提交資料:
  - Problem ID: 1
  - Language: Python (2)
  - Stdin: '3 5'
  - Code: 123 字元

回應狀態: 202
提交成功

回應內容:
{
  "data": {
    "test_id": "selftest-abc123",
    "submission_id": "selftest-abc123",
    "status": "pending"
  },
  "message": "自定義測試已接收"
}

測試資訊:
  - Test ID: selftest-abc123
  - Submission ID: selftest-abc123
  - Status: pending
```

## 常見問題

### Q1: 測試提交後狀態一直是 pending？
**A:** 檢查 Celery worker 是否正常運行：
```bash
celery -A back_end worker -l info
```

### Q2: Redis 連接失敗？
**A:** 確認 Redis 是否運行並監聽正確的端口：
```bash
redis-cli ping
# 應該回傳: PONG
```

### Q3: Sandbox API 無法連接？
**A:** 檢查網路連接和 Sandbox API URL：
```python
# 在 settings.py 檢查
SANDBOX_API_URL = 'http://34.81.90.111:8000'
```

### Q4: 測試失敗但看不到錯誤訊息？
**A:** 使用詳細模式執行：
```bash
pytest submissions/test_file/test_custom_test_unit.py -v -s --tb=long
```

## Mock 測試 vs 整合測試

### Mock 測試（單元測試）
- 快速執行
- 不需要外部服務
- 適合開發時的快速反饋
- 無法測試真實的整合問題

### 整合測試
- 測試真實的服務互動
- 能發現整合問題
- 執行較慢
- 需要所有服務都運行

**建議：**
- 開發時主要使用單元測試
- 上線前執行完整的整合測試
- CI/CD 同時執行兩種測試

## 測試覆蓋率

執行以下命令產生覆蓋率報告：
```bash
pytest submissions/test_file/test_custom_test_unit.py \
  --cov=submissions.views \
  --cov=submissions.tasks \
  --cov=submissions.sandbox_client \
  --cov-report=html \
  --cov-report=term

# 查看 HTML 報告
open htmlcov/index.html
```

## 持續整合

在 CI/CD pipeline 中加入測試：
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:latest
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-django pytest-cov
      
      - name: Run tests
        run: |
          pytest submissions/test_file/test_custom_test_unit.py -v --cov
```

## 相關文件

- [Custom Test API 文檔](../docs/custom_test.MD)
- [Submissions API 文檔](../docs/submissions.MD)
- [Sandbox Integration 文檔](../docs/sandbox_integration.MD)


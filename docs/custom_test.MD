# Custom Test API 使用說明

## 概述

自定義測試功能允許用戶在不正式提交的情況下測試自己的程式碼，使用自己提供的測試資料。

### 特點
- 不存入資料庫
- 使用 Redis 短期暫存（30 分鐘）
- 速率限制：每分鐘最多 5 次
- 資料大小限制：程式碼 64KB，輸入資料 10KB
- 低優先級處理（不影響正式提交）

---

## API 端點

### 1. 提交自定義測試

**端點**: `POST /submission/{problem_id}/custom-test/`

**權限**: 需要登入

**請求參數**:
```json
{
    "language": 2,                    // 必填: 0=C, 1=C++, 2=Python, 3=Java, 4=JavaScript
    "source_code": "print(input())",  // 必填: 程式碼（最大 64KB）
    "stdin": "Hello World"            // 選填: 標準輸入（最大 10KB）
}
```

**成功回應** (202 Accepted):
```json
{
    "data": {
        "test_id": "selftest-12345678-1234-1234-1234-123456789abc",
        "submission_id": "selftest-12345678-1234-1234-1234-123456789abc",
        "status": "pending"
    },
    "message": "測試已提交，請稍後查詢結果",
    "status": "ok"
}
```

**錯誤回應**:
- `400 Bad Request`: 參數錯誤或資料大小超限
- `403 Forbidden`: 帳號已停用
- `404 Not Found`: 題目不存在
- `429 Too Many Requests`: 超過速率限制（每分鐘 5 次）
- `500 Internal Server Error`: 伺服器錯誤

**範例**:
```bash
curl -X POST http://localhost:8000/submission/123/custom-test/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "language": 2,
    "source_code": "a, b = map(int, input().split())\nprint(a + b)",
    "stdin": "1 2"
  }'
```

---

### 2. 查詢測試結果

**端點**: `GET /submission/custom-test/{custom_test_id}/result/`

**權限**: 需要登入（只能查詢自己的測試）

**成功回應** (200 OK):
```json
{
    "data": {
        "test_id": "selftest-12345678-1234-1234-1234-123456789abc",
        "problem_id": 123,
        "language": 2,
        "status": "AC",
        "stdout": "3\n",
        "stderr": "",
        "time": 0.05,
        "memory": 1024,
        "message": "Score: 100",
        "compile_info": {
            "status": "OK",
            "message": "Python interpreted"
        },
        "created_at": "2025-12-13T10:30:00Z"
    },
    "message": "here you are, bro",
    "status": "ok"
}
```

**錯誤回應**:
- `403 Forbidden`: 帳號已停用
- `404 Not Found`: 測試不存在或已過期（30 分鐘）
- `503 Service Unavailable`: Redis 或 Sandbox 服務不可用
- `500 Internal Server Error`: 伺服器錯誤

**範例**:
```bash
curl -X GET http://localhost:8000/submission/custom-test/selftest-12345678-1234-1234-1234-123456789abc/result/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 前端整合範例

### React/JavaScript 範例

```javascript
// 提交測試
async function runCustomTest(problemId, code, stdin, language) {
  try {
    const response = await fetch(`/submission/${problemId}/custom-test/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        language: language,
        source_code: code,
        stdin: stdin
      })
    });

    if (response.status === 429) {
      alert('提交過於頻繁，請稍後再試');
      return;
    }

    if (!response.ok) {
      const error = await response.json();
      alert(`錯誤: ${error.message}`);
      return;
    }

    const result = await response.json();
    const testId = result.data.test_id;

    // 儲存到 localStorage（刷新後可恢復）
    localStorage.setItem('current_test_id', testId);

    // 開始輪詢結果
    pollTestResult(testId);
  } catch (error) {
    console.error('提交失敗:', error);
  }
}

// 輪詢結果
async function pollTestResult(testId) {
  let attempts = 0;
  const maxAttempts = 60; // 最多輪詢 60 次（60 秒）

  const interval = setInterval(async () => {
    attempts++;

    try {
      const response = await fetch(`/submission/custom-test/${testId}/result/`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.status === 404) {
        clearInterval(interval);
        alert('測試結果已過期');
        localStorage.removeItem('current_test_id');
        return;
      }

      if (!response.ok) {
        throw new Error('查詢失敗');
      }

      const result = await response.json();
      const data = result.data;

      // 顯示進行中的狀態
      updateStatus(data.status);

      // 如果完成或錯誤，停止輪詢
      if (['AC', 'WA', 'TLE', 'MLE', 'RE', 'CE', 'completed', 'error'].includes(data.status)) {
        clearInterval(interval);
        displayResult(data);
        localStorage.removeItem('current_test_id');
      }

      // 超時保護
      if (attempts >= maxAttempts) {
        clearInterval(interval);
        alert('查詢超時，請手動刷新查看結果');
      }
    } catch (error) {
      console.error('查詢錯誤:', error);
      clearInterval(interval);
    }
  }, 1000); // 每秒查詢一次
}

// 顯示結果
function displayResult(data) {
  console.log('測試完成!');
  console.log('狀態:', data.status);
  console.log('輸出:', data.stdout);
  console.log('錯誤:', data.stderr);
  console.log('時間:', data.time, '秒');
  console.log('記憶體:', data.memory, 'KB');
  
  // 更新 UI...
}

// 頁面載入時恢復測試
window.addEventListener('load', () => {
  const testId = localStorage.getItem('current_test_id');
  if (testId) {
    pollTestResult(testId);
  }
});
```

---

## 狀態碼說明

### Sandbox 狀態
- `queued`: 排隊中
- `running`: 執行中
- `AC`: Accepted（答案正確）
- `WA`: Wrong Answer（答案錯誤）
- `TLE`: Time Limit Exceeded（超時）
- `MLE`: Memory Limit Exceeded（超記憶體）
- `RE`: Runtime Error（執行錯誤）
- `CE`: Compilation Error（編譯錯誤）
- `completed`: 完成
- `error`: 錯誤

---

## 注意事項

### 1. 資料保留時間
- Redis 暫存 30 分鐘
- 30 分鐘後測試結果會自動刪除
- 建議前端使用 localStorage 暫存 test_id

### 2. 速率限制
- 每分鐘最多 5 次提交
- 超過限制會返回 429 錯誤
- 計數器每分鐘重置

### 3. 資料大小限制
- 程式碼：最大 64KB
- 輸入資料：最大 10KB
- 超過限制會返回 400 錯誤

### 4. 權限控制
- 必須登入
- 帳號必須啟用
- 只能查詢自己的測試結果

### 5. 優先級
- 自定義測試使用低優先級（priority: -1）
- 不會影響正式提交的判題速度

---

## 錯誤處理建議

### 前端應該處理的錯誤

1. **速率限制 (429)**
   - 顯示友善提示：「提交過於頻繁，請等待 XX 秒」
   - 可以實作倒數計時器

2. **測試過期 (404)**
   - 提示：「測試結果已過期，請重新提交」
   - 清除 localStorage 中的 test_id

3. **網路錯誤**
   - 實作重試機制
   - 顯示「網路錯誤，請檢查連線」

4. **超時保護**
   - 輪詢設定最大次數
   - 提供手動刷新按鈕

---

## Redis 資料結構

### 測試資訊
```
Key: custom_test:{user_id}:{test_id}
Value: JSON
TTL: 1800 秒（30 分鐘）

{
    "test_id": "selftest-uuid",
    "problem_id": 123,
    "language": 2,
    "submission_id": "selftest-uuid",
    "status": "queued",
    "created_at": "2025-12-13T10:30:00Z",
    "stdin": "Hello World",
    "last_updated": "2025-12-13T10:30:05Z"
}
```

### 最近測試列表
```
Key: custom_tests:recent:{user_id}
Type: List
Length: 最多 10 個
TTL: 1800 秒（30 分鐘）

["test_id_1", "test_id_2", ...]
```

### 速率限制
```
Key: custom_test_rate:{user_id}
Value: 計數器
TTL: 60 秒

每次提交 +1，60 秒後自動重置
```

---

## 測試範例

### Python 測試範例

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_jwt_token"

# 1. 提交測試
def submit_test():
    response = requests.post(
        f"{BASE_URL}/submission/123/custom-test/",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "language": 2,
            "source_code": "a, b = map(int, input().split())\nprint(a + b)",
            "stdin": "1 2"
        }
    )
    print(f"Status: {response.status_code}")
    result = response.json()
    test_id = result['data']['test_id']
    print(f"Test ID: {test_id}")
    return test_id

# 2. 查詢結果
def get_result(test_id):
    import time
    
    for i in range(30):  # 最多等 30 秒
        response = requests.get(
            f"{BASE_URL}/submission/custom-test/{test_id}/result/",
            headers={"Authorization": f"Bearer {TOKEN}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            data = result['data']
            print(f"Status: {data['status']}")
            
            if data['status'] in ['AC', 'WA', 'TLE', 'MLE', 'RE', 'CE']:
                print(f"Output: {data['stdout']}")
                print(f"Time: {data['time']}s")
                print(f"Memory: {data['memory']}KB")
                break
        
        time.sleep(1)

# 執行
test_id = submit_test()
get_result(test_id)
```

---

## 維護說明

### Redis 清理
Redis 會自動刪除過期資料，但如果需要手動清理：

```bash
# 連接 Redis
redis-cli -n 2

# 查看所有 custom test 相關的 key
KEYS custom_test:*
KEYS custom_tests:recent:*
KEYS custom_test_rate:*

# 刪除特定用戶的測試
DEL custom_test:1:selftest-uuid
DEL custom_tests:recent:1
DEL custom_test_rate:1
```

### 監控指標
建議監控：
1. 每分鐘提交次數
2. 平均測試完成時間
3. Redis 記憶體使用
4. 速率限制觸發次數
5. 404 錯誤率（測試過期）

---

## 常見問題

**Q: 為什麼不存入資料庫？**
A: 自定義測試是臨時性的，用戶通常只關心當下結果，不需要長期保存。使用 Redis 可以提高效能並減少資料庫負擔。

**Q: 30 分鐘後測試結果會怎樣？**
A: 會自動從 Redis 刪除，無法查詢。但 Sandbox Dashboard 可能還能看到（如果需要除錯）。

**Q: 可以查看別人的測試結果嗎？**
A: 不行，每個測試都綁定用戶 ID，只能查詢自己的測試。

**Q: 速率限制可以調整嗎？**
A: 可以，修改 `views.py` 中的速率限制邏輯即可。

**Q: 如何處理 Sandbox 掛掉的情況？**
A: API 會返回 503 錯誤，前端應該顯示友善提示並建議稍後重試。

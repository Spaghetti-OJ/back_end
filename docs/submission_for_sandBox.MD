# Submission Callback API for Sandbox

本文件說明 Sandbox 判題系統完成判題後，如何將結果回傳給 Backend 的 API 規格。

---

## 目錄

1. [概述](#概述)
2. [認證方式](#認證方式)
3. [正式提交 Callback API](#正式提交-callback-api)
4. [自定義測試 Callback API](#自定義測試-callback-api)
5. [錯誤處理](#錯誤處理)
6. [範例程式碼](#範例程式碼)

---

## 概述

當 Sandbox 完成判題後，應該主動呼叫 Backend 提供的 callback URL，將判題結果以 HTTP POST 的方式回傳。

### Callback URLs

- **正式提交**: `{BACKEND_BASE_URL}/submission/callback/`
- **自定義測試**: `{BACKEND_BASE_URL}/submission/custom-test-callback/`

其中 `BACKEND_BASE_URL` 會在 Backend 發送提交請求時，透過 `callback_url` 欄位提供完整網址。

---

## 認證方式

### API Key 認證

所有 callback 請求必須在 HTTP Header 中包含 API Key：

```http
X-API-KEY: your-sandbox-api-key
```

**注意**：此 API Key 與 Backend 呼叫 Sandbox API 時使用的相同。

---

## 正式提交 Callback API

### Endpoint

```
POST {BACKEND_BASE_URL}/submission/callback/
```

### Request Headers

```http
Content-Type: application/json
X-API-KEY: your-sandbox-api-key
```

### Request Body

```json
{
  "submission_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "score": 100,
  "execution_time": 123,
  "memory_usage": 1024,
  "test_results": [
    {
      "test_case_id": 1,
      "test_case_index": 1,
      "status": "accepted",
      "execution_time": 50,
      "memory_usage": 512,
      "score": 10,
      "max_score": 10,
      "error_message": null
    },
    {
      "test_case_id": 2,
      "test_case_index": 2,
      "status": "wrong_answer",
      "execution_time": 45,
      "memory_usage": 480,
      "score": 0,
      "max_score": 10,
      "error_message": "Expected: 5, Got: 4"
    }
  ]
}
```

### 欄位說明

#### 主要欄位

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `submission_id` | string (UUID) | OK | 提交的唯一識別碼 |
| `status` | string | OK | 整體判題結果狀態 |
| `score` | integer | OK | 總得分 (0-100) |
| `execution_time` | integer | OK | 總執行時間（毫秒） |
| `memory_usage` | integer | OK | 總記憶體使用量（KB） |
| `test_results` | array | OK | 各測試案例的詳細結果 |

#### status 可能的值

| 狀態值 | 說明 | Backend 內部狀態碼 |
|--------|------|-------------------|
| `accepted` | 完全正確 (AC) | '0' |
| `wrong_answer` | 答案錯誤 (WA) | '1' |
| `compile_error` | 編譯錯誤 (CE) | '2' |
| `time_limit_exceeded` | 超過時間限制 (TLE) | '3' |
| `memory_limit_exceeded` | 超過記憶體限制 (MLE) | '4' |
| `runtime_error` | 執行時錯誤 (RE) | '5' |

**注意**: Backend 內部狀態碼僅供參考，Sandbox 只需要發送上述字串狀態值即可。

#### test_results 陣列中的物件

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `test_case_id` | integer | OK | 測試案例的資料庫 ID |
| `test_case_index` | integer | OK | 測試案例編號（顯示用） |
| `status` | string | OK | 該測試案例的判題結果 |
| `execution_time` | integer | error | 該測試案例的執行時間（毫秒） |
| `memory_usage` | integer | error | 該測試案例的記憶體使用量（KB） |
| `score` | integer | OK | 該測試案例得到的分數 |
| `max_score` | integer | OK | 該測試案例的滿分 |
| `error_message` | string | error | 錯誤訊息（如果有的話） |

### Response

#### 成功回應 (200 OK)

```json
{
  "data": {
    "submission_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "message": "Callback processed successfully",
  "status": "ok"
}
```

#### 錯誤回應

**401 Unauthorized** - API Key 錯誤

```json
{
  "data": null,
  "message": "Unauthorized",
  "status": "error"
}
```

**404 Not Found** - Submission 不存在

```json
{
  "data": null,
  "message": "Submission not found",
  "status": "error"
}
```

**400 Bad Request** - 缺少必要欄位

```json
{
  "data": null,
  "message": "Missing submission_id",
  "status": "error"
}
```

---

## 自定義測試 Callback API

### Endpoint

```
POST {BACKEND_BASE_URL}/submission/custom-test-callback/
```

### Request Headers

```http
Content-Type: application/json
X-API-KEY: your-sandbox-api-key
```

### Request Body

```json
{
  "submission_id": "selftest-550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "stdout": "5\n10\n15\n",
  "stderr": "",
  "execution_time": 123,
  "memory_usage": 1024,
  "exit_code": 0
}
```

### 欄位說明

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `submission_id` | string | OK | 自定義測試的唯一識別碼（通常以 `selftest-` 開頭） |
| `status` | string | OK | 測試執行狀態：`completed` 或 `error` |
| `stdout` | string | OK | 程式的標準輸出 |
| `stderr` | string | error | 程式的標準錯誤輸出 |
| `execution_time` | integer | OK | 執行時間（毫秒） |
| `memory_usage` | integer | OK | 記憶體使用量（KB） |
| `exit_code` | integer | OK | 程式退出代碼（0 表示正常） |

### Response

#### 成功回應 (200 OK)

```json
{
  "data": {
    "test_id": "selftest-550e8400-e29b-41d4-a716-446655440000"
  },
  "message": "Custom test callback processed successfully",
  "status": "ok"
}
```

#### 錯誤回應

與正式提交 Callback 類似，可能回傳：
- 401 Unauthorized
- 404 Not Found
- 400 Bad Request

---

## 錯誤處理

### 重試機制建議

如果 Backend 回傳 5xx 錯誤或連線失敗，建議 Sandbox 實作重試機制：

- **重試次數**: 3 次
- **重試間隔**: 指數退避（1秒、2秒、4秒）
- **重試條件**: HTTP 5xx 或網路錯誤

### 超時設定

建議設定 HTTP 請求超時時間為 **30 秒**。

### 日誌記錄

建議 Sandbox 記錄所有 callback 請求的結果，包括：
- 請求時間
- submission_id
- HTTP 狀態碼
- 回應內容
- 錯誤訊息（如果有）

---

## 範例程式碼

### Python 範例

```python
import requests
import json

def send_submission_callback(backend_url, api_key, result_data):
    """
    發送判題結果到 Backend
    
    Args:
        backend_url: Backend callback URL
        api_key: API Key for authentication
        result_data: 判題結果數據
    """
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': api_key
    }
    
    try:
        response = requests.post(
            backend_url,
            json=result_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"OK Callback successful: {response.json()}")
            return True
        else:
            print(f"error Callback failed: {response.status_code} - {response.text}")
            return False
            
    except requests.Timeout:
        print("error Callback timeout")
        return False
    except requests.RequestException as e:
        print(f"error Callback error: {str(e)}")
        return False

# 使用範例
result = {
    "submission_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "accepted",
    "score": 100,
    "execution_time": 123,
    "memory_usage": 1024,
    "test_results": [
        {
            "test_case_id": 1,
            "test_case_index": 1,
            "status": "accepted",
            "execution_time": 50,
            "memory_usage": 512,
            "score": 10,
            "max_score": 10,
            "error_message": None
        }
    ]
}

send_submission_callback(
    backend_url="https://noj-backend-dev.little7.pp.ua/submission/callback/",
    api_key="your-api-key",
    result_data=result
)
```

### cURL 範例

```bash
# 正式提交 Callback
curl -X POST "https://noj-backend-dev.little7.pp.ua/submission/callback/" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key" \
  -d '{
    "submission_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "accepted",
    "score": 100,
    "execution_time": 123,
    "memory_usage": 1024,
    "test_results": [
      {
        "test_case_id": 1,
        "test_case_index": 1,
        "status": "accepted",
        "execution_time": 50,
        "memory_usage": 512,
        "score": 10,
        "max_score": 10,
        "error_message": null
      }
    ]
  }'

# 自定義測試 Callback
curl -X POST "https://noj-backend-dev.little7.pp.ua/submission/custom-test-callback/" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key" \
  -d '{
    "submission_id": "selftest-550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "stdout": "Hello, World!\n",
    "stderr": "",
    "execution_time": 50,
    "memory_usage": 512,
    "exit_code": 0
  }'
```

---

## 流程圖

```
┌──────────────┐                                    ┌──────────────┐
│   Backend    │                                    │   Sandbox    │
└──────┬───────┘                                    └──────┬───────┘
       │                                                   │
       │  1. POST /api/v1/submissions                      │
       │     (含 callback_url)                              │
       ├──────────────────────────────────────────────────>│
       │                                                   │
       │  2. 202 Accepted (已排隊)                          │
       │<──────────────────────────────────────────────────┤
       │                                                   │
       │                                                   │  3. 執行判題
       │                                                   │     (背景處理)
       │                                                   │
       │  4. POST {callback_url}                           │
       │     (判題結果)                                     │
       │<──────────────────────────────────────────────────┤
       │                                                   │
       │  5. 200 OK (已接收)                                │
       ├──────────────────────────────────────────────────>│
       │                                                   │
```

---

## 注意事項

1. **非同步處理**: Callback 是非同步的，Sandbox 完成判題後才會呼叫
2. **冪等性**: Backend 會處理重複的 callback（基於 submission_id）
3. **時效性**: 建議在判題完成後立即發送 callback
4. **安全性**: 務必在 Header 中包含正確的 API Key
5. **錯誤處理**: 實作重試機制確保 callback 成功送達

---
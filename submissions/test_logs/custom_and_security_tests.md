# 自定義測試與安全測試日誌

## 測試套件: CustomTestModelTests
**基礎類別**: HypothesisTestCase  
**目的**: 測試自定義測試案例功能

### 設置
- 使用 UUID 創建唯一測試用戶
- 用戶名: `customuser_{uuid}`
- 電子郵件: `custom_{uuid}@example.com`

### 測試方法

#### test_custom_test_creation
**類型**: 屬性基礎測試  
**策略**: 生成隨機自定義測試數據  
**覆蓋範圍**:
- 問題 ID 驗證 (1-99999)
- 語言類型驗證 (c, cpp, java, python, javascript)
- 源代碼生成 (1-500字符)
- 狀態驗證 (pending, running, completed, error)
- 基本模型創建和字段分配

**Hypothesis 設置**: max_examples=10

#### test_custom_test_with_io_data
**類型**: 屬性基礎測試  
**策略**: 測試輸入輸出數據處理  
**覆蓋範圍**:
- 輸入數據驗證
- 預期輸出驗證
- I/O 數據完整性
- 字段映射正確性

**Hypothesis 設置**: max_examples=10

---

## 測試套件: SecurityTests
**基礎類別**: TestCase  
**目的**: 全面的安全性和邊界情況測試

### 測試方法

#### test_serializer_rejects_null_characters
**類型**: 單元測試  
**覆蓋範圍**:
- 空字符注入防護
- 輸入清理驗證
- 惡意字符過濾

#### test_serializer_sql_injection_prevention
**類型**: 單元測試  
**覆蓋範圍**:
- SQL 注入攻擊防護
- 惡意 SQL 語句檢測
- 數據庫安全驗證
- 測試多種 SQL 注入模式

#### test_serializer_xss_prevention
**類型**: 單元測試  
**覆蓋範圍**:
- 跨站腳本攻擊防護
- HTML/JavaScript 注入防護
- 輸出編碼驗證
- 惡意腳本檢測

#### test_authentication_requirements
**類型**: 單元測試  
**覆蓋範圍**:
- 認證要求驗證
- 未認證用戶拒絕
- 序列化器認證檢查

#### test_inactive_user_rejection
**類型**: 單元測試  
**覆蓋範圍**:
- 非活躍用戶拒絕
- 用戶狀態驗證
- 訪問控制測試

#### test_ip_address_logging
**類型**: 單元測試  
**覆蓋範圍**:
- IP 地址自動記錄到 submission.ip_address 字段
- 用戶代理記錄到 submission.user_agent 字段  
- 安全審計日誌：使用 Python logging 記錄提交活動
- 請求追踪功能：支援 X-Forwarded-For 頭部

**安全審計日誌具體內容**：
```python
# 在序列化器的 create 方法中自動記錄
logger.info(
    f'New submission: user_id={request.user.id}, '
    f'problem_id={validated_data["problem_id"]}, '
    f'ip={validated_data["ip_address"]}'
)
```

**審計數據存儲**：
- `ip_address`: GenericIPAddressField（支援 IPv4/IPv6）
- `user_agent`: CharField（最大 500 字符）
- 日誌級別：INFO，使用 'submission_audit' logger

#### test_rate_limiting_duplicate_prevention
**類型**: 單元測試  
**覆蓋範圍**:
- 速率限制機制
- 重複提交防護
- 濫用防護機制

#### test_serializer_code_size_limits
**類型**: 單元測試  
**覆蓋範圍**:
- 代碼大小限制
- 資源保護機制
- 大型輸入處理

#### test_serializer_handles_various_malicious_inputs
**類型**: 單元測試  
**覆蓋範圍**:
- 各種惡意輸入處理
- 邊界條件測試
- 異常輸入驗證

### 安全重點
- 序列化器測試使用 Mock 請求上下文模擬 HTTP 請求環境
- 用戶代理追踪用於安全日誌記錄
- 輸入驗證防止注入攻擊
- 大小限制防止資源耗盡
- 全面的惡意輸入檢測
- 認證和授權控制
- 審計日誌和監控

### Mock 請求上下文說明
在需要測試序列化器的測試中，我們使用 `unittest.mock.Mock` 來模擬 Django 的 HTTP 請求物件：

```python
# 模擬正常認證用戶的請求
request = Mock()
request.user = self.user
request.META = {'HTTP_USER_AGENT': 'test-agent'}

# 模擬未認證用戶的請求（用於測試認證失敗）
request = Mock()
request.user = None
request.META = {'HTTP_USER_AGENT': 'test-agent'}

# 將 mock 請求傳遞給序列化器
serializer = SubmissionCreateSerializer(data=data, context={'request': request})

# 某些測試還需要模擬 IP 地址獲取
def mock_get_client_ip(req):
    return '127.0.0.1'
serializer.get_client_ip = mock_get_client_ip
```

#### 不使用 Mock 請求的測試：
- **SubmissionModelTests**: 直接測試模型，不需要 HTTP 請求上下文
- **CustomTestModelTests**: 直接測試模型，不需要 HTTP 請求上下文  
- **test_submission_read_serializer**: 只測試讀取序列化，不需要複雜的請求上下文

這樣做的目的：
- **模擬真實環境**: 序列化器在實際應用中會接收 HTTP 請求上下文
- **測試認證邏輯**: 驗證序列化器是否正確處理已認證/未認證用戶
- **安全測試**: 確保安全檢查在測試環境中正常運作
- **IP 追踪**: 模擬客戶端 IP 地址以測試安全日誌功能
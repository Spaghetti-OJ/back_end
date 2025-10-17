# 提交模型測試日誌

## 測試套件: SubmissionModelTests
**基礎類別**: HypothesisTestCase  
**目的**: Submission 模型功能的屬性基礎測試

### 設置
- 為每個測試類創建使用 UUID 的唯一測試用戶
- 用戶名: `modeluser_{uuid}`
- 電子郵件: `model_{uuid}@example.com`

### 測試方法

#### test_submission_creation_with_random_data
**類型**: 屬性基礎測試  
**策略**: 生成隨機提交數據  
**覆蓋範圍**: 
- 問題 ID 驗證 (1-99999)
- 語言類型驗證 (c, cpp, java, python, javascript)
- 源代碼生成 (1-500字符)
- 狀態驗證 (pending, running, completed, error)
- 基本模型創建和字段分配

**Hypothesis 設置**: max_examples=10

#### test_submission_execution_time_property
**類型**: 屬性基礎測試  
**策略**: 測試執行時間值 (0-10000毫秒)  
**覆蓋範圍**:
- 執行時間字段驗證
- 屬性分配驗證
- 範圍邊界測試

**Hypothesis 設置**: max_examples=10

#### test_submission_execution_time_property_with_invalid_time
**類型**: 單元測試  
**覆蓋範圍**:
- 無效執行時間處理 (值 = -1)
- 默認值行為
- 模型約束驗證

#### test_submission_is_judged_property
**類型**: 屬性基礎測試  
**策略**: 測試所有可能的狀態值  
**覆蓋範圍**:
- 基於狀態的判定屬性邏輯
- 'pending' 和 'judging' → is_judged = False
- 所有其他狀態 → is_judged = True

**Hypothesis 設置**: max_examples=10

### 關鍵驗證
- 基於 UUID 的唯一用戶創建防止衝突
- 屬性基礎測試確保強健的覆蓋
- 模型約束和默認值得到適當測試
- 狀態邏輯正確實現
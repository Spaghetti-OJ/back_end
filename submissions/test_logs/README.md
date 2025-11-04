# 提交系統測試文檔

此目錄包含提交應用程序的全面測試日誌，記錄所有測試案例及其覆蓋範圍。

## 測試結構

### SubmissionModelTests
- Submission 模型的屬性基礎測試
- 執行時間屬性驗證
- 基於狀態的判斷邏輯

### SubmissionSerializerTests  
- 全面的序列化器驗證
- 輸入驗證和錯誤處理
- 重複防護邏輯

### CustomTestModelTests
- 自定義測試案例功能
- I/O 數據處理

### SecurityTests
- 認證和授權
- 輸入清理
- 速率限制和濫用防護

## 測試覆蓋範圍

1. **模型屬性**: 執行時間、判定狀態
2. **序列化器驗證**: 數據完整性、字段驗證  
3. **安全性**: XSS、SQL 注入、認證
4. **邊界情況**: 無效輸入、邊界條件

所有測試在適當的地方使用 Hypothesis 進行屬性基礎測試，具有受控的示例生成以提高性能。

## 測試執行

```bash
# 運行所有測試
python -m pytest submissions/tests.py -v

# 運行特定測試類
python -m pytest submissions/tests.py::SubmissionModelTests -v

# 運行特定測試方法
python -m pytest submissions/tests.py::SubmissionModelTests::test_submission_creation_with_random_data -v
```

## 測試性能

- 總測試數：23個
- 執行時間：約2.6秒
- 使用 Hypothesis max_examples=10 來控制性能
- 所有測試通過，具有良好的覆蓋率
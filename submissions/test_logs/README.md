# 提交系統測試文檔

此目錄包含提交系統的全面測試日誌，記錄所有測試案例及其覆蓋範圍。

## 測試框架決策

經過討論，我們決定使用 **Django 測試框架** 而不是 pytest，原因如下：

1. **更好的 Django 整合**: Django TestCase 提供完整的 ORM、中間件、和視圖測試支持
2. **自動資料庫管理**: 每個測試自動創建和清理測試資料庫
3. **內建 fixtures**: Django fixtures 與 TestCase 完美整合
4. **更簡單的配置**: 無需額外配置，直接使用 `python manage.py test`

### Hypothesis 整合

我們將 Hypothesis property-based testing 與 Django TestCase 結合使用：

```python
from hypothesis import given
from django.test import TestCase

class MyModelTests(TestCase):
    @given(text=text(min_size=1))
    def test_model_with_random_data(self, text):
        # Property-based test with Django TestCase
        pass
```

## 目前測試結構

### Editorial API 測試 (15個測試)
- 題解 CRUD 操作測試
- 權限驗證 (老師和 TA)
- 點讚功能測試
- 3個 Hypothesis 屬性測試

### 權限系統測試 (8個測試)  
- 老師和 TA 權限驗證
- 課程成員關係檢查
- 權限拒絕測試
- 2個 Hypothesis 權限測試

### 模型測試 (12個測試)
- Submission 和 Editorial 模型
- 關聯關係驗證
- 數據完整性檢查
- 8個 Hypothesis 模型測試

### 序列化器測試 (12個測試)
- 數據驗證和序列化
- 錯誤處理和邊界條件
- API 響應格式檢查
- 6個 Hypothesis 序列化器測試

## 測試覆蓋範圍

1. **API 端點**: 完整的 Editorial CRUD + 點讚 API
2. **權限控制**: 老師和 TA 角色驗證
3. **數據驗證**: 模型和序列化器完整性
4. **安全性**: 認證、授權、輸入驗證
5. **邊界情況**: Hypothesis 自動生成邊界測試案例

## 測試執行

```bash
# 運行所有提交系統測試
python manage.py test submissions

# 運行特定測試文件
python manage.py test submissions.test_file.test_editorial_api

# 運行特定測試類
python manage.py test submissions.test_file.test_editorial_api.EditorialAPITests

# 運行特定測試方法
python manage.py test submissions.test_file.test_editorial_api.EditorialAPITests.test_create_editorial_success

# 詳細輸出
python manage.py test submissions -v 2
```

## 測試性能統計

- **總測試數**: 47個測試
- **Hypothesis 測試**: 19個 (Property-based testing)
- **傳統測試**: 28個 (Unit + Integration)
- **通過率**: 100%
- **執行時間**: 約3-6秒 (完整測試套件)
- **Hypothesis 設定**: max_examples=10 來控制性能

## 測試日誌文件

- `test-log-2025-10-24.md`: 詳細的測試問題發現與解決過程記錄
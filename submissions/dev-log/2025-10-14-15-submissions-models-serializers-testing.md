# Submissions 系統開發日誌

## 專案概述
- **開發時間**: 2025年10月14日 - 2025年10月15日
- **目標**: 基於 schema.sql 完成 Django submissions 系統的 models 和 serializers，並建立完整的 Hypothesis property-based testing

## 開發階段記錄

### 第一階段：模型與序列化器開發 (2025-10-14)

#### 1.1 需求確認
**討論內容**: 組長要求根據 `schema.sql` 建立完整的 submissions 系統

**任務分解**:
- 創建 9 個 Django 模型類
- 建立對應的 DRF 序列化器
- 確保與 PostgreSQL schema 完全一致

#### 1.2 模型實現
**實現的模型**:
1. `Submission` - 核心提交模型
2. `SubmissionResult` - 測試案例結果
3. `UserProblemStats` - 用戶題目統計(作業層級)
4. `UserProblemSolveStatus` - 用戶解題狀態(全域層級)
5. `UserProblemQuota` - 用戶題目配額
6. `CustomTest` - 自定義測試
7. `CodeDraft` - 程式碼草稿
8. `Editorial` - 題解
9. `EditorialLike` - 題解點讚

**關鍵設計決策**:
- 使用 UUID 作為主鍵（符合 schema.sql）
- 遵循 Django 命名慣例：模型類名單數，資料表名複數
- 完整的索引和約束設定

### 第二階段：Git 分支管理問題 (2025-10-14)

#### 2.1 問題發現
**現象**: Django migration 失敗，提示 `problems.Tag` 模型不存在
```bash
django.db.utils.ProgrammingError: relation "problems_tag" does not exist
```

#### 2.2 問題分析
**根本原因**: 
- 發現是 `assignments` app 中引用了錯誤的模型名稱
- `problems.Tag` vs `problems.Tags` 命名不一致
- 不是我們 submissions 代碼的問題

#### 2.3 解決方案
**採取行動**:
叫負責的人跟主管處理

#### 2.4 驗證結果
成功建立乾淨的開發分支
Submissions 代碼通過所有檢查

### 第三階段：測試框架建立 (2025-10-14)

#### 3.1 Hypothesis 測試設計
**選擇理由**: Property-based testing 能夠：
- 生成大量隨機測試案例
- 發現邊界情況和異常輸入
- 提供比傳統單元測試更全面的覆蓋率

**測試策略**:
```python
# 使用 Hypothesis strategies 生成測試數據
@given(
    problem_id=st.integers(min_value=1, max_value=99999),
    language_type=st.sampled_from(['c', 'cpp', 'java', 'python', 'javascript']),
    source_code=st.text(min_size=1, max_size=1000)
)
```


### 第四階段：命名規範修正 (2025-10-14)

#### 4.1 問題發現
**發現問題**: 
- 模型類名 `Submissions`（複數）vs schema.sql 期望的 `submissions`（表名）
- Django 慣例：類名單數，表名複數

#### 4.2 問題分析
**錯誤原因**: 
- 之前的 migration 錯誤地將 `Submission` 重命名為 `Submissions`
- 導致類名和表名都是複數形式

#### 4.3 解決方案
**修正步驟**:
1. 回滾錯誤的 migration
2. 刪除錯誤的 migration 文件
3. 修正所有 ForeignKey 引用
4. 確保 db_table 設定正確

#### 4.4 驗證結果
所有模型類名為單數形式
所有資料表名為複數形式
完全符合 schema.sql 規範

### 第五階段：序列化器 Bug 修復 (2025-10-14)

#### 5.1 問題發現
**錯誤訊息**:
```bash
AssertionError: Cannot set both 'fields' and 'exclude' options on serializer SubmissionCreateSerializer.
```

#### 5.2 問題分析
**根本原因**: 
- DRF 不允許同時設定 `fields` 和 `exclude`
- 序列化器配置衝突

#### 5.3 解決方案
```python
# 修正前
class Meta:
    model = Submission
    fields = ['problem_id', 'language_type', 'source_code']
    exclude = ['user']  # 衝突

# 修正後
class Meta:
    model = Submission
    fields = ['problem_id', 'language_type', 'source_code']  # 只使用 fields
```

#### 5.4 驗證結果
序列化器配置正確
測試通過

### 第六階段：Hypothesis 測試邊界情況 (2025-10-15)

#### 6.1 問題發現
**測試失敗**:
```bash
AssertionError: Errors: {'source_code': [ErrorDetail(string='Null characters are not allowed.', code='null_characters_not_allowed')]}
Falsifying example: source_code='\x00'
```

#### 6.2 問題分析
**發現**: 
- Hypothesis 自動發現了 null 字符問題
- Django REST Framework 正確拒絕了無效輸入

**技術背景**:
- Null 字符 (`\x00`) 在資料庫和網路傳輸中會造成問題
- Django 的拒絕行為是正確的安全機制

#### 6.3 解決方案
**修正測試策略**:
```python
# 修正前：會生成無效字符
source_code=st.text(min_size=1, max_size=500)

# 修正後：排除無效字符
source_code=st.text(
    min_size=1, 
    max_size=500,
    alphabet=st.characters(
        blacklist_categories=['Cc', 'Cs'],  # 排除控制字符
        blacklist_characters=['\x00']        # 排除 null 字符
    )
)
```

#### 6.4 驗證結果
測試生成合理的輸入數據
保持系統安全性
所有測試通過

### 第七階段：安全性驗證 (2025-10-15)

#### 7.1 安全性考量討論
**問題**: "不會遇到真的有人輸入 null 字符導致 Django 崩潰嗎？"

#### 7.2 安全性分析
**威脅模型**:
- 惡意攻擊者可能嘗試注入無效字符
- 意外的二進制數據或編碼問題
- 複製貼上時的字符問題

#### 7.3 防護機制驗證
**多層防護**:
1. **Django REST Framework 層**: 自動拒絕 null 字符
2. **業務邏輯層**: 自定義驗證
3. **資料庫層**: 模型約束

**安全性測試**:
```python
def test_serializer_rejects_null_characters(self):
    data = {'source_code': 'print("hello")\x00malicious_code'}
    serializer = SubmissionCreateSerializer(data=data, context={'request': request})
    assert not serializer.is_valid()  # 正確拒絕
```

#### 7.4 驗證結果
Django 自動防護機制有效
系統不會崩潰
安全性測試覆蓋完整

## 開發成果總結

### 完成的功能
1. **9 個完整的 Django 模型**，完全符合 schema.sql
2. **完整的 DRF 序列化器**，包含驗證和安全檢查
3. **Hypothesis property-based 測試**，覆蓋 models 和 serializers
4. **安全性測試**，驗證系統對惡意輸入的防護

### 技術亮點
- **Property-based testing**: 自動發現邊界情況
- **多層安全防護**: Django + 業務邏輯 + 資料庫約束
- **完整的命名規範**: 符合 Django 和資料庫最佳實踐
- **詳細的錯誤分析**: 系統性問題解決方法

### 學習成果
**測試學習一**: 知道怎麼對 Django 做一個基於 Hypothesis 的 Property-based testing
**測試學習二**: 何時修改測試 vs 何時修改業務代碼
**邊界情況**: Hypothesis 幫助發現意想不到的問題

## 下一步計畫
- [ ] 建立更多複雜的業務邏輯測試
- [ ] 性能測試和優化(目前都沒有考慮效率的部分)
- [ ] 完整的 API 端點實現

---
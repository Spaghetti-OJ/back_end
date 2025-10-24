# Submissions API 開發報告

## 執行摘要

本報告分析現有 NOJ 系統的 Submission API 架構，對比新需求規格，並制定基於 Django REST Framework 的重構方案。重點聚焦於 7 個核心資料表的 API 設計與實作策略。

## 現有系統分析

### 架構特點
- **Framework**: Flask + MongoEngine (MongoDB)
- **認證方式**: `@login_required` decorator
- **權限控制**: 基於 Permission 系統的細粒度控制
- **快取機制**: Redis 快取查詢結果
- **檔案處理**: 直接處理 FormData 上傳

### API 設計模式分析

#### 1. 路由結構
```python
# 現有系統採用巢狀路由
GET /submission/<id>/output/<task_no>/<case_no>  # 獲取特定測試案例輸出
PUT /submission/<id>/complete                     # Sandbox 回呼端點
GET /submission/<id>/pdf/<item>                   # PDF 檔案下載
```

#### 2. 權限驗證模式
```python
# 基於物件層級的權限檢查
if not submission.permission(user, Submission.Permission.FEEDBACK):
    return HTTPError('forbidden.', 403)
```

#### 3. 資料驗證方式
```python
# 自定義 Request decorator 進行參數驗證
@Request.json('score: int')
@Request.files('code')
@Request.doc('submission', Submission)
```

### 現有系統的優缺點

#### 優點
1. **細粒度權限控制**: 每個操作都有明確的權限檢查
2. **完整的工作流程**: 從提交建立到判題完成的完整流程
3. **快取最佳化**: Redis 快取提升查詢效能
4. **檔案處理成熟**: 支援程式碼上傳、PDF 批改等

#### 缺點
1. **API 不一致**: 有些用 GET 觸發動作（如 rejudge）
2. **緊耦合設計**: 業務邏輯與 API 層混合
3. **缺乏標準化**: 沒有統一的回應格式
4. **分散式資料**: 部分功能缺少對應的 API

## 新需求分析

### 主管期望的 API 規格

根據 HackMD 文件，新系統需要支援：

#### 1. 核心提交功能
- 一步式提交（整合建立和上傳）
- 提交列表查詢（支援多重篩選）
- 提交詳情查看
- 重新判題功能

#### 2. 擴展功能
- 自定義測試（Custom Test）
- 程式碼草稿系統
- 題解發布與管理
- 使用者統計資料
- 全域排行榜

#### 3. 管理功能  
- 手動評分
- 提交批改與評論
- 系統設定管理

## 資料表對應 API 設計

### 1. Submissions Table
```
POST   /api/submissions/                    # 建立提交
GET    /api/submissions/                    # 提交列表（支援篩選、分頁）
GET    /api/submissions/{id}/               # 提交詳情
PUT    /api/submissions/{id}/grade/         # 手動評分
POST   /api/submissions/{id}/rejudge/       # 重新判題
GET    /api/submissions/{id}/code/          # 獲取程式碼
DELETE /api/submissions/{id}/               # 刪除提交（管理員）
```

**與現有系統差異：**
- 整合建立和上傳為單一 API
- rejudge 改為 POST 方法
- 新增程式碼單獨獲取端點

### 2. Submission Results Table  
```
GET    /api/submissions/{id}/results/       # 獲取執行結果
GET    /api/submissions/{id}/output/{task}/{case}/  # 特定測試案例輸出
```

**設計考量：**
- 保持與現有系統相容的巢狀路由
- 支援權限控制的輸出查看

### 3. User Problem Stats Table
```
GET    /api/stats/user/{user_id}/           # 用戶整體統計
GET    /api/stats/user/{user_id}/problems/  # 用戶題目統計
GET    /api/stats/problem/{problem_id}/     # 題目統計資訊
```

**新功能：**
- 現有系統缺少的統計 API
- 支援個人和題目維度統計

### 4. Custom Tests Table
```
POST   /api/problems/{id}/custom-test/      # 執行自定義測試
GET    /api/custom-tests/                   # 自定義測試歷史
GET    /api/custom-tests/{id}/              # 自定義測試詳情
DELETE /api/custom-tests/{id}/              # 刪除測試記錄
```

**全新功能：**
- 現有系統沒有對應 API
- 需要新增完整的 Custom Test 工作流程

### 5. Code Drafts Table
```
POST   /api/drafts/                         # 儲存草稿
GET    /api/drafts/                         # 草稿列表
GET    /api/drafts/{problem_id}/            # 特定題目草稿
PUT    /api/drafts/{id}/                    # 更新草稿
DELETE /api/drafts/{id}/                    # 刪除草稿
```

**全新功能：**
- 現有系統沒有草稿功能
- 需要建立完整的草稿管理系統

### 6. Editorials Table  
```
POST /problem/{problemId}/solution — 發布題解
GET /problem/{problemId}/solution — 取得題解
PUT /problem/{problemId}/solution/{solutionId} — 修改題解
DELETE /problem/{problemId}/solution/{solutionId} — 刪除題解
```

**全新功能：**
- 支援 Markdown 內容
- 題解發布與管理工作流程

### 7. Editorial Likes Table
```  
POST   /api/editorials/{id}/like/           # 點讚題解
DELETE /api/editorials/{id}/like/           # 取消點讚
GET    /api/editorials/{id}/likes/          # 點讚列表
```

**輕量化功能：**
- 簡單的點讚系統
- 支援點讚狀態查詢

## 技術架構設計

### 1. Django REST Framework 遷移策略

#### Serializers 設計
```python
# 現有系統：手動資料驗證
@Request.json('language_type: int', 'problem_id: int')

# 新系統：DRF Serializers  
class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ['problem_id', 'language_type', 'source_code']
        
    def validate_source_code(self, value):
        if len(value) > 65536:  # 64KB limit
            raise serializers.ValidationError("程式碼過長")
        return value
```

#### ViewSets 架構
```python
# 採用 DRF ViewSets 提供標準 CRUD
class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'language_type', 'problem_id']
    search_fields = ['user__username']
    
    @action(detail=True, methods=['post'])
    def rejudge(self, request, pk=None):
        # 重新判題邏輯
        pass
```

### 2. 權限系統移植

#### 現有權限模式
```python
# MongoEngine 基於方法的權限
submission.permission(user, Submission.Permission.FEEDBACK)
```

#### Django 權限適配
```python
# Django 基於類別的權限
class SubmissionPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if view.action == 'retrieve':
            return obj.can_view(request.user)
        elif view.action in ['grade', 'comment']:
            return obj.can_grade(request.user)
        return False
```

### 3. 資料庫架構對應

#### MongoDB → PostgreSQL 遷移要點
```python
# 現有 MongoEngine 模型
class Submission(Document):
    problem_id = IntField(required=True)
    user = ReferenceField(User)
    tasks = ListField(EmbeddedDocumentField(Task))

# Django ORM 模型  
class Submission(models.Model):
    problem_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # tasks 拆分為獨立的 SubmissionResult 表

class SubmissionResult(models.Model):
    submission = models.ForeignKey(Submission, related_name='results')
    task_id = models.IntegerField()
    status = models.IntegerField()
```

## 效能最佳化策略

### 1. 快取機制
```python
# 現有系統：手動 Redis 快取
cache_key = '_'.join(map(str, (user, problem_id, status, ...)))
if cache.exists(cache_key):
    return json.loads(cache.get(cache_key))

# 新系統：Django Cache Framework
from django.core.cache import cache
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15分鐘快取
def submission_list(request):
    pass
```

### 2. 資料庫查詢最佳化
```python
# 使用 select_related 和 prefetch_related 減少查詢次數
queryset = Submission.objects.select_related('user', 'problem')\
                              .prefetch_related('results')

# 建立適當的資料庫索引
class Meta:
    indexes = [
        models.Index(fields=['user', 'created_at']),
        models.Index(fields=['problem_id', 'status']),
        models.Index(fields=['created_at']),
    ]
```

## 實作階段規劃

### Phase 1: 核心功能遷移
- [x] 建立 Django 模型和遷移
- [x] 基礎 Submission CRUD API  
- [ ] 權限系統適配
- [ ] 基礎測試撰寫

### Phase 2: 擴展功能實作  
- [ ] Custom Test 系統
- [ ] Code Drafts 管理
- [ ] Editorial 系統
- [ ] 統計 API 實作

### Phase 3: 效能與整合
- [ ] 快取系統整合
- [ ] API 效能測試
- [ ] 與前端系統整合測試
- [ ] 文件撰寫

## 風險與挑戰

### 1. 資料遷移風險
- **MongoDB → PostgreSQL** 的資料結構差異
- **嵌套文件** 轉換為關聯式表格的複雜度
- **現有資料** 的完整性保證

### 2. 權限系統相容性
- 現有細粒度權限如何對應到 Django 權限系統
- 跨應用程式的權限檢查（Problems, Courses 等）

### 3. 效能考量
- 大量提交資料的查詢效能
- 檔案上傳和儲存的效能影響
- 快取策略的有效性

## 結論與建議

### 建議採用的方案
1. **漸進式遷移**: 先實作核心 API，逐步加入擴展功能
2. **保持相容性**: 盡可能保持與現有系統的 API 相容
3. **權限適配**: 建立權限適配層，確保安全性
4. **效能優先**: 從設計階段就考慮效能最佳化

### 下一步行動
1. 確認資料表設計和關聯性
2. 建立詳細的 API 規格文件  
3. 實作核心 Submission ViewSet
4. 建立完整的測試覆蓋

---

**報告撰寫日期**: 2025年10月21日  
**撰寫人**: Backend Developer  
**審核狀態**: 待審核
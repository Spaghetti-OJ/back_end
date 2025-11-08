# 快取對 Model 和 Serializer 的影響對比(僅考慮最基本的實現，不考慮 cache 的一堆有可能的bug)

## Model 層面的對比

### 沒有快取的設計

```python
# submissions/models.py - 簡單版本
class Submission(models.Model):
    problem_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10)
    score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 就是普通的資料庫欄位，沒有其他考量

class UserProblemStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem_id = models.IntegerField()
    best_score = models.IntegerField()
    
    # 簡單的統計表，每次都重新計算
```

### 有快取的設計

```python
# submissions/models.py - 快取版本
class Submission(models.Model):
    problem_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10)
    score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 新增：儲存後清除快取
        self.clear_related_caches()
    
    def clear_related_caches(self):
        """清除相關快取"""
        from django.core.cache import cache
        cache.delete(f"user_stats_{self.user_id}")
        cache.delete(f"problem_stats_{self.problem_id}")
        cache.delete_many([f"submission_list_{pattern}" for pattern in self.get_cache_patterns()])
    
    @classmethod 
    def get_user_high_score(cls, user_id, problem_id):
        """新增：帶快取的查詢方法"""
        from django.core.cache import cache
        cache_key = f"high_score_{user_id}_{problem_id}"
        score = cache.get(cache_key)
        if score is None:
            score = cls.objects.filter(
                user_id=user_id, problem_id=problem_id
            ).aggregate(Max('score'))['score'] or 0
            cache.set(cache_key, score, 600)
        return score

class UserProblemStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem_id = models.IntegerField()
    best_score = models.IntegerField()
    
    # 新增：為快取設計的索引
    class Meta:
        indexes = [
            models.Index(fields=['user', 'problem_id']),
            models.Index(fields=['user', 'best_score']),  # 為排名快取
        ]
```

---

## Serializer 層面的對比

### 沒有快取的設計

```python
# submissions/serializers.py - 簡單版本
class SubmissionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True)
    
    class Meta:
        model = Submission
        fields = ['id', 'problem_id', 'status', 'score', 'user_name', 'problem_title']
    
    # 就是標準的 ModelSerializer，每次都查詢關聯資料
```

### 有快取的設計

```python
# submissions/serializers.py - 快取版本
class SubmissionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True)
    
    # 新增：快取計算欄位
    user_stats = serializers.SerializerMethodField()
    user_rank = serializers.SerializerMethodField()
    problem_acceptance_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Submission
        fields = [
            'id', 'problem_id', 'status', 'score', 'user_name', 'problem_title',
            'user_stats', 'user_rank', 'problem_acceptance_rate'
        ]
    
    def get_user_stats(self, obj):
        """新增：帶快取的用戶統計"""
        from django.core.cache import cache
        cache_key = f"user_stats_{obj.user_id}"
        stats = cache.get(cache_key)
        if stats is None:
            stats = {
                'total_submissions': Submission.objects.filter(user_id=obj.user_id).count(),
                'solved_count': Submission.objects.filter(
                    user_id=obj.user_id, status='AC'
                ).values('problem_id').distinct().count(),
            }
            cache.set(cache_key, stats, 3600)  # 1小時
        return stats
    
    def get_user_rank(self, obj):
        """新增：帶快取的用戶排名"""
        from django.core.cache import cache
        cache_key = f"user_rank_{obj.user_id}"
        rank = cache.get(cache_key)
        if rank is None:
            # 複雜的排名計算邏輯
            rank = calculate_user_rank(obj.user_id)
            cache.set(cache_key, rank, 1800)  # 30分鐘
        return rank

# 新增：分層序列化器
class SubmissionListSerializer(serializers.ModelSerializer):
    """列表用序列化器 - 精簡欄位便於快取"""
    class Meta:
        model = Submission
        fields = ['id', 'problem_id', 'status', 'score', 'created_at']

class SubmissionDetailSerializer(SubmissionSerializer):
    """詳情用序列化器 - 完整資訊"""
    code = serializers.SerializerMethodField()
    execution_details = serializers.SerializerMethodField()
    
    def get_code(self, obj):
        """程式碼也需要快取"""
        from django.core.cache import cache
        cache_key = f"submission_code_{obj.id}"
        code = cache.get(cache_key)
        if code is None:
            code = obj.get_source_code()  # 可能從檔案系統讀取
            cache.set(cache_key, code, 1800)
        return code
```

---

## 具體影響總表

| 面向 | 沒有快取 | 有快取 | 主要差異 |
|------|---------|--------|----------|
| **Model 複雜度** | 簡單 | 複雜 | +快取邏輯、信號處理、索引設計 |
| **Model 方法數量** | 基本CRUD | 大量快取方法 | +get_cached_xxx()方法 |
| **資料庫設計** | 標準正規化 | 考慮反正規化 | +為快取設計的冗餘資料 (沒做好效率會炸掉)|
| **Serializer 欄位** | 基本欄位 | 計算欄位 | +SerializerMethodField |
| **序列化器數量** | 1個通用 | 多個專用 | 列表/詳情分離 |
| **程式碼行數** | ~50行 | ~200行 | 增加4倍程式碼 |
| **維護複雜度** | 低 | 高 | 需要處理快取一致性 |

---

## 效能影響對比

### 沒有快取的查詢
```python
# 每次API調用都要執行的查詢
def get_submission_list():
    submissions = Submission.objects.select_related('user', 'problem').all()
    for submission in submissions:
        # 每個submission都要查詢統計
        user_stats = Submission.objects.filter(user=submission.user).aggregate(...)
        problem_stats = Submission.objects.filter(problem=submission.problem).aggregate(...)
        user_rank = calculate_rank(submission.user)  # 複雜計算
    
    # 結果：N+1 查詢問題，每次都重算
```

### 有快取的查詢
```python  
# 大部分資料從快取取得
def get_submission_list():
    cache_key = f"submission_list_{hash(filters)}"
    result = cache.get(cache_key)
    if result is None:
        submissions = Submission.objects.select_related('user', 'problem').all()
        # 統計資料從快取取得，不用重算
        result = SubmissionListSerializer(submissions, many=True).data
        cache.set(cache_key, result, 30)
    
    # 結果：第一次查詢後，後續30秒內都是快取
```


**結論：有快取會讓開發複雜度會變大很多，但要注意很多 bug 
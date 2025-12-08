from django.db import models
from django.conf import settings
import uuid
from decimal import Decimal

class Submission(models.Model):
    # Language choices - enum (NOJ 兼容：0=C, 1=C++, 2=Python, 跳過 PDF, 3=Java, 4=JavaScript)
    LANGUAGE_CHOICES = [
        (0, 'C'),
        (1, 'C++'), 
        (2, 'Python'),
        # PDF (原本是 3) 跳過，因為我們不支援手寫題
        (3, 'Java'),
        (4, 'JavaScript'),
    ]
    
    # Status choices - enum (使用數字編碼，兼容 NOJ 標準)
    STATUS_CHOICES = [
        ('-2', 'Pending before upload'),              # 兼容舊的 NOJ，還沒有 code 的 submission
        ('-1', 'Pending'),              # 等待判題
        ('0', 'Accepted'),              # AC - 答案正確
        ('1', 'Wrong Answer'),          # WA - 答案錯誤
        ('2', 'Compilation Error'),     # CE - 編譯錯誤
        ('3', 'Time Limit Exceeded'),   # TLE - 超過時間限制
        ('4', 'Memory Limit Exceeded'), # MLE - 超過記憶體限制
        ('5', 'Runtime Error'),         # RE - 執行時錯誤
        ('6', 'Judge Error'),           # JE - 判題系統錯誤
        ('7', 'Output Limit Exceeded'), # OLE - 輸出超過限制
    ]
    # Primary key - UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Foreign keys
    problem_id = models.IntegerField()  # 直接關聯題目 ID
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # 使用 Django 內建 User
    # Core fields
    language_type = models.IntegerField(
        choices=LANGUAGE_CHOICES,
        null=False,
        blank=False
    )
    source_code = models.TextField(null=False, blank=False)  # longtext equivalent
    code_hash = models.CharField(max_length=64, null=True, blank=True)

    # Status and scoring
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='-1'  # 預設為 Pending 狀態
    )
    score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=100)
    # Execution metrics
    execution_time = models.IntegerField(default=-1)  # milliseconds
    memory_usage = models.IntegerField(default=-1)   # KB

    # Request info
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # 支援 IPv4/IPv6
    user_agent = models.CharField(max_length=500, null=True, blank=True)

    # Submission metadata
    is_late = models.BooleanField(default=False)
    is_custom_test = models.BooleanField(default=False)  # 標記是否為自訂測試
    penalty_applied = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    attempt_number = models.IntegerField(default=1)
    judge_server = models.CharField(max_length=100, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    judged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # 定義 index 
        indexes = [
            models.Index(fields=['user', 'problem_id', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
        
        # 排序
        ordering = ['-created_at']
        
        # 表格名稱
        db_table = 'submissions'
    
    def __str__(self):
        return f"Submission {self.id} - {self.user.username} - {self.status}"
    
    @property # 我的判斷是這不能被隨意更新跟刪除
    def is_judged(self):
        """檢查是否已經判題完成"""
        return self.status not in ['-2', '-1']  # No Code 和 Pending 表示尚未判題
    
    @property # 我的判斷是這不能被隨意更新跟刪除
    def execution_time_seconds(self):
        """將執行時間轉換為秒"""
        if self.execution_time == -1:
            return None
        return self.execution_time / 1000.0


class SubmissionResult(models.Model):
    """提交結果 - 每個測資的執行結果"""
    
    STATUS_CHOICES = [
        ('accepted', 'Accepted'),
        ('wrong_answer', 'Wrong Answer'),
        ('time_limit_exceeded', 'Time Limit Exceeded'),
        ('memory_limit_exceeded', 'Memory Limit Exceeded'),
        ('runtime_error', 'Runtime Error'),
    ]
    
    SOLVE_STATUS_CHOICES = [
        ('unsolved', 'Unsolved'),
        ('partial', 'Partial'),
        ('solved', 'Solved'),
    ]
    
    # Primary key - UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Foreign keys
    problem_id = models.IntegerField()
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='results')
    test_case_id = models.IntegerField()
    test_case_index = models.IntegerField()
    
    # Status and scoring
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    execution_time = models.IntegerField(null=True, blank=True)
    memory_usage = models.IntegerField(null=True, blank=True)
    score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=100)
    
    # Output and messages
    output_preview = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    judge_message = models.TextField(blank=True, null=True)
    solve_status = models.CharField(
        max_length=20, 
        choices=SOLVE_STATUS_CHOICES, 
        default='unsolved'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['submission', 'test_case_index']),
        ]
        ordering = ['test_case_index']
        db_table = 'submission_results'
    
    def __str__(self):
        return f"Result {self.id} - {self.submission.id} - Test {self.test_case_index}"


class UserProblemStats(models.Model):
    """使用者題目統計 - 作業層級"""
    
    SOLVE_STATUS_CHOICES = [
        ('unsolved', 'Unsolved'),
        ('partial', 'Partial'),
        ('solved', 'Solved'),
    ]
    
    # Primary key
    id = models.AutoField(primary_key=True)
    
    # Foreign keys
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assignment_id = models.IntegerField()
    problem_id = models.IntegerField()
    best_submission = models.ForeignKey(
        Submission, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='best_for_stats'
    )
    
    # Statistics
    total_submissions = models.IntegerField(default=0)
    best_score = models.IntegerField(default=0)
    max_possible_score = models.IntegerField(default=100)
    first_ac_time = models.DateTimeField(null=True, blank=True)
    last_submission_time = models.DateTimeField(null=True, blank=True)
    solve_status = models.CharField(
        max_length=20, 
        choices=SOLVE_STATUS_CHOICES, 
        default='unsolved'
    )
    best_execution_time = models.IntegerField(null=True, blank=True)
    best_memory_usage = models.IntegerField(null=True, blank=True)
    penalty_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    is_late = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'assignment_id', 'problem_id']),
            models.Index(fields=['assignment_id', 'best_score', 'first_ac_time']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'assignment_id', 'problem_id'],
                name='unique_user_assignment_problem'
            )
        ]
        ordering = ['-updated_at']
        db_table = 'user_problem_stats'
    
    def __str__(self):
        return f"Stats {self.user.username} - Assignment {self.assignment_id} - Problem {self.problem_id}"


class UserProblemSolveStatus(models.Model):
    """使用者題目解題狀態 - 全域層級"""
    
    SOLVE_STATUS_CHOICES = [
        ('never_tried', 'Never Tried'),
        ('attempted', 'Attempted'),
        ('partial_solved', 'Partial Solved'),
        ('fully_solved', 'Fully Solved'),
    ]
    
    # Primary key
    id = models.AutoField(primary_key=True)
    
    # Foreign keys
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem_id = models.IntegerField()
    
    # Statistics
    total_submissions = models.IntegerField(default=0)
    ac_submissions = models.IntegerField(default=0)
    best_score = models.IntegerField(default=0)
    first_solve_time = models.DateTimeField(null=True, blank=True)
    last_submission_time = models.DateTimeField(null=True, blank=True)
    solve_status = models.CharField(
        max_length=20, 
        choices=SOLVE_STATUS_CHOICES, 
        default='never_tried'
    )
    total_execution_time = models.BigIntegerField(default=0)
    best_execution_time = models.IntegerField(null=True, blank=True)
    best_memory_usage = models.IntegerField(null=True, blank=True)
    difficulty_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        null=True, 
        blank=True
    )
    tags_mastered = models.JSONField(default=dict)
    mistake_patterns = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'problem_id']),
            models.Index(fields=['user', 'solve_status']),
            models.Index(fields=['problem_id', 'solve_status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'problem_id'],
                name='unique_user_problem_solve'
            )
        ]
        ordering = ['-updated_at']
        db_table = 'user_problem_solve_status'
    
    def __str__(self):
        return f"Solve Status {self.user.username} - Problem {self.problem_id}"


class UserProblemQuota(models.Model):
    """使用者題目配額"""
    
    # Primary key
    id = models.AutoField(primary_key=True)
    
    # Foreign keys
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem_id = models.IntegerField()
    assignment_id = models.IntegerField(null=True, blank=True)  # 可選，作業層級配額
    
    # Quota settings
    total_quota = models.IntegerField(default=-1)  # -1 = 無限制
    remaining_attempts = models.IntegerField(default=-1)  # -1 = 無限制
    reset_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'problem_id', 'assignment_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'problem_id', 'assignment_id'],
                name='unique_user_problem_assignment_quota'
            )
        ]
        ordering = ['-updated_at']
        db_table = 'user_problem_quotas'
    
    def __str__(self):
        assignment_info = f" - Assignment {self.assignment_id}" if self.assignment_id else ""
        return f"Quota {self.user.username} - Problem {self.problem_id}{assignment_info}"


class CustomTest(models.Model):
    """自定義測試"""
    
    LANGUAGE_CHOICES = [
        (0, 'C'),
        (1, 'C++'),
        (2, 'Python'),
        (3, 'Java'),
        (4, 'JavaScript'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]
    
    # Primary key - UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Foreign keys
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem_id = models.IntegerField()
    
    # Core fields
    language_type = models.IntegerField(choices=LANGUAGE_CHOICES)
    source_code = models.TextField()
    input_data = models.TextField(null=True, blank=True)
    expected_output = models.TextField(null=True, blank=True)
    actual_output = models.TextField(null=True, blank=True)
    
    # Status and results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    execution_time = models.IntegerField(null=True, blank=True)
    memory_usage = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['problem_id', 'created_at']),
        ]
        ordering = ['-created_at']
        db_table = 'custom_tests'
    
    def __str__(self):
        return f"Custom Test {self.id} - {self.user.username} - Problem {self.problem_id}"


class Editorial(models.Model):
    """題解"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Primary key - UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Foreign keys
    problem_id = models.IntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Core fields
    title = models.CharField(max_length=255)
    content = models.TextField()
    difficulty_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        null=True, 
        blank=True
    )
    
    # Statistics
    likes_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_official = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['problem_id', 'is_official']),
            models.Index(fields=['problem_id', 'likes_count']),
            models.Index(fields=['author', 'created_at']),
        ]
        ordering = ['-created_at']
        db_table = 'editorials'
    
    def __str__(self):
        return f"Editorial {self.title} - Problem {self.problem_id} - {self.author.username}"


class EditorialLike(models.Model):
    """題解點讚"""
    
    # Primary key
    id = models.AutoField(primary_key=True)
    
    # Foreign keys
    editorial = models.ForeignKey(Editorial, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['editorial', 'user']),
            models.Index(fields=['user', 'created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['editorial', 'user'],
                name='unique_editorial_user_like'
            )
        ]
        ordering = ['-created_at']
        db_table = 'editorial_likes'
    
    def __str__(self):
        return f"Like {self.editorial.title} by {self.user.username}"

from django.db import models
from django.contrib.auth import get_user_model
import uuid
from django.utils import timezone

# 獲取專案中使用的 User Model (可能是內建或自定義的)
User = get_user_model() 

# ==============================================================================
# 1. ApiToken Model
# ==============================================================================

class ApiToken(models.Model):
    """
    管理使用者的 API 存取 Token
    """
    # id uuid [pk]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # user_id uuid [not null] - 外鍵關聯到 User
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_tokens',
        verbose_name='關聯使用者'
    )
    
    # name varchar(100) [not null]
    name = models.CharField(max_length=100, verbose_name='Token 名稱')
    
    # permissions json [default: '[]']
    permissions = models.JSONField(default=list, verbose_name='權限列表')

    # usage_count integer [default: 0]
    usage_count = models.IntegerField(default=0, verbose_name='使用次數')
    
    # usage_time integer 
    usage_time = models.IntegerField(default=0, verbose_name='總使用時間(秒)')
    
    # last_used_at timestamp [null]
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最後使用時間')
    
    # created_at timestamp [default: `now()`]
    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    
    # expires_at timestamp [null]
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='過期時間')
    
    # is_active boolean [default: true]
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')

    class Meta:
        db_table = 'Api_tokens'
        verbose_name = 'API Token'
        verbose_name_plural = 'API Tokens'

    def __str__(self):
        return f"{self.user.username} - {self.name}"

# ==============================================================================
# 2. UserActivity Model
# ==============================================================================

class UserActivity(models.Model):
    """
    記錄使用者在系統中的各項活動
    """
    # id integer [pk, increment] (Django 預設)
    
    ACTIVITY_CHOICES = [
        ('login', '登入'),
        ('logout', '登出'),
        ('submit', '提交程式碼'),
        ('solve', '解題'),
        ('join_course', '加入課程'),
        ('create_problem', '建立題目'),
    ]
    
    OBJECT_CHOICES = [
        ('problem', '題目'),
        ('assignment', '作業'),
        ('course', '課程'),
        ('submission', '提交'),
    ]

    # user_id uuid [not null]
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name='操作使用者'
    )
    
    # activity_type enum(...) [not null]
    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_CHOICES,
        verbose_name='活動類型'
    )
    
    # object_type enum(...) [null]
    object_type = models.CharField(
        max_length=50,
        choices=OBJECT_CHOICES,
        null=True, blank=True,
        verbose_name='關聯對象類型'
    )
    
    # object_id uuid [null]
    object_id = models.UUIDField(null=True, blank=True, verbose_name='關聯對象 ID')
    
    # description varchar(500)
    description = models.CharField(max_length=500, verbose_name='活動描述')
    
    # ip_address varchar(45)
    ip_address = models.GenericIPAddressField(max_length=45, verbose_name='IP 位址')
    
    # metadata json [default: '{}']
    metadata = models.JSONField(default=dict, verbose_name='額外資料')
    
    # success boolean [default: true]
    success = models.BooleanField(default=True, verbose_name='操作是否成功')
    
    # created_at timestamp [default: `now()`]
    created_at = models.DateTimeField(default=timezone.now, verbose_name='活動時間')

    class Meta:
        db_table = 'User_activities'
        verbose_name = '使用者活動'
        verbose_name_plural = '使用者活動紀錄'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_activity_type_display()}] {self.user.username}"


# ==============================================================================
# 3. LoginLog Model
# ==============================================================================

class LoginLog(models.Model):
    """
    記錄每次的登入嘗試 (無論成功或失敗)
    """
    # id integer [pk, increment] (Django 預設)
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失敗'),
        ('blocked', '被阻擋'),
    ]

    # user_id uuid [pk, null] - 設為 ForeignKey，允許 null
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='login_logs',
        verbose_name='登入使用者'
    )
    
    # username varchar(150)
    username = models.CharField(max_length=150, verbose_name='嘗試登入的用戶名')
    
    # login_status enum(...) [not null]
    login_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name='登入狀態'
    )
    
    # failure_reason varchar(200)
    failure_reason = models.CharField(
        max_length=200,
        null=True, blank=True,
        verbose_name='失敗原因'
    )
    
    # ip_address varchar(45)
    ip_address = models.GenericIPAddressField(max_length=45, verbose_name='IP 位址')
    
    # created_at timestamp [default: `now()`]
    created_at = models.DateTimeField(default=timezone.now, verbose_name='登入時間')

    class Meta:
        db_table = 'Login_logs'
        verbose_name = '登入日誌'
        verbose_name_plural = '登入日誌'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.get_login_status_display()}] {self.username}"
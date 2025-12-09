from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import uuid
from datetime import timedelta
from django.conf import settings

User = get_user_model() 

# ==============================================================================
# 1. UserActivity Model
# ==============================================================================

class UserActivity(models.Model):
    """
    記錄使用者在系統中的關鍵操作活動。
    使用 ContentType 實現通用關聯 (Generic Relations)。
    """
    
    ACTIVITY_CHOICES = [
        ('login', '登入'),
        ('logout', '登出'),
        ('submit', '提交程式碼'),
        ('view_problem', '查看題目'),
        ('download_testcase', '下載測試測資'),
        # ... 其他關鍵活動
    ]

    # user_id [not null]
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
        verbose_name='活動類型',
        db_index=True
    )
    
    # 指向關聯的模型 (例如: Problem, Submission)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    # 儲存關聯物件的 ID (假設系統中其他主要 Model 也使用 UUID)
    object_id = models.UUIDField(null=True, blank=True, db_index=True, verbose_name='關聯對象 ID')
    # 實際的關聯物件接口
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # description varchar(500)
    description = models.CharField(max_length=500, blank=True, verbose_name='活動補充描述')
    
    # ip_address varchar(45)
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 位址')
    
    # [新增] user_agent - 記錄操作時的裝置資訊
    user_agent = models.TextField(null=True, blank=True, verbose_name='User-Agent')

    # metadata json [default: '{}']
    metadata = models.JSONField(default=dict, blank=True, verbose_name='額外資料 (例如提交語言、檔案大小)')
    
    # success boolean [default: true]
    success = models.BooleanField(default=True, verbose_name='操作是否成功')
    
    # created_at timestamp [default: `now()`]
    created_at = models.DateTimeField(default=timezone.now, verbose_name='活動時間', db_index=True)

    class Meta:
        db_table = 'user_activities'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-created_at']
        indexes = [
            # 針對常用的查詢組合建立索引，例如：查詢某使用者最近的活動
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        status = "成功" if self.success else "失敗"
        target = f" on {self.content_type.model}" if self.content_type else ""
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.user.username} {self.get_activity_type_display()}{target} ({status})"


# ==============================================================================
# 2. LoginLog Model
# ==============================================================================

class LoginLog(models.Model):
    """
    記錄每次的登入嘗試，用於安全審計與防代考分析。
    """
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed_credentials', '密碼錯誤'),
        ('failed_user_not_found', '用戶不存在'),
        ('blocked_ip', 'IP 被封鎖'),
        ('blocked_account', '帳號被停用'),
    ]

    # user_id [null] - 登入失敗時可能沒有對應的 User 物件
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='login_logs',
        verbose_name='關聯使用者'
    )
    
    # username varchar(150) [not null] - 記錄嘗試登入的帳號名稱
    username = models.CharField(max_length=150, verbose_name='嘗試用戶名', db_index=True)
    
    # login_status enum(...) [not null]
    login_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        verbose_name='登入狀態'
    )
    
    # ip_address varchar(45)
    ip_address = models.GenericIPAddressField(verbose_name='來源 IP')
    
    #user_agent text - 瀏覽器與裝置資訊，使用 TextField 以容納長字串
    user_agent = models.TextField(null=True, blank=True, verbose_name='User-Agent')

    # location varchar(100) - (選填) 透過 IP Geo 解析的地點
    location = models.CharField(max_length=100, null=True, blank=True, verbose_name='地理位置估計')
    
    # created_at timestamp [default: `now()`]
    created_at = models.DateTimeField(default=timezone.now, verbose_name='登入時間', db_index=True)

    class Meta:
        db_table = 'login_logs' 
        verbose_name = 'Login Log'
        verbose_name_plural = 'Login Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ip_address', '-created_at']), # 用於偵測 IP 暴力破解
            models.Index(fields=['username', '-created_at']),   # 用於偵測帳號暴力破解
        ]
    
    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.username} - {self.get_login_status_display()} (IP: {self.ip_address})"
    
class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return self.created_at < timezone.now() - timedelta(hours=24)

    def __str__(self):
        return f"{self.user} - {self.token}"
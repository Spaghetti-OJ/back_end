from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model() 

class ApiToken(models.Model):
    """
    管理使用者的 API 存取 Token。
    原始 Token 不會儲存在此，僅儲存雜湊值。
    """
    # id uuid [pk]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # user_id [not null] - 外鍵關聯到 User
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_tokens',
        verbose_name='關聯使用者'
    )
    
    # name varchar(100) [not null]
    name = models.CharField(max_length=100, verbose_name='Token 名稱', help_text="例如：我的筆電 CLI、CI/CD 系統")
    
    # [新增] token_hash varchar(128) [not null, unique] - 儲存 Token 的 SHA256 雜湊值
    token_hash = models.CharField(
    max_length=64, 
    unique=True,
    verbose_name='Token Hash'
)

    # [新增] prefix varchar(32) [not null] - Token 的前綴 (例如 oj_ab12...)，用於顯示與快速查找
    prefix = models.CharField(
        max_length=32,
        db_index=True,
        verbose_name='Token 前綴',
        help_text="用於識別 Token 的前幾位字元"
    )

    # permissions json [default: '[]'] - 定義 Scope
    permissions = models.JSONField(default=list, blank=True, verbose_name='權限列表 (Scopes)')

    # usage_count integer [default: 0]
    usage_count = models.IntegerField(default=0, verbose_name='使用次數')
    
    # last_used_at timestamp [null]
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最後使用時間')

    # [建議新增] last_used_ip - 追蹤 Token 使用來源
    last_used_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='最後使用 IP')
    
    # created_at timestamp [default: `now()`]
    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    
    # expires_at timestamp [null]
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='過期時間')
    
    # is_active boolean [default: true] - 允許使用者手動撤銷
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')

    class Meta:
        db_table = 'api_tokens'
        verbose_name = 'API Token'
        verbose_name_plural = 'API Tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_username()} - {self.name} ({self.prefix}...)"
    
    @property
    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False


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
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_tokens',
        verbose_name='關聯使用者'
    )
    
    
    name = models.CharField(max_length=100, verbose_name='Token 名稱', help_text="例如：我的筆電 CLI、CI/CD 系統")
    
    
    token_hash = models.CharField(
        max_length=64, 
        unique=True,
        verbose_name='Token Hash'
    )
    
    
    prefix = models.CharField(
        max_length=32,
        db_index=True,
        verbose_name='Token 前綴',
        help_text="用於識別 Token 的前幾位字元"
    )

    
    permissions = models.JSONField(
        default=list,       
        blank=True,         
        verbose_name='權限範圍 (Scopes)'
    )

    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='過期時間')

    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='上次使用時間')

    last_used_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='上次使用 IP')
    
    usage_count = models.PositiveIntegerField(default=0, verbose_name='使用次數')
    
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
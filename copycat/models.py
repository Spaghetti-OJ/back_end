from django.db import models
from django.conf import settings

class CopycatReport(models.Model):
    """
    記錄 MOSS 的檢查結果。
    我們只存 MOSS 回傳的 URL，不存詳細比對內容。
    """
    STATUS_CHOICES = [
        ('pending', '處理中'),
        ('success', '成功'),
        ('failed', '失敗'),
    ]

    problem_id = models.IntegerField(verbose_name="題目 ID", db_index=True)
    
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    moss_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="MOSS 報告網址")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'copycat_reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['problem_id', 'status']),
        ] 
from django.db import models
from django.conf import settings
import uuid


class CodeDraft(models.Model):
    """程式碼草稿"""
    
    LANGUAGE_CHOICES = [
        (0, 'C'),
        (1, 'C++'),
        (2, 'Python'),
        (3, 'Java'),
        (4, 'JavaScript'),
    ]
    
    # Primary key - UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Foreign keys
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem_id = models.IntegerField()
    assignment_id = models.IntegerField(null=True, blank=True)  # 可選的作業關聯
    
    # Core fields
    language_type = models.IntegerField(choices=LANGUAGE_CHOICES)
    source_code = models.TextField()
    title = models.CharField(max_length=255, null=True, blank=True)
    auto_saved = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'problem_id', 'updated_at']),
            models.Index(fields=['user', 'assignment_id', 'updated_at']),
        ]
        ordering = ['-updated_at']
        db_table = 'code_drafts'
    
    def __str__(self):
        title_info = f" - {self.title}" if self.title else ""
        return f"Draft {self.id} - {self.user.username} - Problem {self.problem_id}{title_info}"

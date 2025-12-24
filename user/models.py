import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings

class User(AbstractUser):
    """
    自訂使用者：
    - 主鍵改成 UUID
    - 保留 username（你表格有 username）
    - 新增 real_name、identity
    - email 設為 unique（和你需求一致）
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Django AbstractUser 已有: username, password, email(非唯一), first_name, last_name, is_staff...
    email = models.EmailField(max_length=254, unique=True)
    real_name = models.CharField(max_length=150)

    class Identity(models.TextChoices):
        TEACHER = 'teacher', 'Teacher'
        ADMIN   = 'admin',   'Admin'
        STUDENT = 'student', 'Student'
    identity = models.CharField(max_length=16, choices=Identity.choices, default=Identity.STUDENT)

    # 對齊你的欄位：date_joined & last_login 其實 AbstractUser 已內建
    # date_joined = models.DateTimeField(default=timezone.now)
    # last_login = models.DateTimeField(blank=True, null=True)

    def is_email_verified(self) -> bool:
        try:
            return bool(self.UserProfile.email_verified)
        except Exception:
            return False

    def __str__(self):
        return f"{self.username} ({self.identity})"


class UserProfile(models.Model):
    """
    對應 user_profiles 表
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    student_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)  # 需要 Pillow
    email_verified = models.BooleanField(default=False)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Profile<{self.user.username}>"
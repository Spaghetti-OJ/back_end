import uuid
import string, secrets
from django.db import models, IntegrityError, transaction
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator

ALPHABET = string.ascii_uppercase + string.digits

def _random_code(n: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))

class Courses(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # 注意：資料庫現有欄位名為 teacher_id（非 teacher_id_id），
    # 因欄位命名為 teacher_id + ForeignKey，Django 會預期欄位 teacher_id_id。
    # 為了與既有資料庫對齊且不改 schema，明確指定 db_column='teacher_id'。
    teacher_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_taught",
        db_column='teacher_id',
    )

    join_code = models.CharField(
        max_length=7,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(r"^[A-Z0-9]{7}$", "join_code 必須是 7 位大寫英數")],
        help_text="課程加入代碼（7 碼英數，大寫）。空值時會自動產生。"
    )

    student_limit = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    semester = models.CharField(max_length=50, blank=True)
    academic_year = models.CharField(max_length=10, blank=True)

    is_active = models.BooleanField(default=True)
    student_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Courses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["join_code"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["semester", "academic_year"]),
        ]

    def __str__(self):
        aca = f" {self.academic_year}" if self.academic_year else ""
        sem = f" {self.semester}" if self.semester else ""
        return f"{self.name}{aca}{sem}"

    def _assign_unique_join_code(self, length: int = 7, max_tries: int = 10) -> str:
        for _ in range(max_tries):
            code = _random_code(length)
            self.join_code = code
            try:
                with transaction.atomic():
                    super().save(update_fields=["join_code"])
                return code
            except IntegrityError:
                self.join_code = None
                continue
        raise IntegrityError("無法在合理次數內產生唯一的 join_code")

    def remove_join_code(self):
        type(self).objects.filter(pk=self.pk).update(join_code=None)
        self.join_code = None

    def regenerate_join_code(self) -> str:
        self.remove_join_code()
        return self._assign_unique_join_code()

    def save(self, *args, **kwargs):
        if self.join_code == "":
            self.join_code = None

        creating = self._state.adding
        super().save(*args, **kwargs)

        if self.join_code is None:
            self._assign_unique_join_code()

class Course_members(models.Model):
    course_id = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_memberships",
    )

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TA = "ta", "Teaching Assistant"
        TEACHER = "teacher", "Teacher"
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STUDENT)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Course_members"
        unique_together = ("course_id", "user_id")
        indexes = [
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user_id} in {self.course_id} ({self.role})"
    
class Announcements(models.Model):
    id = models.BigAutoField(primary_key=True)

    title = models.CharField(max_length=200)
    content = models.TextField()

    course_id = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    creator_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="announcements_created",
    )

    is_pinned = models.BooleanField(default=False)
    view_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Announcements"
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title
    
class Batch_imports(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course_id = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        related_name="batch_imports",
    )
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="imports_created",
    )

    file_name = models.CharField(max_length=255)
    csv_path = models.CharField(max_length=500)
    file_size = models.IntegerField(validators=[MinValueValidator(0)])

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    
    import_result = models.BooleanField(null=True)
    error_log = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "Batch_imports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} ({self.status})"
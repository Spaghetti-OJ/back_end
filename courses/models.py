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

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_taught",
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
        db_table = "courses"
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

class CourseMembers(models.Model):
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
        db_table = "course_members"
        unique_together = ("course_id", "user_id")
        indexes = [
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user_id} in {self.course_id} ({self.role})"
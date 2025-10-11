# assignments/models.py
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q, F


class Assignments(models.Model):
    """作業本體"""

    class Visibility(models.TextChoices):
        PUBLIC = "public", "public"
        COURSE_ONLY = "course_only", "course_only"
        HIDDEN = "hidden", "hidden"

    class Status(models.TextChoices):
        DRAFT = "draft", "draft"
        ACTIVE = "active", "active"
        CLOSED = "closed", "closed"
        ARCHIVED = "archived", "archived"

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    course = models.ForeignKey(
        "courses.Courses", on_delete=models.CASCADE, related_name="assignments"
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assignments_created",
    )

    start_time = models.DateTimeField(null=True, blank=True)
    due_time = models.DateTimeField(null=True, blank=True)

    late_penalty = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    # -1 代表不限次數；>=1 為限制次數
    max_attempts = models.IntegerField(default=-1)

    visibility = models.CharField(
        max_length=16, choices=Visibility.choices, default=Visibility.COURSE_ONLY
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )

    ip_restriction = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assignments"
        ordering = ["-created_at"]
        constraints = [
            # due_time >= start_time（任一為空則放行）
            models.CheckConstraint(
                name="ck_assign_due_after_start_or_null",
                check=Q(start_time__isnull=True)
                | Q(due_time__isnull=True)
                | Q(due_time__gte=F("start_time")),
            ),
            # 0 <= late_penalty <= 100
            models.CheckConstraint(
                name="ck_assign_late_penalty_range",
                check=Q(late_penalty__gte=Decimal("0.00"))
                & Q(late_penalty__lte=Decimal("100.00")),
            ),
            # max_attempts = -1 或 >= 1
            models.CheckConstraint(
                name="ck_assign_max_attempts_valid",
                check=Q(max_attempts=-1) | Q(max_attempts__gte=1),
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.course_id})"


class Assignment_problems(models.Model):
    """作業包含的題目與配置"""

    assignment = models.ForeignKey(
        Assignments, on_delete=models.CASCADE, related_name="assignment_problems"
    )
    problem = models.ForeignKey(
        "problems.Problem", on_delete=models.PROTECT, related_name="in_assignments"
    )

    order_index = models.PositiveIntegerField()  # 題目在作業中的排序（1 起）
    weight = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("1.00")
    )
    special_judge = models.BooleanField(default=False)

    # 覆蓋題目預設限制（為空則沿用題目設定）
    time_limit = models.IntegerField(null=True, blank=True)
    memory_limit = models.IntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    partial_score = models.BooleanField(default=True)
    hint_text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assignment_problems"
        ordering = ["order_index", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "problem"], name="uq_assignment_problem"
            ),
            models.CheckConstraint(
                name="ck_assignprob_order_ge_1", check=Q(order_index__gte=1)
            ),
            models.CheckConstraint(
                name="ck_assignprob_weight_ge_0",
                check=Q(weight__gte=Decimal("0.00")),
            ),
        ]
        indexes = [
            models.Index(
                fields=["assignment", "order_index"], name="idx_assignment_order"
            ),
        ]

    def __str__(self):
        return f"{self.assignment_id} - P{self.problem_id} ({self.order_index})"


class Assignment_tags(models.Model):
    """作業標籤"""

    assignment = models.ForeignKey(
        Assignments, on_delete=models.CASCADE, related_name="assignment_tags"
    )
    tag = models.ForeignKey(
        "problems.Tag", on_delete=models.CASCADE, related_name="in_assignments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assignment_tags"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "tag"], name="uq_assignment_tag"
            )
        ]

    def __str__(self):
        return f"{self.assignment_id}-{self.tag_id}"

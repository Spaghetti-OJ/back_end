import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

def unlimited_or_nonnegative(value: int):
    if value == -1:
        return
    if value < 0:
        raise models.ValidationError("Value must be -1 (unlimited) or non-negative.")

def default_supported_langs():
    return ["c", "cpp", "java", "python"]


class Tags(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    usage_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Problems(models.Model):
    class Difficulty(models.TextChoices):
        EASY = 'easy', 'Easy'
        MEDIUM = 'medium', 'Medium'
        HARD = 'hard', 'Hard'

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    time_limit = models.IntegerField(default=1000)
    memory_limit = models.IntegerField(default=256)
    max_score = models.IntegerField(default=100)
    is_public = models.BooleanField(default=False)
    total_submissions = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    accepted_submissions = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0), MaxValueValidator(100)])
    like_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    view_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    total_quota = models.IntegerField(
        default=-1,
        validators=[unlimited_or_nonnegative],
        help_text="The maximum number of submissions allowed for this problem. Set to -1 for unlimited submissions."
    )
    description = models.TextField()
    input_description = models.TextField(blank=True, null=True)
    output_description = models.TextField(blank=True, null=True)
    sample_input = models.TextField(blank=True, null=True)
    sample_output = models.TextField(blank=True, null=True)
    hint = models.TextField(blank=True, null=True)
    test_case_info = models.TextField(blank=True, null=True)
    supported_languages = models.JSONField(default=default_supported_langs)
    creator_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_problems')
    course_id = models.ForeignKey('courses.Courses', on_delete=models.SET_NULL, null=True, blank=True, related_name='problems')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField('Tag', through='ProblemTag', related_name='problems')

    class Meta:
        indexes = [
            models.Index(fields=['difficulty']),
            models.Index(fields=['is_public']),
        ]

    def __str__(self):
        return f"[{self.get_difficulty_display()}] {self.title}"

    def recompute_acceptance_rate(self, save=True):
        accepted = min(self.accepted_submissions, self.total_submissions)
        if self.total_submissions > 0:
            rate = (accepted / self.total_submissions) * 100
        else:
            rate = 0.0
        self.acceptance_rate = round(Decimal(rate), 2)
        if save:
            self.save(update_fields=['acceptance_rate'])


class Test_cases(models.Model):
    id = models.AutoField(primary_key=True)
    problem_id = models.ForeignKey(Problems, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField()
    expected_output = models.TextField()
    weight = models.IntegerField(default=1)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    case_group = models.IntegerField(default=1)
    file_size = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['problem', 'case_no'], name='uq_problem_case_no')
        ]
        indexes = [
            models.Index(fields=['problem', 'case_group']),
        ]

    def __str__(self):
        return f"{self.problem.id}#{self.case_no}"


class Problem_tags(models.Model):
    problem_id = models.ForeignKey(Problems, on_delete=models.CASCADE)
    tag_id = models.ForeignKey(Tags, on_delete=models.CASCADE)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_problem_tags')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['problem', 'tag'], name='uq_problem_tag')
        ]
        indexes = [
            models.Index(fields=['tag']),
            models.Index(fields=['problem', 'tag']),
        ]

    def __str__(self):
        return f"{self.problem.id}-{self.tag.id}"

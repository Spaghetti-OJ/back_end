import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

def unlimited_or_nonnegative(value: int):
    if value == -1:
        return
    if value < 0:
        raise ValidationError("Value must be -1 (unlimited) or non-negative.")

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
    max_score = models.IntegerField(default=100)
    class Visibility(models.TextChoices):
        HIDDEN = 'hidden', 'Hidden'
        COURSE = 'course', 'Course only'
        PUBLIC = 'public', 'Public'

    # Visibility of problem: hidden (only owner/admin), course (course members), public (everyone)
    # Keep field name `is_public` for backward compatibility, but store tri-state choice value.
    is_public = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.HIDDEN,
        db_index=True,
    )
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
    subtask_description = models.TextField(blank=True, null=True)
    supported_languages = models.JSONField(default=default_supported_langs)
    creator_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_problems')
    course_id = models.ForeignKey('courses.Courses', on_delete=models.PROTECT, null=False, blank=False, related_name='courses')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField('Tags', through='Problem_tags', related_name='problems')

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


class Problem_subtasks(models.Model):
    id = models.AutoField(primary_key=True)  
    problem_id = models.ForeignKey(
        'problems.Problems', 
        on_delete=models.CASCADE,
        related_name='subtasks',
        db_index=True,
    )
    subtask_no = models.PositiveIntegerField()              # 01~99
    weight = models.IntegerField(default=0)                
    time_limit_ms = models.PositiveIntegerField(null=True, blank=True)   
    memory_limit_mb = models.PositiveIntegerField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)   
    updated_at = models.DateTimeField(auto_now=True)       

    class Meta:
        db_table = 'problem_subtasks'
        constraints = [
            models.UniqueConstraint(fields=['problem_id', 'subtask_no'],
                                    name='uniq_problem_subtask_no'),
            
            models.CheckConstraint(
                check=models.Q(subtask_no__gte=1) & models.Q(subtask_no__lte=99),
                name='chk_subtask_no_1_99'
            ),
        ]
        indexes = [
            models.Index(fields=['problem_id']),  
        ]

    def __str__(self):
        return f'Subtask id={self.id} P{self.problem_id} #{self.subtask_no} (w={self.weight})'


class Test_cases(models.Model):
    
    id = models.AutoField(primary_key=True)  
    subtask_id = models.ForeignKey(
        'problems.Problem_subtasks',  
        on_delete=models.CASCADE,
        related_name='test_cases',
    )
    idx = models.PositiveIntegerField()
    
    input_path = models.CharField(max_length=500, null=True, blank=True)
    output_path = models.CharField(max_length=500, null=True, blank=True)
    input_size = models.PositiveIntegerField(default=0)
    output_size = models.PositiveIntegerField(default=0)
    checksum_in = models.CharField(max_length=64, null=True, blank=True)
    checksum_out = models.CharField(max_length=64, null=True, blank=True)

    class status(models.TextChoices):
        DRAFT = 'draft', 'draft'
        READY = 'ready', 'ready'

    status = models.CharField(
        max_length=10,
        choices=status.choices,
        default=status.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)  # default: now()

    class Meta:
        db_table = 'test_cases'
        
        constraints = [
           
            models.UniqueConstraint(fields=['subtask_id', 'idx'],
                                    name='uniq_subtask_idx'),

            models.CheckConstraint(
                check=models.Q(idx__gte=1) & models.Q(idx__lte=99),
                name='chk_idx_1_99'
            ),
            
            models.CheckConstraint(
                check=(
                    models.Q(status='draft') |
                    (
                        models.Q(status='ready') &
                        ~(
                            models.Q(input_path__isnull=True) |
                            models.Q(output_path__isnull=True) |
                            models.Q(input_path='') |
                            models.Q(output_path='')
                        )
                    )
                ),
                name='chk_ready_requires_both_paths'
            ),
        ]
        indexes = [
            models.Index(fields=['subtask_id', 'status']),  # (subtask_id, status)
        ]

    def clean(self):
        if not self.input_path and not self.output_path:
            raise ValidationError('At least one of input_path or output_path must be provided.')
        
        if self.status == self.status.READY:
            if not self.input_path or not self.output_path:
                raise ValidationError('When status is "ready", both input_path and output_path must be provided.')

    def __str__(self):
        return f'TC id={self.id} Subtask={self.subtask_id} idx={self.idx} [{self.status}]' 
    
    
class Problem_tags(models.Model):
    problem_id = models.ForeignKey(Problems, on_delete=models.CASCADE)
    tag_id = models.ForeignKey(Tags, on_delete=models.CASCADE)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_problem_tags')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['problem_id', 'tag_id'], name='uq_problem_tag')
        ]
        indexes = [
            models.Index(fields=['tag_id']),
            models.Index(fields=['problem_id', 'tag_id']),
        ]

    def __str__(self):
        return f"{self.problem_id.id}-{self.tag_id.id}"


class ProblemLike(models.Model):
    """使用者對題目的按讚紀錄

    類似於 `EditorialLike`，用於追蹤使用者對題目的按讚，以支援“我按過的題目列表”。
    """

    id = models.AutoField(primary_key=True)
    problem = models.ForeignKey(Problems, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'problem_likes'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['problem', 'user'], name='unique_problem_user_like')
        ]
        indexes = [
            models.Index(fields=['problem', 'user']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Like Problem {self.problem.id} by {self.user.username}" 

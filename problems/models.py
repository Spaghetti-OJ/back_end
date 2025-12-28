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

def default_allowed_network():
    return []

def _is_valid_domain(value: str) -> bool:
    import re
    if not isinstance(value, str):
        return False
    v = value.strip().lower()
    if not v:
        return False
    # Simple domain pattern: labels separated by '.', no scheme/path/port
    # Allows subdomains; disallows wildcards and protocols
    pattern = r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])\.)+[a-z]{2,}$"
    return re.match(pattern, v) is not None
def default_static_analysis_rules():
    """預設的靜態分析規則（空列表表示不使用）"""
    return []


def default_forbidden_functions():
    """預設的禁止函數列表（空列表）"""
    return []


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
    
    class StaticAnalysisRule(models.TextChoices):
        """靜態分析規則選項"""
        FORBID_LOOPS = 'forbid-loops', 'Forbid Loops'
        FORBID_ARRAYS = 'forbid-arrays', 'Forbid Arrays'
        FORBID_STL = 'forbid-stl', 'Forbid STL'
        FORBID_FUNCTIONS = 'forbid-functions', 'Forbid Functions'
    
    class Visibility(models.TextChoices):
        HIDDEN = 'hidden', 'Hidden'
        COURSE = 'course', 'Course only'
        PUBLIC = 'public', 'Public'

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    max_score = models.IntegerField(default=100)

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
    # Allowed outbound network hosts during sandbox evaluation; empty list blocks network.
    # Stores plain domains like "example.com"; no scheme, path, or port.
    allowed_network = models.JSONField(default=default_allowed_network)
    # --- Solution code for test generation (not editorials) ---
    solution_code = models.TextField(blank=True, null=True, help_text="Optional: reference solution code used for test generation.")
    solution_code_language = models.CharField(max_length=50, blank=True, null=True, help_text="Optional: language of solution code. Required if solution code is provided.")
    # --- Custom checker settings ---
    use_custom_checker = models.BooleanField(
        default=False, 
        help_text="Whether to use a custom checker instead of the default diff comparison."
    )
    checker_name = models.CharField(
        max_length=100, 
        default='diff', 
        blank=True, 
        help_text="Name of the checker to use. 'diff' is the standard default checker when use_custom_checker is False. Common values: 'diff' (exact text match, default), 'float' (floating-point comparison), 'token' (token-based), 'custom' (problem-specific)."
    )
    # --- Static analysis settings ---
    static_analysis_rules = models.JSONField(
        default=default_static_analysis_rules,
        blank=True,
        help_text="List of static analysis rules to apply. Valid values: 'forbid-loops', 'forbid-arrays', 'forbid-stl', 'forbid-functions'. Empty list means no static analysis."
    )
    forbidden_functions = models.JSONField(
        default=default_forbidden_functions,
        blank=True,
        help_text="List of function names that are forbidden when 'forbid-functions' rule is enabled. Required if 'forbid-functions' is in static_analysis_rules."
    )
    # --- Testcase package hash ---
    testcase_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA256 hash of the testcase package (problem.zip). Updated when testcases are uploaded."
    )
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
        constraints = [
            models.CheckConstraint(
                # If solution_code is empty or null, ok; otherwise solution_code_language must be present (not empty, not null)
                check=(
                    models.Q(solution_code__isnull=True) |
                    models.Q(solution_code='') |
                    (~models.Q(solution_code_language__isnull=True) & ~models.Q(solution_code_language=''))
                ),
                name='chk_solution_lang_required_when_code_present'
            ),
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

    def clean(self):
        # Enforce: if solution_code has content, solution_code_language must be provided
        code = (self.solution_code or '').strip()
        lang = (self.solution_code_language or '').strip()
        if code and not lang:
            raise ValidationError({'solution_code_language': '當提供 solution code 時，必須指定其語言。'})
        # Validate allowed_network entries
        nets = self.allowed_network or []
        if not isinstance(nets, (list, tuple)):
            raise ValidationError({'allowed_network': '必須為字串陣列（domain list）。'})
        bad = [d for d in nets if not _is_valid_domain(str(d))]
        if bad:
            raise ValidationError({'allowed_network': f'格式錯誤的網域：{", ".join(map(str, bad))}（請使用如 example.com 的純網域）'})

        # Validate static_analysis_rules
        valid_rules = {choice[0] for choice in self.StaticAnalysisRule.choices}
        rules = self.static_analysis_rules or []
        
        if not isinstance(rules, list):
            raise ValidationError({'static_analysis_rules': '靜態分析規則必須是列表格式。'})
        
        for rule in rules:
            if rule not in valid_rules:
                raise ValidationError({
                    'static_analysis_rules': f'無效的靜態分析規則: {rule}。有效值為: {", ".join(valid_rules)}'
                })
        
        # Validate forbidden_functions when forbid-functions is enabled
        if 'forbid-functions' in rules:
            functions = self.forbidden_functions or []
            if not isinstance(functions, list):
                raise ValidationError({'forbidden_functions': '禁止函數列表必須是列表格式。'})
            if len(functions) == 0:
                raise ValidationError({
                    'forbidden_functions': '當啟用 forbid-functions 規則時，必須至少指定一個禁止使用的函數。'
                })
            for func in functions:
                if not isinstance(func, str) or not func.strip():
                    raise ValidationError({'forbidden_functions': '函數名稱必須是非空字串。'})
            
    @property
    def use_static_analysis(self) -> bool:
        """是否啟用靜態分析"""
        return bool(self.static_analysis_rules)

    def get_static_analysis_config(self) -> dict:
        """取得靜態分析配置（供 Sandbox 使用）"""
        if not self.static_analysis_rules:
            return {'enabled': False}
        
        config = {
            'enabled': True,
            'rules': self.static_analysis_rules,
        }
        
        if 'forbid-functions' in self.static_analysis_rules:
            config['forbidden_functions'] = self.forbidden_functions or []
        
        return config

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

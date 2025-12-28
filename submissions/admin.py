from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from .models import (
    Submission, SubmissionResult, UserProblemStats,
    UserProblemSolveStatus, UserProblemQuota, CustomTest,
    Editorial, EditorialLike
)


class SubmissionResultInline(TabularInline):
    model = SubmissionResult
    extra = 0
    fields = ['test_case_index', 'status', 'execution_time', 'memory_usage', 'score']
    readonly_fields = ['test_case_index', 'status', 'execution_time', 'memory_usage', 'score']
    can_delete = False
    max_num = 0


@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    list_display = ('id', 'user', 'problem_id', 'display_language', 'display_status', 'score', 'execution_time', 'memory_usage', 'created_at')
    list_filter = ('status', 'language_type', 'is_late', 'is_custom_test')
    search_fields = ('user__username', 'problem_id', 'id')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'code_hash', 'created_at', 'judged_at', 'attempt_number')
    inlines = [SubmissionResultInline]
    list_per_page = 25
    
    fieldsets = (
        ("提交資訊", {
            "fields": ("id", "user", "problem_id", "language_type"),
        }),
        ("程式碼", {
            "fields": ("source_code", "code_hash"),
            "classes": ["collapse"],
        }),
        ("判題結果", {
            "fields": ("status", "score", "max_score", "execution_time", "memory_usage"),
        }),
        ("額外資訊", {
            "fields": ("ip_address", "user_agent", "judge_server"),
            "classes": ["collapse"],
        }),
        ("作業相關", {
            "fields": ("is_late", "is_custom_test", "penalty_applied", "attempt_number"),
        }),
        ("時間戳記", {
            "fields": ("created_at", "judged_at"),
            "classes": ["collapse"],
        }),
    )
    
    @display(description="語言", label={
        0: "info",
        1: "primary",
        2: "success",
        3: "warning",
        4: "danger",
    })
    def display_language(self, instance):
        lang_map = {0: 'C', 1: 'C++', 2: 'Python', 3: 'Java', 4: 'JavaScript'}
        return lang_map.get(instance.language_type, 'Unknown')

    @display(description="狀態", label={
        "-2": "secondary",
        "-1": "warning",
        "0": "success",
        "1": "danger",
        "2": "danger",
        "3": "warning",
        "4": "warning",
        "5": "danger",
        "6": "danger",
        "7": "warning",
    })
    def display_status(self, instance):
        status_map = {
            '-2': 'Pending (No Code)',
            '-1': 'Pending',
            '0': 'Accepted',
            '1': 'Wrong Answer',
            '2': 'Compilation Error',
            '3': 'TLE',
            '4': 'MLE',
            '5': 'Runtime Error',
            '6': 'Judge Error',
            '7': 'OLE',
        }
        return status_map.get(instance.status, 'Unknown')


@admin.register(SubmissionResult)
class SubmissionResultAdmin(ModelAdmin):
    list_display = ('id', 'submission', 'test_case_index', 'display_status', 'execution_time', 'memory_usage', 'score')
    list_filter = ('status', 'solve_status')
    search_fields = ('submission__id', 'problem_id')
    ordering = ('submission', 'test_case_index')
    readonly_fields = ('id', 'created_at')
    list_per_page = 25
    
    @display(description="狀態", label={
        "accepted": "success",
        "wrong_answer": "danger",
        "time_limit_exceeded": "warning",
        "memory_limit_exceeded": "warning",
        "runtime_error": "danger",
    })
    def display_status(self, instance):
        return instance.status


@admin.register(UserProblemStats)
class UserProblemStatsAdmin(ModelAdmin):
    list_display = ('user', 'assignment_id', 'problem_id', 'display_solve_status', 'best_score', 'total_submissions', 'last_submission_time')
    list_filter = ('solve_status',)
    search_fields = ('user__username', 'problem_id', 'assignment_id')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    
    @display(description="解題狀態", label={
        "unsolved": "danger",
        "partial": "warning",
        "solved": "success",
    })
    def display_solve_status(self, instance):
        return instance.solve_status


@admin.register(UserProblemSolveStatus)
class UserProblemSolveStatusAdmin(ModelAdmin):
    list_display = ('user', 'problem_id', 'display_solve_status', 'best_score', 'total_submissions', 'ac_submissions', 'first_solve_time')
    list_filter = ('solve_status',)
    search_fields = ('user__username', 'problem_id')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    
    @display(description="解題狀態", label={
        "never_tried": "secondary",
        "attempted": "info",
        "partial_solved": "warning",
        "fully_solved": "success",
    })
    def display_solve_status(self, instance):
        return instance.solve_status


@admin.register(UserProblemQuota)
class UserProblemQuotaAdmin(ModelAdmin):
    list_display = ('user', 'problem_id', 'assignment_id', 'total_quota', 'remaining_attempts', 'reset_at')
    list_filter = ('user',)
    search_fields = ('user__username', 'problem_id')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25


@admin.register(CustomTest)
class CustomTestAdmin(ModelAdmin):
    list_display = ('id', 'user', 'problem_id', 'display_language', 'display_status', 'execution_time', 'created_at')
    list_filter = ('status', 'language_type')
    search_fields = ('user__username', 'problem_id')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'completed_at')
    list_per_page = 25
    
    fieldsets = (
        ("測試資訊", {
            "fields": ("id", "user", "problem_id", "language_type"),
        }),
        ("程式碼與輸入", {
            "fields": ("source_code", "input_data"),
        }),
        ("輸出結果", {
            "fields": ("expected_output", "actual_output", "error_message"),
        }),
        ("執行狀態", {
            "fields": ("status", "execution_time", "memory_usage"),
        }),
        ("時間戳記", {
            "fields": ("created_at", "completed_at"),
            "classes": ["collapse"],
        }),
    )
    
    @display(description="語言")
    def display_language(self, instance):
        lang_map = {0: 'C', 1: 'C++', 2: 'Python', 3: 'Java', 4: 'JavaScript'}
        return lang_map.get(instance.language_type, 'Unknown')
    
    @display(description="狀態", label={
        "pending": "warning",
        "running": "info",
        "completed": "success",
        "error": "danger",
    })
    def display_status(self, instance):
        return instance.status


class EditorialLikeInline(TabularInline):
    model = EditorialLike
    extra = 0
    readonly_fields = ['user', 'created_at']
    can_delete = True


@admin.register(Editorial)
class EditorialAdmin(ModelAdmin):
    list_display = ('id', 'problem_id', 'author', 'display_status', 'likes_count', 'views_count', 'created_at')
    list_filter = ('status',)
    search_fields = ('problem_id', 'author__username', 'content')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'likes_count', 'views_count', 'created_at', 'updated_at')
    inlines = [EditorialLikeInline]
    list_per_page = 25
    
    fieldsets = (
        ("題解資訊", {
            "fields": ("id", "problem_id", "author"),
        }),
        ("內容", {
            "fields": ("content",),
        }),
        ("狀態", {
            "fields": ("status", "published_at"),
        }),
        ("統計", {
            "fields": ("likes_count", "views_count"),
            "classes": ["collapse"],
        }),
        ("時間戳記", {
            "fields": ("created_at", "updated_at"),
            "classes": ["collapse"],
        }),
    )
    
    @display(description="狀態", label={
        "draft": "warning",
        "published": "success",
        "archived": "secondary",
    })
    def display_status(self, instance):
        return instance.status


@admin.register(EditorialLike)
class EditorialLikeAdmin(ModelAdmin):
    list_display = ('editorial', 'user', 'created_at')
    list_filter = ('editorial',)
    search_fields = ('editorial__title', 'user__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    list_per_page = 25
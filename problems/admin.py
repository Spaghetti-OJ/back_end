from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from .models import Problems, Problem_subtasks, Test_cases, Tags, Problem_tags, ProblemLike


class ProblemTagsInline(TabularInline):
    model = Problem_tags
    extra = 0
    autocomplete_fields = ['tag_id', 'added_by']


class ProblemSubtasksInline(TabularInline):
    model = Problem_subtasks
    extra = 0
    fields = ['subtask_no', 'weight', 'time_limit_ms', 'memory_limit_mb']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Problems)
class ProblemAdmin(ModelAdmin):
    list_display = ('id', 'title', 'display_difficulty', 'display_visibility', 'total_submissions', 'accepted_submissions', 'display_acceptance_rate', 'creator_id', 'created_at')
    list_filter = ('difficulty', 'is_public', 'course_id')
    search_fields = ('title', 'description')
    inlines = [ProblemSubtasksInline, ProblemTagsInline]
    list_per_page = 25
    ordering = ['-created_at']
    readonly_fields = ['total_submissions', 'accepted_submissions', 'acceptance_rate', 'like_count', 'view_count', 'created_at', 'updated_at']
    autocomplete_fields = ['creator_id', 'course_id']
    
    fieldsets = (
        ("基本資訊", {
            "fields": ("title", "difficulty", "max_score", "is_public", "total_quota"),
        }),
        ("題目內容", {
            "fields": ("description", "input_description", "output_description", "hint", "subtask_description"),
            "classes": ["collapse"],
        }),
        ("範例", {
            "fields": ("sample_input", "sample_output"),
            "classes": ["collapse"],
        }),
        ("設定", {
            "fields": ("supported_languages", "creator_id", "course_id"),
        }),
        ("統計資料", {
            "fields": ("total_submissions", "accepted_submissions", "acceptance_rate", "like_count", "view_count"),
            "classes": ["collapse"],
        }),
        ("時間戳記", {
            "fields": ("created_at", "updated_at"),
            "classes": ["collapse"],
        }),
    )

    @display(description="難度", label={
        "easy": "success",
        "medium": "warning", 
        "hard": "danger",
    })
    def display_difficulty(self, instance):
        return instance.difficulty

    @display(description="可見性", label={
        "public": "success",
        "course": "info",
        "hidden": "warning",
    })
    def display_visibility(self, instance):
        return instance.is_public

    @display(description="通過率")
    def display_acceptance_rate(self, instance):
        return f"{instance.acceptance_rate}%"


@admin.register(Problem_subtasks)
class ProblemSubtaskAdmin(ModelAdmin):
    list_display = ('id', 'problem_id', 'subtask_no', 'weight', 'time_limit_ms', 'memory_limit_mb', 'created_at', 'updated_at')
    list_filter = ('problem_id',)
    search_fields = ('problem_id__title',)
    ordering = ('problem_id', 'subtask_no')
    list_per_page = 25


class TestCasesInline(TabularInline):
    model = Test_cases
    extra = 0
    fields = ['idx', 'status', 'input_path', 'output_path', 'input_size', 'output_size']
    readonly_fields = ['created_at']


@admin.register(Test_cases)
class TestCaseAdmin(ModelAdmin):
    list_display = ('id', 'subtask_id', 'idx', 'display_status', 'input_path', 'output_path', 'created_at')
    list_filter = ('status', 'subtask_id__problem_id')
    search_fields = ('input_path', 'output_path')
    ordering = ('subtask_id', 'idx')
    list_per_page = 25

    @display(description="狀態", label={
        "draft": "warning",
        "ready": "success",
    })
    def display_status(self, instance):
        return instance.status


@admin.register(Tags)
class TagAdmin(ModelAdmin):
    list_display = ('id', 'name', 'usage_count')
    search_fields = ('name',)
    ordering = ('id',)
    readonly_fields = ('usage_count',)
    list_per_page = 50


@admin.register(Problem_tags)
class ProblemTagAdmin(ModelAdmin):
    list_display = ('problem_id', 'tag_id', 'added_by')
    list_filter = ('tag_id',)
    search_fields = ('problem_id__title', 'tag_id__name')
    ordering = ('problem_id', 'tag_id')
    autocomplete_fields = ['problem_id', 'tag_id', 'added_by']
    list_per_page = 25


@admin.register(ProblemLike)
class ProblemLikeAdmin(ModelAdmin):
    list_display = ('id', 'problem', 'user', 'created_at')
    list_filter = ('problem', 'user')
    search_fields = ('problem__title', 'user__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    list_per_page = 25
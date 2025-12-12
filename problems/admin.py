from django.contrib import admin
from .models import Problems, Problem_subtasks, Test_cases, Tags, Problem_tags

class ProblemTagsInline(admin.TabularInline):
    model = Problem_tags
    extra = 0
    autocomplete_fields = ['tag_id', 'added_by']


class ProblemSubtaskInline(admin.TabularInline):
    model = Problem_subtasks
    extra = 0
    fields = ('subtask_no', 'weight', 'time_limit_ms', 'memory_limit_mb', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


class TestCaseInline(admin.TabularInline):
    model = Test_cases
    extra = 0
    fields = ('idx', 'status', 'input_path', 'output_path', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Problems)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'difficulty', 'is_public', 'total_submissions', 'accepted_submissions', 'acceptance_rate')
    list_filter = ('difficulty', 'is_public')
    search_fields = ('title',)
    inlines = [ProblemTagsInline, ProblemSubtaskInline]


@admin.register(Problem_subtasks)
class ProblemSubtaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'problem_id', 'subtask_no', 'weight', 'time_limit_ms', 'memory_limit_mb', 'created_at', 'updated_at')
    list_filter = ('problem_id',)
    search_fields = ('problem_id__title',)   # 依你的 Problem 欄位調整
    ordering = ('problem_id', 'subtask_no')
    inlines = [TestCaseInline]

@admin.register(Test_cases)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'subtask_id', 'idx', 'status', 'input_path', 'output_path', 'created_at')
    list_filter = ('status', 'subtask_id__problem_id')
    search_fields = ('input_path', 'output_path')
    ordering = ('subtask_id', 'idx')


# ---- Tags & Problem_tags admin ----
@admin.register(Tags)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'usage_count')
    search_fields = ('name',)
    ordering = ('id',)
    readonly_fields = ('usage_count',)
    list_per_page = 50


@admin.register(Problem_tags)
class ProblemTagAdmin(admin.ModelAdmin):
    list_display = ('problem_id', 'tag_id', 'added_by')
    list_filter = ('tag_id',)
    search_fields = ('problem_id__title', 'tag_id__name')
    ordering = ('problem_id', 'tag_id')
    autocomplete_fields = ['problem_id', 'tag_id', 'added_by']
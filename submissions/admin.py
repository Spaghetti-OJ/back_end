from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Submission, 
    SubmissionResult, 
    UserProblemStats, 
    UserProblemSolveStatus,
    UserProblemQuota,
    CustomTest,
    Editorial,
    EditorialLike
)


class SubmissionResultInline(admin.TabularInline):
    """Submission 結果的內嵌顯示"""
    model = SubmissionResult
    extra = 0
    readonly_fields = ['id', 'test_case_id', 'test_case_index', 'status', 'execution_time', 
                       'memory_usage', 'score', 'max_score', 'solve_status', 'created_at']
    fields = ['test_case_index', 'status', 'execution_time', 'memory_usage', 'score', 'max_score']
    ordering = ['test_case_index']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['short_id', 'user', 'problem_id', 'language_display', 'status_display', 
                    'score_display', 'execution_time_display', 'memory_display', 'created_at']
    list_filter = ['status', 'language_type', 'is_late', 'is_custom_test', 'created_at']
    search_fields = ['id', 'user__username', 'problem_id', 'source_code']
    readonly_fields = ['id', 'code_hash', 'created_at', 'judged_at', 'is_judged', 'execution_time_seconds']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = [
        ('基本資訊', {
            'fields': ['id', 'user', 'problem_id', 'language_type']
        }),
        ('程式碼', {
            'fields': ['source_code', 'code_hash'],
            'classes': ['collapse']
        }),
        ('判題結果', {
            'fields': ['status', 'score', 'max_score', 'execution_time', 'memory_usage', 'judge_server']
        }),
        ('提交資訊', {
            'fields': ['ip_address', 'user_agent', 'is_late', 'is_custom_test', 
                       'penalty_applied', 'attempt_number']
        }),
        ('時間戳記', {
            'fields': ['created_at', 'judged_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [SubmissionResultInline]
    
    def short_id(self, obj):
        """顯示縮短的 UUID"""
        return str(obj.id)[:8] + '...'
    short_id.short_description = 'ID'
    
    def language_display(self, obj):
        """顯示語言名稱"""
        return obj.get_language_type_display()
    language_display.short_description = '語言'
    
    def status_display(self, obj):
        """顯示狀態，帶顏色標記"""
        status_colors = {
            '0': 'green',      # Accepted
            '1': 'red',        # Wrong Answer
            '2': 'orange',     # Compilation Error
            '3': 'purple',     # TLE
            '4': 'purple',     # MLE
            '5': 'red',        # Runtime Error
            '6': 'gray',       # Judge Error
            '7': 'orange',     # OLE
            '-1': 'blue',      # Pending
            '-2': 'gray',      # Pending before upload
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = '狀態'
    
    def score_display(self, obj):
        """顯示分數"""
        return f"{obj.score}/{obj.max_score}"
    score_display.short_description = '分數'
    
    def execution_time_display(self, obj):
        """顯示執行時間"""
        if obj.execution_time == -1:
            return '-'
        return f"{obj.execution_time} ms"
    execution_time_display.short_description = '執行時間'
    
    def memory_display(self, obj):
        """顯示記憶體使用"""
        if obj.memory_usage == -1:
            return '-'
        return f"{obj.memory_usage} KB"
    memory_display.short_description = '記憶體'


@admin.register(SubmissionResult)
class SubmissionResultAdmin(admin.ModelAdmin):
    list_display = ['short_id', 'submission_link', 'problem_id', 'test_case_index', 
                    'status', 'execution_time', 'memory_usage', 'score_display']
    list_filter = ['status', 'solve_status', 'created_at']
    search_fields = ['id', 'submission__id', 'problem_id']
    readonly_fields = ['id', 'created_at']
    ordering = ['submission', 'test_case_index']
    
    def short_id(self, obj):
        return str(obj.id)[:8] + '...'
    short_id.short_description = 'ID'
    
    def submission_link(self, obj):
        return format_html(
            '<a href="/admin/submissions/submission/{}/change/">{}</a>',
            obj.submission_id,
            str(obj.submission_id)[:8] + '...'
        )
    submission_link.short_description = 'Submission'
    
    def score_display(self, obj):
        return f"{obj.score}/{obj.max_score}"
    score_display.short_description = '分數'


@admin.register(UserProblemStats)
class UserProblemStatsAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'assignment_id', 'problem_id', 'total_submissions', 
                    'best_score_display', 'solve_status', 'first_ac_time', 'updated_at']
    list_filter = ['solve_status', 'is_late', 'created_at']
    search_fields = ['user__username', 'assignment_id', 'problem_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    fieldsets = [
        ('關聯資訊', {
            'fields': ['user', 'assignment_id', 'problem_id', 'best_submission']
        }),
        ('統計資料', {
            'fields': ['total_submissions', 'best_score', 'max_possible_score', 'solve_status']
        }),
        ('時間資訊', {
            'fields': ['first_ac_time', 'last_submission_time']
        }),
        ('效能資訊', {
            'fields': ['best_execution_time', 'best_memory_usage']
        }),
        ('懲罰與遲交', {
            'fields': ['penalty_score', 'is_late']
        }),
        ('系統資訊', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def best_score_display(self, obj):
        return f"{obj.best_score}/{obj.max_possible_score}"
    best_score_display.short_description = '最佳分數'


@admin.register(UserProblemSolveStatus)
class UserProblemSolveStatusAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'problem_id', 'total_submissions', 'ac_submissions',
                    'best_score', 'solve_status', 'first_solve_time', 'updated_at']
    list_filter = ['solve_status', 'created_at']
    search_fields = ['user__username', 'problem_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    fieldsets = [
        ('關聯資訊', {
            'fields': ['user', 'problem_id']
        }),
        ('統計資料', {
            'fields': ['total_submissions', 'ac_submissions', 'best_score', 'solve_status']
        }),
        ('效能資訊', {
            'fields': ['total_execution_time', 'best_execution_time', 'best_memory_usage']
        }),
        ('時間資訊', {
            'fields': ['first_solve_time', 'last_submission_time']
        }),
        ('進階統計', {
            'fields': ['difficulty_rating', 'tags_mastered', 'mistake_patterns'],
            'classes': ['collapse']
        }),
        ('系統資訊', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(UserProblemQuota)
class UserProblemQuotaAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'problem_id', 'assignment_id', 'total_quota', 
                    'remaining_attempts', 'quota_usage', 'reset_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'problem_id', 'assignment_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    fieldsets = [
        ('關聯資訊', {
            'fields': ['user', 'problem_id', 'assignment_id']
        }),
        ('配額設定', {
            'fields': ['total_quota', 'remaining_attempts', 'reset_at']
        }),
        ('系統資訊', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def quota_usage(self, obj):
        """顯示配額使用狀況"""
        if obj.total_quota == -1:
            return "無限制"
        used = obj.total_quota - obj.remaining_attempts
        percentage = (used / obj.total_quota * 100) if obj.total_quota > 0 else 0
        color = 'green' if percentage < 50 else 'orange' if percentage < 80 else 'red'
        return format_html(
            '<span style="color: {};">{}/{} ({:.0f}%)</span>',
            color, used, obj.total_quota, percentage
        )
    quota_usage.short_description = '配額使用'


@admin.register(CustomTest)
class CustomTestAdmin(admin.ModelAdmin):
    list_display = ['short_id', 'user', 'problem_id', 'language_display', 'status', 
                    'execution_time', 'memory_usage', 'created_at']
    list_filter = ['status', 'language_type', 'created_at']
    search_fields = ['id', 'user__username', 'problem_id']
    readonly_fields = ['id', 'created_at', 'completed_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = [
        ('基本資訊', {
            'fields': ['id', 'user', 'problem_id', 'language_type']
        }),
        ('程式碼與輸入', {
            'fields': ['source_code', 'input_data', 'expected_output'],
        }),
        ('執行結果', {
            'fields': ['status', 'actual_output', 'error_message', 'execution_time', 'memory_usage']
        }),
        ('時間戳記', {
            'fields': ['created_at', 'completed_at'],
            'classes': ['collapse']
        }),
    ]
    
    def short_id(self, obj):
        return str(obj.id)[:8] + '...'
    short_id.short_description = 'ID'
    
    def language_display(self, obj):
        return obj.get_language_type_display()
    language_display.short_description = '語言'


class EditorialLikeInline(admin.TabularInline):
    """題解點讚的內嵌顯示"""
    model = EditorialLike
    extra = 0
    readonly_fields = ['user', 'created_at']
    can_delete = True
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Editorial)
class EditorialAdmin(admin.ModelAdmin):
    list_display = ['short_id', 'title', 'problem_id', 'author', 'status', 
                    'is_official', 'likes_count', 'views_count', 'created_at']
    list_filter = ['status', 'is_official', 'created_at']
    search_fields = ['id', 'title', 'problem_id', 'author__username', 'content']
    readonly_fields = ['id', 'likes_count', 'views_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = [
        ('基本資訊', {
            'fields': ['id', 'problem_id', 'author', 'title']
        }),
        ('內容', {
            'fields': ['content', 'difficulty_rating'],
        }),
        ('狀態與設定', {
            'fields': ['status', 'is_official', 'published_at']
        }),
        ('統計', {
            'fields': ['likes_count', 'views_count'],
            'classes': ['collapse']
        }),
        ('時間戳記', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [EditorialLikeInline]
    
    def short_id(self, obj):
        return str(obj.id)[:8] + '...'
    short_id.short_description = 'ID'


@admin.register(EditorialLike)
class EditorialLikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'editorial_title', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['editorial__title', 'user__username']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def editorial_title(self, obj):
        return obj.editorial.title
    editorial_title.short_description = '題解標題'

from django.contrib import admin
from .models import Assignments, Assignment_problems


class AssignmentProblemsInline(admin.TabularInline):
    model = Assignment_problems
    extra = 1
    fields = ['problem', 'order_index', 'weight', 'special_judge', 'time_limit', 'memory_limit', 'attempt_quota', 'is_active', 'partial_score', 'hint_text']
    ordering = ['order_index']


@admin.register(Assignments)
class AssignmentsAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'course', 'creator', 'start_time', 'due_time', 'status', 'created_at']
    list_filter = ['status', 'visibility', 'created_at']
    search_fields = ['title', 'course__name', 'creator__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('基本資訊', {
            'fields': ['title', 'description', 'course', 'creator']
        }),
        ('時間設定', {
            'fields': ['start_time', 'due_time']
        }),
        ('進階設定', {
            'fields': ['late_penalty', 'max_attempts', 'visibility', 'status', 'ip_restriction'],
            'classes': ['collapse']
        }),
        ('系統資訊', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [AssignmentProblemsInline]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(Assignment_problems)
class AssignmentProblemsAdmin(admin.ModelAdmin):
    list_display = ['id', 'assignment', 'problem', 'order_index', 'weight', 'special_judge']
    list_filter = ['special_judge', 'is_active', 'partial_score']
    search_fields = ['assignment__title', 'problem__title']
    ordering = ['assignment', 'order_index']
    readonly_fields = ['created_at']

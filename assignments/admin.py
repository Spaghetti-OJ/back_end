from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from .models import Assignments, Assignment_problems, Assignment_tags


class AssignmentProblemsInline(TabularInline):
    model = Assignment_problems
    extra = 0
    fields = ['problem', 'order_index', 'weight', 'partial_score', 'is_active']
    autocomplete_fields = ['problem']


class AssignmentTagsInline(TabularInline):
    model = Assignment_tags
    extra = 0
    autocomplete_fields = ['tag']


@admin.register(Assignments)
class AssignmentsAdmin(ModelAdmin):
    list_display = ('id', 'title', 'course', 'creator', 'display_visibility', 'display_status', 'start_time', 'due_time', 'created_at')
    list_filter = ('status', 'visibility', 'course')
    search_fields = ('title', 'description', 'course__name', 'creator__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['course', 'creator']
    inlines = [AssignmentProblemsInline, AssignmentTagsInline]
    list_per_page = 25
    
    fieldsets = (
        ("基本資訊", {
            "fields": ("title", "description"),
        }),
        ("關聯", {
            "fields": ("course", "creator"),
        }),
        ("時間設定", {
            "fields": ("start_time", "due_time"),
        }),
        ("作業設定", {
            "fields": ("late_penalty", "max_attempts", "visibility", "status"),
        }),
        ("進階設定", {
            "fields": ("ip_restriction",),
            "classes": ["collapse"],
        }),
        ("時間戳記", {
            "fields": ("created_at", "updated_at"),
            "classes": ["collapse"],
        }),
    )
    
    @display(description="可見性", label={
        "public": "success",
        "course_only": "info",
        "hidden": "warning",
    })
    def display_visibility(self, instance):
        return instance.visibility
    
    @display(description="狀態", label={
        "draft": "secondary",
        "active": "success",
        "closed": "warning",
        "archived": "danger",
    })
    def display_status(self, instance):
        return instance.status


@admin.register(Assignment_problems)
class AssignmentProblemsAdmin(ModelAdmin):
    list_display = ('assignment', 'problem', 'order_index', 'weight', 'display_is_active', 'display_partial_score')
    list_filter = ('is_active', 'partial_score', 'assignment')
    search_fields = ('assignment__title', 'problem__title')
    ordering = ('assignment', 'order_index')
    autocomplete_fields = ['assignment', 'problem']
    list_per_page = 25
    
    fieldsets = (
        ("關聯", {
            "fields": ("assignment", "problem", "order_index"),
        }),
        ("配分", {
            "fields": ("weight", "partial_score"),
        }),
        ("限制覆蓋", {
            "fields": ("time_limit", "memory_limit", "attempt_quota"),
            "classes": ["collapse"],
        }),
        ("設定", {
            "fields": ("special_judge", "is_active", "hint_text"),
        }),
    )
    
    @display(description="啟用", label=True)
    def display_is_active(self, instance):
        return instance.is_active
    
    @display(description="部分計分", label=True)
    def display_partial_score(self, instance):
        return instance.partial_score


@admin.register(Assignment_tags)
class AssignmentTagsAdmin(ModelAdmin):
    list_display = ('assignment', 'tag', 'created_at')
    list_filter = ('tag', 'assignment')
    search_fields = ('assignment__title', 'tag__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    autocomplete_fields = ['assignment', 'tag']
    list_per_page = 25
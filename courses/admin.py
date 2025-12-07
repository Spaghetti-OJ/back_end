from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from .models import Courses, Course_members, CourseGrade, Announcements, Batch_imports


class CourseMembersInline(TabularInline):
    model = Course_members
    extra = 0
    fields = ['user_id', 'role', 'joined_at']
    readonly_fields = ['joined_at']
    autocomplete_fields = ['user_id']


@admin.register(Courses)
class CoursesAdmin(ModelAdmin):
    list_display = (
        "id", "name", "teacher_id", "join_code",
        "semester", "academic_year",
        "student_limit", "student_count",
        "display_is_active", "created_at"
    )
    list_filter = ("is_active", "semester", "academic_year")
    search_fields = ("name", "join_code", "teacher_id__username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "student_count")
    autocomplete_fields = ['teacher_id']
    inlines = [CourseMembersInline]
    list_per_page = 25
    
    fieldsets = (
        ("基本資訊", {
            "fields": ("name", "description", "teacher_id"),
        }),
        ("學期設定", {
            "fields": ("semester", "academic_year"),
        }),
        ("課程設定", {
            "fields": ("join_code", "student_limit", "student_count", "is_active"),
        }),
        ("時間戳記", {
            "fields": ("created_at", "updated_at"),
            "classes": ["collapse"],
        }),
    )
    
    @display(description="狀態", label=True)
    def display_is_active(self, instance):
        return instance.is_active


@admin.register(Course_members)
class CourseMembersAdmin(ModelAdmin):
    list_display = ("course_id", "user_id", "display_role", "joined_at")
    list_filter = ("role", "course_id")
    search_fields = ("course_id__name", "user_id__username")
    ordering = ("-joined_at",)
    autocomplete_fields = ['course_id', 'user_id']
    list_per_page = 25
    
    @display(description="角色", label={
        "student": "info",
        "ta": "warning",
        "teacher": "success",
    })
    def display_role(self, instance):
        return instance.role


@admin.register(CourseGrade)
class CourseGradeAdmin(ModelAdmin):
    list_display = ("course", "student", "title", "score", "created_at")
    list_filter = ("course",)
    search_fields = ("course__name", "student__username", "title")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ['course', 'student']
    list_per_page = 25


@admin.register(Announcements)
class AnnouncementsAdmin(ModelAdmin):
    list_display = ("id", "title", "course_id", "creator_id", "display_is_pinned", "view_count", "created_at")
    list_filter = ("is_pinned", "course_id")
    search_fields = ("title", "content", "course_id__name", "creator_id__username")
    ordering = ("-is_pinned", "-created_at")
    readonly_fields = ("created_at", "updated_at", "view_count")
    autocomplete_fields = ['course_id', 'creator_id']
    list_per_page = 25
    
    fieldsets = (
        ("公告內容", {
            "fields": ("title", "content"),
        }),
        ("關聯設定", {
            "fields": ("course_id", "creator_id"),
        }),
        ("設定", {
            "fields": ("is_pinned", "view_count"),
        }),
        ("時間戳記", {
            "fields": ("created_at", "updated_at"),
            "classes": ["collapse"],
        }),
    )
    
    @display(description="置頂", label=True)
    def display_is_pinned(self, instance):
        return instance.is_pinned


@admin.register(Batch_imports)
class BatchImportsAdmin(ModelAdmin):
    list_display = ("id", "file_name", "course_id", "imported_by", "display_status", "file_size", "created_at")
    list_filter = ("status", "course_id")
    search_fields = ("file_name", "course_id__name", "imported_by__username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "completed_at", "error_log", "import_result")
    autocomplete_fields = ['course_id', 'imported_by']
    list_per_page = 25
    
    fieldsets = (
        ("匯入資訊", {
            "fields": ("file_name", "csv_path", "file_size"),
        }),
        ("關聯", {
            "fields": ("course_id", "imported_by"),
        }),
        ("狀態", {
            "fields": ("status", "import_result"),
        }),
        ("錯誤記錄", {
            "fields": ("error_log",),
            "classes": ["collapse"],
        }),
        ("時間戳記", {
            "fields": ("created_at", "completed_at"),
            "classes": ["collapse"],
        }),
    )
    
    @display(description="狀態", label={
        "pending": "warning",
        "processing": "info",
        "completed": "success",
        "failed": "danger",
    })
    def display_status(self, instance):
        return instance.status

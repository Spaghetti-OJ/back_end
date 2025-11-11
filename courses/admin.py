from django.contrib import admin
from .models import Courses, Course_members, CourseGrade, Announcements, Batch_imports

@admin.register(Courses)
class CoursesAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "teacher_id", "join_code",
        "semester", "academic_year",
        "student_limit", "student_count",
        "is_active", "created_at"
    )
    list_filter = ("is_active", "semester", "academic_year")
    search_fields = ("name", "join_code", "teacher_id__username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Course_members)
class CourseMembersAdmin(admin.ModelAdmin):
    list_display = ("course_id", "user_id", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("course_id__name", "user_id__username")
    ordering = ("-joined_at",)


@admin.register(CourseGrade)
class CourseGradeAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "title", "score", "created_at")
    list_filter = ("course",)
    search_fields = ("course__name", "student__username", "title")
    ordering = ("-created_at",)


@admin.register(Announcements)
class AnnouncementsAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "course_id", "creator_id", "is_pinned", "view_count", "created_at")
    list_filter = ("is_pinned", "course_id")
    search_fields = ("title", "content", "course_id__name", "creator_id__username")
    ordering = ("-is_pinned", "-created_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Batch_imports)
class BatchImportsAdmin(admin.ModelAdmin):
    list_display = ("id", "file_name", "course_id", "imported_by", "status", "file_size", "created_at")
    list_filter = ("status", "course_id")
    search_fields = ("file_name", "course_id__name", "imported_by__username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "completed_at", "error_log")

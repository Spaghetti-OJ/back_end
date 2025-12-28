from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import CodeDraft


@admin.register(CodeDraft)
class CodeDraftAdmin(ModelAdmin):
    """程式碼草稿 Admin"""
    
    list_display = (
        'id', 'user', 'problem_id', 'assignment_id', 'title',
        'display_language', 'display_auto_saved', 'updated_at'
    )
    list_filter = ('language_type', 'auto_saved', 'updated_at')
    search_fields = ('user__username', 'problem_id', 'title')
    ordering = ('-updated_at',)
    list_per_page = 25
    
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ("草稿資訊", {
            "fields": ("id", "user", "problem_id", "assignment_id", "title"),
        }),
        ("程式碼", {
            "fields": ("language_type", "source_code"),
        }),
        ("設定", {
            "fields": ("auto_saved",),
        }),
        ("時間戳記", {
            "fields": ("created_at", "updated_at"),
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
    
    @display(description="自動儲存", label=True)
    def display_auto_saved(self, instance):
        return instance.auto_saved

from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import CopycatReport


@admin.register(CopycatReport)
class CopycatReportAdmin(ModelAdmin):
    """抄襲檢測報告 Admin - 唯讀"""
    
    list_display = (
        'id', 'problem_id', 'requester', 'display_status', 
        'moss_url_link', 'created_at', 'updated_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('problem_id', 'requester__username')
    ordering = ('-created_at',)
    list_per_page = 25
    
    readonly_fields = (
        'problem_id', 'requester', 'moss_url', 'status',
        'error_message', 'created_at', 'updated_at'
    )
    
    fieldsets = (
        ("報告資訊", {
            "fields": ("problem_id", "requester", "status"),
        }),
        ("MOSS 結果", {
            "fields": ("moss_url",),
        }),
        ("錯誤訊息", {
            "fields": ("error_message",),
            "classes": ["collapse"],
        }),
        ("時間戳記", {
            "fields": ("created_at", "updated_at"),
            "classes": ["collapse"],
        }),
    )
    
    @display(description="狀態", label={
        "pending": "warning",
        "success": "success",
        "failed": "danger",
    })
    def display_status(self, instance):
        return instance.status
    
    def moss_url_link(self, obj):
        if obj.moss_url:
            from django.utils.html import format_html
            return format_html('<a href="{}" target="_blank">查看報告</a>', obj.moss_url)
        return "-"
    moss_url_link.short_description = "MOSS 報告"
    
    def has_add_permission(self, request):
        return False  
    
    def has_change_permission(self, request, obj=None):
        return False  
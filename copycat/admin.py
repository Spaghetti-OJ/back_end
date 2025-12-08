from django.contrib import admin
from .models import CopycatReport
@admin.register(CopycatReport)
class CopycatReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'problem_id', 'requester', 'status', 
        'created_at', 'updated_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('problem_id', 'requester__username')
    readonly_fields = (
        'problem_id', 'requester', 'moss_url', 'status',
        'error_message', 'created_at', 'updated_at'
    )
    
    def has_add_permission(self, request):
        return False  
    
    def has_change_permission(self, request, obj=None):
        return False  
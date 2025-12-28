from django.contrib import admin
from .models import LoginLog, UserActivity 

# ==============================================================================
# 1. 註冊 LoginLog
# ==============================================================================

@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """
    客製化 LoginLog 在 Django Admin 中的顯示方式。
    日誌應為唯讀 (Read-Only)。
    """
    
    
    list_display = (
        'username', 
        'login_status', 
        'ip_address', 
        'created_at',
        'user'  
    )
    
    list_filter = (
        'login_status', 
        'created_at'   
    )
    
    search_fields = ('username', 'ip_address', 'user__username')
    
    date_hierarchy = 'created_at'
    
    #read-only
    readonly_fields = (
        'user', 'username', 'login_status', 'ip_address', 
        'user_agent', 'location', 'created_at'
    )

    # permission
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False

# ==============================================================================
# 2. 註冊 UserActivity (使用者活動)
# ==============================================================================

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """
    客製化 UserActivity 在 Django Admin 中的顯示方式。
    日誌應為唯讀 (Read-Only)。
    """

    list_display = (
        'user', 
        'activity_type', 
        'success', 
        'ip_address', 
        'created_at',
        'content_object' 
    )
    
    list_filter = (
        'activity_type',
        'success',       
        'created_at'
    )
    
    search_fields = ('user__username', 'description', 'ip_address', 'object_id')

    readonly_fields = (
        'user', 'activity_type', 'content_type', 'object_id',
        'description', 'ip_address', 'user_agent', 'metadata',
        'success', 'created_at'
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

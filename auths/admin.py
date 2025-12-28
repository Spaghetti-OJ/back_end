from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import LoginLog, UserActivity, EmailVerificationToken, PasswordResetToken


@admin.register(LoginLog)
class LoginLogAdmin(ModelAdmin):
    """登入紀錄 Admin - 唯讀"""
    
    list_display = (
        'username', 
        'display_login_status', 
        'ip_address',
        'location',
        'created_at',
        'user'  
    )
    
    list_filter = ('login_status', 'created_at')
    search_fields = ('username', 'ip_address', 'user__username', 'location')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 50
    
    readonly_fields = (
        'user', 'username', 'login_status', 'ip_address', 
        'user_agent', 'location', 'created_at'
    )
    
    fieldsets = (
        ("登入資訊", {
            "fields": ("username", "user", "login_status"),
        }),
        ("來源資訊", {
            "fields": ("ip_address", "location"),
        }),
        ("裝置資訊", {
            "fields": ("user_agent",),
            "classes": ["collapse"],
        }),
        ("時間戳記", {
            "fields": ("created_at",),
        }),
    )
    
    @display(description="登入狀態", label={
        "success": "success",
        "failed_credentials": "danger",
        "failed_user_not_found": "danger",
        "blocked_ip": "warning",
        "blocked_account": "warning",
    })
    def display_login_status(self, instance):
        return instance.login_status

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserActivity)
class UserActivityAdmin(ModelAdmin):
    """使用者活動紀錄 Admin - 唯讀"""

    list_display = (
        'user', 
        'display_activity_type', 
        'display_success', 
        'ip_address', 
        'created_at',
        'content_object' 
    )
    
    list_filter = ('activity_type', 'success', 'created_at')
    search_fields = ('user__username', 'description', 'ip_address')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 50

    readonly_fields = (
        'user', 'activity_type', 'content_type', 'object_id',
        'description', 'ip_address', 'user_agent', 'metadata',
        'success', 'created_at'
    )
    
    fieldsets = (
        ("活動資訊", {
            "fields": ("user", "activity_type", "success", "description"),
        }),
        ("關聯物件", {
            "fields": ("content_type", "object_id"),
            "classes": ["collapse"],
        }),
        ("來源資訊", {
            "fields": ("ip_address", "user_agent"),
            "classes": ["collapse"],
        }),
        ("額外資料", {
            "fields": ("metadata",),
            "classes": ["collapse"],
        }),
        ("時間戳記", {
            "fields": ("created_at",),
        }),
    )
    
    @display(description="活動類型", label={
        "login": "info",
        "logout": "secondary",
        "submit": "success",
        "view_problem": "info",
        "download_testcase": "warning",
    })
    def display_activity_type(self, instance):
        return instance.activity_type
    
    @display(description="成功", label=True)
    def display_success(self, instance):
        return instance.success
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(ModelAdmin):
    """Email 驗證 Token Admin - 唯讀"""
    
    list_display = ('user', 'token_preview', 'display_used', 'display_expired', 'created_at')
    list_filter = ('used', 'created_at')
    search_fields = ('user__username', 'user__email', 'token')
    ordering = ('-created_at',)
    list_per_page = 25
    readonly_fields = ('user', 'token', 'created_at', 'used')
    
    def token_preview(self, obj):
        return f"{obj.token[:8]}..." if obj.token else "-"
    token_preview.short_description = "Token"
    
    @display(description="已使用", label=True)
    def display_used(self, instance):
        return instance.used
    
    @display(description="已過期", label={
        True: "danger",
        False: "success",
    })
    def display_expired(self, instance):
        return instance.is_expired
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(ModelAdmin):
    """密碼重設 Token Admin - 唯讀"""
    
    list_display = ('user', 'token_preview', 'display_used', 'expires_at', 'created_at')
    list_filter = ('used', 'created_at')
    search_fields = ('user__username', 'user__email', 'token')
    ordering = ('-created_at',)
    list_per_page = 25
    readonly_fields = ('user', 'token', 'created_at', 'expires_at', 'used')
    
    def token_preview(self, obj):
        return f"{obj.token[:8]}..." if obj.token else "-"
    token_preview.short_description = "Token"
    
    @display(description="已使用", label=True)
    def display_used(self, instance):
        return instance.used
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

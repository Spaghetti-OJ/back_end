from django.contrib import admin
from .models import ApiToken, UserActivity, LoginLog

@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'prefix', 'created_at', 'expires_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'name')
    readonly_fields = ('prefix', 'token_hash')

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'description', 'created_at', 'ip_address', 'success')
    list_filter = ('activity_type', 'created_at', 'success')
    search_fields = ('user__username', 'description')

@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ('username', 'login_status', 'ip_address', 'created_at')
    list_filter = ('login_status', 'created_at')
    search_fields = ('username', 'ip_address')
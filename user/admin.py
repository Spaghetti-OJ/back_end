from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.decorators import display
from .models import User, UserProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('個人資訊', {'fields': ('real_name', 'email')}),
        ('角色', {'fields': ('identity',)}),
        ('權限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'real_name', 'identity', 'password1', 'password2')
        }),
    )
    list_display = ('username', 'email', 'real_name', 'display_identity', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('identity', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'real_name')
    ordering = ('-date_joined',)
    list_per_page = 25
    
    @display(description="身份", label={
        "student": "info",
        "teacher": "success",
        "admin": "danger",
    })
    def display_identity(self, instance):
        return instance.identity


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('user', 'student_id', 'display_email_verified', 'updated_at')
    list_filter = ('email_verified',)
    search_fields = ('user__username', 'student_id')
    ordering = ('-updated_at',)
    readonly_fields = ('updated_at',)
    list_per_page = 25
    
    fieldsets = (
        ("使用者資訊", {
            "fields": ("user", "student_id", "email_verified"),
        }),
        ("個人資料", {
            "fields": ("bio", "avatar"),
        }),
        ("時間戳記", {
            "fields": ("updated_at",),
            "classes": ["collapse"],
        }),
    )
    
    @display(description="Email 驗證", label=True)
    def display_email_verified(self, instance):
        return instance.email_verified
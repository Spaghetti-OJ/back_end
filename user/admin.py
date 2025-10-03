from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, UserProfile

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('real_name', 'email')}),
        ('Roles', {'fields': ('identity',)}),
        ('Permissions', {'fields': ('is_active','is_staff','is_superuser','groups','user_permissions')}),
        ('Important dates', {'fields': ('last_login','date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('username','email','real_name','identity','password1','password2')}),
    )
    list_display = ('username','email','real_name','identity','is_staff')
    search_fields = ('username','email','real_name')
    ordering = ('date_joined',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user','student_id','email_verified','updated_at')
    search_fields = ('user__username','student_id')
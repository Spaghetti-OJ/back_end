# auths/admin.py

from django.contrib import admin
from .models import LoginLog, UserActivity # 導入你的模型

# ==============================================================================
# 1. 註冊 LoginLog (登入日誌)
# ==============================================================================

@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """
    客製化 LoginLog 在 Django Admin 中的顯示方式。
    日誌應為唯讀 (Read-Only)。
    """
    
    # 列表頁顯示的欄位
    list_display = (
        'username', 
        'login_status', 
        'ip_address', 
        'created_at',
        'user'  # 'user' 欄位可能為 None (登入失敗時)
    )
    
    # 右側的過濾器
    list_filter = (
        'login_status', # 讓你快速篩選「成功」或「失敗」
        'created_at'    # 依時間過濾
    )
    
    # 頂部的搜尋欄位
    # 允許搜尋 `username`, `ip_address`
    # 透過 `user__username` 可以搜尋關聯 User 的 username
    search_fields = ('username', 'ip_address', 'user__username')
    
    # 列表頂部增加日期導覽列
    date_hierarchy = 'created_at'
    
    # --- 安全性設定：讓日誌變成唯讀 ---
    
    # 讓所有欄位在編輯頁面都變成唯讀
    readonly_fields = (
        'user', 'username', 'login_status', 'ip_address', 
        'user_agent', 'location', 'created_at'
    )

    # 在 admin 中隱藏「新增 (Add)」按鈕
    def has_add_permission(self, request):
        return False

    # 在 admin 中隱藏「修改 (Change)」按鈕
    def has_change_permission(self, request, obj=None):
        return False
        
    # (可選) 如果你也想防止刪除，可以取消註解下面這行
    # def has_delete_permission(self, request, obj=None):
    #     return False

# ==============================================================================
# 2. 註冊 UserActivity (使用者活動)
# ==============================================================================

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """
    客製化 UserActivity 在 Django Admin 中的顯示方式。
    日誌應為唯讀 (Read-Only)。
    """
    
    # 列表頁顯示的欄位
    list_display = (
        'user', 
        'activity_type', 
        'success', 
        'ip_address', 
        'created_at',
        'content_object' # 顯示它所關聯的物件 (例如某個 Problem)
    )
    
    # 右側的過濾器
    list_filter = (
        'activity_type', # 篩選「提交程式碼」、「查看題目」等
        'success',       # 篩選「成功」或「失敗」
        'created_at'
    )
    
    # 頂部的搜尋欄位
    # 允許搜尋 `user__username`, `description`, `ip_address`
    # `object_id` 允許你貼上某個 Submission 的 UUID 來反查
    search_fields = ('user__username', 'description', 'ip_address', 'object_id')

    # 列表頂部增加日期
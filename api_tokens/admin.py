# api_tokens/admin.py
from django.contrib import admin
from .models import ApiToken  # 導入你的 ApiToken 模型

@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    # 讓後台列表顯示這幾個欄位
    list_display = ('user', 'name', 'prefix', 'created_at', 'expires_at')
    # 增加一個搜尋欄位（可以透過 user 的 username 搜尋）
    search_fields = ('user__username', 'name')
    # 增加過濾器
    list_filter = ('created_at', 'expires_at')
    # 讓 token_hash 和 prefix 在編輯頁面中變成 "唯讀"
    readonly_fields = ('token_hash', 'prefix')
# api_tokens/admin.py

from django.contrib import admin, messages
from .models import ApiToken
# 引入我們寫好的生成邏輯
from .services import generate_api_token

@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    # 列表頁顯示的欄位
    list_display = ('name', 'user', 'prefix', 'usage_count', 'created_at')
    
    # 編輯頁面：隱藏不該手動改的欄位，設為唯讀
    readonly_fields = ('prefix', 'token_hash', 'created_at', 'last_used_at', 'last_used_ip', 'usage_count')
    
    # 編輯頁面：只顯示這些欄位讓你填 (Hash 會自動生成，所以不顯示)
    fields = ('user', 'name', 'permissions', 'expires_at', 'is_active')

    # ⬇️ 重寫儲存邏輯 (核心解法) ⬇️
    def save_model(self, request, obj, form, change):
        """
        當管理員在後台按下 'Save' 時觸發。
        """
        # 如果是「新增」 (change is False) 且還沒有 hash
        if not change and not obj.token_hash:
            # 1. 呼叫我們的服務生成 Token
            full_token, token_hash = generate_api_token()
            
            # 2. 填入模型
            obj.token_hash = token_hash
            obj.prefix = full_token[:8]
            
            # 3. 關鍵步驟：利用 Django 的訊息框架，把完整的 Key 彈出顯示給管理員
            # 這樣你才看得到這把鑰匙！
            messages.success(request, f"✅ Token 已成功建立！請立即複製您的金鑰（只顯示這一次）： {full_token}")
            
        # 4. 執行真正的存檔
        super().save_model(request, obj, form, change)
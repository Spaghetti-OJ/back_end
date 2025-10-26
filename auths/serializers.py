# auths/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ApiToken, UserActivity, LoginLog

User = get_user_model()

# ==============================================================================
# 1. ApiToken Serializers (對應 ApiToken Model)
# ==============================================================================

class ApiTokenCreateSerializer(serializers.ModelSerializer):
    """
    用於「建立」ApiToken 的 Serializer。
    對應 POST /me/api-tokens 的請求內文 (body)。
    只包含使用者需要輸入的欄位。
    """
    class Meta:
        model = ApiToken
        # 使用者在建立 Token 時，只需要提供這幾個資訊
        fields = ['name', 'permissions', 'expires_at']
        # 'permissions' 和 'expires_at' 都不是必填的
        extra_kwargs = {
            'permissions': {'required': False},
            'expires_at': {'required': False}
        }


class ApiTokenListSerializer(serializers.ModelSerializer):
    """
    用於「列出」ApiToken 的 Serializer。
    對應 GET /me/api-tokens 的回應內容。
    只顯示安全的、用於列表的資訊，絕對不能包含 token_hash。
    """
    # 從 Model 的 @property 獲取 is_expired 狀態
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = ApiToken
        # 在列表頁，我們想讓使用者看到這些資訊來辨識他的 Token
        fields = [
            'id', 
            'name', 
            'prefix', 
            'permissions', 
            'usage_count', 
            'last_used_at', 
            'last_used_ip',
            'created_at', 
            'expires_at', 
            'is_active',
            'is_expired' # 這個欄位來自上面的 ReadOnlyField
        ]


# ==============================================================================
# 2. UserActivity Serializer (對應 UserActivity Model)
# ==============================================================================

class UserActivitySerializer(serializers.ModelSerializer):
    """
    用於顯示使用者活動紀錄的 Serializer。
    對應 GET /me/activities 和 GET /admin/users/{userId}/activities 的回應。
    """
    # 為了讓輸出的 JSON 更易讀，我們把 ForeignKey 關聯的 user 物件換成它的字串表示 (username)
    user = serializers.StringRelatedField()
    
    # 為了顯示中文名稱 ('登入') 而不是英文鍵 ('login')
    activity_type = serializers.CharField(source='get_activity_type_display')

    # 顯示關聯物件的字串表示，例如 'Problem: Two Sum'
    # 我們的 Model __str__ 裡有更詳細的表示，但這裡用 StringRelatedField 獲取基本資訊
    content_object = serializers.StringRelatedField()

    class Meta:
        model = UserActivity
        fields = [
            'id',
            'user',
            'activity_type',
            'content_object', # 顯示關聯的物件
            'description',
            'ip_address',
            'user_agent',
            'created_at',
            'success'
        ]


# ==============================================================================
# 3. LoginLog Serializer (對應 LoginLog Model)
# ==============================================================================

class LoginLogSerializer(serializers.ModelSerializer):
    """
    用於顯示登入日誌的 Serializer。
    對應 GET /me/login-logs 和 GET /admin/users/{userId}/login-logs 的回應。
    """
    # 為了顯示中文名稱 ('成功') 而不是英文鍵 ('success')
    login_status = serializers.CharField(source='get_login_status_display')

    class Meta:
        model = LoginLog
        fields = [
            'id',
            'username',
            'login_status',
            'ip_address',
            'user_agent',
            'location',
            'created_at'
        ]
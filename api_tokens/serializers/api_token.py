# auths/serializers/api_token.py
from rest_framework import serializers
from api_tokens.models import ApiToken

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
from rest_framework import serializers
from ..models import ApiToken
from ..scopes import Scopes

VALID_SCOPES = set(Scopes.all_scopes())

class ApiTokenCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiToken
        fields = ['name', 'permissions', 'expires_at']
        extra_kwargs = {
            'permissions': {'required': False},
            'expires_at': {'required': False}
        }

    def validate_permissions(self, value):
        """
        驗證 permissions 欄位：
        1. 必須是 list
        2. 裡面的每一個字串都必須在 VALID_SCOPES 裡
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Permissions 必須是一個列表 (List)。")
        
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Permissions 列表包含重複的權限範圍。")
        
        invalid_scopes = set(value) - VALID_SCOPES
        if invalid_scopes:
            raise serializers.ValidationError(
                f"包含無效的權限範圍: {', '.join(invalid_scopes)}。合法的權限為: {', '.join(VALID_SCOPES)}"
            )
        
        return value

class ApiTokenListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiToken
        fields = [
            'id', 'name', 'prefix', 'permissions', 
            'usage_count', 'last_used_at', 'last_used_ip', 
            'created_at', 'expires_at', 'is_active', 'is_expired'
        ]
        read_only_fields = fields
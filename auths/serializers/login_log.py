from rest_framework import serializers
from ..models import LoginLog

class LoginLogSerializer(serializers.ModelSerializer):
    """
    用於顯示登入日誌的 Serializer。
    對應 GET /me/login-logs 和 GET /admin/users/{userId}/login-logs 的回應。
    """

    login_status = serializers.CharField(source='get_login_status_display', read_only=True)

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
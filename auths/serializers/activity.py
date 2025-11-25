from rest_framework import serializers
from ..models import UserActivity

class UserActivitySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user', 'username', 'activity_type', 
            'description', 'ip_address', 'user_agent', 
            'success', 'created_at', 'metadata'
        ]
        
        read_only_fields = ['user', 'ip_address', 'user_agent', 'created_at']
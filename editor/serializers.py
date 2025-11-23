# editor/serializers.py
"""
草稿序列化器
"""
from rest_framework import serializers
from .models import CodeDraft
from django.contrib.auth import get_user_model

User = get_user_model()


class DraftSerializer(serializers.ModelSerializer):
    """草稿詳情序列化器"""
    
    user = serializers.SerializerMethodField()
    
    class Meta:
        model = CodeDraft
        fields = [
            'id',
            'user',
            'problem_id',
            'assignment_id',
            'language_type',
            'source_code',
            'title',
            'auto_saved',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_user(self, obj):
        """返回用戶基本信息"""
        return {
            'id': str(obj.user.id),
            'username': obj.user.username,
            'email': obj.user.email
        }


class DraftCreateUpdateSerializer(serializers.ModelSerializer):
    """草稿創建/更新序列化器"""
    
    class Meta:
        model = CodeDraft
        fields = [
            'problem_id',
            'assignment_id',
            'language_type',
            'source_code',
            'title',
            'auto_saved'
        ]
    
    def validate_language_type(self, value):
        """驗證語言類型"""
        valid_languages = [choice[0] for choice in CodeDraft.LANGUAGE_CHOICES]
        if value not in valid_languages:
            raise serializers.ValidationError(
                f"Invalid language type. Must be one of: {valid_languages}"
            )
        return value
    
    def validate_source_code(self, value):
        """驗證源代碼不為空"""
        if not value or not value.strip():
            raise serializers.ValidationError("Source code cannot be empty")
        return value

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
    
    # 最大代碼大小：64KB（與 Submission API 一致）
    MAX_CODE_SIZE = 65535
    
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
        """驗證源代碼不為空且不超過大小限制"""
        if not value or not value.strip():
            raise serializers.ValidationError("Source code cannot be empty")
        
        # 檢查代碼大小（使用 UTF-8 編碼計算字節數）
        code_size = len(value.encode('utf-8'))
        if code_size > self.MAX_CODE_SIZE:
            raise serializers.ValidationError(
                f"Source code too large. Maximum size is {self.MAX_CODE_SIZE} bytes (64KB), "
                f"but got {code_size} bytes"
            )
        
        return value

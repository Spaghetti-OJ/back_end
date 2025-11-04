# submissions/serializers.py
from rest_framework import serializers
from django.core.validators import MaxLengthValidator
from .models import (
    Submission, SubmissionResult, UserProblemStats, UserProblemSolveStatus,
    UserProblemQuota, CustomTest, CodeDraft, Editorial, EditorialLike
)
import hashlib

class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = '__all__'
        read_only_fields = [
            'id', 'code_hash', 'status', 'score', 'execution_time',
            'memory_usage', 'judged_at', 'created_at'
        ]

class SubmissionCreateSerializer(serializers.ModelSerializer):
    ### 此處我只有限制 code 的大小跟最小長度
    ### 其他的安全性檢查交給判題系統的沙盒
    source_code = serializers.CharField(
        max_length=65535,  # 64KB 限制
        min_length=1,
        error_messages={
            'max_length': '程式碼長度不能超過 64KB',
            'min_length': '程式碼不能為空',
            'blank': '請輸入程式碼'
        }
    )
    
    language_type = serializers.ChoiceField(
        choices=Submission.LANGUAGE_CHOICES,
        error_messages={
            'invalid_choice': '不支援的程式語言'
        }
    )
    
    problem_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': '題目 ID 必須大於 0'
        }
    )
    
    class Meta:
        model = Submission
        fields = ['problem_id', 'language_type', 'source_code']
    
    def validate_problem_id(self, value):
        """驗證題目是否存在"""
        # 這裡應該檢查 Problem model，假設你有 Problem model
        # from problems.models import Problem
        # if not Problem.objects.filter(id=value).exists():
        #     raise serializers.ValidationError('題目不存在')
        return value
    
    def validate(self, attrs):
        """整體驗證"""
        user = self.context['request'].user
        
        # 確保使用者已認證且帳號啟用
        if not user or not user.is_authenticated:
            raise serializers.ValidationError('使用者未認證')
        
        if not user.is_active:
            raise serializers.ValidationError('使用者帳號已停用')
        
        # 檢查用戶是否已經提交過相同的程式碼
        problem_id = attrs['problem_id']
        source_code = attrs['source_code']
        
        # 基本資料品質檢查
        if not source_code.strip():
            raise serializers.ValidationError('程式碼不能只包含空白字元')
        
        # 計算 hash
        code_hash = hashlib.sha256(source_code.encode()).hexdigest()
        
        # 檢查是否重複提交
        if Submission.objects.filter(
            user=user, 
            problem_id=problem_id, 
            code_hash=code_hash
        ).exists():
            raise serializers.ValidationError(
                '您已經提交過相同的程式碼'
            )
        
        return attrs
    
    def create(self, validated_data):
        # 雙重確認使用者認證（安全防護）
        request = self.context['request']
        if not request.user.is_authenticated:
            raise serializers.ValidationError('使用者認證失敗')
        
        # 強制設定 user（防止偽造）
        validated_data['user'] = request.user
        
        # 計算並設定 code_hash
        source_code = validated_data['source_code']
        validated_data['code_hash'] = hashlib.sha256(
            source_code.encode()
        ).hexdigest()
        
        # 設定 IP 和 User Agent（用於審計）
        validated_data['ip_address'] = self.get_client_ip(request)
        validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        # 安全日誌（可選）
        import logging
        logger = logging.getLogger('submission_audit')
        logger.info(
            f'New submission: user_id={request.user.id}, '
            f'problem_id={validated_data["problem_id"]}, '
            f'ip={validated_data["ip_address"]}'
        )
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """獲取客戶端 IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SubmissionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionResult
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class UserProblemStatsSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    best_submission_id = serializers.UUIDField(source='best_submission.id', read_only=True)
    
    class Meta:
        model = UserProblemStats
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserProblemSolveStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserProblemSolveStatus
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserProblemQuotaSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserProblemQuota
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomTestCreateSerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(
        max_length=65535,
        min_length=1,
        error_messages={
            'max_length': '程式碼長度不能超過 64KB',
            'min_length': '程式碼不能為空',
        }
    )
    
    language_type = serializers.ChoiceField(
        choices=CustomTest.LANGUAGE_CHOICES,
        error_messages={
            'invalid_choice': '不支援的程式語言'
        }
    )
    
    problem_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': '題目 ID 必須大於 0'
        }
    )
    
    class Meta:
        model = CustomTest
        fields = ['problem_id', 'language_type', 'source_code', 'input_data', 'expected_output']
    
    def validate_source_code(self, value):
        """基本資料品質驗證"""
        if not value.strip():
            raise serializers.ValidationError('程式碼不能只包含空白字元')
        return value
    
    def validate(self, attrs):
        """整體驗證"""
        user = self.context['request'].user
        
        if not user or not user.is_authenticated:
            raise serializers.ValidationError('使用者未認證')
        
        if not user.is_active:
            raise serializers.ValidationError('使用者帳號已停用')
        
        return attrs
    
    def create(self, validated_data):
        request = self.context['request']
        if not request.user.is_authenticated:
            raise serializers.ValidationError('使用者認證失敗')
        
        validated_data['user'] = request.user
        return super().create(validated_data)


class CustomTestSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = CustomTest
        fields = '__all__'
        read_only_fields = [
            'id', 'user', 'status', 'actual_output', 'execution_time', 
            'memory_usage', 'error_message', 'created_at', 'completed_at'
        ]


class CodeDraftCreateSerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(
        max_length=65535,
        min_length=1,
        error_messages={
            'max_length': '程式碼長度不能超過 64KB',
            'min_length': '程式碼不能為空',
        }
    )
    
    language_type = serializers.ChoiceField(
        choices=CodeDraft.LANGUAGE_CHOICES,
        error_messages={
            'invalid_choice': '不支援的程式語言'
        }
    )
    
    problem_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': '題目 ID 必須大於 0'
        }
    )
    
    class Meta:
        model = CodeDraft
        fields = ['problem_id', 'assignment_id', 'language_type', 'source_code', 'title', 'auto_saved']
    
    def validate_source_code(self, value):
        """基本資料品質驗證"""
        if not value.strip():
            raise serializers.ValidationError('程式碼不能只包含空白字元')
        return value
    
    def create(self, validated_data):
        request = self.context['request']
        validated_data['user'] = request.user
        return super().create(validated_data)


class CodeDraftSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = CodeDraft
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class EditorialCreateSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        max_length=255,
        min_length=1,
        error_messages={
            'max_length': '標題長度不能超過 255 字元',
            'min_length': '標題不能為空',
        }
    )
    
    content = serializers.CharField(
        min_length=10,
        error_messages={
            'min_length': '內容至少需要 10 個字元',
        }
    )
    
    problem_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': '題目 ID 必須大於 0'
        }
    )
    
    class Meta:
        model = Editorial
        fields = ['problem_id', 'title', 'content', 'difficulty_rating', 'is_official']
    
    def validate_title(self, value):
        """標題驗證"""
        if not value.strip():
            raise serializers.ValidationError('標題不能只包含空白字元')
        return value.strip()
    
    def validate_content(self, value):
        """內容驗證"""
        if not value.strip():
            raise serializers.ValidationError('內容不能只包含空白字元')
        return value.strip()
    
    def create(self, validated_data):
        request = self.context['request']
        validated_data['author'] = request.user
        return super().create(validated_data)


class EditorialSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    is_liked_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Editorial
        fields = '__all__'
        read_only_fields = [
            'id', 'author', 'likes_count', 'views_count', 
            'created_at', 'updated_at', 'published_at'
        ]
    
    def get_is_liked_by_user(self, obj):
        """檢查當前使用者是否已按讚"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return EditorialLike.objects.filter(
                editorial=obj, 
                user=request.user
            ).exists()
        return False


class EditorialLikeSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    editorial_title = serializers.CharField(source='editorial.title', read_only=True)
    
    class Meta:
        model = EditorialLike
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at']
    
    def create(self, validated_data):
        request = self.context['request']
        validated_data['user'] = request.user
        
        # 檢查是否已經按過讚
        editorial = validated_data['editorial']
        if EditorialLike.objects.filter(editorial=editorial, user=request.user).exists():
            raise serializers.ValidationError('您已經對這篇題解按過讚了')
        
        return super().create(validated_data)
# submissions/serializers.py
from rest_framework import serializers
from django.core.validators import MaxLengthValidator
from .models import (
    Submission, SubmissionResult, UserProblemStats, UserProblemSolveStatus,
    UserProblemQuota, CustomTest, Editorial, EditorialLike
)
import hashlib

class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = '__all__'
        read_only_fields = [
            'id', 'code_hash', 'status', 'score', 'execution_time',
            'memory_usage', 'judged_at', 'created_at', 'is_custom_test'
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
        # 檢查 Problem model 是否存在
        from problems.models import Problems
        if not Problems.objects.filter(id=value).exists():
            raise serializers.ValidationError('題目不存在')
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
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'SubmissionBaseCreateSerializer.create() called')
        logger.info(f'validated_data keys: {validated_data.keys()}')
        logger.info(f'has source_code: {"source_code" in validated_data}')
        
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
        
        # 設定初始狀態為 Pending
        validated_data['status'] = '-1'  # Pending
        
        # 安全日誌（可選）
        import logging
        logger = logging.getLogger('submission_audit')
        logger.info(
            f'New submission: user_id={request.user.id}, '
            f'problem_id={validated_data["problem_id"]}, '
            f'ip={validated_data["ip_address"]}'
        )
        
        # 創建 Submission
        submission = super().create(validated_data)
        
        # 觸發 Celery 任務送到 Sandbox
        from .tasks import submit_to_sandbox_task
        submit_to_sandbox_task.delay(str(submission.id))
        logger.info(f'Queued submission {submission.id} for Sandbox judging')
        
        return submission
    
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
        trim_whitespace=False,  # 保持與 input_data/expected_output 一致
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
    
    input_data = serializers.CharField(
        required=False, 
        allow_blank=True, 
        allow_null=True,
        trim_whitespace=False
    )
    
    expected_output = serializers.CharField(
        required=False, 
        allow_blank=True, 
        allow_null=True,
        trim_whitespace=False
    )
    
    class Meta:
        model = CustomTest
        fields = ['problem_id', 'language_type', 'source_code', 'input_data', 'expected_output']
    
    def validate_source_code(self, value):
        """基本資料品質驗證"""
        if not value.strip():
            raise serializers.ValidationError('程式碼不能只包含空白字元')
        return value  # 保持原始空白，與 input_data/expected_output 一致
    
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


class EditorialCreateSerializer(serializers.ModelSerializer):
    content = serializers.CharField(
        max_length=10000,
        min_length=1,
        error_messages={
            'max_length': '內容不能超過 10000 字元',
            'min_length': '內容不能為空',
            'blank': '內容不能為空'
        }
    )
    
    class Meta:
        model = Editorial
        fields = ['id', 'content']
        read_only_fields = ['id']

    def validate_content(self, value):
        """內容驗證"""
        if not value.strip():
            raise serializers.ValidationError('內容不能只包含空白字元')
        return value  # 保持原始內容，允許格式空白

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


# ===== 新增：Submission API 相關 Serializers =====

class SubmissionBaseCreateSerializer(serializers.ModelSerializer):
    """創建提交的 Serializer (NOJ 兼容版本)"""
    
    problem_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': 'problemId is required!',
            'required': 'problemId is required!'
        }
    )
    
    language_type = serializers.IntegerField(
        min_value=0,
        max_value=4,
        error_messages={
            'invalid': 'invalid data!',
            'required': 'post data missing!',
            'min_value': 'not allowed language',
            'max_value': 'not allowed language'
        }
    )
    
    def validate_language_type(self, value):
        """驗證語言類型，我們支援 0=C, 1=C++, 2=Python, 3=Java, 4=JavaScript（跳過 PDF）"""
        # 檢查是否為支援的語言
        valid_languages = [choice[0] for choice in Submission.LANGUAGE_CHOICES]
        if value not in valid_languages:
            raise serializers.ValidationError('not allowed language')
        
        return value
    
    class Meta:
        model = Submission
        fields = ['problem_id', 'language_type']
        # 安全：明確指定可接受欄位，自動排除 user 等敏感欄位
    
    def validate_problem_id(self, value):
        """驗證題目是否存在"""
        from problems.models import Problems  # 注意：model 名稱是 Problems（複數）
        if not Problems.objects.filter(id=value).exists():
            raise serializers.ValidationError('題目不存在')
        return value
    
    def create(self, validated_data):
        request = self.context['request']
        validated_data['user'] = request.user
        validated_data['status'] = '-2'  # No Code 狀態
        validated_data['source_code'] = ''  # 空程式碼
        
        # 設定 IP 和 User Agent
        validated_data['ip_address'] = self.get_client_ip(request)
        validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """獲取客戶端 IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class SubmissionCodeUploadSerializer(serializers.ModelSerializer):
    """上傳程式碼的 Serializer"""
    
    source_code = serializers.CharField(
        max_length=65535,
        min_length=1,
        trim_whitespace=False,  # 保持程式碼格式
        error_messages={
            'max_length': '程式碼長度不能超過 64KB',
            'min_length': '程式碼不能為空',
            'blank': '請輸入程式碼'
        }
    )
    
    class Meta:
        model = Submission
        fields = ['source_code']
    
    def validate_source_code(self, value):
        if not value.strip():
            raise serializers.ValidationError('程式碼不能只包含空白字元')
        return value
    
    def update(self, instance, validated_data):
        # 只能更新狀態為 No Code 的提交
        if instance.status != '-2':
            raise serializers.ValidationError('此提交已經上傳過程式碼')
        
        # 計算 code hash
        source_code = validated_data['source_code']
        instance.code_hash = hashlib.sha256(source_code.encode()).hexdigest()
        instance.source_code = source_code
        instance.status = '-1'  # 更新為 Pending 狀態
        instance.save()
        
        # 發送到 SandBox 進行判題
        try:
            self.send_to_sandbox(instance)
        except Exception as e:
            # 如果發送失敗，更新狀態為 System Error
            instance.status = '3'  # System Error
            instance.save()
            import logging
            logging.getLogger(__name__).error(f"Failed to send submission {instance.id} to sandbox: {e}")
            raise serializers.ValidationError('提交到判題系統失敗，請稍後重試')
        
        return instance
    
    def send_to_sandbox(self, submission):
        """
        發送提交到 Sandbox 進行判題（異步）
        
        使用 Celery 異步任務，避免阻塞 API 回應
        """
        from .tasks import submit_to_sandbox_task
        
        try:
            # 異步提交到 Sandbox（立即返回，不等待結果）
            submit_to_sandbox_task.delay(str(submission.id))
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'Queued submission for Sandbox: {submission.id}')
            
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Failed to queue submission {submission.id}: {str(e)}')
            raise


class SubmissionListSerializer(serializers.ModelSerializer):
    """提交列表的 Serializer"""
    
    submissionId = serializers.CharField(source='id', read_only=True)
    problemId = serializers.IntegerField(source='problem_id', read_only=True)
    user = serializers.SerializerMethodField()
    runTime = serializers.SerializerMethodField()
    memoryUsage = serializers.SerializerMethodField()
    languageType = serializers.CharField(source='language_type', read_only=True)
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)
    ipAddr = serializers.CharField(source='ip_address', read_only=True)
    
    class Meta:
        model = Submission
        fields = [
            'submissionId', 'problemId', 'user', 'status', 'score', 
            'runTime', 'memoryUsage', 'languageType', 'timestamp', 'ipAddr'
        ]
    
    def get_user(self, obj):
        return {
            'id': str(obj.user.id),
            'username': obj.user.username,
            'real_name': getattr(obj.user, 'real_name', obj.user.username)
        }
    
    def get_runTime(self, obj):
        """執行時間 (毫秒)，沒有結果時返回 '-'"""
        return obj.execution_time if obj.execution_time != -1 else '-'
    
    def get_memoryUsage(self, obj):
        """記憶體使用量 (KB)，沒有結果時返回 '-'"""
        return obj.memory_usage if obj.memory_usage != -1 else '-'


class SubmissionDetailSerializer(serializers.ModelSerializer):
    """提交詳情的 Serializer"""
    
    submissionId = serializers.CharField(source='id', read_only=True)
    problemId = serializers.IntegerField(source='problem_id', read_only=True)
    user = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)
    lastSend = serializers.SerializerMethodField()
    runTime = serializers.SerializerMethodField()
    memoryUsage = serializers.SerializerMethodField()
    languageType = serializers.CharField(source='language_type', read_only=True)
    ipAddr = serializers.CharField(source='ip_address', read_only=True)
    
    class Meta:
        model = Submission
        fields = [
            'submissionId', 'problemId', 'user', 'timestamp', 'lastSend',
            'status', 'score', 'runTime', 'memoryUsage', 'languageType', 'ipAddr'
        ]
    
    def get_user(self, obj):
        return {
            'id': str(obj.user.id),
            'username': obj.user.username,
            'real_name': getattr(obj.user, 'real_name', obj.user.username)
        }
    
    def get_lastSend(self, obj):
        """最後發送時間 (judged_at)，沒有結果時返回 '-'"""
        return obj.judged_at.isoformat() if obj.judged_at else '-'
    
    def get_runTime(self, obj):
        """執行時間 (毫秒)，沒有結果時返回 '-'"""
        return obj.execution_time if obj.execution_time != -1 else '-'
    
    def get_memoryUsage(self, obj):
        """記憶體使用量 (KB)，沒有結果時返回 '-'"""
        return obj.memory_usage if obj.memory_usage != -1 else '-'


class SubmissionCodeSerializer(serializers.ModelSerializer):
    """程式碼查看的 Serializer"""
    
    class Meta:
        model = Submission
        fields = ['id', 'source_code', 'language_type', 'created_at']


class SubmissionStdoutSerializer(serializers.Serializer):
    """標準輸出的 Serializer"""
    
    stdout = serializers.CharField()
    submission_id = serializers.UUIDField()
    status = serializers.CharField()
    
    def to_representation(self, instance):
        """從 SubmissionResult 獲取標準輸出"""
        # 獲取該提交的所有測試結果
        results = instance.results.all().order_by('test_case_index')
        
        if not results.exists():
            stdout_content = '-'
        else:
            # 合併所有測試案例的輸出
            stdout_lines = []
            for result in results:
                if result.output_preview:
                    stdout_lines.append(f"Test Case {result.test_case_index}:")
                    stdout_lines.append(result.output_preview)
                    stdout_lines.append("")
            
            stdout_content = '\n'.join(stdout_lines) if stdout_lines else '-'
        
        return {
            'stdout': stdout_content,
            'submission_id': str(instance.id),
            'status': instance.status
        }
class UserStatusSerializer(serializers.Serializer):
    """使用者狀態的 Serializer"""
    
    user_id = serializers.CharField()
    username = serializers.CharField()
    total_solved = serializers.IntegerField()
    total_submissions = serializers.IntegerField()
    accept_percent = serializers.FloatField()

    difficulty = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    beats_percent = serializers.FloatField()
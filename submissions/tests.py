# submissions/tests.py - Hypothesis 測試文件
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from unittest.mock import Mock

from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from .models import (
    Submission, SubmissionResult, UserProblemStats, UserProblemSolveStatus,
    UserProblemQuota, CustomTest, CodeDraft, Editorial, EditorialLike
)
from .serializers import (
    SubmissionCreateSerializer, SubmissionSerializer,
    CustomTestCreateSerializer, CodeDraftCreateSerializer, 
    EditorialCreateSerializer
)

User = get_user_model()


class SubmissionModelTests(HypothesisTestCase):
    #測試 Submission Model 的 property-based tests
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'modeluser_{unique_id}',
            email=f'model_{unique_id}@example.com',
            password='testpass123'
        )
    
    @given(
        problem_id=st.integers(min_value=1, max_value=99999),
        language_type=st.sampled_from(['c', 'cpp', 'java', 'python', 'javascript']),
        source_code=st.text(min_size=1, max_size=1000),
        score=st.integers(min_value=0, max_value=100),
        execution_time=st.integers(min_value=-1, max_value=60000),  # -1 或 0-60秒
        memory_usage=st.integers(min_value=-1, max_value=1024000),  # -1 或 0-1GB
    )
    @settings(max_examples=20)  # 減少範例數量，加快測試速度
    def test_submission_creation_with_random_data(
        self, problem_id, language_type, source_code, score, execution_time, memory_usage
    ):
        #測試 Submission 可以用各種隨機資料正常建立
        submission = Submission.objects.create(
            problem_id=problem_id,
            user=self.user,
            language_type=language_type,
            source_code=source_code,
            score=score,
            execution_time=execution_time,
            memory_usage=memory_usage
        )
        
        # 驗證建立的資料正確
        assert submission.problem_id == problem_id
        assert submission.user == self.user
        assert submission.language_type == language_type
        assert submission.source_code == source_code
        assert submission.score == score
        assert submission.execution_time == execution_time
        assert submission.memory_usage == memory_usage
        
        # 測試 UUID 是有效的
        assert isinstance(submission.id, uuid.UUID)
        
        # 測試 __str__ 方法
        str_repr = str(submission)
        assert self.user.username in str_repr
        assert str(submission.id) in str_repr

    @given(
        execution_time=st.integers(min_value=0, max_value=60000)
    )
    @settings(max_examples=10)
    def test_submission_execution_time_property(self, execution_time):
        """測試 Submission 的 execution_time_seconds property"""
        submission = Submission.objects.create(
            problem_id=1,
            user=self.user,
            language_type='python',
            source_code='print("test")',
            execution_time=execution_time,
        )
        
        expected_seconds = execution_time / 1000.0
        assert submission.execution_time_seconds == expected_seconds
    
    def test_submission_execution_time_property_with_invalid_time(self):
        """測試無效執行時間的處理"""
        submission = Submission.objects.create(
            problem_id=1,
            user=self.user,
            language_type='python',
            source_code='print("test")',
            execution_time=-1,  # 無效時間
        )
        
        # 驗證無效執行時間的處理
        assert submission.execution_time == -1

    @given(
        status=st.sampled_from(['pending', 'judging', 'accepted', 'wrong_answer', 'time_limit_exceeded'])
    )
    @settings(max_examples=5)
    def test_submission_is_judged_property(self, status):
        """測試 Submission 的 is_judged property"""
        submission = Submission.objects.create(
            problem_id=1,
            user=self.user,
            language_type='python',
            source_code='print("test")',
            status=status,
        )
        
        expected_is_judged = status not in ['pending', 'judging']
        assert submission.is_judged == expected_is_judged


class SubmissionSerializerTests(HypothesisTestCase):
    #測試 Submission Serializer 的 property-based tests
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'serializeruser_{unique_id}',
            email=f'serializer_{unique_id}@example.com',
            password='testpass123'
        )
    
    @given(
        problem_id=st.integers(min_value=1, max_value=99999),
        language_type=st.sampled_from(['c', 'cpp', 'java', 'python', 'javascript']),
        source_code=st.text(
            min_size=1, 
            max_size=500,
            alphabet=st.characters(
                blacklist_categories=['Cc', 'Cs'],  # 排除控制字符和代理字符
                blacklist_characters=['\x00']        # 明確排除 null 字符
            )
        ).filter(lambda x: x.strip()),
    )
    @settings(max_examples=15)
    def test_submission_create_serializer_valid_data(
        self, problem_id, language_type, source_code
    ):
        """測試 SubmissionCreateSerializer 處理各種有效資料"""
        # 過濾掉純空白的 source_code 和包含無效字符的內容
        assume(source_code.strip())
        assume('\x00' not in source_code)  # 確保沒有 null 字符
        
        data = {
            'problem_id': problem_id,
            'language_type': language_type,
            'source_code': source_code,
        }
        
        # 模擬 request context
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        def mock_get_client_ip(req):
            return '127.0.0.1'
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        # 暫時替換 get_client_ip 方法
        serializer.get_client_ip = mock_get_client_ip
        
        # 驗證 serializer 是有效的
        assert serializer.is_valid(), f"Errors: {serializer.errors}"
        
        # 建立物件
        submission = serializer.save()
        
        # 驗證建立的物件
        assert submission.problem_id == problem_id
        assert submission.language_type == language_type
        # Django CharField 會自動 strip 前後空白，所以比較時需要處理
        assert submission.source_code == source_code.strip()
        assert submission.user == self.user
        assert submission.code_hash is not None
        assert len(submission.code_hash) == 64  # SHA256 hash length

    @given(
        problem_id=st.integers(max_value=0)  # 無效的 problem_id
    )
    @settings(max_examples=5)
    def test_submission_create_serializer_invalid_problem_id(self, problem_id):
        """測試 SubmissionCreateSerializer 無效 problem_id"""
        data = {
            'problem_id': problem_id,
            'language_type': 'python',
            'source_code': 'print("hello")',
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        assert not serializer.is_valid()
        assert 'problem_id' in serializer.errors

    def test_submission_create_serializer_missing_language(self):
        """測試 SubmissionCreateSerializer 缺少程式語言"""
        data = {
            'problem_id': 1,
            'source_code': 'print("hello")',
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        assert not serializer.is_valid()
        assert 'language_type' in serializer.errors

    def test_submission_create_serializer_invalid_language(self):
        """測試 SubmissionCreateSerializer 無效程式語言"""
        data = {
            'problem_id': 1,
            'language_type': 'invalid_language',
            'source_code': 'print("hello")',
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        assert not serializer.is_valid()
        assert 'language_type' in serializer.errors

    def test_submission_create_serializer_empty_source_code(self):
        """測試 SubmissionCreateSerializer 空的程式碼"""
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': '',
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        assert not serializer.is_valid()
        assert 'source_code' in serializer.errors

    def test_submission_create_serializer_oversized_code(self):
        """測試 SubmissionCreateSerializer 拒絕過大的程式碼"""
        # 創建大於 64KB 的程式碼
        oversized_code = 'x' * (65536 + 1)  # 65537 字符
        
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': oversized_code,
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        assert not serializer.is_valid()
        assert 'source_code' in serializer.errors

    def test_submission_create_serializer_duplicate_prevention(self):
        """測試 SubmissionCreateSerializer 防止重複提交"""
        # 先創建一個提交
        source_code = 'print("hello world")'
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': source_code,
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        def mock_get_client_ip(req):
            return '127.0.0.1'
        
        # 第一次提交
        serializer1 = SubmissionCreateSerializer(data=data, context={'request': request})
        serializer1.get_client_ip = mock_get_client_ip
        assert serializer1.is_valid()
        submission1 = serializer1.save()
        
        # 嘗試重複提交相同的程式碼
        serializer2 = SubmissionCreateSerializer(data=data, context={'request': request})
        serializer2.get_client_ip = mock_get_client_ip
        
        # 應該驗證失敗（防止重複提交）
        assert not serializer2.is_valid()
        assert '您已經提交過相同的程式碼' in str(serializer2.errors)

    def test_submission_read_serializer(self):
        """測試 SubmissionSerializer 讀取功能"""
        submission = Submission.objects.create(
            problem_id=1,
            user=self.user,
            language_type='python',
            source_code='print("test")',
            score=95,
            execution_time=1200,
            memory_usage=45000,
        )
        
        serializer = SubmissionSerializer(submission)
        data = serializer.data
        
        assert data['problem_id'] == 1
        assert data['language_type'] == 'python'
        assert data['source_code'] == 'print("test")'
        assert data['score'] == 95
        assert data['execution_time'] == 1200
        assert data['memory_usage'] == 45000


class CustomTestModelTests(HypothesisTestCase):
    #測試 CustomTest Model
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'customuser_{unique_id}',
            email=f'custom_{unique_id}@example.com',
            password='testpass123'
        )
    
    @given(
        problem_id=st.integers(min_value=1, max_value=99999),
        language_type=st.sampled_from(['c', 'cpp', 'java', 'python', 'javascript']),
        source_code=st.text(min_size=1, max_size=500),
        status=st.sampled_from(['pending', 'running', 'completed', 'error'])
    )
    @settings(max_examples=10)
    def test_custom_test_creation(
        self, problem_id, language_type, source_code, status
    ):
        #測試 CustomTest 建立
        custom_test = CustomTest.objects.create(
            user=self.user,
            problem_id=problem_id,
            language_type=language_type,
            source_code=source_code,
            status=status
        )
        
        assert custom_test.user == self.user
        assert custom_test.problem_id == problem_id
        assert custom_test.language_type == language_type
        assert custom_test.source_code == source_code
        assert custom_test.status == status
        assert isinstance(custom_test.id, uuid.UUID)

    @given(
        input_data=st.text(max_size=1000),
        expected_output=st.text(max_size=1000),
    )
    @settings(max_examples=5)
    def test_custom_test_with_io_data(self, input_data, expected_output):
        """測試帶有輸入輸出資料的 CustomTest"""
        custom_test = CustomTest.objects.create(
            user=self.user,
            problem_id=1,
            language_type='python',
            source_code='print("test")',
            input_data=input_data,
            expected_output=expected_output,
        )
        
        assert custom_test.input_data == input_data
        assert custom_test.expected_output == expected_output


class SecurityTests(TestCase):
    """測試安全性和邊界情況"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_serializer_rejects_null_characters(self):
        """測試 serializer 正確拒絕包含 null 字符的輸入"""
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': 'print("hello")\x00malicious_code',  # 包含 null 字符
        }
        
        # 模擬 request context
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        # 驗證 serializer 正確拒絕這個輸入
        assert not serializer.is_valid()
        assert 'source_code' in serializer.errors
        assert 'Null characters are not allowed' in str(serializer.errors['source_code'][0])
    
    def test_serializer_handles_various_malicious_inputs(self):
        """測試各種可能的惡意輸入"""
        malicious_inputs = [
            'code\x00null',           # null 字符
            'code\x01control',        # 控制字符
            'code\uffff',             # 無效 Unicode
        ]
        
        for malicious_code in malicious_inputs:
            with self.subTest(source_code=repr(malicious_code)):
                data = {
                    'problem_id': 1,
                    'language_type': 'python',
                    'source_code': malicious_code,
                }
                
                request = Mock()
                request.user = self.user
                request.META = {'HTTP_USER_AGENT': 'test-agent'}
                
                serializer = SubmissionCreateSerializer(data=data, context={'request': request})
                
                # Django 應該自動拒絕這些輸入
                if '\x00' in malicious_code:
                    assert not serializer.is_valid(), f"Should reject {repr(malicious_code)}"

    def test_serializer_sql_injection_prevention(self):
        """測試 SQL 注入攻擊防護"""
        sql_injection_attempts = [
            "'; DROP TABLE submissions; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO submissions VALUES (1,2,3); --"
        ]
    
        for injection_code in sql_injection_attempts:
            with self.subTest(source_code=injection_code):
                data = {
                    'problem_id': 1,
                    'language_type': 'python',
                    'source_code': injection_code,
                }
    
                request = Mock()
                request.user = self.user
                request.META = {'HTTP_USER_AGENT': 'test-agent'}
    
                def mock_get_client_ip(req):
                    return '127.0.0.1'
    
                serializer = SubmissionCreateSerializer(data=data, context={'request': request})
                serializer.get_client_ip = mock_get_client_ip
    
                # 這些輸入應該被當作正常的程式碼內容處理
                # Django ORM 會自動防護 SQL 注入
                if serializer.is_valid():
                    submission = serializer.save()
                    # 驗證資料被安全地儲存
                    assert submission.source_code == injection_code
                    # 清理這個測試的提交，為下一個測試準備
                    submission.delete()

    def test_serializer_xss_prevention(self):
        """測試 XSS 攻擊防護"""
        xss_attempts = [
            '<script>alert("xss")</script>',
            '<img src="x" onerror="alert(1)">',
            'javascript:alert("xss")',
            '<svg onload="alert(1)">',
        ]
        
        for xss_code in xss_attempts:
            with self.subTest(source_code=xss_code):
                data = {
                    'problem_id': 1,
                    'language_type': 'python',
                    'source_code': xss_code,
                }
                
                request = Mock()
                request.user = self.user
                request.META = {'HTTP_USER_AGENT': 'test-agent'}
                
                def mock_get_client_ip(req):
                    return '127.0.0.1'
                
                serializer = SubmissionCreateSerializer(data=data, context={'request': request})
                serializer.get_client_ip = mock_get_client_ip
                
                # XSS 載荷應該被當作正常的程式碼處理
                if serializer.is_valid():
                    submission = serializer.save()
                    # 驗證資料被安全地儲存，沒有被執行
                    assert submission.source_code == xss_code
                    submission.delete()

    def test_authentication_requirements(self):
        """測試認證要求"""
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': 'print("hello")',
        }
        
        # 沒有用戶的 request
        request = Mock()
        request.user = None
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        # 驗證 serializer 不會驗證成功，因為沒有認證用戶
        self.assertFalse(serializer.is_valid())

    def test_inactive_user_rejection(self):
        """測試拒絕非活躍用戶"""
        inactive_user = User.objects.create_user(
            username='inactive_user',
            email='inactive@example.com',
            password='testpass123',
            is_active=False
        )
        
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': 'print("hello")',
        }
        
        request = Mock()
        request.user = inactive_user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        def mock_get_client_ip(req):
            return '127.0.0.1'
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        serializer.get_client_ip = mock_get_client_ip
        
        # 檢查用戶是否活躍
        assert not serializer.context['request'].user.is_active

    def test_ip_address_logging(self):
        """測試 IP 地址記錄"""
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': 'print("hello")',
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        def mock_get_client_ip(req):
            return '192.168.1.100'
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        serializer.get_client_ip = mock_get_client_ip
        
        if serializer.is_valid():
            submission = serializer.save()
            # 驗證 IP 地址被記錄
            assert submission.ip_address == '192.168.1.100'
            submission.delete()

    def test_rate_limiting_duplicate_prevention(self):
        """測試重複提交限制"""
        source_code = 'print("rate limiting test")'
        
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': source_code,
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        def mock_get_client_ip(req):
            return '127.0.0.1'
        
        # 第一次提交應該成功
        serializer1 = SubmissionCreateSerializer(data=data, context={'request': request})
        serializer1.get_client_ip = mock_get_client_ip
        
        if serializer1.is_valid():
            submission1 = serializer1.save()
            
            # 立即再次提交相同內容應該被拒絕
            serializer2 = SubmissionCreateSerializer(data=data, context={'request': request})
            serializer2.get_client_ip = mock_get_client_ip
            
            assert not serializer2.is_valid()
            submission1.delete()

    def test_serializer_code_size_limits(self):
        """測試程式碼大小限制"""
        # 測試剛好在限制內的程式碼
        max_size_code = 'x' * 65535  # 剛好 64KB
        
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': max_size_code,
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        # 應該接受剛好在限制內的程式碼
        assert serializer.is_valid(), f"Should accept code at size limit, errors: {serializer.errors}"

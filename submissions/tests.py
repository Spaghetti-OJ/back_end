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
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
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


class SubmissionSerializerTests(HypothesisTestCase):
    #測試 Submission Serializer 的 property-based tests
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @given(
        problem_id=st.integers(min_value=1, max_value=99999),
        language_type=st.sampled_from(['c', 'cpp', 'java', 'python', 'javascript']),
        source_code=st.text(min_size=1, max_size=500).filter(lambda x: x.strip()),
    )
    @settings(max_examples=15)
    def test_submission_create_serializer_valid_data(
        self, problem_id, language_type, source_code
    ):
        #測試 SubmissionCreateSerializer 處理各種有效資料
        # 過濾掉純空白的 source_code
        assume(source_code.strip())
        
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


class CustomTestModelTests(HypothesisTestCase):
    #測試 CustomTest Model
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
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

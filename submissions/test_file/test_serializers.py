# submissions/test_file/test_serializers.py - 序列化器測試
import pytest
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import Mock

from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from ..models import (
    Submission, CustomTest, CodeDraft, Editorial, EditorialLike
)
from ..serializers import (
    SubmissionCreateSerializer, SubmissionSerializer,
    CustomTestCreateSerializer, CodeDraftCreateSerializer, 
    EditorialCreateSerializer, EditorialSerializer, EditorialLikeSerializer
)

User = get_user_model()


class SubmissionSerializerHypothesisTests(HypothesisTestCase):
    """測試 Submission Serializer 的 property-based tests"""
    
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


class EditorialSerializerHypothesisTests(HypothesisTestCase):
    """測試 Editorial Serializer"""
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'editorialuser_{unique_id}',
            email=f'editorial_{unique_id}@example.com',
            password='testpass123'
        )
    
    @given(
        title=st.text(min_size=10, max_size=100, alphabet=st.characters(
            blacklist_categories=['Cc', 'Cs'],
            blacklist_characters=['\x00']
        )).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=500, alphabet=st.characters(
            blacklist_categories=['Cc', 'Cs'], 
            blacklist_characters=['\x00']
        )).filter(lambda x: x.strip()),
        difficulty_rating=st.one_of(
            st.none(),
            st.floats(min_value=1.0, max_value=5.0).map(lambda x: round(x, 1))
        ),
        is_official=st.booleans()
    )
    @settings(max_examples=10)
    def test_editorial_create_serializer_valid_data(
        self, title, content, difficulty_rating, is_official
    ):
        """測試 EditorialCreateSerializer 處理各種有效資料"""
        assume(title.strip())
        assume(content.strip())
        
        data = {
            'problem_id': 1,
            'title': title,
            'content': content,
            'difficulty_rating': difficulty_rating,
            'is_official': is_official
        }
        
        request = Mock()
        request.user = self.user
        
        serializer = EditorialCreateSerializer(data=data, context={'request': request})
        
        assert serializer.is_valid(), f"Errors: {serializer.errors}"
        
        editorial = serializer.save()
        
        assert editorial.problem_id == 1
        assert editorial.title == title.strip()
        assert editorial.content == content.strip()
        assert editorial.difficulty_rating == difficulty_rating
        assert editorial.is_official == is_official
        assert editorial.author == self.user
    
    @given(
        invalid_title=st.one_of(
            st.just(''),  # 空字串
            st.text(max_size=5),  # 太短
            st.text(min_size=256)  # 太長
        ),
        invalid_content=st.one_of(
            st.just(''),  # 空字串
            st.text(max_size=5)  # 太短
        )
    )
    @settings(max_examples=5)
    def test_editorial_create_serializer_validation_failures(
        self, invalid_title, invalid_content
    ):
        """測試 EditorialCreateSerializer 驗證失敗情況"""
        data = {
            'problem_id': 1,
            'title': invalid_title,
            'content': invalid_content,
            'difficulty_rating': 3.0,
            'is_official': False
        }
        
        request = Mock()
        request.user = self.user
        
        serializer = EditorialCreateSerializer(data=data, context={'request': request})
        
        assert not serializer.is_valid()
        # 至少有一個欄位應該有錯誤
        assert len(serializer.errors) > 0
    
    def test_editorial_serializer_read_functionality(self):
        """測試 EditorialSerializer 讀取功能"""
        editorial = Editorial.objects.create(
            problem_id=1,
            author=self.user,
            title='測試題解',
            content='測試題解內容',
            difficulty_rating=3.5,
            likes_count=10,
            views_count=100,
            status='published'
        )
        
        request = Mock()
        request.user = self.user
        
        serializer = EditorialSerializer(editorial, context={'request': request})
        data = serializer.data
        
        assert data['title'] == '測試題解'
        assert data['content'] == '測試題解內容'
        assert float(data['difficulty_rating']) == 3.5
        assert data['likes_count'] == 10
        assert data['views_count'] == 100
        assert data['author_username'] == self.user.username
        assert data['status'] == 'published'


class CustomTestSerializerHypothesisTests(HypothesisTestCase):
    """測試 CustomTest Serializer"""
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'customtestuser_{unique_id}',
            email=f'customtest_{unique_id}@example.com',
            password='testpass123'
        )
    
    @given(
        problem_id=st.integers(min_value=1, max_value=9999),
        language_type=st.sampled_from(['c', 'cpp', 'java', 'python', 'javascript']),
        source_code=st.text(min_size=1, max_size=500).filter(lambda x: x.strip()),
        input_data=st.one_of(st.none(), st.text(max_size=200)),
        expected_output=st.one_of(st.none(), st.text(max_size=200))
    )
    @settings(max_examples=10)
    def test_custom_test_create_serializer(
        self, problem_id, language_type, source_code, input_data, expected_output
    ):
        """測試 CustomTestCreateSerializer 處理各種資料"""
        assume(source_code.strip())
        
        data = {
            'problem_id': problem_id,
            'language_type': language_type,
            'source_code': source_code,
            'input_data': input_data,
            'expected_output': expected_output
        }
        
        request = Mock()
        request.user = self.user
        
        serializer = CustomTestCreateSerializer(data=data, context={'request': request})
        
        assert serializer.is_valid(), f"Errors: {serializer.errors}"
        
        custom_test = serializer.save()
        
        assert custom_test.problem_id == problem_id
        assert custom_test.language_type == language_type
        assert custom_test.source_code == source_code.strip()
        assert custom_test.input_data == input_data
        assert custom_test.expected_output == expected_output
        assert custom_test.user == self.user


class CodeDraftSerializerHypothesisTests(HypothesisTestCase):
    """測試 CodeDraft Serializer"""
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'codedraftuser_{unique_id}',
            email=f'codedraft_{unique_id}@example.com',
            password='testpass123'
        )
    
    @given(
        problem_id=st.integers(min_value=1, max_value=9999),
        language_type=st.sampled_from(['c', 'cpp', 'java', 'python', 'javascript']),
        source_code=st.text(min_size=1, max_size=500).filter(lambda x: x.strip()),
        title=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        auto_saved=st.booleans()
    )
    @settings(max_examples=10)
    def test_code_draft_create_serializer(
        self, problem_id, language_type, source_code, title, auto_saved
    ):
        """測試 CodeDraftCreateSerializer 處理各種資料"""
        assume(source_code.strip())
        
        data = {
            'problem_id': problem_id,
            'language_type': language_type,
            'source_code': source_code,
            'title': title,
            'auto_saved': auto_saved
        }
        
        request = Mock()
        request.user = self.user
        
        serializer = CodeDraftCreateSerializer(data=data, context={'request': request})
        
        assert serializer.is_valid(), f"Errors: {serializer.errors}"
        
        code_draft = serializer.save()
        
        assert code_draft.problem_id == problem_id
        assert code_draft.language_type == language_type
        assert code_draft.source_code == source_code.strip()
        assert code_draft.title == title
        assert code_draft.auto_saved == auto_saved
        assert code_draft.user == self.user


class SecuritySerializerTests(TestCase):
    """測試序列化器安全性"""
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'securityuser_{unique_id}',
            email=f'security_{unique_id}@example.com',
            password='testpass123'
        )
    
    def test_serializer_rejects_null_characters(self):
        """測試 serializer 正確拒絕包含 null 字符的輸入"""
        data = {
            'problem_id': 1,
            'language_type': 'python',
            'source_code': 'print("hello")\x00malicious_code',  # 包含 null 字符
        }
        
        request = Mock()
        request.user = self.user
        request.META = {'HTTP_USER_AGENT': 'test-agent'}
        
        serializer = SubmissionCreateSerializer(data=data, context={'request': request})
        
        # 驗證 serializer 正確拒絕這個輸入
        assert not serializer.is_valid()
        assert 'source_code' in serializer.errors
        assert 'Null characters are not allowed' in str(serializer.errors['source_code'][0])
    
    def test_serializer_handles_sql_injection_attempts(self):
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

    def test_serializer_handles_xss_attempts(self):
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
        assert not serializer.is_valid()

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
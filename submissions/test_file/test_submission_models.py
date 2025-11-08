# submissions/test_file/test_submission_models.py - 提交模型測試
import pytest
import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from unittest.mock import Mock

from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from ..models import (
    Submission, SubmissionResult, UserProblemStats, UserProblemSolveStatus,
    UserProblemQuota, CustomTest, CodeDraft
)

User = get_user_model()


class SubmissionModelHypothesisTests(HypothesisTestCase):
    """測試 Submission Model 的 property-based tests"""
    
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
        """測試 Submission 可以用各種隨機資料正常建立"""
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
        status=st.sampled_from(['-2', '-1', '0', '1', '2', '3', '4', '5'])
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
        
        # 根據新的狀態編碼：-2=No Code, -1=Pending 表示尚未判題
        expected_is_judged = status not in ['-2', '-1']
        assert submission.is_judged == expected_is_judged


class CustomTestModelHypothesisTests(HypothesisTestCase):
    """測試 CustomTest Model"""
    
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
        """測試 CustomTest 建立"""
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


class UserProblemStatsHypothesisTests(HypothesisTestCase):
    """測試 UserProblemStats Model"""
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'statsuser_{unique_id}',
            email=f'stats_{unique_id}@example.com',
            password='testpass123'
        )
    
    @given(
        assignment_id=st.integers(min_value=1, max_value=9999),
        problem_id=st.integers(min_value=1, max_value=9999),
        total_submissions=st.integers(min_value=0, max_value=100),
        best_score=st.integers(min_value=0, max_value=100),
        solve_status=st.sampled_from(['unsolved', 'partial', 'solved']),
        penalty_score=st.decimals(min_value=0, max_value=999.99, places=2)
    )
    @settings(max_examples=15)
    def test_user_problem_stats_creation(
        self, assignment_id, problem_id, total_submissions, best_score, 
        solve_status, penalty_score
    ):
        """測試 UserProblemStats 用各種隨機資料建立"""
        stats = UserProblemStats.objects.create(
            user=self.user,
            assignment_id=assignment_id,
            problem_id=problem_id,
            total_submissions=total_submissions,
            best_score=best_score,
            solve_status=solve_status,
            penalty_score=penalty_score
        )
        
        assert stats.user == self.user
        assert stats.assignment_id == assignment_id
        assert stats.problem_id == problem_id
        assert stats.total_submissions == total_submissions
        assert stats.best_score == best_score
        assert stats.solve_status == solve_status
        assert stats.penalty_score == penalty_score
        
        # 測試 __str__ 方法
        str_repr = str(stats)
        assert self.user.username in str_repr
        assert str(assignment_id) in str_repr
        assert str(problem_id) in str_repr


class CodeDraftHypothesisTests(HypothesisTestCase):
    """測試 CodeDraft Model"""
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'draftuser_{unique_id}',
            email=f'draft_{unique_id}@example.com',
            password='testpass123'
        )
    
    @given(
        problem_id=st.integers(min_value=1, max_value=9999),
        language_type=st.sampled_from(['c', 'cpp', 'java', 'python', 'javascript']),
        source_code=st.text(min_size=1, max_size=1000),
        title=st.one_of(
            st.none(), 
            st.text(min_size=1, max_size=100)
        ),
        auto_saved=st.booleans()
    )
    @settings(max_examples=10)
    def test_code_draft_creation(
        self, problem_id, language_type, source_code, title, auto_saved
    ):
        """測試 CodeDraft 用各種隨機資料建立"""
        draft = CodeDraft.objects.create(
            user=self.user,
            problem_id=problem_id,
            language_type=language_type,
            source_code=source_code,
            title=title,
            auto_saved=auto_saved
        )
        
        assert draft.user == self.user
        assert draft.problem_id == problem_id
        assert draft.language_type == language_type
        assert draft.source_code == source_code
        assert draft.title == title
        assert draft.auto_saved == auto_saved
        assert isinstance(draft.id, uuid.UUID)
        
        # 測試 __str__ 方法
        str_repr = str(draft)
        assert self.user.username in str_repr
        assert str(problem_id) in str_repr
        if title:
            assert title in str_repr


class SubmissionResultHypothesisTests(HypothesisTestCase):
    """測試 SubmissionResult Model"""
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'resultuser_{unique_id}',
            email=f'result_{unique_id}@example.com',
            password='testpass123'
        )
        
        self.submission = Submission.objects.create(
            problem_id=1,
            user=self.user,
            language_type='python',
            source_code='print("test")'
        )
    
    @given(
        test_case_id=st.integers(min_value=1, max_value=100),
        test_case_index=st.integers(min_value=1, max_value=100),
        status=st.sampled_from(['accepted', 'wrong_answer', 'time_limit_exceeded', 'memory_limit_exceeded']),
        execution_time=st.integers(min_value=0, max_value=30000),
        memory_usage=st.integers(min_value=0, max_value=512000)
    )
    @settings(max_examples=10)
    def test_submission_result_creation(
        self, test_case_id, test_case_index, status, execution_time, memory_usage
    ):
        """測試 SubmissionResult 用各種隨機資料建立"""
        result = SubmissionResult.objects.create(
            submission=self.submission,
            problem_id=1,
            test_case_id=test_case_id,
            test_case_index=test_case_index,
            status=status,
            execution_time=execution_time,
            memory_usage=memory_usage
        )
        
        assert result.submission == self.submission
        assert result.problem_id == 1
        assert result.test_case_id == test_case_id
        assert result.test_case_index == test_case_index
        assert result.status == status
        assert result.execution_time == execution_time
        assert result.memory_usage == memory_usage
        
        # 測試 __str__ 方法
        str_repr = str(result)
        assert str(result.id) in str_repr
        assert str(self.submission.id) in str_repr
        assert str(test_case_index) in str_repr


class ModelConstraintsTests(TestCase):
    """測試模型約束和驗證"""
    
    def setUp(self):
        unique_id = str(uuid.uuid4())[:8]
        self.user = User.objects.create_user(
            username=f'constraintuser_{unique_id}',
            email=f'constraint_{unique_id}@example.com',
            password='testpass123'
        )
    
    def test_user_problem_stats_unique_constraint(self):
        """測試 UserProblemStats 唯一約束"""
        # 創建第一個統計記錄
        UserProblemStats.objects.create(
            user=self.user,
            assignment_id=1,
            problem_id=1,
            best_score=90
        )
        
        # 嘗試創建重複的記錄應該失敗
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            UserProblemStats.objects.create(
                user=self.user,
                assignment_id=1,
                problem_id=1,
                best_score=95
            )
    
    def test_user_problem_solve_status_unique_constraint(self):
        """測試 UserProblemSolveStatus 唯一約束"""
        # 創建第一個解題狀態記錄
        UserProblemSolveStatus.objects.create(
            user=self.user,
            problem_id=1,
            solve_status='solved'
        )
        
        # 嘗試創建重複的記錄應該失敗
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            UserProblemSolveStatus.objects.create(
                user=self.user,
                problem_id=1,
                solve_status='partial_solved'
            )
    
    def test_editorial_like_unique_constraint(self):
        """測試 EditorialLike 唯一約束"""
        from ..models import Editorial, EditorialLike
        
        # 創建題解
        editorial = Editorial.objects.create(
            problem_id=1,
            author=self.user,
            title='測試題解',
            content='測試內容',
            status='published'
        )
        
        # 創建第一個按讚記錄
        EditorialLike.objects.create(
            editorial=editorial,
            user=self.user
        )
        
        # 嘗試創建重複的按讚記錄應該失敗
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            EditorialLike.objects.create(
                editorial=editorial,
                user=self.user
            )
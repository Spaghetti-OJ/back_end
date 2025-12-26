# editor/tests/test_draft_models.py
"""
測試 CodeDraft Model
"""
import pytest
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from ..models import CodeDraft

User = get_user_model()


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
        language_type=st.sampled_from([0, 1, 2, 3, 4]),
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

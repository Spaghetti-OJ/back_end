# editor/tests/test_draft_serializers.py
"""
測試 CodeDraft Serializers
"""
import pytest
import uuid
from unittest.mock import Mock
from django.test import TestCase
from django.contrib.auth import get_user_model

from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from ..models import CodeDraft
from ..serializers import (
    DraftSerializer,
    DraftCreateUpdateSerializer
)

User = get_user_model()


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
        language_type=st.sampled_from([0, 1, 2, 3, 4]),  # 使用整數語言類型
        source_code=st.text(min_size=1, max_size=500).filter(lambda x: x.strip() and '\x00' not in x),
        title=st.one_of(st.none(), st.text(min_size=1, max_size=50).filter(lambda x: '\x00' not in x)),
        auto_saved=st.booleans()
    )
    @settings(max_examples=10)
    def test_code_draft_create_serializer(
        self, problem_id, language_type, source_code, title, auto_saved
    ):
        """測試 DraftCreateUpdateSerializer 處理各種資料"""
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
        
        serializer = DraftCreateUpdateSerializer(data=data, context={'request': request})
        
        assert serializer.is_valid(), f"Errors: {serializer.errors}"
        
        code_draft = serializer.save(user=self.user)
        
        assert code_draft.problem_id == problem_id
        assert code_draft.language_type == language_type
        assert code_draft.source_code == source_code.strip()
        # Django CharField 會自動處理空白字符,包括 \r, \n 等
        assert code_draft.title == (title.strip() if title else title)
        assert code_draft.auto_saved == auto_saved
        assert code_draft.user == self.user

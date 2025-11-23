# editor/tests/test_draft_api.py
"""
測試 Draft API Views
"""
import pytest
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from ..models import CodeDraft

User = get_user_model()


class DraftAPITestCase(APITestCase):
    """Draft API 測試基類"""
    
    def setUp(self):
        """每個測試前的設置"""
        self.client = APIClient()
        
        # 創建測試用戶
        self.user1 = User.objects.create_user(
            username='draftuser1',
            email='draft1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='draftuser2',
            email='draft2@test.com',
            password='testpass123'
        )
    
    def get_api_message(self, response):
        """從 api_response 格式的響應中提取 message"""
        if isinstance(response.data, dict) and 'message' in response.data:
            return response.data['message']
        return response.data
    
    def get_api_data(self, response):
        """從 api_response 格式的響應中提取 data"""
        if isinstance(response.data, dict) and 'data' in response.data:
            return response.data['data']
        return response.data


@pytest.mark.django_db
class TestDraftCreateAPI(DraftAPITestCase):
    """測試草稿創建"""
    
    def test_create_draft_success(self):
        """測試成功創建草稿"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'problem_id': 1001,
            'language_type': 2,  # Python
            'source_code': 'print("Hello World")',
            'title': 'Test Draft',
            'auto_saved': True
        }
        
        response = self.client.put('/editor/draft/1001/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_api_message(response), '草稿保存成功')
        
        # 驗證數據庫
        draft = CodeDraft.objects.get(user=self.user1, problem_id=1001)
        self.assertEqual(draft.language_type, 2)
        self.assertEqual(draft.source_code, 'print("Hello World")')
    
    def test_create_draft_unauthenticated(self):
        """測試未認證用戶創建草稿"""
        data = {
            'problem_id': 1001,
            'language_type': 2,
            'source_code': 'print("Hello")'
        }
        
        response = self.client.put('/editor/draft/1001/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.django_db
class TestDraftUpdateAPI(DraftAPITestCase):
    """測試草稿更新"""
    
    def test_update_draft_success(self):
        """測試更新現有草稿"""
        self.client.force_authenticate(user=self.user1)
        
        # 先創建草稿
        draft = CodeDraft.objects.create(
            user=self.user1,
            problem_id=1001,
            language_type=2,
            source_code='old code'
        )
        
        # 更新草稿
        data = {
            'source_code': 'new code updated',
            'auto_saved': True
        }
        
        response = self.client.put('/editor/draft/1001/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_api_message(response), '草稿保存成功')
        
        # 驗證更新
        draft.refresh_from_db()
        self.assertEqual(draft.source_code, 'new code updated')
        self.assertTrue(draft.auto_saved)


@pytest.mark.django_db
class TestDraftRetrieveAPI(DraftAPITestCase):
    """測試草稿查詢"""
    
    def test_get_draft_success(self):
        """測試獲取草稿"""
        self.client.force_authenticate(user=self.user1)
        
        # 創建草稿
        draft = CodeDraft.objects.create(
            user=self.user1,
            problem_id=1001,
            language_type=2,
            source_code='test code',
            title='My Draft'
        )
        
        response = self.client.get('/editor/draft/1001/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_api_message(response), '草稿載入成功')
        
        data = self.get_api_data(response)
        self.assertEqual(data['problem_id'], 1001)
        self.assertEqual(data['source_code'], 'test code')
        self.assertEqual(data['title'], 'My Draft')
    
    def test_get_draft_not_found(self):
        """測試草稿不存在"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/editor/draft/9999/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.get_api_message(response), '找不到草稿')
    
    def test_get_other_user_draft(self):
        """測試無法獲取其他用戶的草稿"""
        self.client.force_authenticate(user=self.user2)
        
        # user1 的草稿
        CodeDraft.objects.create(
            user=self.user1,
            problem_id=1001,
            language_type=2,
            source_code='private code'
        )
        
        response = self.client.get('/editor/draft/1001/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
class TestDraftDeleteAPI(DraftAPITestCase):
    """測試草稿刪除"""
    
    def test_delete_draft_success(self):
        """測試刪除草稿"""
        self.client.force_authenticate(user=self.user1)
        
        draft = CodeDraft.objects.create(
            user=self.user1,
            problem_id=1001,
            language_type=2,
            source_code='to be deleted'
        )
        
        response = self.client.delete('/editor/draft/1001/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_api_message(response), '草稿刪除成功')
        
        # 驗證已刪除
        self.assertFalse(
            CodeDraft.objects.filter(user=self.user1, problem_id=1001).exists()
        )
    
    def test_delete_draft_not_found(self):
        """測試刪除不存在的草稿"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.delete('/editor/draft/9999/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

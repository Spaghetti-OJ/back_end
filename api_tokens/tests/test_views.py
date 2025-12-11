# api_tokens/tests/test_views.py
"""
測試 API Token Views
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from api_tokens.models import ApiToken
from api_tokens.services import generate_api_token

User = get_user_model()


class ApiTokenListViewTest(TestCase):
    """測試 ApiTokenListView (GET /api-tokens/, POST /api-tokens/)"""

    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.url = reverse('api-token-list')

    def test_list_tokens_requires_authentication(self):
        """測試列出 tokens 需要認證"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_tokens_authenticated(self):
        """測試已認證用戶可以列出自己的 tokens"""
        self.client.force_authenticate(user=self.user)
        
        # 創建一些 tokens
        full_token1, token_hash1 = generate_api_token()
        ApiToken.objects.create(
            user=self.user,
            name='Token 1',
            token_hash=token_hash1,
            prefix=full_token1[:16]
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')
        self.assertEqual(len(response.data['data']), 1)

    def test_list_tokens_only_shows_own_tokens(self):
        """測試用戶只能看到自己的 tokens"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # 為當前用戶創建 token
        full_token1, token_hash1 = generate_api_token()
        ApiToken.objects.create(
            user=self.user,
            name='My Token',
            token_hash=token_hash1,
            prefix=full_token1[:16]
        )
        
        # 為其他用戶創建 token
        full_token2, token_hash2 = generate_api_token()
        ApiToken.objects.create(
            user=other_user,
            name='Other Token',
            token_hash=token_hash2,
            prefix=full_token2[:16]
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'My Token')

    def test_create_token_requires_authentication(self):
        """測試創建 token 需要認證"""
        data = {'name': 'Test Token'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_token_with_valid_data(self):
        """測試使用有效數據創建 token"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'name': 'My New Token',
            'permissions': ['read:user', 'read:problems']
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'ok')
        self.assertIn('full_token', response.data['data'])
        
        # 確認 token 已創建
        self.assertTrue(ApiToken.objects.filter(user=self.user, name='My New Token').exists())

    def test_create_token_returns_full_token_once(self):
        """測試創建 token 時返回完整 token（僅此一次）"""
        self.client.force_authenticate(user=self.user)
        
        data = {'name': 'Test Token'}
        response = self.client.post(self.url, data, format='json')
        
        full_token = response.data['data']['full_token']
        self.assertTrue(full_token.startswith('noj_pat_'))
        
        # 再次列出 tokens，不應該包含完整 token
        list_response = self.client.get(self.url)
        self.assertNotIn('full_token', list_response.data['data'][0])

    def test_create_token_without_name(self):
        """測試創建 token 時缺少 name"""
        self.client.force_authenticate(user=self.user)
        
        data = {'permissions': ['read:user']}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_with_invalid_permissions(self):
        """測試使用無效權限創建 token"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'name': 'Test Token',
            'permissions': ['invalid:scope']
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_with_expiry(self):
        """測試創建帶過期時間的 token"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'name': 'Expiring Token',
            'expires_at': '2026-12-31T23:59:59Z'
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        token = ApiToken.objects.get(user=self.user, name='Expiring Token')
        self.assertIsNotNone(token.expires_at)


class ApiTokenDetailViewTest(TestCase):
    """測試 ApiTokenDetailView (GET /api-tokens/<id>/, DELETE /api-tokens/<id>/)"""

    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        full_token, token_hash = generate_api_token()
        self.token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=token_hash,
            prefix=full_token[:16]
        )
        self.url = reverse('api-token-detail', kwargs={'tokenId': self.token.id})

    def test_get_token_requires_authentication(self):
        """測試獲取 token 詳情需要認證"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_token_detail(self):
        """測試獲取 token 詳情"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['name'], 'Test Token')
        self.assertNotIn('token_hash', response.data['data'])

    def test_get_other_user_token_fails(self):
        """測試無法獲取其他用戶的 token"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        self.client.force_authenticate(user=other_user)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_token_requires_authentication(self):
        """測試刪除 token 需要認證"""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_token(self):
        """測試刪除 token"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.delete(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')
        
        # 確認 token 已被刪除
        self.assertFalse(ApiToken.objects.filter(id=self.token.id).exists())

    def test_delete_other_user_token_fails(self):
        """測試無法刪除其他用戶的 token"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        self.client.force_authenticate(user=other_user)
        response = self.client.delete(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # 確認 token 仍然存在
        self.assertTrue(ApiToken.objects.filter(id=self.token.id).exists())

    def test_delete_nonexistent_token(self):
        """測試刪除不存在的 token"""
        self.client.force_authenticate(user=self.user)
        
        # 使用一個不存在的 UUID
        import uuid
        fake_url = reverse('api-token-detail', kwargs={'tokenId': uuid.uuid4()})
        response = self.client.delete(fake_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ApiTokenAuthenticationIntegrationTest(TestCase):
    """測試使用 API Token 進行認證的整合測試"""

    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.full_token, token_hash = generate_api_token()
        self.token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=token_hash,
            prefix=self.full_token[:16],
            permissions=['read:user']
        )
        self.url = reverse('api-token-list')

    def test_authenticate_with_api_token(self):
        """測試使用 API Token 認證並訪問 API"""
        # 使用 API Token 認證
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.full_token}')
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 確認 token 的使用統計已更新
        self.token.refresh_from_db()
        self.assertEqual(self.token.usage_count, 1)
        self.assertIsNotNone(self.token.last_used_at)

    def test_invalid_token_authentication_fails(self):
        """測試使用無效 token 認證失敗"""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

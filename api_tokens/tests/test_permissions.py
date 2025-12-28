# api_tokens/tests/test_permissions.py
"""
測試 API Token 權限系統
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from api_tokens.models import ApiToken
from api_tokens.permissions import TokenHasScope
from api_tokens.services import generate_api_token

User = get_user_model()


class MockView(APIView):
    """用於測試的模擬 View"""
    required_scopes = []


class TokenHasScopeTest(TestCase):
    """測試 TokenHasScope 權限類"""

    def setUp(self):
        """設置測試環境"""
        self.factory = RequestFactory()
        self.permission = TokenHasScope()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.view = MockView()

    def test_unauthenticated_user_denied(self):
        """測試未認證用戶被拒絕"""
        request = self.factory.get('/')
        request.user = None
        
        has_permission = self.permission.has_permission(request, self.view)
        
        self.assertFalse(has_permission)

    def test_session_authenticated_user_allowed(self):
        """測試 Session 認證的用戶擁有所有權限"""
        request = self.factory.get('/')
        request.user = self.user
        request.auth = None  # Session 認證時 auth 為 None
        
        has_permission = self.permission.has_permission(request, self.view)
        
        self.assertTrue(has_permission)

    def test_token_authenticated_without_required_scopes(self):
        """測試 Token 認證但 View 沒有要求特定權限"""
        full_token, token_hash = generate_api_token()
        token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=token_hash,
            prefix=full_token[:16],
            permissions=[]
        )
        
        request = self.factory.get('/')
        request.user = self.user
        request.auth = token
        
        # View 沒有設置 required_scopes
        self.view.required_scopes = []
        
        has_permission = self.permission.has_permission(request, self.view)
        
        self.assertTrue(has_permission)

    def test_token_with_sufficient_permissions(self):
        """測試 Token 擁有足夠的權限"""
        full_token, token_hash = generate_api_token()
        token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=token_hash,
            prefix=full_token[:16],
            permissions=['read:user', 'read:problems']
        )
        
        request = self.factory.get('/')
        request.user = self.user
        request.auth = token
        
        # View 要求 read:user 權限
        self.view.required_scopes = ['read:user']
        
        has_permission = self.permission.has_permission(request, self.view)
        
        self.assertTrue(has_permission)

    def test_token_with_insufficient_permissions(self):
        """測試 Token 權限不足"""
        full_token, token_hash = generate_api_token()
        token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=token_hash,
            prefix=full_token[:16],
            permissions=['read:user']
        )
        
        request = self.factory.get('/')
        request.user = self.user
        request.auth = token
        
        # View 要求 write:problems 權限，但 token 沒有
        self.view.required_scopes = ['write:problems']
        
        has_permission = self.permission.has_permission(request, self.view)
        
        self.assertFalse(has_permission)

    def test_token_with_multiple_required_scopes(self):
        """測試 Token 需要多個權限"""
        full_token, token_hash = generate_api_token()
        token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=token_hash,
            prefix=full_token[:16],
            permissions=['read:user', 'read:problems', 'write:problems']
        )
        
        request = self.factory.get('/')
        request.user = self.user
        request.auth = token
        
        # View 要求多個權限
        self.view.required_scopes = ['read:user', 'write:problems']
        
        has_permission = self.permission.has_permission(request, self.view)
        
        self.assertTrue(has_permission)

    def test_token_missing_one_of_multiple_scopes(self):
        """測試 Token 缺少多個要求權限中的一個"""
        full_token, token_hash = generate_api_token()
        token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=token_hash,
            prefix=full_token[:16],
            permissions=['read:user']
        )
        
        request = self.factory.get('/')
        request.user = self.user
        request.auth = token
        
        # View 要求兩個權限，但 token 只有一個
        self.view.required_scopes = ['read:user', 'write:problems']
        
        has_permission = self.permission.has_permission(request, self.view)
        
        self.assertFalse(has_permission)

    def test_token_with_empty_permissions(self):
        """測試沒有任何權限的 Token"""
        full_token, token_hash = generate_api_token()
        token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=token_hash,
            prefix=full_token[:16],
            permissions=[]
        )
        
        request = self.factory.get('/')
        request.user = self.user
        request.auth = token
        
        # View 要求權限
        self.view.required_scopes = ['read:user']
        
        has_permission = self.permission.has_permission(request, self.view)
        
        self.assertFalse(has_permission)


        """測試 View 沒有 required_scopes 屬性"""
        full_token, token_hash = generate_api_token()
        token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=token_hash,
            prefix=full_token[:16],
            permissions=['read:user']
        )
        
        request = self.factory.get('/')
        request.user = self.user
        request.auth = token
        
        # 創建沒有 required_scopes 的 view
        view_without_scopes = APIView()
        
        has_permission = self.permission.has_permission(request, view_without_scopes)
        
        # 沒有要求權限時應該允許
        self.assertTrue(has_permission)

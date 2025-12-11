# api_tokens/tests/test_authentication.py
"""
測試 API Token 認證機制
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import AuthenticationFailed
from api_tokens.models import ApiToken
from api_tokens.authentication import ApiTokenAuthentication
from api_tokens.services import generate_api_token

User = get_user_model()


class ApiTokenAuthenticationTest(TestCase):
    """測試 ApiTokenAuthentication"""

    def setUp(self):
        """設置測試環境"""
        self.factory = RequestFactory()
        self.auth = ApiTokenAuthentication()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.full_token, self.token_hash = generate_api_token()
        self.token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=self.token_hash,
            prefix=self.full_token[:16]
        )

    def test_authenticate_with_valid_token(self):
        """測試使用有效 token 認證"""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.full_token}'
        
        user, auth = self.auth.authenticate(request)
        
        self.assertEqual(user, self.user)
        self.assertEqual(auth, self.token)

    def test_authenticate_without_authorization_header(self):
        """測試沒有 Authorization header 時返回 None"""
        request = self.factory.get('/')
        
        result = self.auth.authenticate(request)
        
        self.assertIsNone(result)

    def test_authenticate_with_wrong_scheme(self):
        """測試使用錯誤的認證方案（不是 Bearer）"""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Basic {self.full_token}'
        
        result = self.auth.authenticate(request)
        
        self.assertIsNone(result)

    def test_authenticate_with_malformed_header(self):
        """測試格式錯誤的 Authorization header"""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer'  # 缺少 token
        
        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)
        
        self.assertIn('格式錯誤', str(context.exception))

    def test_authenticate_with_invalid_token(self):
        """測試使用無效的 token"""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer invalid_token_12345'
        
        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)
        
        self.assertIn('無效', str(context.exception))

    def test_authenticate_with_expired_token(self):
        """測試使用已過期的 token"""
        # 創建已過期的 token
        past_time = timezone.now() - timedelta(days=1)
        full_token2, token_hash2 = generate_api_token()
        expired_token = ApiToken.objects.create(
            user=self.user,
            name='Expired Token',
            token_hash=token_hash2,
            prefix=full_token2[:16],
            expires_at=past_time
        )
        
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {full_token2}'
        
        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)
        
        self.assertIn('過期', str(context.exception))

    def test_authenticate_with_inactive_token(self):
        """測試使用已停用的 token"""
        self.token.is_active = False
        self.token.save()
        
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.full_token}'
        
        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)
        
        self.assertIn('撤銷', str(context.exception))

    def test_authenticate_updates_last_used_at(self):
        """測試認證成功後更新 last_used_at"""
        old_last_used = self.token.last_used_at
        
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.full_token}'
        
        self.auth.authenticate(request)
        
        self.token.refresh_from_db()
        self.assertIsNotNone(self.token.last_used_at)
        self.assertNotEqual(self.token.last_used_at, old_last_used)

    def test_authenticate_updates_usage_count(self):
        """測試認證成功後增加 usage_count"""
        old_count = self.token.usage_count
        
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.full_token}'
        
        self.auth.authenticate(request)
        
        self.token.refresh_from_db()
        self.assertEqual(self.token.usage_count, old_count + 1)

    def test_authenticate_updates_last_used_ip(self):
        """測試認證成功後更新 last_used_ip"""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.full_token}'
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        self.auth.authenticate(request)
        
        self.token.refresh_from_db()
        self.assertEqual(self.token.last_used_ip, '192.168.1.100')

    def test_authenticate_with_x_forwarded_for(self):
        """測試從 X-Forwarded-For 獲取 IP"""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.full_token}'
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        self.auth.authenticate(request)
        
        self.token.refresh_from_db()
        # 應該使用 X-Forwarded-For 的第一個 IP
        self.assertEqual(self.token.last_used_ip, '10.0.0.1')

    def test_multiple_authentications_increment_count(self):
        """測試多次認證會累加使用次數"""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.full_token}'
        
        # 認證 3 次
        for _ in range(3):
            self.auth.authenticate(request)
        
        self.token.refresh_from_db()
        self.assertEqual(self.token.usage_count, 3)

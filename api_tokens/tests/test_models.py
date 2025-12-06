# api_tokens/tests/test_models.py
"""
測試 ApiToken Model
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from api_tokens.models import ApiToken
from api_tokens.services import generate_api_token

User = get_user_model()


class ApiTokenModelTest(TestCase):
    """測試 ApiToken Model"""

    def setUp(self):
        """設置測試環境"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.full_token, self.token_hash = generate_api_token()

    def test_create_api_token(self):
        """測試創建 API Token"""
        token = ApiToken.objects.create(
            user=self.user,
            name='Test Token',
            token_hash=self.token_hash,
            prefix=self.full_token[:16],
            permissions=['read:user']
        )
        
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.name, 'Test Token')
        self.assertEqual(token.permissions, ['read:user'])
        self.assertTrue(token.is_active)
        self.assertFalse(token.is_expired)

    def test_token_string_representation(self):
        """測試 Token 的字串表示"""
        token = ApiToken.objects.create(
            user=self.user,
            name='My Token',
            token_hash=self.token_hash,
            prefix='noj_pat_abc123'
        )
        
        expected = f"{self.user.username} - My Token (noj_pat_abc123...)"
        self.assertEqual(str(token), expected)

    def test_token_is_not_expired_without_expiry(self):
        """測試沒有過期時間的 Token 不會過期"""
        token = ApiToken.objects.create(
            user=self.user,
            name='Permanent Token',
            token_hash=self.token_hash,
            prefix=self.full_token[:16]
        )
        
        self.assertFalse(token.is_expired)

    def test_token_is_not_expired_before_expiry(self):
        """測試 Token 在過期時間之前不會過期"""
        future_time = timezone.now() + timedelta(days=30)
        token = ApiToken.objects.create(
            user=self.user,
            name='Future Token',
            token_hash=self.token_hash,
            prefix=self.full_token[:16],
            expires_at=future_time
        )
        
        self.assertFalse(token.is_expired)

    def test_token_is_expired_after_expiry(self):
        """測試 Token 在過期時間之後會過期"""
        past_time = timezone.now() - timedelta(days=1)
        token = ApiToken.objects.create(
            user=self.user,
            name='Expired Token',
            token_hash=self.token_hash,
            prefix=self.full_token[:16],
            expires_at=past_time
        )
        
        self.assertTrue(token.is_expired)

    def test_token_default_values(self):
        """測試 Token 的預設值"""
        token = ApiToken.objects.create(
            user=self.user,
            name='Default Token',
            token_hash=self.token_hash,
            prefix=self.full_token[:16]
        )
        
        self.assertEqual(token.usage_count, 0)
        self.assertTrue(token.is_active)
        self.assertEqual(token.permissions, [])
        self.assertIsNone(token.last_used_at)
        self.assertIsNone(token.last_used_ip)
        self.assertIsNone(token.expires_at)

    def test_token_permissions_json_field(self):
        """測試 permissions JSONField"""
        permissions = ['read:user', 'write:problems', 'read:submissions']
        token = ApiToken.objects.create(
            user=self.user,
            name='Multi-Permission Token',
            token_hash=self.token_hash,
            prefix=self.full_token[:16],
            permissions=permissions
        )
        
        # 重新從資料庫讀取
        token.refresh_from_db()
        self.assertEqual(token.permissions, permissions)

    def test_token_cascade_delete_with_user(self):
        """測試當使用者被刪除時，Token 也會被刪除"""
        token = ApiToken.objects.create(
            user=self.user,
            name='Cascade Test Token',
            token_hash=self.token_hash,
            prefix=self.full_token[:16]
        )
        
        token_id = token.id
        self.user.delete()
        
        # 確認 Token 已被刪除
        self.assertFalse(ApiToken.objects.filter(id=token_id).exists())

    def test_token_ordering(self):
        """測試 Token 按創建時間倒序排列"""
        import time
        
        # 創建第一個 token
        token1 = ApiToken.objects.create(
            user=self.user,
            name='First Token',
            token_hash=self.token_hash,
            prefix='prefix1'
        )
        
        # 等待一小段時間確保時間戳不同
        time.sleep(0.01)
        
        # 創建第二個 token
        full_token2, token_hash2 = generate_api_token()
        token2 = ApiToken.objects.create(
            user=self.user,
            name='Second Token',
            token_hash=token_hash2,
            prefix='prefix2'
        )
        
        tokens = list(ApiToken.objects.all())
        # 最新的應該在前面
        self.assertEqual(tokens[0].id, token2.id)
        self.assertEqual(tokens[1].id, token1.id)

    def test_token_hash_uniqueness(self):
        """測試 token_hash 必須唯一"""
        ApiToken.objects.create(
            user=self.user,
            name='First Token',
            token_hash=self.token_hash,
            prefix=self.full_token[:16]
        )
        
        # 嘗試創建相同 hash 的 token 應該失敗
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ApiToken.objects.create(
                user=self.user,
                name='Duplicate Token',
                token_hash=self.token_hash,  # 相同的 hash
                prefix='different_prefix'
            )

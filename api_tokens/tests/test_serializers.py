# api_tokens/tests/test_serializers.py
"""
測試 API Token Serializers
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from api_tokens.models import ApiToken
from api_tokens.serializers.api_token import (
    ApiTokenCreateSerializer,
    ApiTokenListSerializer,
    VALID_SCOPES
)
from api_tokens.services import generate_api_token

User = get_user_model()


class ApiTokenCreateSerializerTest(TestCase):
    """測試 ApiTokenCreateSerializer"""

    def setUp(self):
        """設置測試環境"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_valid_data(self):
        """測試有效的數據"""
        data = {
            'name': 'Test Token',
            'permissions': ['read:user', 'read:problems'],
        }
        serializer = ApiTokenCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_valid_data_with_expiry(self):
        """測試包含過期時間的有效數據"""
        data = {
            'name': 'Test Token',
            'permissions': ['read:user'],
            'expires_at': '2026-12-31T23:59:59Z'
        }
        serializer = ApiTokenCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_missing_name(self):
        """測試缺少 name 欄位"""
        data = {
            'permissions': ['read:user']
        }
        serializer = ApiTokenCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_permissions_optional(self):
        """測試 permissions 是選填的"""
        data = {
            'name': 'Test Token'
        }
        serializer = ApiTokenCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_permissions_not_list(self):
        """測試 permissions 不是列表時的錯誤"""
        data = {
            'name': 'Test Token',
            'permissions': 'read:user'  # 應該是列表
        }
        serializer = ApiTokenCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('permissions', serializer.errors)

    def test_invalid_permissions_scope(self):
        """測試無效的權限範圍"""
        data = {
            'name': 'Test Token',
            'permissions': ['read:user', 'invalid:scope']
        }
        serializer = ApiTokenCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('permissions', serializer.errors)

    def test_duplicate_permissions(self):
        """測試重複的權限"""
        data = {
            'name': 'Test Token',
            'permissions': ['read:user', 'read:user']
        }
        serializer = ApiTokenCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('permissions', serializer.errors)

    def test_all_valid_scopes(self):
        """測試所有有效的權限範圍"""
        data = {
            'name': 'Test Token',
            'permissions': list(VALID_SCOPES)
        }
        serializer = ApiTokenCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_empty_permissions_list(self):
        """測試空的 permissions 列表"""
        data = {
            'name': 'Test Token',
            'permissions': []
        }
        serializer = ApiTokenCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())


class ApiTokenListSerializerTest(TestCase):
    """測試 ApiTokenListSerializer"""

    def setUp(self):
        """設置測試環境"""
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
            prefix=full_token[:16],
            permissions=['read:user', 'read:problems']
        )

    def test_serializer_contains_expected_fields(self):
        """測試序列化器包含預期的欄位"""
        serializer = ApiTokenListSerializer(self.token)
        data = serializer.data
        
        expected_fields = [
            'id', 'name', 'prefix', 'permissions',
            'usage_count', 'last_used_at', 'last_used_ip',
            'created_at', 'expires_at', 'is_active', 'is_expired'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_serializer_does_not_contain_token_hash(self):
        """測試序列化器不包含 token_hash（安全性）"""
        serializer = ApiTokenListSerializer(self.token)
        data = serializer.data
        
        self.assertNotIn('token_hash', data)

    def test_is_expired_field(self):
        """測試 is_expired 欄位"""
        serializer = ApiTokenListSerializer(self.token)
        data = serializer.data
        
        # 沒有過期時間的 token 不應該過期
        self.assertFalse(data['is_expired'])

    def test_permissions_serialization(self):
        """測試 permissions 的序列化"""
        serializer = ApiTokenListSerializer(self.token)
        data = serializer.data
        
        self.assertEqual(data['permissions'], ['read:user', 'read:problems'])

    def test_all_fields_are_read_only(self):
        """測試所有欄位都是唯讀的"""
        serializer = ApiTokenListSerializer(self.token)
        
        # 嘗試修改數據不應該影響原始對象
        data = serializer.data
        data['name'] = 'Modified Name'
        
        # 重新序列化，名稱應該保持不變
        serializer2 = ApiTokenListSerializer(self.token)
        self.assertEqual(serializer2.data['name'], 'Test Token')

    def test_multiple_tokens_serialization(self):
        """測試多個 tokens 的序列化"""
        full_token2, token_hash2 = generate_api_token()
        token2 = ApiToken.objects.create(
            user=self.user,
            name='Second Token',
            token_hash=token_hash2,
            prefix=full_token2[:16],
            permissions=['write:problems']
        )
        
        tokens = [self.token, token2]
        serializer = ApiTokenListSerializer(tokens, many=True)
        data = serializer.data
        
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'Test Token')
        self.assertEqual(data[1]['name'], 'Second Token')

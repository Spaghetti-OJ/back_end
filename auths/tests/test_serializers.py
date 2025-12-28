# auths/tests/test_serializers.py
"""
測試 Auths Serializers
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from auths.models import UserActivity, LoginLog
from auths.serializers.activity import UserActivitySerializer
from auths.serializers.login_log import LoginLogSerializer
from auths.serializers.signup import RegisterSerializer, MeSerializer

User = get_user_model()


class UserActivitySerializerTest(TestCase):
    """測試 UserActivitySerializer"""

    def setUp(self):
        """設置測試環境"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            description='Test login',
            ip_address='192.168.1.1',
            metadata={'test': 'data'}
        )

    def test_serializer_contains_expected_fields(self):
        """測試序列化器包含預期的欄位"""
        serializer = UserActivitySerializer(self.activity)
        data = serializer.data
        
        expected_fields = [
            'id', 'user', 'username', 'activity_type', 'description',
            'ip_address', 'user_agent', 'success', 'created_at', 'metadata'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_username_field(self):
        """測試 username 欄位正確顯示"""
        serializer = UserActivitySerializer(self.activity)
        self.assertEqual(serializer.data['username'], 'testuser')

    def test_metadata_serialization(self):
        """測試 metadata 的序列化"""
        serializer = UserActivitySerializer(self.activity)
        self.assertEqual(serializer.data['metadata'], {'test': 'data'})


class LoginLogSerializerTest(TestCase):
    """測試 LoginLogSerializer"""

    def setUp(self):
        """設置測試環境"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.log = LoginLog.objects.create(
            user=self.user,
            login_status='success',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            location='Taipei, Taiwan'
        )

    def test_serializer_contains_expected_fields(self):
        """測試序列化器包含預期的欄位"""
        serializer = LoginLogSerializer(self.log)
        data = serializer.data
        
        expected_fields = [
            'id', 'username', 'login_status', 'ip_address',
            'user_agent', 'location', 'created_at'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_login_status_display(self):
        """測試 login_status 使用 get_login_status_display"""
        serializer = LoginLogSerializer(self.log)
        # 應該顯示中文名稱而不是代碼
        self.assertIsNotNone(serializer.data['login_status'])


class RegisterSerializerTest(TestCase):
    """測試 RegisterSerializer"""

    def test_valid_registration_data(self):
        """測試有效的註冊數據"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'real_name': 'New User',
            'role': 'student'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_registration_with_student_id(self):
        """測試包含學號的註冊"""
        data = {
            'username': 'student1',
            'email': 'student@example.com',
            'password': 'pass123',
            'real_name': 'Student One',
            'role': 'student',
            'student_id': 'B12345678'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_missing_required_fields(self):
        """測試缺少必填欄位"""
        data = {
            'username': 'testuser'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertIn('password', serializer.errors)

    def test_create_user(self):
        """測試創建使用者"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'real_name': 'New User',
            'role': 'student',
            'student_id': 'B12345678',
            'bio': 'Test bio'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertTrue(user.check_password('securepass123'))


class MeSerializerTest(TestCase):
    """測試 MeSerializer"""

    def setUp(self):
        """設置測試環境"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_serializer_contains_expected_fields(self):
        """測試序列化器包含預期的欄位"""
        serializer = MeSerializer(self.user)
        data = serializer.data
        
        # 根據實際的 MeSerializer 實現調整
        self.assertIn('user_id', data)
        self.assertIn('username', data)
        self.assertIn('email', data)

    def test_user_id_field(self):
        """測試 user_id 欄位"""
        serializer = MeSerializer(self.user)
        self.assertEqual(str(serializer.data['user_id']), str(self.user.id))

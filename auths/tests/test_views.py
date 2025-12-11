# auths/tests/test_views.py
"""
測試 Auths Views
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from auths.models import UserActivity, LoginLog

User = get_user_model()


class RegisterViewTest(TestCase):
    """測試 RegisterView (POST /auth/signup/)"""

    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.url = reverse('register')

    def test_register_with_valid_data(self):
        """測試使用有效數據註冊"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'real_name': 'New User',
            'role': 'student'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'ok')
        
        # 確認使用者已創建
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_with_student_id(self):
        """測試包含學號的註冊"""
        data = {
            'username': 'student1',
            'email': 'student@example.com',
            'password': 'pass123',
            'real_name': 'Student One',
            'role': 'student',
            'student_id': 'B12345678'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_with_missing_fields(self):
        """測試缺少必填欄位"""
        data = {
            'username': 'incomplete'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_with_duplicate_username(self):
        """測試重複的使用者名稱"""
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='pass123'
        )
        
        data = {
            'username': 'existing',
            'email': 'new@example.com',
            'password': 'pass123',
            'real_name': 'New User',
            'role': 'student'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeViewTest(TestCase):
    """測試 MeView (GET /auth/me/)"""

    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.url = reverse('me')

    def test_me_requires_authentication(self):
        """測試獲取當前使用者資訊需要認證"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        """測試返回當前使用者資訊"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['username'], 'testuser')


class UserActivityViewTest(TestCase):
    """測試 UserActivity Views"""

    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_staff=True
        )

    def test_create_activity_requires_authentication(self):
        """測試創建活動記錄需要認證"""
        url = reverse('user-activity-create')
        data = {
            'activity_type': 'view_problem',
            'description': 'Viewed problem 1'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_activity(self):
        """測試創建活動記錄"""
        self.client.force_authenticate(user=self.user)
        url = reverse('user-activity-create')
        
        data = {
            'activity_type': 'view_problem',
            'description': 'Viewed problem 1',
            'metadata': {'problem_id': 1}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 確認活動已創建
        self.assertTrue(
            UserActivity.objects.filter(
                user=self.user,
                activity_type='view_problem'
            ).exists()
        )

    def test_list_user_activities_requires_admin(self):
        """測試列出特定使用者活動需要管理員權限"""
        url = reverse('user-activity-list', kwargs={'user_id': self.user.id})
        
        # 普通使用者無法訪問
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_user_activities(self):
        """測試管理員可以列出使用者活動"""
        # 創建一些活動
        UserActivity.objects.create(
            user=self.user,
            activity_type='login'
        )
        
        self.client.force_authenticate(user=self.admin)
        url = reverse('user-activity-list', kwargs={'user_id': self.user.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['data']), 0)


class LoginLogViewTest(TestCase):
    """測試 LoginLog Views"""

    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_staff=True
        )

    def test_list_own_login_logs_requires_authentication(self):
        """測試列出自己的登入日誌需要認證"""
        url = reverse('login-logs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_own_login_logs(self):
        """測試列出自己的登入日誌"""
        # 創建登入日誌
        LoginLog.objects.create(
            user=self.user,
            login_status='success',
            ip_address='192.168.1.1'
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('login-logs')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)

    def test_list_user_login_logs_requires_admin(self):
        """測試列出特定使用者登入日誌需要管理員權限"""
        url = reverse('user-login-logs', kwargs={'user_id': self.user.id})
        
        # 普通使用者無法訪問
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_user_login_logs(self):
        """測試管理員可以列出使用者登入日誌"""
        LoginLog.objects.create(
            user=self.user,
            login_status='success',
            ip_address='192.168.1.1'
        )
        
        self.client.force_authenticate(user=self.admin)
        url = reverse('user-login-logs', kwargs={'user_id': self.user.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_suspicious_activities_requires_admin(self):
        """測試列出異常登入需要管理員權限"""
        url = reverse('suspicious-activities')
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_suspicious_activities(self):
        """測試管理員可以列出異常登入"""
        # 創建失敗的登入記錄
        LoginLog.objects.create(
            user=None,
            login_status='failed_credentials',
            ip_address='192.168.1.100'
        )
        
        self.client.force_authenticate(user=self.admin)
        url = reverse('suspicious-activities')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SessionRevokeViewTest(TestCase):
    """測試 SessionRevokeView (POST /auth/session/revoke/)"""

    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_revoke_requires_authentication(self):
        """測試撤銷 session 需要認證"""
        url = reverse('session-revoke')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revoke_without_refresh_token(self):
        """測試沒有提供 refresh token"""
        self.client.force_authenticate(user=self.user)
        url = reverse('session-revoke')
        
        response = self.client.post(url, {}, format='json')
        
        # 應該返回錯誤
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

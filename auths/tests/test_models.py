# auths/tests/test_models.py
"""
測試 Auths Models (UserActivity, LoginLog)
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from auths.models import UserActivity, LoginLog

User = get_user_model()


class UserActivityModelTest(TestCase):
    """測試 UserActivity Model"""

    def setUp(self):
        """設置測試環境"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_user_activity(self):
        """測試創建使用者活動記錄"""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            description='User logged in',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0'
        )
        
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, 'login')
        self.assertTrue(activity.success)
        self.assertEqual(activity.ip_address, '192.168.1.1')

    def test_activity_default_values(self):
        """測試活動記錄的預設值"""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='view_problem'
        )
        
        self.assertTrue(activity.success)
        self.assertEqual(activity.metadata, {})
        self.assertIsNotNone(activity.created_at)

    def test_activity_with_metadata(self):
        """測試帶有 metadata 的活動記錄"""
        metadata = {
            'problem_id': '123',
            'language': 'python',
            'file_size': 1024
        }
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='submit',
            metadata=metadata
        )
        
        activity.refresh_from_db()
        self.assertEqual(activity.metadata, metadata)

    def test_activity_with_generic_foreign_key(self):
        """測試使用 GenericForeignKey 關聯對象"""
        # 使用 User 作為測試對象
        content_type = ContentType.objects.get_for_model(User)
        
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='view_problem',
            content_type=content_type,
            object_id=self.user.id
        )
        
        # 測試 GenericForeignKey
        self.assertEqual(activity.content_object, self.user)

    def test_activity_ordering(self):
        """測試活動記錄按時間倒序排列"""
        import time
        
        activity1 = UserActivity.objects.create(
            user=self.user,
            activity_type='login'
        )
        
        time.sleep(0.01)
        
        activity2 = UserActivity.objects.create(
            user=self.user,
            activity_type='logout'
        )
        
        activities = list(UserActivity.objects.all())
        self.assertEqual(activities[0].id, activity2.id)
        self.assertEqual(activities[1].id, activity1.id)

    def test_activity_cascade_delete_with_user(self):
        """測試當使用者被刪除時，活動記錄也會被刪除"""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login'
        )
        
        activity_id = activity.id
        self.user.delete()
        
        self.assertFalse(UserActivity.objects.filter(id=activity_id).exists())

    def test_activity_string_representation(self):
        """測試活動記錄的字串表示"""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            description='Test login'
        )
        
        str_repr = str(activity)
        self.assertIn(self.user.username, str_repr)
        self.assertIn('登入', str_repr)


class LoginLogModelTest(TestCase):
    """測試 LoginLog Model"""

    def setUp(self):
        """設置測試環境"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_login_log(self):
        """測試創建登入日誌"""
        log = LoginLog.objects.create(
            user=self.user,
            login_status='success',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            location='Taipei, Taiwan'
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.login_status, 'success')
        self.assertEqual(log.location, 'Taipei, Taiwan')

    def test_login_log_status_choices(self):
        """測試登入狀態選項"""
        statuses = ['success', 'failed_credentials', 'failed_user_not_found', 
                   'blocked_ip', 'blocked_account']
        
        for status in statuses:
            log = LoginLog.objects.create(
                user=self.user,
                login_status=status,
                ip_address='127.0.0.1'
            )
            self.assertEqual(log.login_status, status)

    def test_login_log_without_user(self):
        """測試沒有使用者的登入日誌（失敗的登入嘗試）"""
        log = LoginLog.objects.create(
            user=None,
            login_status='failed_user_not_found',
            ip_address='192.168.1.100',
            user_agent='curl/7.68.0'
        )
        
        self.assertIsNone(log.user)
        self.assertEqual(log.login_status, 'failed_user_not_found')

    def test_login_log_ordering(self):
        """測試登入日誌按時間倒序排列"""
        import time
        
        log1 = LoginLog.objects.create(
            user=self.user,
            login_status='success',
            ip_address='127.0.0.1'
        )
        
        time.sleep(0.01)
        
        log2 = LoginLog.objects.create(
            user=self.user,
            login_status='success',
            ip_address='127.0.0.1'
        )
        
        logs = list(LoginLog.objects.all())
        self.assertEqual(logs[0].id, log2.id)
        self.assertEqual(logs[1].id, log1.id)

    def test_login_log_cascade_delete_with_user(self):
        """測試當使用者被刪除時，登入日誌也會被刪除"""
        log = LoginLog.objects.create(
            user=self.user,
            login_status='success',
            ip_address='127.0.0.1'
        )
        
        log_id = log.id
        self.user.delete()
        
        self.assertFalse(LoginLog.objects.filter(id=log_id).exists())

    def test_login_log_string_representation(self):
        """測試登入日誌的字串表示"""
        log = LoginLog.objects.create(
            user=self.user,
            login_status='success',
            ip_address='192.168.1.1'
        )
        
        str_repr = str(log)
        self.assertIn(self.user.username, str_repr)
        self.assertIn('192.168.1.1', str_repr)

    def test_login_log_get_status_display(self):
        """測試 get_login_status_display 方法"""
        log = LoginLog.objects.create(
            user=self.user,
            login_status='success',
            ip_address='127.0.0.1'
        )
        
        # 應該返回中文顯示名稱
        display = log.get_login_status_display()
        self.assertIsNotNone(display)

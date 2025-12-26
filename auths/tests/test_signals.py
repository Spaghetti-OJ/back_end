# auths/tests/test_signals.py
"""
測試 Auths Signals
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_login_failed
from auths.models import LoginLog

User = get_user_model()


class LoginSignalsTest(TestCase):
    """測試登入相關的 Signals"""

    def setUp(self):
        """設置測試環境"""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_successful_login_creates_log(self):
        """測試成功登入時創建日誌"""
        request = self.factory.post('/auth/session/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        # 觸發信號
        user_logged_in.send(
            sender=self.user.__class__,
            request=request,
            user=self.user
        )
        
        # 檢查是否創建了登入日誌
        log = LoginLog.objects.filter(user=self.user).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.login_status, 'success')
        self.assertEqual(log.ip_address, '192.168.1.1')

    def test_failed_login_creates_log(self):
        """測試失敗登入時創建日誌"""
        request = self.factory.post('/auth/session/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'curl/7.68.0'
        
        credentials = {'username': 'wronguser'}
        
        # 觸發失敗登入信號
        user_login_failed.send(
            sender=__name__,
            credentials=credentials,
            request=request
        )
        
        # 檢查是否創建了失敗日誌
        logs = LoginLog.objects.filter(login_status='failed_credentials')
        self.assertTrue(logs.exists())

    def test_login_log_with_x_forwarded_for(self):
        """測試使用 X-Forwarded-For 的登入日誌"""
        request = self.factory.post('/auth/session/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        user_logged_in.send(
            sender=self.user.__class__,
            request=request,
            user=self.user
        )
        
        log = LoginLog.objects.filter(user=self.user).first()
        # 應該使用 X-Forwarded-For 的第一個 IP
        self.assertEqual(log.ip_address, '10.0.0.1')

    def test_login_log_without_user_agent(self):
        """測試沒有 User-Agent 的登入日誌"""
        request = self.factory.post('/auth/session/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        # 沒有 HTTP_USER_AGENT
        
        user_logged_in.send(
            sender=self.user.__class__,
            request=request,
            user=self.user
        )
        
        log = LoginLog.objects.filter(user=self.user).first()
        self.assertIsNotNone(log)
        # user_agent 應該是 None 或空字符串
        self.assertTrue(log.user_agent is None or log.user_agent == '')

    def test_multiple_logins_create_multiple_logs(self):
        """測試多次登入創建多個日誌"""
        request = self.factory.post('/auth/session/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        # 觸發 3 次登入
        for _ in range(3):
            user_logged_in.send(
                sender=self.user.__class__,
                request=request,
                user=self.user
            )
        
        logs_count = LoginLog.objects.filter(user=self.user).count()
        self.assertEqual(logs_count, 3)

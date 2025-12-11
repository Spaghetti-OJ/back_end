# copycat/tests/test_views.py
"""
測試 Copycat Views
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from copycat.models import CopycatReport

User = get_user_model()


class CopycatViewTest(TestCase):
    """測試 CopycatView (POST /copycat/, GET /copycat/)"""

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
        self.url = reverse('copycat')

    def test_trigger_check_requires_authentication(self):
        """測試觸發檢測需要認證"""
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_trigger_check_requires_admin(self):
        """測試觸發檢測需要管理員權限"""
        self.client.force_authenticate(user=self.user)
        
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_trigger_check_without_problem_id(self):
        """測試沒有提供 problem_id"""
        self.client.force_authenticate(user=self.admin)
        
        data = {'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('problem_id', response.data['message'])

    def test_trigger_check_with_invalid_problem_id(self):
        """測試無效的 problem_id"""
        self.client.force_authenticate(user=self.admin)
        
        data = {'problem_id': 'invalid', 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_trigger_check_with_invalid_language(self):
        """測試無效的語言"""
        self.client.force_authenticate(user=self.admin)
        
        data = {'problem_id': 101, 'language': 'invalid_lang'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('不支援的語言', response.data['message'])

    @patch('copycat.views.threading.Thread')
    def test_trigger_check_success(self, mock_thread):
        """測試成功觸發檢測"""
        self.client.force_authenticate(user=self.admin)
        
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['status'], 'ok')
        self.assertIn('report_id', response.data['data'])
        
        # 確認報告已創建
        self.assertTrue(CopycatReport.objects.filter(problem_id=101).exists())
        
        # 確認線程已啟動
        mock_thread.assert_called_once()

    @patch('copycat.views.threading.Thread')
    def test_trigger_check_with_pending_task(self, mock_thread):
        """測試已有進行中的任務"""
        # 創建一個 pending 的報告
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.admin,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.admin)
        
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('正在進行中', response.data['message'])

    @patch('copycat.views.threading.Thread')
    def test_trigger_check_default_language(self, mock_thread):
        """測試預設語言為 python"""
        self.client.force_authenticate(user=self.admin)
        
        data = {'problem_id': 101}  # 沒有指定語言
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_query_report_requires_authentication(self):
        """測試查詢報告需要認證"""
        response = self.client.get(f'{self.url}?problem_id=101')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_query_report_requires_admin(self):
        """測試查詢報告需要管理員權限"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_query_report_without_problem_id(self):
        """測試查詢報告沒有提供 problem_id"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_query_report_not_found(self):
        """測試查詢不存在的報告"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(f'{self.url}?problem_id=999')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('尚未進行過', response.data['message'])

    def test_query_report_pending(self):
        """測試查詢處理中的報告"""
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.admin,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'pending')
        self.assertIsNone(response.data['data']['moss_url'])

    def test_query_report_success(self):
        """測試查詢成功的報告"""
        moss_url = 'http://moss.stanford.edu/results/123/'
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.admin,
            status='success',
            moss_url=moss_url
        )
        
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'success')
        self.assertEqual(response.data['data']['moss_url'], moss_url)

    def test_query_report_failed(self):
        """測試查詢失敗的報告"""
        error_msg = 'Connection timeout'
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.admin,
            status='failed',
            error_message=error_msg
        )
        
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'failed')
        self.assertEqual(response.data['data']['error_message'], error_msg)

    def test_query_report_returns_latest(self):
        """測試查詢返回最新的報告"""
        import time
        
        # 創建舊報告
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.admin,
            status='success',
            moss_url='http://old.url'
        )
        
        time.sleep(0.01)
        
        # 創建新報告
        new_report = CopycatReport.objects.create(
            problem_id=101,
            requester=self.admin,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['id'], new_report.id)
        self.assertEqual(response.data['data']['status'], 'pending')

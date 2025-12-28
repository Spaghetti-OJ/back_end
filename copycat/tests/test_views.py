# copycat/tests/test_views.py
"""
測試 Copycat Views
權限邏輯：使用者必須是該題所屬課程的老師或助教
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from copycat.models import CopycatReport
from courses.models import Courses, Course_members
from problems.models import Problems
from user.models import UserProfile

User = get_user_model()


class CopycatViewTest(TestCase):
    """測試 CopycatView (POST /copycat/, GET /copycat/)"""

    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        
        # 創建普通使用者
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        UserProfile.objects.update_or_create(user=self.user, defaults={'email_verified': True})
        
        # 創建課程老師
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='teacher123'
        )
        UserProfile.objects.update_or_create(user=self.teacher, defaults={'email_verified': True})
        
        # 創建課程助教
        self.ta = User.objects.create_user(
            username='ta',
            email='ta@example.com',
            password='ta123'
        )
        UserProfile.objects.update_or_create(user=self.ta, defaults={'email_verified': True})
        
        # 創建學生
        self.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='student123'
        )
        UserProfile.objects.update_or_create(user=self.student, defaults={'email_verified': True})
        
        # 創建課程（teacher 是主要老師）
        self.course = Courses.objects.create(
            name='Test Course',
            description='Test Description',
            teacher_id=self.teacher
        )
        
        # 將 TA 加入課程成員
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.ta,
            role=Course_members.Role.TA
        )
        
        # 將學生加入課程成員
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.student,
            role=Course_members.Role.STUDENT
        )
        
        # 創建題目（關聯到課程）
        self.problem = Problems.objects.create(
            id=101,
            title='Test Problem',
            description='Test Description',
            course_id=self.course,
            creator_id=self.teacher
        )
        
        self.url = reverse('copycat')

    # ===========================================
    # 認證測試
    # ===========================================
    
    def test_trigger_check_requires_authentication(self):
        """測試觸發檢測需要認證"""
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        # DRF 預設在未認證時可能返回 401 或 403，取決於設定
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_query_report_requires_authentication(self):
        """測試查詢報告需要認證"""
        response = self.client.get(f'{self.url}?problem_id=101')
        # DRF 預設在未認證時可能返回 401 或 403，取決於設定
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    # ===========================================
    # 權限測試 - POST
    # ===========================================
    
    def test_trigger_check_denied_for_non_course_member(self):
        """測試非課程成員無法觸發檢測"""
        self.client.force_authenticate(user=self.user)
        
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('老師或助教', response.data['message'])

    def test_trigger_check_denied_for_student(self):
        """測試學生無法觸發檢測"""
        self.client.force_authenticate(user=self.student)
        
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('老師或助教', response.data['message'])

    @patch('copycat.views.threading.Thread')
    def test_trigger_check_allowed_for_course_teacher(self, mock_thread):
        """測試課程主要老師可以觸發檢測"""
        self.client.force_authenticate(user=self.teacher)
        
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['status'], 'ok')

    @patch('copycat.views.threading.Thread')
    def test_trigger_check_allowed_for_ta(self, mock_thread):
        """測試助教可以觸發檢測"""
        self.client.force_authenticate(user=self.ta)
        
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['status'], 'ok')

    @patch('copycat.views.threading.Thread')
    def test_trigger_check_allowed_for_course_member_teacher_role(self, mock_thread):
        """測試課程成員中角色為老師的使用者可以觸發檢測"""
        # 創建另一位老師並加入課程成員
        another_teacher = User.objects.create_user(
            username='another_teacher',
            email='another_teacher@example.com',
            password='teacher123'
        )
        UserProfile.objects.update_or_create(user=another_teacher, defaults={'email_verified': True})
        Course_members.objects.create(
            course_id=self.course,
            user_id=another_teacher,
            role=Course_members.Role.TEACHER
        )
        
        self.client.force_authenticate(user=another_teacher)
        
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    # ===========================================
    # 權限測試 - GET
    # ===========================================
    
    def test_query_report_denied_for_non_course_member(self):
        """測試非課程成員無法查詢報告"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_query_report_denied_for_student(self):
        """測試學生無法查詢報告"""
        self.client.force_authenticate(user=self.student)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_query_report_allowed_for_teacher(self):
        """測試老師可以查詢報告"""
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.teacher,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.teacher)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_query_report_allowed_for_ta(self):
        """測試助教可以查詢報告"""
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.teacher,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.ta)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ===========================================
    # 參數驗證測試 - POST
    # ===========================================
    
    def test_trigger_check_without_problem_id(self):
        """測試沒有提供 problem_id"""
        self.client.force_authenticate(user=self.teacher)
        
        data = {'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('problem_id', response.data['message'])

    def test_trigger_check_with_invalid_problem_id(self):
        """測試無效的 problem_id"""
        self.client.force_authenticate(user=self.teacher)
        
        data = {'problem_id': 'invalid', 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_trigger_check_with_nonexistent_problem_id(self):
        """測試不存在的 problem_id"""
        self.client.force_authenticate(user=self.teacher)
        
        data = {'problem_id': 99999, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_trigger_check_with_invalid_language(self):
        """測試無效的語言"""
        self.client.force_authenticate(user=self.teacher)
        
        data = {'problem_id': 101, 'language': 'invalid_lang'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('不支援的語言', response.data['message'])

    # ===========================================
    # 參數驗證測試 - GET
    # ===========================================
    
    def test_query_report_without_problem_id(self):
        """測試查詢報告沒有提供 problem_id"""
        self.client.force_authenticate(user=self.teacher)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_query_report_with_invalid_problem_id(self):
        """測試查詢報告使用無效的 problem_id"""
        self.client.force_authenticate(user=self.teacher)
        
        response = self.client.get(f'{self.url}?problem_id=invalid')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ===========================================
    # 功能測試 - POST
    # ===========================================

    @patch('copycat.views.threading.Thread')
    def test_trigger_check_success(self, mock_thread):
        """測試成功觸發檢測"""
        self.client.force_authenticate(user=self.teacher)
        
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
            requester=self.teacher,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.teacher)
        
        data = {'problem_id': 101, 'language': 'python'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('正在進行中', response.data['message'])

    @patch('copycat.views.threading.Thread')
    def test_trigger_check_default_language(self, mock_thread):
        """測試預設語言為 python"""
        self.client.force_authenticate(user=self.teacher)
        
        data = {'problem_id': 101}  # 沒有指定語言
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    # ===========================================
    # 功能測試 - GET
    # ===========================================

    def test_query_report_not_found(self):
        """測試查詢不存在的報告"""
        self.client.force_authenticate(user=self.teacher)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('尚未進行過', response.data['message'])

    def test_query_report_pending(self):
        """測試查詢處理中的報告"""
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.teacher,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.teacher)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'pending')
        self.assertIsNone(response.data['data']['moss_url'])

    def test_query_report_success(self):
        """測試查詢成功的報告"""
        moss_url = 'http://moss.stanford.edu/results/123/'
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.teacher,
            status='success',
            moss_url=moss_url
        )
        
        self.client.force_authenticate(user=self.teacher)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'success')
        self.assertEqual(response.data['data']['moss_url'], moss_url)

    def test_query_report_failed(self):
        """測試查詢失敗的報告"""
        error_msg = 'Connection timeout'
        CopycatReport.objects.create(
            problem_id=101,
            requester=self.teacher,
            status='failed',
            error_message=error_msg
        )
        
        self.client.force_authenticate(user=self.teacher)
        
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
            requester=self.teacher,
            status='success',
            moss_url='http://old.url'
        )
        
        time.sleep(0.01)
        
        # 創建新報告
        new_report = CopycatReport.objects.create(
            problem_id=101,
            requester=self.teacher,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.teacher)
        
        response = self.client.get(f'{self.url}?problem_id=101')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['id'], new_report.id)
        self.assertEqual(response.data['data']['status'], 'pending')

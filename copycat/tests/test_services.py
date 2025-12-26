# copycat/tests/test_services.py
"""
測試 Copycat Services (MOSS Integration)
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from copycat.models import CopycatReport
from copycat.services import run_moss_check, LANG_DB_MAP

User = get_user_model()


class MossServicesTest(TestCase):
    """測試 MOSS 服務層"""

    def setUp(self):
        """設置測試環境"""
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_staff=True
        )
        self.report = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user,
            status='pending'
        )

    @patch('copycat.services.mosspy.Moss')
    @patch('copycat.services.Submission.objects.filter')
    def test_run_moss_check_with_no_submissions(self, mock_submissions, mock_moss):
        """測試沒有提交時的 MOSS 檢查"""
        # 模擬沒有提交
        mock_submissions.return_value.values.return_value.annotate.return_value = []
        
        run_moss_check(self.report.id, 101, 'python')
        
        # 報告應該更新為失敗
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'failed')
        self.assertIn('沒有找到任何提交', self.report.error_message)

    @patch('copycat.services.mosspy.Moss')
    @patch('copycat.services.Submission.objects.filter')
    def test_run_moss_check_with_invalid_language(self, mock_submissions, mock_moss):
        """測試使用無效語言的 MOSS 檢查"""
        run_moss_check(self.report.id, 101, 'invalid_language')
        
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'failed')
        self.assertIn('不支援的語言', self.report.error_message)

    @patch('copycat.services.mosspy.Moss')
    @patch('copycat.services.Submission.objects.filter')
    @patch('copycat.services.tempfile.NamedTemporaryFile')
    def test_run_moss_check_success(self, mock_tempfile, mock_submissions, mock_moss):
        """測試成功的 MOSS 檢查"""
        # 模擬提交數據
        mock_submission = MagicMock()
        mock_submission.user__username = 'student1'
        mock_submission.code = 'print("Hello")'
        mock_submission.language = 2  # Python
        
        mock_submissions.return_value.values.return_value.annotate.return_value = [
            {
                'user__username': 'student1',
                'code': 'print("Hello")',
                'language': 2,
                'latest_created_at': '2025-01-01'
            }
        ]
        
        # 模擬 MOSS 實例
        mock_moss_instance = MagicMock()
        mock_moss_instance.send.return_value = 'http://moss.stanford.edu/results/123/'
        mock_moss.return_value = mock_moss_instance
        
        # 模擬臨時文件
        mock_file = MagicMock()
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        run_moss_check(self.report.id, 101, 'python')
        
        # 檢查報告狀態
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'success')
        self.assertIsNotNone(self.report.moss_url)

    @patch('copycat.services.CopycatReport.objects.get')
    def test_run_moss_check_with_nonexistent_report(self, mock_get):
        """測試不存在的報告"""
        from copycat.models import CopycatReport as Report
        mock_get.side_effect = Report.DoesNotExist
        
        # 不應該拋出異常
        run_moss_check(999, 101, 'python')

    @patch('copycat.services.mosspy.Moss')
    @patch('copycat.services.Submission.objects.filter')
    def test_run_moss_check_handles_moss_exception(self, mock_submissions, mock_moss):
        """測試處理 MOSS 異常"""
        # 模擬提交
        mock_submissions.return_value.values.return_value.annotate.return_value = [
            {
                'user__username': 'student1',
                'code': 'print("Hello")',
                'language': 2,
                'latest_created_at': '2025-01-01'
            }
        ]
        
        # 模擬 MOSS 拋出異常
        mock_moss.return_value.send.side_effect = Exception('MOSS server error')
        
        run_moss_check(self.report.id, 101, 'python')
        
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'failed')
        self.assertIn('MOSS server error', self.report.error_message)


class LanguageMappingTest(TestCase):
    """測試語言映射"""

    def test_all_language_aliases_map_correctly(self):
        """測試所有語言別名正確映射"""
        # C 語言
        self.assertEqual(LANG_DB_MAP['c'], 0)
        
        # C++ 的所有別名
        self.assertEqual(LANG_DB_MAP['cpp'], 1)
        self.assertEqual(LANG_DB_MAP['c++'], 1)
        self.assertEqual(LANG_DB_MAP['cc'], 1)
        
        # Python 的別名
        self.assertEqual(LANG_DB_MAP['python'], 2)
        self.assertEqual(LANG_DB_MAP['py'], 2)
        
        # Java
        self.assertEqual(LANG_DB_MAP['java'], 3)
        
        # JavaScript 的別名
        self.assertEqual(LANG_DB_MAP['javascript'], 4)
        self.assertEqual(LANG_DB_MAP['js'], 4)

# copycat/tests/test_models.py
"""
測試 CopycatReport Model
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from copycat.models import CopycatReport

User = get_user_model()


class CopycatReportModelTest(TestCase):
    """測試 CopycatReport Model"""

    def setUp(self):
        """設置測試環境"""
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_staff=True
        )

    def test_create_copycat_report(self):
        """測試創建抄襲檢測報告"""
        report = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user,
            status='pending'
        )
        
        self.assertEqual(report.problem_id, 101)
        self.assertEqual(report.requester, self.user)
        self.assertEqual(report.status, 'pending')
        self.assertIsNone(report.moss_url)

    def test_report_default_status(self):
        """測試報告的預設狀態"""
        report = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user
        )
        
        self.assertEqual(report.status, 'pending')

    def test_report_status_choices(self):
        """測試報告狀態選項"""
        statuses = ['pending', 'success', 'failed']
        
        for status in statuses:
            report = CopycatReport.objects.create(
                problem_id=100 + statuses.index(status),
                requester=self.user,
                status=status
            )
            self.assertEqual(report.status, status)

    def test_report_with_moss_url(self):
        """測試包含 MOSS URL 的報告"""
        moss_url = 'http://moss.stanford.edu/results/123456789/'
        report = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user,
            status='success',
            moss_url=moss_url
        )
        
        self.assertEqual(report.moss_url, moss_url)

    def test_report_with_error_message(self):
        """測試包含錯誤訊息的報告"""
        error_msg = 'Connection timeout'
        report = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user,
            status='failed',
            error_message=error_msg
        )
        
        self.assertEqual(report.error_message, error_msg)

    def test_report_without_requester(self):
        """測試沒有請求者的報告（requester 被刪除）"""
        report = CopycatReport.objects.create(
            problem_id=101,
            requester=None,
            status='pending'
        )
        
        self.assertIsNone(report.requester)

    def test_report_ordering(self):
        """測試報告按創建時間倒序排列"""
        import time
        
        report1 = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user
        )
        
        time.sleep(0.01)
        
        report2 = CopycatReport.objects.create(
            problem_id=102,
            requester=self.user
        )
        
        reports = list(CopycatReport.objects.all())
        self.assertEqual(reports[0].id, report2.id)
        self.assertEqual(reports[1].id, report1.id)

    def test_report_set_null_on_user_delete(self):
        """測試當使用者被刪除時，requester 設為 NULL"""
        report = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user
        )
        
        report_id = report.id
        self.user.delete()
        
        # 報告應該仍然存在，但 requester 為 None
        report.refresh_from_db()
        self.assertIsNone(report.requester)

    def test_report_timestamps(self):
        """測試報告的時間戳"""
        report = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user
        )
        
        self.assertIsNotNone(report.created_at)
        self.assertIsNotNone(report.updated_at)
        
        # 更新報告
        old_updated_at = report.updated_at
        import time
        time.sleep(0.01)
        
        report.status = 'success'
        report.save()
        
        report.refresh_from_db()
        self.assertGreater(report.updated_at, old_updated_at)

    def test_multiple_reports_for_same_problem(self):
        """測試同一題目可以有多個報告"""
        report1 = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user,
            status='success'
        )
        
        report2 = CopycatReport.objects.create(
            problem_id=101,
            requester=self.user,
            status='pending'
        )
        
        reports = CopycatReport.objects.filter(problem_id=101)
        self.assertEqual(reports.count(), 2)

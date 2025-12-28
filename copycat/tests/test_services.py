# copycat/tests/test_services.py
"""
測試 Copycat Services (MOSS Integration)

執行方式:
1. 單元測試: python manage.py test copycat.tests.test_services
2. MOSS 連線測試: python copycat/tests/test_services.py
"""
import os
import sys

# 設定 Django 環境（僅在直接執行時需要）
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
    import django
    django.setup()

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


# ============================================================
# 直接執行時的 MOSS 連線測試
# ============================================================

def test_moss_connection():
    """
    測試 MOSS 是否能成功連線到 Stanford 伺服器
    這會實際發送請求到 MOSS 伺服器
    """
    import mosspy
    import tempfile
    from django.conf import settings
    
    print("=" * 60)
    print("  MOSS 連線測試")
    print("=" * 60)
    
    # 1. 檢查 MOSS_USER_ID
    moss_user_id = getattr(settings, 'MOSS_USER_ID', 0)
    print(f"\n1. MOSS_USER_ID: {moss_user_id}")
    
    if moss_user_id == 0:
        print("\n❌ 錯誤: MOSS_USER_ID 為 0，這是無效的 ID")
        print("   請至 https://theory.stanford.edu/~aiken/moss/ 申請")
        print("   發送郵件到 moss@moss.stanford.edu，內容只需要寫:")
        print("   registeruser")
        print("   然後將收到的 User ID 設定到 .env 的 MOSS_USER_ID")
        return False
    
    # 2. 建立 MOSS 客戶端
    print(f"\n2. 建立 MOSS 客戶端 (語言: python)...")
    m = mosspy.Moss(moss_user_id, "python")
    
    # 3. 建立測試檔案
    print(f"\n3. 建立測試檔案...")
    with tempfile.TemporaryDirectory() as temp_dir:
        # 建立兩個測試檔案（至少需要 2 個檔案才能比對）
        file1_path = os.path.join(temp_dir, "student1_test.py")
        file2_path = os.path.join(temp_dir, "student2_test.py")
        
        # 故意讓兩個檔案相似，方便測試
        with open(file1_path, "w") as f:
            f.write('''
def calculate_sum(numbers):
    """計算數字列表的總和"""
    total = 0
    for num in numbers:
        total += num
    return total

def main():
    data = [1, 2, 3, 4, 5]
    result = calculate_sum(data)
    print(f"Sum: {result}")

if __name__ == "__main__":
    main()
''')
        
        with open(file2_path, "w") as f:
            f.write('''
def sum_numbers(number_list):
    """計算數字列表的總和"""
    total = 0
    for n in number_list:
        total += n
    return total

def main():
    numbers = [1, 2, 3, 4, 5]
    answer = sum_numbers(numbers)
    print(f"Sum: {answer}")

if __name__ == "__main__":
    main()
''')
        
        m.addFile(file1_path)
        m.addFile(file2_path)
        
        print(f"   ✅ student1_test.py")
        print(f"   ✅ student2_test.py")
        
        # 4. 發送到 MOSS 伺服器
        print(f"\n4. 發送到 MOSS 伺服器...")
        print("   （這可能需要 5-30 秒，請耐心等待）")
        
        try:
            url = m.send()
            print(f"\n{'=' * 60}")
            print(f"  ✅ 成功！MOSS 報告網址:")
            print(f"{'=' * 60}")
            print(f"\n  {url}\n")
            print("  請在瀏覽器中開啟此網址查看抄襲比對結果")
            print(f"{'=' * 60}")
            return True
        except Exception as e:
            print(f"\n❌ 發送失敗: {e}")
            print("\n可能原因:")
            print("  1. MOSS_USER_ID 無效或已過期")
            print("  2. 網路無法連接到 Stanford 伺服器")
            print("  3. MOSS 伺服器暫時無法使用")
            return False


def test_moss_with_real_submissions(problem_id=None):
    """
    使用真實資料庫中的提交進行 MOSS 測試
    """
    from submissions.models import Submission
    from django.conf import settings
    import mosspy
    import tempfile
    
    print("=" * 60)
    print("  MOSS 真實資料測試")
    print("=" * 60)
    
    moss_user_id = getattr(settings, 'MOSS_USER_ID', 0)
    if moss_user_id == 0:
        print("\n❌ MOSS_USER_ID 未設定")
        return False
    
    # 如果沒有指定 problem_id，列出可用的題目
    if problem_id is None:
        print("\n可用的題目 (有 Python 提交):")
        from django.db.models import Count
        problems = Submission.objects.filter(
            language_type=2  # Python
        ).values('problem_id').annotate(
            count=Count('id')
        ).filter(count__gte=2).order_by('-count')[:10]
        
        if not problems:
            print("  ❌ 沒有找到有足夠 Python 提交的題目")
            return False
        
        for p in problems:
            print(f"  - Problem {p['problem_id']}: {p['count']} 份提交")
        
        print("\n請使用 test_moss_with_real_submissions(problem_id) 指定題目 ID")
        return False
    
    # 取得提交
    print(f"\n1. 查詢 Problem {problem_id} 的 Python 提交...")
    submissions = Submission.objects.filter(
        problem_id=problem_id,
        language_type=2  # Python
    ).select_related('user').order_by('-created_at')
    
    # 只保留每位使用者最新的提交
    latest = {}
    for sub in submissions:
        if sub.user_id not in latest:
            latest[sub.user_id] = sub
    
    final_list = list(latest.values())
    print(f"   找到 {len(final_list)} 份有效提交")
    
    if len(final_list) < 2:
        print("   ❌ 提交數量不足 (至少需要 2 份)")
        return False
    
    # 建立 MOSS 客戶端
    print(f"\n2. 建立 MOSS 客戶端...")
    m = mosspy.Moss(moss_user_id, "python")
    
    # 準備檔案
    print(f"\n3. 準備提交檔案...")
    with tempfile.TemporaryDirectory() as temp_dir:
        for sub in final_list:
            filename = f"{sub.user.username}_{sub.id}.py"
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(sub.source_code)
            m.addFile(filepath)
            print(f"   ✅ {filename}")
        
        # 發送
        print(f"\n4. 發送到 MOSS 伺服器...")
        try:
            url = m.send()
            print(f"\n{'=' * 60}")
            print(f"  ✅ 成功！MOSS 報告網址:")
            print(f"{'=' * 60}")
            print(f"\n  {url}\n")
            return True
        except Exception as e:
            print(f"\n❌ 發送失敗: {e}")
            return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MOSS 連線測試工具")
    parser.add_argument(
        "--real", "-r",
        action="store_true",
        help="使用真實資料庫中的提交進行測試"
    )
    parser.add_argument(
        "--problem", "-p",
        type=int,
        default=None,
        help="指定題目 ID (與 --real 一起使用)"
    )
    
    args = parser.parse_args()
    
    if args.real:
        success = test_moss_with_real_submissions(args.problem)
    else:
        success = test_moss_connection()
    
    sys.exit(0 if success else 1)

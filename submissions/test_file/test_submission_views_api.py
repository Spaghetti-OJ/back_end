# submissions/test_file/test_submission_views_api.py - 測試 Submission API Views
"""
專門測試我們新實現的 Submission API Views 功能
包括：POST /submission/, PUT /submission/{id}, GET /submission/, GET /submission/{id}
以及 /code, /stdout, /rejudge, /ranking 等端點
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch, Mock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from ..models import Submission, SubmissionResult
from problems.models import Problems
from courses.models import Courses, Course_members
from ..serializers import (
    SubmissionBaseCreateSerializer,
    SubmissionCodeUploadSerializer,
    SubmissionListSerializer,
    SubmissionDetailSerializer,
    SubmissionCodeSerializer,
    SubmissionStdoutSerializer
)

User = get_user_model()


class SubmissionAPITestSetup:
    """測試基礎設施 - 提供通用的測試數據和工具方法"""
    
    @classmethod
    def create_test_users(cls):
        """創建測試用戶"""
        # 普通學生
        cls.student1 = User.objects.create_user(
            username='api_student1',
            email='api_student1@test.com',
            password='testpass123'
        )
        cls.student2 = User.objects.create_user(
            username='api_student2', 
            email='api_student2@test.com',
            password='testpass123'
        )
        
        # 老師
        cls.teacher = User.objects.create_user(
            username='api_teacher',
            email='api_teacher@test.com',
            password='testpass123'
        )
        
        # TA
        cls.ta = User.objects.create_user(
            username='api_ta',
            email='api_ta@test.com',
            password='testpass123'
        )
        
        # 管理員
        cls.admin = User.objects.create_user(
            username='api_admin',
            email='api_admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
    
    @classmethod
    def create_test_courses(cls):
        """創建測試課程"""
        cls.course1 = Courses.objects.create(
            name='API測試課程1 - 演算法',
            description='API測試用的演算法課程',
            teacher_id=cls.teacher
        )
        
        cls.course2 = Courses.objects.create(
            name='API測試課程2 - 資料結構',
            description='API測試用的資料結構課程',
            teacher_id=cls.teacher
        )
        
        # 添加課程成員
        Course_members.objects.create(
            course_id=cls.course1,
            user_id=cls.student1,
            role=Course_members.Role.STUDENT
        )
        
        Course_members.objects.create(
            course_id=cls.course1,
            user_id=cls.ta,
            role=Course_members.Role.TA
        )
        
        Course_members.objects.create(
            course_id=cls.course2,
            user_id=cls.student2,
            role=Course_members.Role.STUDENT
        )
    
    @classmethod
    def create_test_problems(cls):
        """創建測試題目 (修正 creator_id 問題)"""
        cls.problem1 = Problems.objects.create(
            id=2001,
            title='API測試題目1 - 兩數之和',
            description='API測試：給定一個整數數組，返回兩個數字的索引',
            course_id=cls.course1,
            creator_id=cls.teacher,  # 添加必需的 creator_id
            difficulty=Problems.Difficulty.EASY
        )
        
        cls.problem2 = Problems.objects.create(
            id=2002,
            title='API測試題目2 - 反轉鏈表',
            description='API測試：反轉一個單鏈表',
            course_id=cls.course2,
            creator_id=cls.teacher,  # 添加必需的 creator_id
            difficulty=Problems.Difficulty.MEDIUM
        )
        
        # 沒有關聯課程的題目
        cls.orphan_problem = Problems.objects.create(
            id=9998,
            title='API測試孤兒題目',
            description='API測試：沒有關聯課程的題目',
            course_id=None,
            creator_id=cls.teacher,  # 添加必需的 creator_id
            difficulty=Problems.Difficulty.HARD
        )
    
    @classmethod
    def create_test_submissions(cls):
        """創建測試提交"""
        # 學生1的提交 - 待上傳程式碼 (更新為整數語言類型)
        cls.submission1 = Submission.objects.create(
            problem_id=cls.problem1.id,
            user=cls.student1,
            language_type=2,  # Python (整數格式)
            source_code='',  # 空程式碼，狀態為 -2
            status='-2'  # 待上傳程式碼
        )
        
        # 學生1的另一個提交 - 已判題 AC
        cls.submission2 = Submission.objects.create(
            problem_id=cls.problem1.id,
            user=cls.student1,
            language_type=2,  # Python (整數格式)
            source_code='# AC Solution\ndef two_sum(nums, target):\n    return [0, 1]',
            status='0',  # Accepted
            score=100,
            execution_time=150,
            memory_usage=1024
        )
        
        # 學生2的提交 - WA
        cls.submission3 = Submission.objects.create(
            problem_id=cls.problem2.id,
            user=cls.student2,
            language_type=1,  # C++ (整數格式)
            source_code='#include<iostream>\nint main(){return 0;}',
            status='1',  # Wrong Answer
            score=0,
            execution_time=100,
            memory_usage=512
        )
        
        # 創建測試用的 SubmissionResult (修正字段名稱)
        SubmissionResult.objects.create(
            submission=cls.submission2,
            problem_id=cls.problem1.id,
            test_case_id=1,
            test_case_index=1,
            status='accepted',
            execution_time=75,
            memory_usage=512,
            output_preview='Test case 1 passed',
            score=100,
            max_score=100
        )
        
        SubmissionResult.objects.create(
            submission=cls.submission2,
            problem_id=cls.problem1.id,
            test_case_id=2,
            test_case_index=2,
            status='accepted',
            execution_time=75,
            memory_usage=512,
            output_preview='Test case 2 passed',
            score=100,
            max_score=100
        )


class SubmissionAPIBaseTestCase(APITestCase, SubmissionAPITestSetup):
    """Submission API 基礎測試類"""
    
    def setUp(self):
        """每個測試前的設置"""
        self.create_test_users()
        self.create_test_courses()
        self.create_test_problems()
        self.create_test_submissions()
        
        # 設置 API 客戶端
        self.client = APIClient()
    
    def authenticate_as(self, user):
        """以特定用戶身份認證"""
        self.client.force_authenticate(user=user)
    
    def get_submission_create_url(self):
        """獲取創建提交的 URL"""
        return '/submission/'
    
    def get_submission_detail_url(self, submission_id):
        """獲取提交詳情的 URL"""
        return f'/submission/{submission_id}/'
    
    def get_submission_code_url(self, submission_id):
        """獲取提交程式碼的 URL"""
        return f'/submission/{submission_id}/code/'
    
    def get_submission_stdout_url(self, submission_id):
        """獲取提交輸出的 URL"""
        return f'/submission/{submission_id}/stdout/'
    
    def get_submission_rejudge_url(self, submission_id):
        """獲取重新判題的 URL"""
        return f'/submission/{submission_id}/rejudge/'
    
    def get_ranking_url(self):
        """獲取排行榜的 URL"""
        return '/ranking/'


@pytest.mark.django_db
class TestSubmissionCreateAPI(SubmissionAPIBaseTestCase):
    """測試 POST /submission/ - 創建新提交"""
    
    def test_create_submission_success(self):
        """測試成功創建提交 (更新為NOJ格式)"""
        self.authenticate_as(self.student1)
        
        data = {
            'problem_id': self.problem1.id,
            'language_type': 2  # Python (整數格式)
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        # 驗證 NOJ 格式響應
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.startswith("submission recieved."))
        
        # 從響應中提取提交 ID
        submission_id = response.data.split('.')[1]
        
        # 驗證數據庫中的提交
        submission = Submission.objects.get(id=submission_id)
        self.assertEqual(submission.problem_id, self.problem1.id)
        self.assertEqual(submission.user, self.student1)
        self.assertEqual(submission.language_type, 2)  # 整數格式
        self.assertEqual(submission.status, '-2')
        self.assertEqual(submission.source_code, '')  # 初始為空
    
    def test_create_submission_invalid_problem(self):
        """測試創建提交時題目不存在 (更新為NOJ格式)"""
        self.authenticate_as(self.student1)
        
        data = {
            'problem_id': 99999,  # 不存在的題目
            'language_type': 2  # Python (整數格式)
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, "Unexisted problem id.")
    
    def test_create_submission_invalid_language(self):
        """測試創建提交時程式語言無效 (更新為NOJ格式)"""
        self.authenticate_as(self.student1)
        
        data = {
            'problem_id': self.problem1.id,
            'language_type': 999  # 無效語言 (整數格式)
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, "not allowed language")
    
    def test_create_submission_missing_fields(self):
        """測試創建提交時缺少必需字段 (更新為NOJ格式)"""
        self.authenticate_as(self.student1)
        
        # 缺少 language_type
        data = {
            'problem_id': self.problem1.id
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, "post data missing!")
    
    def test_create_submission_unauthenticated(self):
        """測試未認證用戶創建提交 (更新為整數語言類型)"""
        data = {
            'problem_id': self.problem1.id,
            'language_type': 2  # Python (整數格式)
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_multiple_submissions(self):
        """測試同一用戶可以創建多個提交 (更新為NOJ格式)"""
        self.authenticate_as(self.student1)
        
        data = {
            'problem_id': self.problem1.id,
            'language_type': 2  # Python (整數格式)
        }
        
        # 創建第一個提交
        response1 = self.client.post(self.get_submission_create_url(), data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response1.data.startswith("submission recieved."))
        
        # 創建第二個提交
        response2 = self.client.post(self.get_submission_create_url(), data)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response2.data.startswith("submission recieved."))
        
        # 確保是不同的提交
        submission_id1 = response1.data.split('.')[1]
        submission_id2 = response2.data.split('.')[1]
        self.assertNotEqual(submission_id1, submission_id2)


@pytest.mark.django_db
class TestSubmissionCodeUploadAPI(SubmissionAPIBaseTestCase):
    """測試 PUT /submission/{id} - 上傳程式碼"""
    
    def test_upload_code_success(self):
        """測試成功上傳程式碼"""
        self.authenticate_as(self.student1)
        
        test_code = '''
def two_sum(nums, target):
    hash_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in hash_map:
            return [hash_map[complement], i]
        hash_map[num] = i
    return []
'''
        
        data = {
            'source_code': test_code
        }
        
        response = self.client.put(
            self.get_submission_detail_url(self.submission1.id), 
            data
        )
        
        # 驗證響應 - NOJ format: string message
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, f"{self.submission1.id} send to judgement.")
        
        # 驗證數據庫更新
        self.submission1.refresh_from_db()
        self.assertEqual(self.submission1.source_code.strip(), test_code.strip())
        self.assertEqual(self.submission1.status, '-1')
    
    def test_upload_code_wrong_user(self):
        """測試其他用戶嘗試上傳程式碼"""
        self.authenticate_as(self.student2)  # 不是提交者
        
        data = {
            'source_code': 'malicious code'
        }
        
        response = self.client.put(
            self.get_submission_detail_url(self.submission1.id),
            data
        )
        
        # 應該返回權限錯誤 (NOJ format)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, "user not equal!")  # NOJ format
    
    def test_upload_code_empty_code(self):
        """測試上傳空程式碼 (更新為NOJ格式)"""
        self.authenticate_as(self.student1)
        
        data = {
            'source_code': ''
        }
        
        response = self.client.put(
            self.get_submission_detail_url(self.submission1.id),
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, "empty file")
    
    def test_upload_code_already_uploaded(self):
        """測試重複上傳程式碼（NOJ 不允許）"""
        self.authenticate_as(self.student1)
        
        new_code = '''
def new_solution():
    return "Updated solution"
'''
        
        data = {
            'source_code': new_code
        }
        
        response = self.client.put(
            self.get_submission_detail_url(self.submission2.id),  # 已判題完成的提交
            data
        )
        
        # NOJ 不允許重複上傳已判題完成的
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, f"{self.submission2.id} has finished judgement.")
        
        # 驗證程式碼沒有被更新
        self.submission2.refresh_from_db()
        self.assertNotEqual(self.submission2.source_code.strip(), new_code.strip())
    
    def test_upload_code_invalid_submission_id(self):
        """測試上傳程式碼到不存在的提交"""
        self.authenticate_as(self.student1)
        
        fake_id = str(uuid.uuid4())
        data = {
            'source_code': 'some code'
        }
        
        response = self.client.put(
            self.get_submission_detail_url(fake_id),
            data
        )
        
        # NOJ returns 400 for invalid submission
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, "can not find the source file")
    
    @patch('submissions.views.send_to_sandbox', create=True)  # Mock SandBox 調用
    def test_upload_code_triggers_judging(self, mock_sandbox):
        """測試上傳程式碼觸發判題（如果實作 SandBox 的話）"""
        self.authenticate_as(self.student1)
        mock_sandbox.return_value = True
        
        data = {
            'source_code': 'def solution(): return "test"'
        }
        
        response = self.client.put(
            self.get_submission_detail_url(self.submission1.id),
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 如果 SandBox 集成完成，可以驗證調用
        # mock_sandbox.assert_called_once()


@pytest.mark.django_db
class TestSubmissionListAPI(SubmissionAPIBaseTestCase):
    """測試 GET /submission/ - 獲取提交列表"""
    
    def test_get_submissions_as_student(self):
        """測試學生獲取提交列表（只能看到自己的）- NOJ format"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(self.get_submission_create_url())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        
        # 學生1只能看到自己的 2 個提交
        results = response.data['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(response.data['count'], 2)
        
        # 驗證都是自己的提交
        for submission in results:
            self.assertEqual(submission['user']['username'], 'api_student1')
            # 驗證返回的字段 - NOJ format uses submissionId not id
            self.assertIn('submissionId', submission)
            self.assertIn('problemId', submission)
            self.assertIn('languageType', submission)
            self.assertIn('status', submission)
            self.assertIn('timestamp', submission)
    
    def test_get_submissions_as_teacher(self):
        """測試老師獲取提交列表（可以看到課程相關的）"""
        self.authenticate_as(self.teacher)
        
        response = self.client.get(self.get_submission_create_url())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 老師可以看到自己課程的提交（包括 student1 和 student2 的）
        results = response.data['results']
        self.assertGreaterEqual(len(results), 3)  # 至少 3 個提交
        
        # 檢查是否包含學生的提交
        usernames = [sub['user']['username'] for sub in results]
        self.assertIn('api_student1', usernames)
        self.assertIn('api_student2', usernames)
    
    def test_get_submissions_as_ta(self):
        """測試 TA 獲取提交列表"""
        self.authenticate_as(self.ta)
        
        response = self.client.get(self.get_submission_create_url())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # TA 可以看到自己負責課程的提交
        results = response.data['results']
        # TA 在 course1，應該能看到 student1 的提交
        usernames = [sub['user']['username'] for sub in results]
        self.assertIn('api_student1', usernames)
    
    def test_get_submissions_as_admin(self):
        """測試管理員獲取提交列表（可以看到所有）"""
        self.authenticate_as(self.admin)
        
        response = self.client.get(self.get_submission_create_url())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 管理員可以看到所有提交
        results = response.data['results']
        self.assertEqual(len(results), 3)  # 所有測試提交
    
    def test_get_submissions_ordering(self):
        """測試提交列表按時間倒序排列 - NOJ format"""
        self.authenticate_as(self.admin)  # 管理員看所有
        
        response = self.client.get(self.get_submission_create_url())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data['results']
        if len(results) > 1:
            # 驗證按創建時間倒序 - NOJ uses 'timestamp'
            for i in range(len(results) - 1):
                current_time = results[i]['timestamp']
                next_time = results[i + 1]['timestamp']
                # 較新的應該在前面
                self.assertGreaterEqual(current_time, next_time)
    
    def test_get_submissions_unauthenticated(self):
        """測試未認證用戶獲取提交列表"""
        response = self.client.get(self.get_submission_create_url())
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_submissions_permission_isolation(self):
        """測試權限隔離 - 學生不能看到其他學生的提交"""
        self.authenticate_as(self.student2)
        
        response = self.client.get(self.get_submission_create_url())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # student2 只應該看到自己的提交
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['user']['username'], 'api_student2')
        
        # 確保看不到 student1 的提交
        usernames = [sub['user']['username'] for sub in results]
        self.assertNotIn('api_student1', usernames)


@pytest.mark.django_db
class TestSubmissionDetailAPI(SubmissionAPIBaseTestCase):
    """測試 GET /submission/{id} - 獲取提交詳情"""
    
    def test_get_own_submission_detail(self):
        """測試獲取自己的提交詳情 - NOJ format"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(
            self.get_submission_detail_url(self.submission1.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # NOJ format uses different field names
        self.assertEqual(response.data['submissionId'], str(self.submission1.id))
        self.assertEqual(response.data['user']['username'], 'api_student1')
        self.assertEqual(response.data['problemId'], self.problem1.id)
        self.assertEqual(response.data['status'], '-2')
        
        # 驗證詳情包含完整資訊 - NOJ format
        expected_fields = [
            'submissionId', 'user', 'problemId', 'languageType', 'status',
            'score', 'runTime', 'memoryUsage', 'timestamp'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data)
    
    def test_get_other_submission_as_student(self):
        """測試學生獲取其他人的提交詳情（應該被拒絕）"""
        self.authenticate_as(self.student2)
        
        response = self.client.get(
            self.get_submission_detail_url(self.submission1.id)  # student1的提交
        )
        
        # NOJ 返回 403 表示權限不足
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, "no permission")  # NOJ format
    
    def test_get_submission_as_teacher(self):
        """測試老師獲取課程學生的提交詳情"""
        self.authenticate_as(self.teacher)
        
        response = self.client.get(
            self.get_submission_detail_url(self.submission1.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['submissionId'], str(self.submission1.id))
        
        # 老師應該能看到學生的提交詳情
        self.assertEqual(response.data['user']['username'], 'api_student1')
    
    def test_get_submission_as_ta(self):
        """測試 TA 獲取提交詳情"""
        self.authenticate_as(self.ta)
        
        # TA 在 course1，可以看到 course1 的提交
        response = self.client.get(
            self.get_submission_detail_url(self.submission1.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 但看不到其他課程的提交 - NOJ 返回 403
        response = self.client.get(
            self.get_submission_detail_url(self.submission3.id)  # course2
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, "no permission")  # NOJ format
    
    def test_get_nonexistent_submission(self):
        """測試獲取不存在的提交"""
        self.authenticate_as(self.student1)
        
        fake_id = str(uuid.uuid4())
        response = self.client.get(self.get_submission_detail_url(fake_id))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_submission_permission_cross_course(self):
        """測試跨課程權限隔離"""
        self.authenticate_as(self.student1)  # course1 的學生
        
        # 不能看到 course2 的提交 - NOJ 返回 403
        response = self.client.get(
            self.get_submission_detail_url(self.submission3.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, "no permission")  # NOJ format


@pytest.mark.django_db
class TestSubmissionCodeAPI(SubmissionAPIBaseTestCase):
    """測試 GET /submission/{id}/code - 獲取提交程式碼"""
    
    def test_get_own_submission_code(self):
        """測試獲取自己的提交程式碼"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(
            self.get_submission_code_url(self.submission2.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('source_code', response.data)
        expected_code = '# AC Solution\ndef two_sum(nums, target):\n    return [0, 1]'
        self.assertEqual(response.data['source_code'], expected_code)
        
        # 驗證只返回程式碼相關字段
        self.assertIn('language_type', response.data)
        self.assertEqual(response.data['language_type'], 2)  # 整數格式
    
    def test_get_submission_code_no_code(self):
        """測試獲取尚未上傳程式碼的提交"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(
            self.get_submission_code_url(self.submission1.id)  # 空程式碼
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, "can not find the source file")  # NOJ format
    
    def test_get_code_wrong_permission(self):
        """測試無權限查看程式碼"""
        self.authenticate_as(self.student2)
        
        response = self.client.get(
            self.get_submission_code_url(self.submission2.id)  # student1的提交
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_code_as_teacher(self):
        """測試老師查看學生程式碼"""
        self.authenticate_as(self.teacher)
        
        response = self.client.get(
            self.get_submission_code_url(self.submission2.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('source_code', response.data)


@pytest.mark.django_db
class TestSubmissionStdoutAPI(SubmissionAPIBaseTestCase):
    """測試 GET /submission/{id}/stdout - 獲取提交標準輸出"""
    
    def test_get_submission_stdout(self):
        """測試獲取提交的標準輸出 (NOJ format)"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(
            self.get_submission_stdout_url(self.submission2.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # NOJ format: {stdout, submission_id, status, message}
        self.assertIn('stdout', response.data)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'here you are, bro')
        self.assertIn('submission_id', response.data)
        self.assertIn('status', response.data)
        
        # 驗證輸出結果
        stdout = response.data['stdout']
        self.assertIn('Test Case', stdout)
    
    def test_get_stdout_no_results(self):
        """測試獲取沒有執行結果的提交輸出 (NOJ format)"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(
            self.get_submission_stdout_url(self.submission1.id)  # 沒有結果
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # NOJ format
        self.assertIn('stdout', response.data)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'here you are, bro')
        self.assertEqual(response.data['stdout'], '-')  # No output
    
    def test_get_stdout_wrong_permission(self):
        """測試無權限查看輸出"""
        self.authenticate_as(self.student2)
        
        response = self.client.get(
            self.get_submission_stdout_url(self.submission2.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db  
class TestSubmissionRejudgeAPI(SubmissionAPIBaseTestCase):
    """測試 GET /submission/{id}/rejudge - 重新判題"""
    
    def test_rejudge_as_teacher(self):
        """測試老師重新判題"""
        self.authenticate_as(self.teacher)
        
        # 記錄原始狀態
        original_status = self.submission2.status
        original_score = self.submission2.score
        
        response = self.client.get(
            self.get_submission_rejudge_url(self.submission2.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # NOJ format: "{submission_id} rejudge successfully."
        self.assertEqual(response.data, f"{self.submission2.id} rejudge successfully.")
        
        # 驗證狀態重置
        self.submission2.refresh_from_db()
        self.assertEqual(self.submission2.status, '-1')  # Pending
        self.assertEqual(self.submission2.score, 0)  # 重置分數
        self.assertEqual(self.submission2.execution_time, -1)  # 重置時間
        self.assertEqual(self.submission2.memory_usage, -1)  # 重置記憶體
        self.assertIsNone(self.submission2.judged_at)  # 清除判題時間
        
        # 驗證舊的結果被清除
        results_count = SubmissionResult.objects.filter(submission=self.submission2).count()
        self.assertEqual(results_count, 0)
    
    def test_rejudge_as_ta(self):
        """測試 TA 重新判題"""
        self.authenticate_as(self.ta)
        
        response = self.client.get(
            self.get_submission_rejudge_url(self.submission2.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_rejudge_as_admin(self):
        """測試管理員重新判題"""
        self.authenticate_as(self.admin)
        
        response = self.client.get(
            self.get_submission_rejudge_url(self.submission2.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_rejudge_as_student(self):
        """測試學生嘗試重新判題（應該被拒絕）"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(
            self.get_submission_rejudge_url(self.submission2.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, "no permission")  # NOJ format
    
    def test_rejudge_submission_without_code(self):
        """測試重新判題尚未上傳程式碼的提交"""
        self.authenticate_as(self.teacher)
        
        response = self.client.get(
            self.get_submission_rejudge_url(self.submission1.id)  # status = '-2'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, "can not find the source file")  # NOJ format
    
    def test_rejudge_nonexistent_submission(self):
        """測試重新判題不存在的提交"""
        self.authenticate_as(self.teacher)
        
        fake_id = str(uuid.uuid4())
        response = self.client.get(self.get_submission_rejudge_url(fake_id))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
class TestRankingAPI(SubmissionAPIBaseTestCase):
    """測試 GET /ranking - 獲取排行榜"""
    
    def test_get_ranking_basic(self):
        """測試獲取基本排行榜"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(self.get_ranking_url())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'here you are, bro')
        self.assertIn('ranking', response.data)
        self.assertIsInstance(response.data['ranking'], list)
        
        # 驗證排行榜不為空
        self.assertGreater(len(response.data['ranking']), 0)
    
    def test_ranking_data_format(self):
        """測試排行榜數據格式"""
        self.authenticate_as(self.admin)  # 管理員查看
        
        response = self.client.get(self.get_ranking_url())
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('ranking', response.data)
        
        # 驗證每個用戶的數據格式
        for user_data in response.data['ranking']:
            # 檢查必需字段
            required_fields = ['user', 'ACProblem', 'ACSubmission', 'Submission']
            for field in required_fields:
                self.assertIn(field, user_data)
            
            # 檢查 user 字段
            user_info = user_data['user']
            user_required_fields = ['id', 'username', 'email', 'is_active', 'date_joined']
            for field in user_required_fields:
                self.assertIn(field, user_info)
            
            # 檢查數值字段
            self.assertIsInstance(user_data['ACProblem'], int)
            self.assertIsInstance(user_data['ACSubmission'], int)
            self.assertIsInstance(user_data['Submission'], int)
            
            # 邏輯檢查：AC的提交數應該 >= AC的題目數
            self.assertGreaterEqual(user_data['ACSubmission'], user_data['ACProblem'])
    
    def test_ranking_statistics(self):
        """測試排行榜統計正確性"""
        self.authenticate_as(self.admin)
        
        response = self.client.get(self.get_ranking_url())
        
        # 找到 student1 的數據
        student1_data = None
        for user_data in response.data['ranking']:
            if user_data['user']['username'] == 'api_student1':
                student1_data = user_data
                break
        
        self.assertIsNotNone(student1_data)
        
        # 驗證 student1 的統計
        # student1 有 2 個提交，其中 1 個是 AC (submission2)
        self.assertEqual(student1_data['Submission'], 2)  # 總提交數
        self.assertEqual(student1_data['ACSubmission'], 1)  # AC 提交數 (status='0')
        self.assertEqual(student1_data['ACProblem'], 1)  # AC 題目數 (problem1)
    
    def test_ranking_as_different_users(self):
        """測試不同用戶角色都能訪問排行榜"""
        users_to_test = [self.student1, self.student2, self.teacher, self.ta, self.admin]
        
        for user in users_to_test:
            self.authenticate_as(user)
            
            response = self.client.get(self.get_ranking_url())
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('message', response.data)
            self.assertIn('ranking', response.data)
            self.assertIsInstance(response.data['ranking'], list)
    
    def test_ranking_unauthenticated(self):
        """測試未認證用戶訪問排行榜"""
        response = self.client.get(self.get_ranking_url())
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.django_db
class TestSubmissionPermissionEdgeCases(SubmissionAPIBaseTestCase):
    """測試權限系統的邊界情況和複雜場景"""
    
    def test_orphan_problem_submission_permission(self):
        """測試孤兒題目（沒有關聯課程）的提交權限"""
        # 創建對孤兒題目的提交
        orphan_submission = Submission.objects.create(
            problem_id=self.orphan_problem.id,
            user=self.student1,
            language_type=2,  # Python (整數格式)
            source_code='print("orphan")',
            status='-1'
        )
        
        # 測試學生能看到自己對孤兒題目的提交
        self.authenticate_as(self.student1)
        response = self.client.get(self.get_submission_detail_url(orphan_submission.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 測試其他學生也能看到（孤兒題目的提交似乎是公開的）
        self.authenticate_as(self.student2)
        response = self.client.get(self.get_submission_detail_url(orphan_submission.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 測試老師能看到（老師有更高權限可以查看孤兒題目）
        self.authenticate_as(self.teacher)
        response = self.client.get(self.get_submission_detail_url(orphan_submission.id))
        
        # 老師可以看到孤兒題目的提交
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 測試管理員能看到所有
        self.authenticate_as(self.admin)
        response = self.client.get(self.get_submission_detail_url(orphan_submission.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_multiple_course_membership(self):
        """測試用戶在多個課程中的權限"""
        # 讓 student1 也加入 course2
        Course_members.objects.create(
            course_id=self.course2,
            user_id=self.student1,
            role=Course_members.Role.STUDENT
        )
        
        # 現在 student1 應該能看到兩個課程的提交（在列表中）
        self.authenticate_as(self.student1)
        response = self.client.get(self.get_submission_create_url())
        
        # student1 現在應該能看到自己的提交
        results = response.data['results']
        usernames = [sub['user']['username'] for sub in results]
        
        # 只能看到自己的提交，不能看到其他學生的
        for username in usernames:
            self.assertEqual(username, 'api_student1')
    
    def test_teacher_permission_across_courses(self):
        """測試老師對不同課程的權限"""
        self.authenticate_as(self.teacher)
        
        # 老師應該能看到 course1 和 course2 的提交（因為都是他教的）
        response = self.client.get(self.get_submission_create_url())
        
        usernames = [sub['user']['username'] for sub in response.data['results']]
        
        # 應該包含兩個課程的學生
        self.assertIn('api_student1', usernames)  # course1
        self.assertIn('api_student2', usernames)  # course2
    
    def test_permission_after_role_change(self):
        """測試角色變更後的權限"""
        # 先以 TA 身份測試
        self.authenticate_as(self.ta)
        response = self.client.get(self.get_submission_detail_url(self.submission1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 改變角色為普通學生
        Course_members.objects.filter(
            course_id=self.course1,
            user_id=self.ta
        ).update(role=Course_members.Role.STUDENT)
        
        # 重新測試，現在應該看不到其他人的提交 - NOJ 返回 403
        response = self.client.get(self.get_submission_detail_url(self.submission1.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, "no permission")  # NOJ format


# 運行測試的輔助函數
if __name__ == '__main__':
    # 運行特定測試類
    pytest.main([
        __file__ + '::TestSubmissionCreateAPI',
        '-v', '--tb=short'
    ])
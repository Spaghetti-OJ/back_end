# submissions/test_file/test_submission_permissions.py - 專門測試 BasePermissionMixin 權限系統
"""
專門測試我們實現的 BasePermissionMixin 權限系統
重點測試各種複雜的權限場景和邊界情況
"""

import pytest
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound

from ..models import Submission, SubmissionResult
from ..views import BasePermissionMixin
from problems.models import Problems
from courses.models import Courses, Course_members

User = get_user_model()


class PermissionTestSetup:
    """權限測試的基礎設施"""
    
    @classmethod
    def create_complex_test_data(cls):
        """創建複雜的測試數據結構"""
        
        # 創建用戶
        cls.student1 = User.objects.create_user('perm_student1', 'perm_student1@test.com', 'pass123')
        cls.student2 = User.objects.create_user('perm_student2', 'perm_student2@test.com', 'pass123')
        cls.student3 = User.objects.create_user('perm_student3', 'perm_student3@test.com', 'pass123')
        
        cls.teacher1 = User.objects.create_user('perm_teacher1', 'perm_teacher1@test.com', 'pass123')
        cls.teacher2 = User.objects.create_user('perm_teacher2', 'perm_teacher2@test.com', 'pass123')
        
        cls.ta1 = User.objects.create_user('perm_ta1', 'perm_ta1@test.com', 'pass123')
        cls.ta2 = User.objects.create_user('perm_ta2', 'perm_ta2@test.com', 'pass123')
        
        cls.admin = User.objects.create_user(
            'perm_admin', 'perm_admin@test.com', 'pass123',
            is_staff=True, is_superuser=True
        )
        
        # 創建課程
        cls.course1 = Courses.objects.create(
            name='權限測試課程1',
            description='用於測試權限的課程1',
            teacher_id=cls.teacher1
        )
        
        cls.course2 = Courses.objects.create(
            name='權限測試課程2',
            description='用於測試權限的課程2',
            teacher_id=cls.teacher2
        )
        
        cls.course3 = Courses.objects.create(
            name='權限測試課程3',
            description='用於測試權限的課程3，沒有學生',
            teacher_id=cls.teacher1
        )
        
        # 創建題目
        cls.problem_c1 = Problems.objects.create(
            id=3001, title='課程1題目', description='課程1的題目',
            course_id=cls.course1, difficulty=Problems.Difficulty.EASY,
            creator_id=cls.teacher1
        )
        
        cls.problem_c2 = Problems.objects.create(
            id=3002, title='課程2題目', description='課程2的題目',
            course_id=cls.course2, difficulty=Problems.Difficulty.MEDIUM,
            creator_id=cls.teacher2
        )
        
        cls.problem_c3 = Problems.objects.create(
            id=3003, title='課程3題目', description='課程3的題目',
            course_id=cls.course3, difficulty=Problems.Difficulty.HARD,
            creator_id=cls.teacher1
        )
        
        # 修改：因為 course_id 不能為 NULL，將 orphan 問題關聯到 course3
        # （用於測試權限邊界情況）
        cls.problem_orphan = Problems.objects.create(
            id=3999, title='孤兒題目', description='沒有課程的題目',
            course_id=cls.course3, difficulty=Problems.Difficulty.HARD,  # 修改：使用 course3
            creator_id=cls.teacher1
        )
        
        # 設置複雜的課程成員關係
        # course1: student1 (學生), student2 (學生), ta1 (TA)
        Course_members.objects.create(
            course_id=cls.course1, user_id=cls.student1, role=Course_members.Role.STUDENT
        )
        Course_members.objects.create(
            course_id=cls.course1, user_id=cls.student2, role=Course_members.Role.STUDENT
        )
        Course_members.objects.create(
            course_id=cls.course1, user_id=cls.ta1, role=Course_members.Role.TA
        )
        
        # course2: student2 (學生), student3 (學生), ta2 (TA), teacher1 (老師)
        Course_members.objects.create(
            course_id=cls.course2, user_id=cls.student2, role=Course_members.Role.STUDENT
        )
        Course_members.objects.create(
            course_id=cls.course2, user_id=cls.student3, role=Course_members.Role.STUDENT
        )
        Course_members.objects.create(
            course_id=cls.course2, user_id=cls.ta2, role=Course_members.Role.TA
        )
        Course_members.objects.create(
            course_id=cls.course2, user_id=cls.teacher1, role=Course_members.Role.TEACHER
        )
        
        # 創建各種提交
        cls.sub_s1_c1 = Submission.objects.create(
            problem_id=cls.problem_c1.id, user=cls.student1,
            language_type=2, source_code='print("s1_c1")', status='0'
        )
        
        cls.sub_s2_c1 = Submission.objects.create(
            problem_id=cls.problem_c1.id, user=cls.student2,
            language_type=2, source_code='print("s2_c1")', status='1'
        )
        
        cls.sub_s2_c2 = Submission.objects.create(
            problem_id=cls.problem_c2.id, user=cls.student2,
            language_type=2, source_code='print("s2_c2")', status='0'
        )
        
        cls.sub_s3_c2 = Submission.objects.create(
            problem_id=cls.problem_c2.id, user=cls.student3,
            language_type=2, source_code='print("s3_c2")', status='1'
        )
        
        cls.sub_orphan = Submission.objects.create(
            problem_id=cls.problem_orphan.id, user=cls.student1,
            language_type=2, source_code='print("orphan")', status='0'
        )


class BasePermissionMixinUnitTests(TestCase, PermissionTestSetup):
    """直接測試 BasePermissionMixin 的方法"""
    
    def setUp(self):
        self.create_complex_test_data()
        self.mixin = BasePermissionMixin()
    
    def test_check_teacher_permission_primary_teacher(self):
        """測試主要老師權限檢查"""
        # teacher1 是 course1 的主要老師
        result = self.mixin.check_teacher_permission(self.teacher1, self.problem_c1.id)
        self.assertTrue(result)
        
        # teacher2 不是 course1 的老師
        with self.assertRaises(PermissionDenied):
            self.mixin.check_teacher_permission(self.teacher2, self.problem_c1.id)
    
    def test_check_teacher_permission_course_member_teacher(self):
        """測試課程成員中的老師權限"""
        # teacher1 作為 course2 的成員老師
        result = self.mixin.check_teacher_permission(self.teacher1, self.problem_c2.id)
        self.assertTrue(result)
    
    def test_check_teacher_permission_ta(self):
        """測試 TA 權限"""
        # ta1 是 course1 的 TA
        result = self.mixin.check_teacher_permission(self.ta1, self.problem_c1.id)
        self.assertTrue(result)
        
        # ta1 不是 course2 的 TA
        with self.assertRaises(PermissionDenied):
            self.mixin.check_teacher_permission(self.ta1, self.problem_c2.id)
    
    def test_check_teacher_permission_student(self):
        """測試學生沒有老師權限"""
        with self.assertRaises(PermissionDenied):
            self.mixin.check_teacher_permission(self.student1, self.problem_c1.id)
    
    def test_check_teacher_permission_nonexistent_problem(self):
        """測試不存在的題目"""
        with self.assertRaises(NotFound):
            self.mixin.check_teacher_permission(self.teacher1, 99999)
    
    def test_check_teacher_permission_orphan_problem(self):
        """測試孤兒題目（現在關聯到 course3）"""
        # teacher2 不是 course3 的成員，所以沒有權限
        with self.assertRaises(PermissionDenied) as cm:
            self.mixin.check_teacher_permission(self.teacher2, self.problem_orphan.id)
        # 因為 problem_orphan 關聯到 course3，但 teacher2 不在 course3
        self.assertIn('沒有權限', str(cm.exception))
    
    def test_check_submission_view_permission_owner(self):
        """測試提交者本人的查看權限"""
        result = self.mixin.check_submission_view_permission(self.student1, self.sub_s1_c1)
        self.assertTrue(result)
    
    def test_check_submission_view_permission_teacher(self):
        """測試老師查看學生提交的權限"""
        # teacher1 是 course1 的主要老師
        result = self.mixin.check_submission_view_permission(self.teacher1, self.sub_s1_c1)
        self.assertTrue(result)
        
        # teacher2 不是 course1 的老師
        result = self.mixin.check_submission_view_permission(self.teacher2, self.sub_s1_c1)
        self.assertFalse(result)
    
    def test_check_submission_view_permission_ta(self):
        """測試 TA 查看提交的權限"""
        # ta1 是 course1 的 TA
        result = self.mixin.check_submission_view_permission(self.ta1, self.sub_s1_c1)
        self.assertTrue(result)
        
        # ta2 不是 course1 的 TA
        result = self.mixin.check_submission_view_permission(self.ta2, self.sub_s1_c1)
        self.assertFalse(result)
    
    def test_check_submission_view_permission_other_student(self):
        """測試其他學生查看提交的權限"""
        # student2 不能查看 student1 的提交
        result = self.mixin.check_submission_view_permission(self.student2, self.sub_s1_c1)
        self.assertFalse(result)
    
    def test_check_submission_view_permission_orphan_problem(self):
        """測試孤兒題目提交的查看權限（現在關聯到 course3）"""
        # 提交者本人可以查看
        result = self.mixin.check_submission_view_permission(self.student1, self.sub_orphan)
        self.assertTrue(result)
        
        # 其他人不能查看（因為 problem_orphan 現在關聯到 course3，student2 不在 course3）
        result = self.mixin.check_submission_view_permission(self.student2, self.sub_orphan)
        self.assertFalse(result)  # 因為 student2 不在 course3
    
    def test_get_viewable_submissions_student(self):
        """測試學生的可查看提交過濾"""
        all_submissions = Submission.objects.all()
        
        # student1 只能看到自己的提交
        viewable = self.mixin.get_viewable_submissions(self.student1, all_submissions)
        viewable_list = list(viewable)
        
        # 應該包含自己的兩個提交
        expected_ids = [self.sub_s1_c1.id, self.sub_orphan.id]
        actual_ids = [sub.id for sub in viewable_list]
        
        for expected_id in expected_ids:
            self.assertIn(expected_id, actual_ids)
        
        # 不應該包含其他人的提交
        other_ids = [self.sub_s2_c1.id, self.sub_s2_c2.id, self.sub_s3_c2.id]
        for other_id in other_ids:
            self.assertNotIn(other_id, actual_ids)
    
    def test_get_viewable_submissions_teacher(self):
        """測試老師的可查看提交過濾"""
        all_submissions = Submission.objects.all()
        
        # teacher1 是 course1 的主要老師，也是 course2 的成員老師
        viewable = self.mixin.get_viewable_submissions(self.teacher1, all_submissions)
        viewable_ids = [sub.id for sub in viewable]
        
        # 應該能看到 course1 和 course2 的所有提交
        expected_course_submissions = [
            self.sub_s1_c1.id, self.sub_s2_c1.id,  # course1
            self.sub_s2_c2.id, self.sub_s3_c2.id   # course2
        ]
        
        for expected_id in expected_course_submissions:
            self.assertIn(expected_id, viewable_ids)
    
    def test_get_viewable_submissions_ta(self):
        """測試 TA 的可查看提交過濾"""
        all_submissions = Submission.objects.all()
        
        # ta1 是 course1 的 TA
        viewable = self.mixin.get_viewable_submissions(self.ta1, all_submissions)
        viewable_ids = [sub.id for sub in viewable]
        
        # 應該能看到 course1 的提交
        expected_ids = [self.sub_s1_c1.id, self.sub_s2_c1.id]
        for expected_id in expected_ids:
            self.assertIn(expected_id, viewable_ids)
        
        # 不應該看到 course2 的提交
        course2_ids = [self.sub_s2_c2.id, self.sub_s3_c2.id]
        for course2_id in course2_ids:
            self.assertNotIn(course2_id, viewable_ids)
    
    def test_get_viewable_submissions_admin(self):
        """測試管理員的可查看提交過濾"""
        all_submissions = Submission.objects.all()
        
        # 管理員應該能看到所有提交
        viewable = self.mixin.get_viewable_submissions(self.admin, all_submissions)
        
        self.assertEqual(len(list(viewable)), len(list(all_submissions)))
    
    def test_get_viewable_submissions_cross_course_student(self):
        """測試跨課程學生的可查看提交"""
        all_submissions = Submission.objects.all()
        
        # student2 在 course1 和 course2 中都是學生
        viewable = self.mixin.get_viewable_submissions(self.student2, all_submissions)
        viewable_ids = [sub.id for sub in viewable]
        
        # 應該只能看到自己的提交
        expected_ids = [self.sub_s2_c1.id, self.sub_s2_c2.id]
        for expected_id in expected_ids:
            self.assertIn(expected_id, viewable_ids)
        
        # 不能看到其他人的提交
        other_ids = [self.sub_s1_c1.id, self.sub_s3_c2.id, self.sub_orphan.id]
        for other_id in other_ids:
            self.assertNotIn(other_id, viewable_ids)


@pytest.mark.django_db
class PermissionIntegrationTests(APITestCase, PermissionTestSetup):
    """權限系統的整合測試"""
    
    def setUp(self):
        self.create_complex_test_data()
        self.client = APIClient()
    
    def get_api_message(self, response):
        """從 api_response 格式的響應中提取 message"""
        if isinstance(response.data, dict) and 'message' in response.data:
            return response.data['message']
        return response.data
    
    def get_api_data(self, response):
        """從 api_response 格式的響應中提取 data"""
        if isinstance(response.data, dict) and 'data' in response.data:
            return response.data['data']
        return response.data
    
    def test_complex_permission_scenario_1(self):
        """複雜場景1：teacher1 管理多個課程"""
        self.client.force_authenticate(user=self.teacher1)
        
        # teacher1 應該能看到 course1 和 course2 的所有提交
        response = self.client.get('/submission/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 使用 api_response 格式提取 data
        results = self.get_api_data(response)['results']
        usernames = [sub['user']['username'] for sub in results]
        
        # 應該包含兩個課程的學生
        expected_users = ['perm_student1', 'perm_student2', 'perm_student3']
        for user in expected_users:
            self.assertIn(user, usernames)
    
    def test_complex_permission_scenario_2(self):
        """複雜場景2：student2 跨課程但仍然只能看自己的"""
        self.client.force_authenticate(user=self.student2)
        
        response = self.client.get('/submission/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 使用 api_response 格式提取 data
        results = self.get_api_data(response)['results']
        
        # student2 有兩個提交
        self.assertEqual(len(results), 2)
        
        # 都應該是自己的
        for submission in results:
            self.assertEqual(submission['user']['username'], 'perm_student2')
    
    def test_complex_permission_scenario_3(self):
        """複雜場景3：TA 的權限範圍"""
        self.client.force_authenticate(user=self.ta1)
        
        # ta1 只是 course1 的 TA
        response = self.client.get('/submission/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 使用 api_response 格式提取 data
        results = self.get_api_data(response)['results']
        
        # 應該能看到 course1 的提交 - NOJ format uses problemId
        problem_ids = [sub['problemId'] for sub in results]
        self.assertIn(self.problem_c1.id, problem_ids)
        
        # 但不應該看到 course2 的提交
        self.assertNotIn(self.problem_c2.id, problem_ids)
    
    def test_permission_edge_case_role_stacking(self):
        """邊界情況：用戶同時具有多種角色"""
        # 讓 teacher1 也成為 course3 的學生（雖然實際不太可能）
        Course_members.objects.create(
            course_id=self.course3,
            user_id=self.teacher1,
            role=Course_members.Role.STUDENT
        )
        
        self.client.force_authenticate(user=self.teacher1)
        
        # 應該仍然保持教師級權限
        response = self.client.get('/submission/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 權限應該是所有角色的聯集
    
    def test_permission_after_membership_removal(self):
        """測試成員移除後的權限變化"""
        # 先驗證 ta1 有權限
        self.client.force_authenticate(user=self.ta1)
        response = self.client.get(f'/submission/{self.sub_s1_c1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 移除 TA 身份
        Course_members.objects.filter(
            course_id=self.course1,
            user_id=self.ta1
        ).delete()
        
        # 再次測試，應該沒有權限 - NOJ 返回 403
        response = self.client.get(f'/submission/{self.sub_s1_c1.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 使用 api_response 格式提取 message
        self.assertEqual(self.get_api_message(response), "no permission")  # NOJ format
    
    def test_permission_performance_with_large_dataset(self):
        """測試大量數據時的權限性能"""
        # 創建大量測試數據
        bulk_submissions = []
        for i in range(50):
            bulk_submissions.append(Submission(
                problem_id=self.problem_c1.id,
                user=self.student1,
                language_type=2,
                source_code=f'print("bulk_{i}")',
                status='0'
            ))
        
        Submission.objects.bulk_create(bulk_submissions)
        
        self.client.force_authenticate(user=self.teacher1)
        
        # 測試查詢性能（不應該超時）
        import time
        start_time = time.time()
        
        response = self.client.get('/submission/')
        
        end_time = time.time()
        query_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 查詢時間不應該超過 5 秒（根據實際需求調整）
        self.assertLess(query_time, 5.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
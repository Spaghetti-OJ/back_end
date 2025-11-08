# submissions/test_file/test_permissions.py - 權限測試
import pytest
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase

from problems.models import Problems
from courses.models import Courses, Course_members

User = get_user_model()


class EditorialPermissionTests(TestCase):
    """題解權限專項測試"""
    
    def setUp(self):
        """測試準備"""
        unique_id = str(uuid.uuid4())[:8]
        
        # 創建用戶
        self.course_teacher = User.objects.create_user(
            username=f'course_teacher_{unique_id}',
            email=f'course_teacher_{unique_id}@example.com',
            password='testpass123'
        )
        self.member_teacher = User.objects.create_user(
            username=f'member_teacher_{unique_id}',
            email=f'member_teacher_{unique_id}@example.com',
            password='testpass123'
        )
        self.ta_user = User.objects.create_user(
            username=f'ta_{unique_id}',
            email=f'ta_{unique_id}@example.com',
            password='testpass123'
        )
        self.student = User.objects.create_user(
            username=f'student_{unique_id}',
            email=f'student_{unique_id}@example.com',
            password='testpass123'
        )
        self.outsider = User.objects.create_user(
            username=f'outsider_{unique_id}',
            email=f'outsider_{unique_id}@example.com',
            password='testpass123'
        )
        
        # 創建課程
        self.course = Courses.objects.create(
            name=f'權限測試課程_{unique_id}',
            description='權限測試課程',
            teacher_id=self.course_teacher
        )
        
        # 添加成員老師
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.member_teacher,
            role=Course_members.Role.TEACHER
        )
        
        # 添加 TA
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.ta_user,
            role=Course_members.Role.TA
        )
        
        # 添加學生
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.student,
            role=Course_members.Role.STUDENT
        )
        
        # 創建問題
        self.problem = Problems.objects.create(
            title=f'權限測試問題_{unique_id}',
            description='權限測試問題',
            creator_id=self.course_teacher,
            course_id=self.course
        )
        
        # 創建沒有課程的問題
        self.no_course_problem = Problems.objects.create(
            title=f'無課程問題_{unique_id}',
            description='無課程問題',
            creator_id=self.course_teacher,
            course_id=None
        )
    
    def test_course_main_teacher_has_permission(self):
        """測試課程主要老師有權限"""
        from ..views import EditorialPermissionMixin
        
        mixin = EditorialPermissionMixin()
        
        # 課程主要老師應該有權限
        result = mixin.check_teacher_permission(self.course_teacher, self.problem.id)
        assert result == True
    
    def test_course_member_teacher_has_permission(self):
        """測試課程成員老師有權限"""
        from ..views import EditorialPermissionMixin
        
        mixin = EditorialPermissionMixin()
        
        # 課程成員老師應該有權限
        result = mixin.check_teacher_permission(self.member_teacher, self.problem.id)
        assert result == True
    
    def test_ta_has_permission(self):
        """測試 TA 有權限"""
        from ..views import EditorialPermissionMixin
        
        mixin = EditorialPermissionMixin()
        
        # TA 應該有權限
        result = mixin.check_teacher_permission(self.ta_user, self.problem.id)
        assert result == True
    
    def test_student_has_no_permission(self):
        """測試學生沒有權限"""
        from ..views import EditorialPermissionMixin
        from rest_framework.exceptions import PermissionDenied
        
        mixin = EditorialPermissionMixin()
        
        # 學生應該沒有權限
        with pytest.raises(PermissionDenied):
            mixin.check_teacher_permission(self.student, self.problem.id)
    
    def test_outsider_has_no_permission(self):
        """測試外部用戶沒有權限"""
        from ..views import EditorialPermissionMixin
        from rest_framework.exceptions import PermissionDenied
        
        mixin = EditorialPermissionMixin()
        
        # 外部用戶應該沒有權限
        with pytest.raises(PermissionDenied):
            mixin.check_teacher_permission(self.outsider, self.problem.id)
    
    def test_nonexistent_problem_permission(self):
        """測試不存在問題的權限檢查"""
        from ..views import EditorialPermissionMixin
        from rest_framework.exceptions import NotFound
        
        mixin = EditorialPermissionMixin()
        
        # 不存在的問題應該拋出 NotFound
        with pytest.raises(NotFound):
            mixin.check_teacher_permission(self.course_teacher, 99999)
    
    def test_problem_without_course_permission(self):
        """測試沒有關聯課程的問題權限檢查"""
        from ..views import EditorialPermissionMixin
        from rest_framework.exceptions import PermissionDenied
        
        mixin = EditorialPermissionMixin()
        
        # 沒有關聯課程的問題應該拋出 PermissionDenied
        with pytest.raises(PermissionDenied) as exc_info:
            mixin.check_teacher_permission(self.course_teacher, self.no_course_problem.id)
        
        assert '未關聯到任何課程' in str(exc_info.value)


class CoursePermissionHypothesisTests(HypothesisTestCase):
    """使用 Hypothesis 測試課程權限的各種組合"""
    
    def setUp(self):
        """測試準備"""
        unique_id = str(uuid.uuid4())[:8]
        
        # 創建基礎用戶
        self.teacher = User.objects.create_user(
            username=f'teacher_{unique_id}',
            email=f'teacher_{unique_id}@example.com',
            password='testpass123'
        )
        
        # 創建課程
        self.course = Courses.objects.create(
            name=f'Hypothesis課程_{unique_id}',
            description='Hypothesis 測試課程',
            teacher_id=self.teacher
        )
    
    @given(
        role=st.sampled_from([
            Course_members.Role.STUDENT,
            Course_members.Role.TA,
            Course_members.Role.TEACHER
        ])
    )
    @settings(max_examples=10)
    def test_course_member_permission_by_role(self, role):
        """測試不同角色的課程成員權限"""
        unique_id = str(uuid.uuid4())[:8]
        
        # 創建測試用戶
        user = User.objects.create_user(
            username=f'user_{role}_{unique_id}',
            email=f'user_{role}_{unique_id}@example.com',
            password='testpass123'
        )
        
        # 添加到課程
        Course_members.objects.create(
            course_id=self.course,
            user_id=user,
            role=role
        )
        
        # 創建問題
        problem = Problems.objects.create(
            title=f'測試問題_{role}_{unique_id}',
            description=f'測試角色 {role} 的權限',
            creator_id=self.teacher,
            course_id=self.course
        )
        
        from ..views import EditorialPermissionMixin
        from rest_framework.exceptions import PermissionDenied
        
        mixin = EditorialPermissionMixin()
        
        if role == Course_members.Role.STUDENT:
            # 學生應該沒有權限
            with pytest.raises(PermissionDenied):
                mixin.check_teacher_permission(user, problem.id)
        else:
            # 老師和 TA 應該有權限
            result = mixin.check_teacher_permission(user, problem.id)
            assert result == True
    
    @given(
        num_teachers=st.integers(min_value=1, max_value=5),
        num_tas=st.integers(min_value=0, max_value=3),
        num_students=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=5, deadline=2000)
    def test_multiple_course_members_permissions(self, num_teachers, num_tas, num_students):
        """測試多個課程成員的權限"""
        unique_id = str(uuid.uuid4())[:8]
        
        # 創建問題
        problem = Problems.objects.create(
            title=f'多成員測試_{unique_id}',
            description='測試多個成員的權限',
            creator_id=self.teacher,
            course_id=self.course
        )
        
        from ..views import EditorialPermissionMixin
        from rest_framework.exceptions import PermissionDenied
        
        mixin = EditorialPermissionMixin()
        
        # 創建並測試老師
        for i in range(num_teachers):
            teacher = User.objects.create_user(
                username=f'teacher_{i}_{unique_id}',
                email=f'teacher_{i}_{unique_id}@example.com',
                password='testpass123'
            )
            Course_members.objects.create(
                course_id=self.course,
                user_id=teacher,
                role=Course_members.Role.TEACHER
            )
            
            # 老師應該有權限
            result = mixin.check_teacher_permission(teacher, problem.id)
            assert result == True
        
        # 創建並測試 TA
        for i in range(num_tas):
            ta = User.objects.create_user(
                username=f'ta_{i}_{unique_id}',
                email=f'ta_{i}_{unique_id}@example.com',
                password='testpass123'
            )
            Course_members.objects.create(
                course_id=self.course,
                user_id=ta,
                role=Course_members.Role.TA
            )
            
            # TA 應該有權限
            result = mixin.check_teacher_permission(ta, problem.id)
            assert result == True
        
        # 創建並測試學生
        for i in range(num_students):
            student = User.objects.create_user(
                username=f'student_{i}_{unique_id}',
                email=f'student_{i}_{unique_id}@example.com',
                password='testpass123'
            )
            Course_members.objects.create(
                course_id=self.course,
                user_id=student,
                role=Course_members.Role.STUDENT
            )
            
            # 學生應該沒有權限
            with pytest.raises(PermissionDenied):
                mixin.check_teacher_permission(student, problem.id)
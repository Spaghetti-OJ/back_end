from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from courses.models import Courses, Course_members
from problems.models import Problems
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class CopycatRBACTests(APITestCase):
    def _authenticate(self, user):
        """Helper method to authenticate user with JWT token"""
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def setUp(self):
        from user.models import UserProfile
        
        # Create users
        self.teacher = User.objects.create_user(username='teacher', password='password', email='teacher@example.com')
        pt, _ = UserProfile.objects.get_or_create(user=self.teacher)
        pt.email_verified = True
        pt.save()
        
        self.ta = User.objects.create_user(username='ta', password='password', email='ta@example.com')
        pta, _ = UserProfile.objects.get_or_create(user=self.ta)
        pta.email_verified = True
        pta.save()
        
        self.student = User.objects.create_user(username='student', password='password', email='student@example.com')
        ps, _ = UserProfile.objects.get_or_create(user=self.student)
        ps.email_verified = True
        ps.save()
        
        self.outsider = User.objects.create_user(username='outsider', password='password', email='outsider@example.com')
        po, _ = UserProfile.objects.get_or_create(user=self.outsider)
        po.email_verified = True
        po.save()

        # Create admin
        self.admin = User.objects.create_superuser(username='admin', password='password', email='admin@example.com')
        pa, _ = UserProfile.objects.get_or_create(user=self.admin)
        pa.email_verified = True
        pa.save()

        # Create another teacher for cross-course testing
        self.teacher2 = User.objects.create_user(username='teacher2', password='password', email='teacher2@example.com')
        pt2, _ = UserProfile.objects.get_or_create(user=self.teacher2)
        pt2.email_verified = True
        pt2.save()

        # Create Course 1
        self.course = Courses.objects.create(name='Test Course', teacher_id=self.teacher, student_limit=100)
        
        # Add members to Course 1
        Course_members.objects.create(course_id=self.course, user_id=self.ta, role=Course_members.Role.TA)
        Course_members.objects.create(course_id=self.course, user_id=self.student, role=Course_members.Role.STUDENT)

        # Create Course 2 (for cross-course testing)
        self.course2 = Courses.objects.create(name='Test Course 2', teacher_id=self.teacher2, student_limit=100)

        # Create Problem in Course 1
        self.problem = Problems.objects.create(
            title='Test Problem', 
            description='desc', 
            course_id=self.course,
            creator_id=self.teacher
        )

        # Create Problem in Course 2
        self.problem2 = Problems.objects.create(
            title='Test Problem 2', 
            description='desc2', 
            course_id=self.course2,
            creator_id=self.teacher2
        )

        self.url = reverse('copycat')

    def test_teacher_create_report(self):
        """ Teacher should be able to create a report """
        self._authenticate(self.teacher)
        data = {'problem_id': self.problem.id, 'language': 'python'}
        response = self.client.post(self.url, data)
        # Assuming MOSS might not run, but permission check passes. 
        # API returns 202 on success, or 429 if pending.
        self.assertIn(response.status_code, [status.HTTP_202_ACCEPTED, status.HTTP_200_OK])

    def test_ta_create_report(self):
        """ TA should be able to create a report """
        self._authenticate(self.ta)
        data = {'problem_id': self.problem.id, 'language': 'python'}
        response = self.client.post(self.url, data)
        self.assertIn(response.status_code, [status.HTTP_202_ACCEPTED, status.HTTP_200_OK])

    def test_student_create_report_forbidden(self):
        """ Student should be forbidden from creating a report """
        self._authenticate(self.student)
        data = {'problem_id': self.problem.id, 'language': 'python'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_outsider_create_report_forbidden(self):
        """ Outsider should be forbidden """
        self._authenticate(self.outsider)
        data = {'problem_id': self.problem.id, 'language': 'python'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_view_report(self):
        """ Teacher should be able to view report """
        self._authenticate(self.teacher)
        response = self.client.get(self.url, {'problem_id': self.problem.id})
        # Even if 404 (no report yet), permission check happens first. 
        # But wait, code checks permission then queries. If no report, returns 404.
        # If permission denied, returns 403.
        # So we verify it is NOT 403.
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_view_report_forbidden(self):
        """ Student should be forbidden from viewing report """
        self._authenticate(self.student)
        response = self.client.get(self.url, {'problem_id': self.problem.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_report_any_course(self):
        """ Admin should be able to create report for any course's problem """
        self._authenticate(self.admin)
        data = {'problem_id': self.problem.id, 'language': 'python'}
        response = self.client.post(self.url, data)
        # This test will likely FAIL - admin privilege not implemented yet
        self.assertIn(response.status_code, [status.HTTP_202_ACCEPTED, status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS])

    def test_admin_can_view_report_any_course(self):
        """ Admin should be able to view report for any course """
        self._authenticate(self.admin)
        response = self.client.get(self.url, {'problem_id': self.problem.id})
        # This test will likely FAIL - admin privilege not implemented yet
        # Should not return 403 Forbidden
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_create_report_other_course(self):
        """ Teacher A cannot create report for Teacher B's course """
        self._authenticate(self.teacher)
        data = {'problem_id': self.problem2.id, 'language': 'python'}  # problem2 belongs to teacher2's course
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_view_report_other_course(self):
        """ Teacher A cannot view report for Teacher B's course """
        self._authenticate(self.teacher)
        response = self.client.get(self.url, {'problem_id': self.problem2.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ta_cannot_create_report_other_course(self):
        """ TA cannot create report for problems in courses they're not part of """
        self._authenticate(self.ta)
        data = {'problem_id': self.problem2.id, 'language': 'python'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ta_cannot_view_report_other_course(self):
        """ TA cannot view report for problems in courses they're not part of """
        self._authenticate(self.ta)
        response = self.client.get(self.url, {'problem_id': self.problem2.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher2_can_create_report_own_course(self):
        """ Teacher 2 can create report for their own course """
        self._authenticate(self.teacher2)
        data = {'problem_id': self.problem2.id, 'language': 'python'}
        response = self.client.post(self.url, data)
        self.assertIn(response.status_code, [status.HTTP_202_ACCEPTED, status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS])

    def test_teacher2_can_view_report_own_course(self):
        """ Teacher 2 can view report for their own course """
        self._authenticate(self.teacher2)
        response = self.client.get(self.url, {'problem_id': self.problem2.id})
        # Even if no report exists (404), should not be 403 Forbidden
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


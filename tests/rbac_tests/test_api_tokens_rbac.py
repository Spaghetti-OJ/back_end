from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from api_tokens.models import ApiToken
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class ApiTokenRBACTests(APITestCase):
    def _authenticate(self, user):
        """Helper method to authenticate user with JWT token"""
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def setUp(self):
        from user.models import UserProfile
        
        self.user1 = User.objects.create_user(username='user1', password='password', email='user1@example.com')
        p1, _ = UserProfile.objects.get_or_create(user=self.user1)
        p1.email_verified = True
        p1.save()
        
        self.user2 = User.objects.create_user(username='user2', password='password', email='user2@example.com')
        p2, _ = UserProfile.objects.get_or_create(user=self.user2)
        p2.email_verified = True
        p2.save()
        
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
        
        self.admin = User.objects.create_superuser(username='admin', password='password', email='admin@example.com')
        pa, _ = UserProfile.objects.get_or_create(user=self.admin)
        pa.email_verified = True
        pa.save()
        
        # Create a course to assign roles
        from courses.models import Courses, Course_members
        self.course = Courses.objects.create(name='Test Course', teacher_id=self.teacher, student_limit=100)
        Course_members.objects.create(course_id=self.course, user_id=self.ta, role=Course_members.Role.TA)
        Course_members.objects.create(course_id=self.course, user_id=self.student, role=Course_members.Role.STUDENT)
        
        # User1 creates a token
        self.token1 = ApiToken.objects.create(
            user=self.user1,
            name='User1 Token',
            token_hash='hash123',
            prefix='prefix'
        )
        self.list_url = reverse('api-token-list')
        self.detail_url = reverse('api-token-detail', args=[self.token1.id])

    def test_user_can_list_own_tokens(self):
        self._authenticate(self.user1)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see 1 token
        self.assertEqual(len(response.data['data']), 1)

    def test_user_cannot_list_others_tokens(self):
        # User2 lists tokens, should not see User1's
        self._authenticate(self.user2)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 0)

    def test_user_can_delete_own_token(self):
        self._authenticate(self.user1)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(ApiToken.objects.filter(id=self.token1.id).exists())

    def test_user_cannot_delete_others_token(self):
        self._authenticate(self.user2)
        response = self.client.delete(self.detail_url)
        # API returns 404 if not found (because filtered by user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Token should still exist
        self.assertTrue(ApiToken.objects.filter(id=self.token1.id).exists())

    def test_user_cannot_get_others_token_details(self):
        self._authenticate(self.user2)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_can_create_token(self):
        """ Teacher should be able to create API tokens """
        self._authenticate(self.teacher)
        data = {'name': 'Teacher Token', 'permissions': ['read']}
        response = self.client.post(self.list_url, data, format='json')
        # This test will likely FAIL because the feature is not implemented yet
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('full_token', response.data['data'])

    def test_ta_can_create_token(self):
        """ TA should be able to create API tokens """
        self._authenticate(self.ta)
        data = {'name': 'TA Token', 'permissions': ['read']}
        response = self.client.post(self.list_url, data, format='json')
        # This test will likely FAIL because the feature is not implemented yet
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('full_token', response.data['data'])

    def test_student_cannot_create_token(self):
        """ Student should NOT be able to create API tokens """
        self._authenticate(self.student)
        data = {'name': 'Student Token', 'permissions': ['read']}
        response = self.client.post(self.list_url, data, format='json')
        # This test will likely FAIL because the feature is not implemented yet
        # Expected: 403 Forbidden, but currently returns 201 Created
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_token(self):
        """ Admin should be able to create API tokens """
        self._authenticate(self.admin)
        data = {'name': 'Admin Token', 'permissions': ['read', 'write']}
        response = self.client.post(self.list_url, data, format='json')
        # This test will likely FAIL because the feature is not implemented yet
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_can_view_all_tokens(self):
        """ Admin should be able to view all users' tokens """
        # Create tokens for different users
        ApiToken.objects.create(user=self.teacher, name='Teacher Token', token_hash='hash_t', prefix='prefix_t')
        ApiToken.objects.create(user=self.student, name='Student Token', token_hash='hash_s', prefix='prefix_s')
        
        self._authenticate(self.admin)
        response = self.client.get(self.list_url)
        # This test will likely FAIL - need admin endpoint to see all tokens
        # Currently only returns admin's own tokens
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see tokens from multiple users (at least 3: user1, teacher, student)
        # This assertion will likely fail
        self.assertGreaterEqual(len(response.data['data']), 3)

    def test_admin_can_delete_any_token(self):
        """ Admin should be able to delete any user's token """
        # Create a token for teacher
        teacher_token = ApiToken.objects.create(
            user=self.teacher, 
            name='Teacher Token To Delete', 
            token_hash='hash_del', 
            prefix='prefix_del'
        )
        
        self._authenticate(self.admin)
        delete_url = reverse('api-token-detail', args=[teacher_token.id])
        response = self.client.delete(delete_url)
        # This test will likely FAIL - admin needs special permission
        # Currently returns 404 because token is filtered by user
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(ApiToken.objects.filter(id=teacher_token.id).exists())


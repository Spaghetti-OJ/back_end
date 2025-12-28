from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from auths.models import LoginLog
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class AuthsRBACTests(APITestCase):
    def _authenticate(self, user):
        """Helper method to authenticate user with JWT token"""
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def setUp(self):
        from user.models import UserProfile
        
        self.user1 = User.objects.create_user(username='user1', password='password', email='user1@example.com')
        profile1, _ = UserProfile.objects.get_or_create(user=self.user1)
        profile1.email_verified = True
        profile1.save()
        
        self.user2 = User.objects.create_user(username='user2', password='password', email='user2@example.com')
        profile2, _ = UserProfile.objects.get_or_create(user=self.user2)
        profile2.email_verified = True
        profile2.save()
        
        self.admin = User.objects.create_superuser(username='admin', password='password', email='admin@example.com')
        profile_admin, _ = UserProfile.objects.get_or_create(user=self.admin)
        profile_admin.email_verified = True
        profile_admin.save()
        
        # Create some logs
        LoginLog.objects.create(user=self.user1, username=self.user1.username, login_status='success', ip_address='127.0.0.1')

        self.self_logs_url = reverse('login-log-list-self')
        self.user_logs_url = reverse('user-login-log-list', args=[self.user1.id])
        self.stats_url = reverse('user-submission-activity', args=[self.user1.id])

    def test_user_can_view_own_logs(self):
        self._authenticate(self.user1)
        response = self.client.get(self.self_logs_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)

    def test_user_cannot_view_others_logs_via_admin_api(self):
        # User2 tries to access User1's logs via admin endpoint
        self._authenticate(self.user2)
        response = self.client.get(self.user_logs_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_others_logs(self):
        self._authenticate(self.admin)
        response = self.client.get(self.user_logs_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see User1's logs
        self.assertEqual(len(response.data['data']), 1)

    def test_user_can_view_others_submission_stats(self):
        # Public profile scenario
        self._authenticate(self.user2)
        response = self.client.get(self.stats_url)
        # Should be allowed (200)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_cannot_view_suspicious_activities(self):
        """ Regular user (teacher/student/TA) cannot access suspicious activities """
        self._authenticate(self.user1)
        response = self.client.get(reverse('suspicious-activity-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_suspicious_activities(self):
        """ Admin can access suspicious activities """
        self._authenticate(self.admin)
        response = self.client.get(reverse('suspicious-activity-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_cannot_view_others_activities(self):
        """ Regular user cannot view other users' activity records """
        self._authenticate(self.user2)
        response = self.client.get(reverse('user-activity-list', args=[self.user1.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_others_activities(self):
        """ Admin can view other users' activity records """
        self._authenticate(self.admin)
        response = self.client.get(reverse('user-activity-list', args=[self.user1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_can_create_own_activity(self):
        """ Regular user can create their own activity records """
        self._authenticate(self.user1)
        data = {'activity_type': 'view_problem', 'metadata': {'problem_id': '123'}}
        response = self.client.post(reverse('activity-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


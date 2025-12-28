
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from user.models import UserProfile

User = get_user_model()

class ProfileViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile, created = UserProfile.objects.get_or_create(user=self.user)
        self.profile.email_verified = True
        self.profile.save()
        
        self.url_me = reverse('profile-me')

    def test_get_me_profile_unauthenticated(self):
        response = self.client.get(self.url_me)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_get_me_profile_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # response.data = {'data': {...}, 'message': '...', 'status': 'ok'}
        self.assertEqual(response.data['data']['username'], self.user.username)

    def test_get_public_profile(self):
        self.client.force_authenticate(user=self.user) # Public profile needs auth
        url_public = reverse('profile-public', kwargs={'username': self.user.username})
        response = self.client.get(url_public)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['username'], self.user.username)

    def test_get_public_profile_not_found(self):
        self.client.force_authenticate(user=self.user)
        url_public = reverse('profile-public', kwargs={'username': 'nonexistent'})
        response = self.client.get(url_public)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

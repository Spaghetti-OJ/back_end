import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class DebugAuthTest(APITestCase):
    def setUp(self):
        from user.models import UserProfile
        
        self.user = User.objects.create_user(username='testuser', password='password', email='test@example.com')
        profile, created = UserProfile.objects.get_or_create(user=self.user, defaults={'email_verified': True})
        if not created:
            profile.email_verified = True
            profile.save()
    
    def test_user_authentication_and_profile(self):
        """Test if user can authenticate and has email_verified=True"""
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Check user profile exists and is verified
        from user.models import UserProfile
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.email_verified)
        
        # Try a simple API call
        response = self.client.get(reverse('login-log-list-self'))
        print(f"Response status: {response.status_code}")
        print(f"Response  data: {response.data if hasattr(response, 'data') else response.content}")
        
        # If 403, print more debug info
        if response.status_code == 403:
            print(f"User: {self.user}")
            print(f"User.is_authenticated: {self.user.is_authenticated}")
            print(f"Profile email verification using is_email_verified(): {self.user.is_email_verified()}")

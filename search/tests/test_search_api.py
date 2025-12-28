
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from problems.models import Problems
from courses.models import Courses
from django.contrib.auth import get_user_model
from user.models import UserProfile

User = get_user_model()

class SearchViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='teacher', password='password')
        UserProfile.objects.update_or_create(user=self.user, defaults={'email_verified': True})
        self.course = Courses.objects.create(name="Test Course", teacher_id=self.user)
        
        # Create some problems
        self.p1 = Problems.objects.create(
            title="Hello World Problem", 
            description="Description 1", 
            creator_id=self.user,
            course_id=self.course,
            is_public=Problems.Visibility.PUBLIC 
        )
        self.p2 = Problems.objects.create(
            title="Another Challenge", 
            description="Description 2", 
            creator_id=self.user,
            course_id=self.course,
            is_public=Problems.Visibility.PUBLIC
        )
        self.p3 = Problems.objects.create(
            title="Hidden Problem", 
            description="Hidden", 
            is_public=Problems.Visibility.HIDDEN,
            creator_id=self.user,
            course_id=self.course
        )

    def test_global_search_problems(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('global-problem-search')
        response = self.client.get(url, {'q': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check response structure. Assuming standard DRF or custom api_response
        data = response.data.get('data', response.data)
        self.assertTrue(any(p['title'] == "Hello World Problem" for p in data['items']))

    def test_problem_search(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('problem-search')
        response = self.client.get(url, {'title': 'Challenge'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('data', response.data)
        # response might be paginated or list
        if isinstance(data, dict) and 'items' in data:
            results = data['items']
        elif isinstance(data, dict) and 'results' in data:
            results = data['results']
        else:
            results = data
        self.assertTrue(len(results) > 0)

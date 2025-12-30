
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from courses.models import Courses, Course_members
from user.models import UserProfile

User = get_user_model()

class CourseApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(username='teacher', email='teacher@example.com', password='password', identity=User.Identity.TEACHER)
        UserProfile.objects.update_or_create(user=self.teacher, defaults={'email_verified': True})

        self.student = User.objects.create_user(username='student', email='student@example.com', password='password', identity=User.Identity.STUDENT)
        UserProfile.objects.update_or_create(user=self.student, defaults={'email_verified': True})

        self.course = Courses.objects.create(name="Existing Course", teacher_id=self.teacher)
        if not self.course.join_code:
             self.course.join_code = "ABC1234"
             self.course.save()

    def test_list_courses(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('courses:courses:list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if wrapped in api_response or similar
        # If response.data is list or dict with data
        data = response.data.get('data', response.data)
        self.assertTrue(len(data) > 0)

    def test_create_course(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('courses:courses:list')
        data = {
            'course': 'New Course',
            'teacher': self.teacher.username,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Courses.objects.filter(name='New Course').exists())

    def test_get_course_detail(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('courses:course_courseid:detail', kwargs={'course_id': self.course.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check wrapper
        data = response.data.get('data', response.data)
        # Detail view returns object or dict
        if 'course' in data:
            self.assertEqual(data['course']['course'], 'Existing Course')
        else:
            self.assertEqual(data['course'], 'Existing Course')

    def test_join_course(self):
        self.client.force_authenticate(user=self.student)
        # url pattern: courses/<join_code>/join/
        url = reverse('courses:join:join', kwargs={'join_code': self.course.join_code})
        response = self.client.post(url)
        
        # Check status code. Could be 200 or 201.
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        
        self.assertTrue(Course_members.objects.filter(course_id=self.course, user_id=self.student).exists())

    def test_join_course_bad_code(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('courses:join:join', kwargs={'join_code': 'INVALID'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from courses.models import Courses, Announcements, Course_members
from user.models import UserProfile

User = get_user_model()

class AnnouncementApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(username='teacher', email='teacher@example.com', password='password', identity=User.Identity.TEACHER)
        UserProfile.objects.update_or_create(user=self.teacher, defaults={'email_verified': True})
        
        self.student = User.objects.create_user(username='student', email='student@example.com', password='password', identity=User.Identity.STUDENT)
        UserProfile.objects.update_or_create(user=self.student, defaults={'email_verified': True})

        self.course = Courses.objects.create(name="Test Course", teacher_id=self.teacher)
        
        # Add student
        Course_members.objects.create(course_id=self.course, user_id=self.student, role=Course_members.Role.STUDENT)

        self.announcement = Announcements.objects.create(
            course_id=self.course,
            title="Welcome",
            content="Hello everyone",
            creator_id=self.teacher
        )

    def test_list_announcements(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('announcements:course', kwargs={'course_id': self.course.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['data']) >= 1)

    def test_retrieve_announcement(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('announcements:announcement', kwargs={'course_id': self.course.id, 'ann_id': self.announcement.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['title'], "Welcome")

    def test_create_announcement_teacher(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('announcements:create')
        data = {
            'course_id': self.course.id,
            'title': 'New Announcement',
            'content': 'Content here',
            'is_pinned': False
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_announcement_student_forbidden(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('announcements:create')
        data = {
            'course_id': self.course.id,
            'title': 'Hacker Announcement',
            'content': 'Content here'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_announcement(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('announcements:create') # PUT uses same endpoint name logic? No, let's check view.
        # View class AnnouncementCreateView handles POST, PUT, DELETE at /ann/ (name='create')
        
        data = {
            'annId': self.announcement.id,
            'title': 'Updated Title',
            'content': 'Updated Content',
            'is_pinned': True
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.title, 'Updated Title')

    def test_delete_announcement(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('announcements:create') # DELETE uses same endpoint
        
        data = {'annId': self.announcement.id}
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Announcements.objects.filter(id=self.announcement.id).exists())

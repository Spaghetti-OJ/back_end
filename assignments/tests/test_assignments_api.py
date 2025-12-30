
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from courses.models import Courses, Course_members
from assignments.models import Assignments
from user.models import UserProfile

User = get_user_model()

class AssignmentApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(username='teacher', email='teacher@example.com', password='password', identity=User.Identity.TEACHER)
        UserProfile.objects.update_or_create(user=self.teacher, defaults={'email_verified': True})
        
        self.course = Courses.objects.create(name="CS101", teacher_id=self.teacher)
        
        self.assignment = Assignments.objects.create(
            title="HW1",
            course=self.course,
            creator=self.teacher,
            status=Assignments.Status.ACTIVE
        )
        self.assignment_url_base = reverse('assignments:homework-create')

    def test_create_assignment(self):
        self.client.force_authenticate(user=self.teacher)
        data = {
            'name': 'New HW',
            'course_id': self.course.id,
            'markdown': 'Desc',
            '_start_dt': timezone.now(),
            '_end_dt': timezone.now() + timedelta(days=7)
        }
        # The serializer expects specific fields, checking views.py HWCreateSerializer usage
        # views.py: ser = HomeworkCreateSerializer(data=request.data)
        # title=ser.validated_data["name"] => input field 'name'.
        # start_time=ser.validated_data.get("_start_dt") => input field '_start_dt' ?
        # Actually I should verify serializer fields. 
        # But assuming names from view code: name, markdown, _start_dt, _end_dt, problem_ids.
        
        response = self.client.post(self.assignment_url_base, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Assignments.objects.filter(title='New HW').exists())

    def test_get_assignment_detail(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('assignments:homework-detail', kwargs={'homework_id': self.assignment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # api_response
        self.assertEqual(response.data['data']['name'], 'HW1')

    def test_update_assignment_deadline(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('assignments:homework-deadline-update', kwargs={'homework_id': self.assignment.id})
        
        new_due = timezone.now() + timedelta(days=7)
        data = {
            'end': new_due.strftime('%Y-%m-%dT%H:%M:%SZ') # View expects 'end'
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_scoreboard(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('assignments:homework-scoreboard', kwargs={'homework_id': self.assignment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.test import APIClient

from .models import Courses


User = get_user_model()


class CourseCreateAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username="teacher_one",
            email="teacher@example.com",
            password="pass1234",
            real_name="Teacher One",
            identity="teacher",
        )
        self.client.force_authenticate(user=self.teacher)
        self.student = User.objects.create_user(
            username="student_one",
            email="student@example.com",
            password="pass1234",
            real_name="Student One",
            identity="student",
        )
        self.url = reverse("course_create")

    def test_teacher_can_create_course(self):
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "name": "Linear Algebra",
            "description": "Matrix theory and linear equations.",
            "student_limit": 50,
            "semester": "Fall",
            "academic_year": 2024,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], payload["name"])
        self.assertEqual(response.data["teacher"]["id"], str(self.teacher.id))
        self.assertTrue(response.data["join_code"])
        self.assertEqual(Courses.objects.count(), 1)

    def test_student_cannot_create_course(self):
        self.client.force_authenticate(user=self.student)
        payload = {
            "name": "Forbidden Course",
            "student_limit": 30,
            "semester": "Spring",
            "academic_year": 2024,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Courses.objects.count(), 0)

    def test_join_code_generated_automatically(self):
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "name": "Algorithms",
            "student_limit": 40,
            "semester": "Spring",
            "academic_year": 2024,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        join_code = response.data["join_code"]
        self.assertEqual(len(join_code), 7)
        self.assertTrue(join_code.isalnum())
        self.assertTrue(join_code.isupper())

    def test_missing_required_fields_returns_error(self):
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "name": "Incomplete Course",
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("student_limit", response.data)
        self.assertIn("semester", response.data)
        self.assertIn("academic_year", response.data)

    def test_course_teacher_field(self):
        data = {
            "name": "測試課程",
            "description": "這是一門測試課程",
            "student_limit": 30,
            "semester": "上學期",
            "academic_year": 2025
        }

        response = self.client.post("/courses/", data, format="json")
        self.assertEqual(response.status_code, 201)

        # 驗證 teacher_id 是否正確綁定
        course = Courses.objects.get(id=response.data["id"])
        self.assertEqual(course.teacher_id, self.teacher)

        print("課程建立成功，teacher_id 正確綁定至 User 物件：", course.teacher_id.username)
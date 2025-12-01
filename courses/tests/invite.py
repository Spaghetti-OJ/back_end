import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Courses

User = get_user_model()


class CourseInviteCodeAPITestCase(APITestCase):
    url_name = "courses:invite:create"

    def setUp(self):
        super().setUp()
        self.client.defaults["HTTP_HOST"] = "127.0.0.1"

        suffix = uuid.uuid4().hex[:6]
        self.teacher = User.objects.create_user(
            username=f"teacher_{suffix}",
            email=f"teacher_{suffix}@example.com",
            password="pass1234",
            real_name="Teacher One",
            identity="teacher",
        )
        self.admin = User.objects.create_user(
            username=f"admin_{suffix}",
            email=f"admin_{suffix}@example.com",
            password="pass1234",
            real_name="Admin One",
            identity="admin",
        )
        self.another_teacher = User.objects.create_user(
            username=f"teacher2_{suffix}",
            email=f"teacher2_{suffix}@example.com",
            password="pass1234",
            real_name="Teacher Two",
            identity="teacher",
        )
        self.student = User.objects.create_user(
            username=f"student_{suffix}",
            email=f"student_{suffix}@example.com",
            password="pass1234",
            real_name="Student One",
            identity="student",
        )

        self.course = Courses.objects.create(
            name=f"Algorithms_{suffix}",
            teacher_id=self.teacher,
            join_code="ABC1234",
        )

    def _url(self, course):
        course_id = course.id if hasattr(course, "id") else course
        return reverse(self.url_name, kwargs={"course_id": course_id})

    def test_teacher_can_regenerate_invite_code(self):
        self.client.force_authenticate(self.teacher)
        old_code = self.course.join_code

        response = self.client.post(self._url(self.course))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        new_code = response.data["data"]["joinCode"]
        self.assertRegex(new_code, r"^[A-Z0-9]{7}$")
        self.course.refresh_from_db()
        self.assertEqual(self.course.join_code, new_code)
        self.assertNotEqual(old_code, new_code)

    def test_admin_can_regenerate_invite_code(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(self._url(self.course))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertRegex(response.data["data"]["joinCode"], r"^[A-Z0-9]{7}$")

    def test_non_owner_teacher_cannot_regenerate(self):
        outsider_course = Courses.objects.create(
            name="OutsiderCourse",
            teacher_id=self.another_teacher,
        )
        self.client.force_authenticate(self.teacher)

        response = self.client.post(self._url(outsider_course))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You are not in this course.")

    def test_student_cannot_regenerate_invite_code(self):
        self.client.force_authenticate(self.student)

        response = self.client.post(self._url(self.course))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")

    def test_returns_not_found_when_course_missing(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(self._url(999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Course not found.")

import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Course_members, Courses

User = get_user_model()


class CourseJoinAPITestCase(APITestCase):
    join_url_name = "courses:join:join"

    def setUp(self):
        super().setUp()
        self.client.defaults["HTTP_HOST"] = "127.0.0.1"

        self.unique = uuid.uuid4().hex[:6]
        self.teacher = User.objects.create_user(
            username=f"teacher_{self.unique}",
            email=f"teacher_{self.unique}@example.com",
            password="pass1234",
            real_name="Teacher",
            identity="teacher",
        )
        self.student = User.objects.create_user(
            username=f"student_{self.unique}",
            email=f"student_{self.unique}@example.com",
            password="pass1234",
            real_name="Student",
            identity="student",
        )

    def _create_course(self, *, name=None, teacher=None):
        course_name = name or f"SampleCourse_{self.unique}"
        return Courses.objects.create(name=course_name, teacher_id=teacher or self.teacher)

    def _join_url(self, course_id):
        return reverse(self.join_url_name, kwargs={"course_id": course_id})

    def test_student_can_join_with_valid_code(self):
        course = self._create_course(name="JoinableCourse", teacher=self.teacher)
        course.join_code = "JOIN123"
        course.save(update_fields=["join_code"])

        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            self._join_url(course.id),
            {"joinCode": "join123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertTrue(
            Course_members.objects.filter(
                course_id=course,
                user_id=self.student,
                role=Course_members.Role.STUDENT,
            ).exists()
        )
        course.refresh_from_db()
        self.assertEqual(course.student_count, 1)

    def test_join_rejects_invalid_code(self):
        course = self._create_course(name="JoinableCourse", teacher=self.teacher)
        course.join_code = "JOIN123"
        course.save(update_fields=["join_code"])

        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            self._join_url(course.id),
            {"joinCode": "WRONG12"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Invalid join code.")

    def test_join_requires_student_identity(self):
        course = self._create_course(name="StaffCourse", teacher=self.teacher)
        course.join_code = "JOIN123"
        course.save(update_fields=["join_code"])

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self._join_url(course.id),
            {"joinCode": "JOIN123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")

    def test_join_prevents_duplicate_membership(self):
        course = self._create_course(name="ExistingMemberCourse", teacher=self.teacher)
        course.join_code = "JOIN123"
        course.save(update_fields=["join_code"])
        Course_members.objects.create(
            course_id=course,
            user_id=self.student,
            role=Course_members.Role.STUDENT,
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            self._join_url(course.id),
            {"joinCode": "JOIN123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "You are already in this course.")

    def test_join_respects_student_limit(self):
        course = self._create_course(
            name="LimitedCourse",
            teacher=self.teacher,
        )
        course.join_code = "JOIN123"
        course.student_limit = 1
        course.save(update_fields=["join_code", "student_limit"])
        existing_student = User.objects.create_user(
            username=f"existing_student_{self.unique}",
            email=f"existing_student_{self.unique}@example.com",
            password="pass1234",
            real_name="Existing Student",
            identity="student",
        )
        Course_members.objects.create(
            course_id=course,
            user_id=existing_student,
            role=Course_members.Role.STUDENT,
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            self._join_url(course.id),
            {"joinCode": "JOIN123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Course is full.")

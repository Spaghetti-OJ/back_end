import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import CourseGrade, Course_members, Courses

User = get_user_model()


class CourseGradeViewTests(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher01",
            email="teacher01@example.com",
            password="pass1234",
            real_name="Teacher One",
            identity="teacher",
        )
        self.student = User.objects.create_user(
            username="student01",
            email="student01@example.com",
            password="pass1234",
            real_name="Student One",
            identity="student",
        )
        self.another_student = User.objects.create_user(
            username="student02",
            email="student02@example.com",
            password="pass1234",
            real_name="Student Two",
            identity="student",
        )
        self.outsider = User.objects.create_user(
            username="student03",
            email="student03@example.com",
            password="pass1234",
            real_name="Student Three",
            identity="student",
        )

        self.course = Courses.objects.create(name="Algorithms101", teacher_id=self.teacher)
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.student,
            role=Course_members.Role.STUDENT,
        )
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.another_student,
            role=Course_members.Role.STUDENT,
        )

        CourseGrade.objects.create(
            course=self.course,
            student=self.student,
            title="Quiz 1",
            content="Intro quiz",
            score=80,
        )
        CourseGrade.objects.create(
            course=self.course,
            student=self.student,
            title="Midterm",
            content="Midterm exam",
            score=95,
        )

    def test_student_can_view_own_grades(self):
        self.client.force_authenticate(self.student)

        response = self.client.get(self._url(self.course, self.student))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertEqual(len(response.data["grades"]), 2)
        self.assertEqual(response.data["grades"][0]["title"], "Midterm")

    def test_teacher_can_view_student_grades(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get(self._url(self.course, self.student))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["grades"]), 2)

    def test_student_cannot_view_other_student_grades(self):
        self.client.force_authenticate(self.student)

        response = self.client.get(self._url(self.course, self.another_student))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You can only view your score.")

    def test_non_member_cannot_view_course_grades(self):
        self.client.force_authenticate(self.outsider)

        response = self.client.get(self._url(self.course, self.student))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You are not in this course.")

    def test_returns_not_found_when_student_not_in_course(self):
        student = User.objects.create_user(
            username="student04",
            email="student04@example.com",
            password="pass1234",
            real_name="Student Four",
            identity="student",
        )
        self.client.force_authenticate(self.teacher)

        response = self.client.get(self._url(self.course, student))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "The student is not in the course.")

    def test_returns_not_found_when_course_missing(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get(self._url(uuid.uuid4(), self.student))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Course not found.")

    def test_requires_authentication(self):
        response = self.client.get(self._url(self.course, self.student))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @staticmethod
    def _url(course, student):
        course_id = course.id if hasattr(course, "id") else course
        student_id = student.id if hasattr(student, "id") else student
        return reverse(
            "courses:grade:detail",
            kwargs={"course_id": course_id, "student": student_id},
        )

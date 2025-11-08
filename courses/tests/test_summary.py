from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from assignments.models import Assignments
from problems.models import Problems
from submissions.models import Submission

from ..models import Course_members, Courses

User = get_user_model()


class CourseSummaryAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="pass1234",
            real_name="Admin User",
            identity="admin",
        )
        self.teacher = User.objects.create_user(
            username="summary_teacher",
            email="summary_teacher@example.com",
            password="pass1234",
            real_name="Summary Teacher",
            identity="teacher",
        )
        self.student = User.objects.create_user(
            username="summary_student",
            email="summary_student@example.com",
            password="pass1234",
            real_name="Summary Student",
            identity="student",
        )

        self.course1 = Courses.objects.create(
            name="Algorithms",
            description="Algo course",
            student_limit=50,
            semester="Fall",
            academic_year="2024",
            teacher_id=self.teacher,
        )
        self.course2 = Courses.objects.create(
            name="Databases",
            description="DB course",
            student_limit=40,
            semester="Spring",
            academic_year="2024",
            teacher_id=self.teacher,
        )

        Course_members.objects.create(
            course_id=self.course1,
            user_id=self.teacher,
            role=Course_members.Role.TEACHER,
        )
        Course_members.objects.create(
            course_id=self.course1,
            user_id=self.student,
            role=Course_members.Role.STUDENT,
        )

        Assignments.objects.create(
            title="HW1",
            description="Homework 1",
            course=self.course1,
            creator=self.teacher,
        )
        Assignments.objects.create(
            title="HW2",
            description="Homework 2",
            course=self.course1,
            creator=self.teacher,
        )

        problem1 = Problems.objects.create(
            title="Problem 1",
            description="Solve it",
            creator_id=self.teacher,
            course_id=self.course1,
        )
        problem2 = Problems.objects.create(
            title="Problem 2",
            description="Solve it too",
            creator_id=self.teacher,
            course_id=self.course1,
        )

        Submission.objects.create(
            problem_id=problem1.id,
            user=self.student,
            language_type="python",
            source_code="print(1)",
        )
        Submission.objects.create(
            problem_id=problem1.id,
            user=self.student,
            language_type="python",
            source_code="print(2)",
        )
        Submission.objects.create(
            problem_id=problem2.id,
            user=self.student,
            language_type="python",
            source_code="print(3)",
        )

        self.url = reverse("courses:summary:overview")

    def test_admin_can_view_course_summary(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertEqual(response.data["courseCount"], 2)

        summary = {item["course"]: item for item in response.data["breakdown"]}

        self.assertEqual(
            summary["Algorithms"],
            {
                "course": "Algorithms",
                "userCount": 2,
                "homeworkCount": 2,
                "submissionCount": 3,
                "problemCount": 2,
            },
        )
        self.assertEqual(
            summary["Databases"],
            {
                "course": "Databases",
                "userCount": 0,
                "homeworkCount": 0,
                "submissionCount": 0,
                "problemCount": 0,
            },
        )

    def test_non_admin_cannot_view_course_summary(self):
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_access_denied(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data,
            {"detail": "Authentication credentials were not provided."},
        )

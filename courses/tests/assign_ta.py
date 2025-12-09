import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Course_members, Courses

User = get_user_model()


class CourseAssignTAAPITestCase(APITestCase):
    assign_url_name = "courses:assign_ta:assign"

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
        self.admin = User.objects.create_user(
            username=f"admin_{self.unique}",
            email=f"admin_{self.unique}@example.com",
            password="pass1234",
            real_name="Admin",
            identity="admin",
        )
        self.student = User.objects.create_user(
            username=f"student_{self.unique}",
            email=f"student_{self.unique}@example.com",
            password="pass1234",
            real_name="Student",
            identity="student",
        )
        self.another_teacher = User.objects.create_user(
            username=f"another_teacher_{self.unique}",
            email=f"another_teacher_{self.unique}@example.com",
            password="pass1234",
            real_name="Another Teacher",
            identity="teacher",
        )
        self.course = Courses.objects.create(
            name=f"Course_{self.unique}",
            teacher_id=self.teacher,
        )

    def _assign_url(self, course_id):
        return reverse(self.assign_url_name, kwargs={"course_id": course_id})

    def test_teacher_can_promote_student_member_to_ta(self):
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.student,
            role=Course_members.Role.STUDENT,
        )
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            self._assign_url(self.course.id),
            {"username": self.student.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = Course_members.objects.get(
            course_id=self.course, user_id=self.student
        )
        self.assertEqual(membership.role, Course_members.Role.TA)

    def test_teacher_can_assign_non_member_as_ta(self):
        new_student = User.objects.create_user(
            username=f"new_student_{self.unique}",
            email=f"new_student_{self.unique}@example.com",
            password="pass1234",
            real_name="New Student",
            identity="student",
        )
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            self._assign_url(self.course.id),
            {"username": new_student.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = Course_members.objects.get(
            course_id=self.course, user_id=new_student
        )
        self.assertEqual(membership.role, Course_members.Role.TA)

    def test_admin_can_assign_ta(self):
        candidate = User.objects.create_user(
            username=f"candidate_{self.unique}",
            email=f"candidate_{self.unique}@example.com",
            password="pass1234",
            real_name="Candidate",
            identity="student",
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self._assign_url(self.course.id),
            {"username": candidate.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = Course_members.objects.get(
            course_id=self.course, user_id=candidate
        )
        self.assertEqual(membership.role, Course_members.Role.TA)

    def test_student_cannot_assign_ta(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            self._assign_url(self.course.id),
            {"username": self.student.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")

    def test_teacher_cannot_assign_other_course(self):
        other_course = Courses.objects.create(
            name=f"OtherCourse_{self.unique}",
            teacher_id=self.another_teacher,
        )
        target_student = User.objects.create_user(
            username=f"target_{self.unique}",
            email=f"target_{self.unique}@example.com",
            password="pass1234",
            real_name="Target Student",
            identity="student",
        )
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            self._assign_url(other_course.id),
            {"username": target_student.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You are not in this course.")

    def test_returns_not_found_for_unknown_user(self):
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            self._assign_url(self.course.id),
            {"username": f"missing_{self.unique}"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "User not found.")

    def test_rejects_non_student_identity(self):
        teacher_user = User.objects.create_user(
            username=f"teacher_candidate_{self.unique}",
            email=f"teacher_candidate_{self.unique}@example.com",
            password="pass1234",
            real_name="Teacher Candidate",
            identity="teacher",
        )
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            self._assign_url(self.course.id),
            {"username": teacher_user.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "User is not a student.")
        self.assertFalse(
            Course_members.objects.filter(
                course_id=self.course, user_id=teacher_user
            ).exists()
        )

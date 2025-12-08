import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Course_members, Courses

User = get_user_model()


class CourseDetailAPITestCase(APITestCase):
    detail_url_name = "courses:course_courseid:detail"

    def setUp(self):
        super().setUp()
        self.client.defaults["HTTP_HOST"] = "127.0.0.1"

        self.unique = uuid.uuid4().hex[:6]
        self.detail_course_name = f"DetailCourse_{self.unique}"
        self.member_course_name = f"MemberCourse_{self.unique}"
        self.closed_course_name = f"ClosedCourse_{self.unique}"
        self.unknown_course_id = 999999

        self.teacher = User.objects.create_user(
            username=f"teacher_one_{self.unique}",
            email=f"teacher_{self.unique}@example.com",
            password="pass1234",
            real_name="Teacher One",
            identity="teacher",
        )
        self.another_teacher = User.objects.create_user(
            username=f"teacher_two_{self.unique}",
            email=f"teacher2_{self.unique}@example.com",
            password="pass1234",
            real_name="Teacher Two",
            identity="teacher",
        )
        self.student = User.objects.create_user(
            username=f"student_one_{self.unique}",
            email=f"student_{self.unique}@example.com",
            password="pass1234",
            real_name="Student One",
            identity="student",
        )

    def _create_course(self, *, name=None, teacher=None):
        course_name = name or f"SampleCourse_{self.unique}"
        return Courses.objects.create(name=course_name, teacher_id=teacher or self.teacher)

    def _detail_url(self, course_id):
        return reverse(self.detail_url_name, kwargs={"course_id": course_id})

    def test_teacher_can_view_course_detail(self):
        ta_user = User.objects.create_user(
            username=f"ta_user_{self.unique}",
            email=f"ta_{self.unique}@example.com",
            password="pass1234",
            real_name="Assistant One",
            identity="student",
        )
        course = Courses.objects.create(
            name=self.detail_course_name,
            description="Intro course",
            teacher_id=self.teacher,
            semester="Spring",
            academic_year="2025",
            student_limit=50,
            join_code="ABC1234",
            student_count=2,
        )
        Course_members.objects.create(
            course_id=course, user_id=ta_user, role=Course_members.Role.TA
        )
        Course_members.objects.create(
            course_id=course, user_id=self.student, role=Course_members.Role.STUDENT
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self._detail_url(course.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertEqual(response.data["course"]["course"], self.detail_course_name)
        self.assertEqual(response.data["course"]["semester"], "Spring")
        self.assertEqual(response.data["course"]["academicYear"], "2025")
        self.assertEqual(response.data["course"]["joinCode"], "ABC1234")
        self.assertEqual(response.data["teacher"]["username"], self.teacher.username)
        self.assertEqual(len(response.data["TAs"]), 1)
        self.assertEqual(response.data["TAs"][0]["username"], ta_user.username)
        self.assertEqual(len(response.data["students"]), 1)
        self.assertEqual(response.data["students"][0]["username"], self.student.username)

    def test_student_member_can_view_course_detail(self):
        course = self._create_course(name=self.member_course_name, teacher=self.teacher)
        Course_members.objects.create(
            course_id=course, user_id=self.student, role=Course_members.Role.STUDENT
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.get(self._detail_url(course.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")

    def test_non_member_cannot_view_course_detail(self):
        course = self._create_course(name=self.closed_course_name, teacher=self.teacher)
        self.client.force_authenticate(user=self.student)

        response = self.client.get(self._detail_url(course.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You are not in this course.")

    def test_course_detail_not_found(self):
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(self._detail_url(self.unknown_course_id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Course not found.")

    def test_teacher_can_update_tas_list(self):
        course = self._create_course(teacher=self.teacher)
        existing_ta = User.objects.create_user(
            username=f"ta_existing_{self.unique}",
            email=f"ta_existing_{self.unique}@example.com",
            password="pass1234",
            real_name="Existing TA",
            identity="student",
        )
        new_ta = User.objects.create_user(
            username=f"ta_new_{self.unique}",
            email=f"ta_new_{self.unique}@example.com",
            password="pass1234",
            real_name="New TA",
            identity="student",
        )
        Course_members.objects.create(
            course_id=course, user_id=existing_ta, role=Course_members.Role.TA
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.put(
            self._detail_url(course.id),
            {"TAs": [new_ta.username]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        tas = Course_members.objects.filter(course_id=course, role=Course_members.Role.TA)
        self.assertEqual(tas.count(), 1)
        self.assertEqual(tas.first().user_id, new_ta)

    def test_put_returns_not_found_when_ta_missing(self):
        course = self._create_course(teacher=self.teacher)
        self.client.force_authenticate(user=self.teacher)

        response = self.client.put(
            self._detail_url(course.id),
            {"TAs": ["unknown_ta_user"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "User: unknown_ta_user not found.")

    def test_teacher_cannot_update_other_course(self):
        course = self._create_course(teacher=self.another_teacher)
        self.client.force_authenticate(user=self.teacher)

        response = self.client.put(
            self._detail_url(course.id),
            {"TAs": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You are not in this course.")

    def test_student_cannot_update_course_members(self):
        course = self._create_course(teacher=self.teacher)
        self.client.force_authenticate(user=self.student)

        response = self.client.put(
            self._detail_url(course.id),
            {"TAs": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")

    def test_teacher_can_remove_student_with_query_param(self):
        course = self._create_course(teacher=self.teacher)
        Course_members.objects.create(
            course_id=course,
            user_id=self.student,
            role=Course_members.Role.STUDENT,
        )
        self.client.force_authenticate(user=self.teacher)

        response = self.client.put(
            f"{self._detail_url(course.id)}?student={self.student.id}",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Course_members.objects.filter(
                course_id=course,
                user_id=self.student,
                role=Course_members.Role.STUDENT,
            ).exists()
        )

    def test_put_returns_not_found_when_student_missing(self):
        course = self._create_course(teacher=self.teacher)
        self.client.force_authenticate(user=self.teacher)

        response = self.client.put(
            f"{self._detail_url(course.id)}?student={uuid.uuid4()}",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Student not found.")

    def test_put_returns_not_found_when_student_not_in_course(self):
        course = self._create_course(teacher=self.teacher)
        outsider = User.objects.create_user(
            username=f"outsider_{self.unique}",
            email=f"outsider_{self.unique}@example.com",
            password="pass1234",
            real_name="Outsider",
            identity="student",
        )
        self.client.force_authenticate(user=self.teacher)

        response = self.client.put(
            f"{self._detail_url(course.id)}?student={outsider.id}",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Student not found.")

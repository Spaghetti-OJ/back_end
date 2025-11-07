from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Course_members, Courses

User = get_user_model()


class CourseAPITestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher_one",
            email="teacher@example.com",
            password="pass1234",
            real_name="Teacher One",
            identity="teacher",
        )
        self.another_teacher = User.objects.create_user(
            username="teacher_two",
            email="teacher2@example.com",
            password="pass1234",
            real_name="Teacher Two",
            identity="teacher",
        )
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="pass1234",
            real_name="Admin",
            identity="admin",
        )
        self.student = User.objects.create_user(
            username="student_one",
            email="student@example.com",
            password="pass1234",
            real_name="Student One",
            identity="student",
        )
        self.url = reverse("courses:courses:list")

    def test_teacher_can_create_course_for_self(self):
        self.client.force_authenticate(user=self.teacher)
        payload = {"course": "Linear.Algebra_101", "teacher": self.teacher.username}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertEqual(Courses.objects.count(), 1)
        self.assertEqual(Courses.objects.first().teacher_id, self.teacher)

    def test_teacher_cannot_assign_other_teacher(self):
        self.client.force_authenticate(user=self.teacher)
        payload = {"course": "AnotherCourse", "teacher": self.another_teacher.username}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")
        self.assertEqual(Courses.objects.count(), 0)

    def test_admin_can_assign_teacher(self):
        self.client.force_authenticate(user=self.admin)
        payload = {"course": "AdminCourse", "teacher": self.teacher.username}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        course = Courses.objects.get(name="AdminCourse")
        self.assertEqual(course.teacher_id, self.teacher)

    def test_student_cannot_create_course(self):
        self.client.force_authenticate(user=self.student)
        payload = {"course": "StudentCourse", "teacher": self.teacher.username}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")
        self.assertEqual(Courses.objects.count(), 0)

    def test_invalid_course_name_returns_error(self):
        self.client.force_authenticate(user=self.teacher)
        payload = {"course": "Invalid Name!", "teacher": self.teacher.username}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Not allowed name.")

    def test_duplicate_course_name_returns_error(self):
        Courses.objects.create(name="DuplicateCourse", teacher_id=self.teacher)

        self.client.force_authenticate(user=self.teacher)
        payload = {"course": "duplicatecourse", "teacher": self.teacher.username}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Course exists.")

    def test_assign_nonexistent_teacher_returns_not_found(self):
        self.client.force_authenticate(user=self.admin)
        payload = {"course": "NewCourse", "teacher": "unknown_user"}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "User not found.")

    def test_get_returns_courses_for_teacher(self):
        Courses.objects.create(name="Course A", teacher_id=self.teacher)
        Courses.objects.create(name="Course B", teacher_id=self.teacher)

        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertEqual(len(response.data["courses"]), 2)
        self.assertEqual(response.data["courses"][0]["course"], "Course B")
        self.assertEqual(response.data["courses"][1]["course"], "Course A")

    def test_get_returns_courses_for_student_memberships(self):
        course = Courses.objects.create(name="Course A", teacher_id=self.teacher)
        Course_members.objects.create(
            course_id=course,
            user_id=self.student,
            role=Course_members.Role.STUDENT,
        )
        Courses.objects.create(name="Course B", teacher_id=self.teacher)

        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertEqual(len(response.data["courses"]), 1)
        self.assertEqual(response.data["courses"][0]["course"], "Course A")

    def test_unauthenticated_access_denied(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def _create_course(self, *, name="SampleCourse", teacher=None):
        return Courses.objects.create(name=name, teacher_id=teacher or self.teacher)

    def test_teacher_can_update_own_course(self):
        course = self._create_course(name="Algorithms2024", teacher=self.teacher)
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "course": "Algorithms2024",
            "new_course": "Algorithms2025",
            "teacher": self.another_teacher.username,
        }

        response = self.client.put(self.url, payload, format="json")

        course.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertEqual(course.name, "Algorithms2025")
        self.assertEqual(course.teacher_id, self.another_teacher)

    def test_admin_can_update_any_course(self):
        course = self._create_course(name="DataStructures", teacher=self.teacher)
        self.client.force_authenticate(user=self.admin)
        payload = {
            "course": "DataStructures",
            "new_course": "AdvancedDS",
            "teacher": self.another_teacher.username,
        }

        response = self.client.put(self.url, payload, format="json")

        course.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(course.name, "AdvancedDS")
        self.assertEqual(course.teacher_id, self.another_teacher)

    def test_teacher_cannot_update_course_they_do_not_own(self):
        self._create_course(name="Physics101", teacher=self.another_teacher)
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "course": "Physics101",
            "new_course": "Physics102",
            "teacher": self.teacher.username,
        }

        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")

    def test_student_cannot_update_course(self):
        self._create_course(name="Chemistry101", teacher=self.teacher)
        self.client.force_authenticate(user=self.student)
        payload = {
            "course": "Chemistry101",
            "new_course": "Chemistry102",
            "teacher": self.teacher.username,
        }

        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")

    def test_update_invalid_new_name_returns_error(self):
        self._create_course(name="Math101", teacher=self.teacher)
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "course": "Math101",
            "new_course": "Invalid Name!",
            "teacher": self.teacher.username,
        }

        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Not allowed name.")

    def test_update_duplicate_course_name_returns_error(self):
        self._create_course(name="ExistingCourse", teacher=self.teacher)
        course = self._create_course(name="OriginalCourse", teacher=self.teacher)
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "course": "OriginalCourse",
            "new_course": "existingcourse",
            "teacher": self.teacher.username,
        }

        response = self.client.put(self.url, payload, format="json")

        course.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Course exists.")
        self.assertEqual(course.name, "OriginalCourse")

    def test_update_with_nonexistent_teacher_returns_not_found(self):
        self._create_course(name="History101", teacher=self.teacher)
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "course": "History101",
            "new_course": "History102",
            "teacher": "unknown_teacher",
        }

        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "User not found.")

    def test_update_with_missing_course_returns_not_found(self):
        self.client.force_authenticate(user=self.teacher)
        payload = {
            "course": "NonExistingCourse",
            "new_course": "AnyCourse",
            "teacher": self.teacher.username,
        }

        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Course not found.")

    def test_teacher_can_delete_own_course(self):
        course = self._create_course(name="DeleteMe", teacher=self.teacher)
        self.client.force_authenticate(user=self.teacher)

        response = self.client.delete(self.url, {"course": "DeleteMe"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertFalse(Courses.objects.filter(pk=course.pk).exists())

    def test_admin_can_delete_course(self):
        course = self._create_course(name="AdminDelete", teacher=self.teacher)
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url, {"course": "AdminDelete"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertFalse(Courses.objects.filter(pk=course.pk).exists())

    def test_teacher_cannot_delete_other_course(self):
        course = self._create_course(name="NotYours", teacher=self.another_teacher)
        self.client.force_authenticate(user=self.teacher)

        response = self.client.delete(self.url, {"course": "NotYours"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")
        self.assertTrue(Courses.objects.filter(pk=course.pk).exists())

    def test_student_cannot_delete_course(self):
        course = self._create_course(name="StudentNope", teacher=self.teacher)
        self.client.force_authenticate(user=self.student)

        response = self.client.delete(self.url, {"course": "StudentNope"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")
        self.assertTrue(Courses.objects.filter(pk=course.pk).exists())

    def test_delete_missing_course_returns_not_found(self):
        self.client.force_authenticate(user=self.teacher)

        response = self.client.delete(self.url, {"course": "UnknownCourse"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Course not found.")

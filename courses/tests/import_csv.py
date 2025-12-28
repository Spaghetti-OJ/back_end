import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Batch_imports, Course_members, Courses
from user.models import UserProfile

User = get_user_model()


class CourseImportCSVAPITestCase(APITestCase):
    import_url_name = "courses:import_csv:import_csv"

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

    def _create_course(self, *, name=None, teacher=None, student_limit=None):
        return Courses.objects.create(
            name=name or f"Course_{self.unique}",
            teacher_id=teacher or self.teacher,
            student_limit=student_limit,
        )

    def _import_url(self, course_id):
        return reverse(self.import_url_name, kwargs={"course_id": course_id})

    def _build_csv(self, rows):
        header = "username,email,real_name,student_id,password\n"
        body = "\n".join(rows)
        return f"{header}{body}".encode("utf-8")

    def test_import_existing_student_without_force_does_not_update(self):
        course = self._create_course(name="NoForceCourse", teacher=self.teacher)
        profile = UserProfile.objects.get_or_create(user=self.student)[0]
        profile.student_id = f"OLD{self.unique}"
        profile.save(update_fields=["student_id"])
        self.student.real_name = "Original Name"
        self.student.save(update_fields=["real_name"])

        payload = self._build_csv(
            [
                f"{self.student.username},{self.student.email},New Name,NEW{self.unique},",
            ]
        )
        upload = SimpleUploadedFile("students.csv", payload, content_type="text/csv")

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self._import_url(course.id),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["data"]["import"]
        self.assertTrue(result["importResult"])
        self.assertEqual(result["newMembers"], 1)
        self.assertEqual(result["createdUsers"], 0)

        course.refresh_from_db()
        self.student.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(course.student_count, 1)
        self.assertEqual(self.student.real_name, "Original Name")
        self.assertEqual(profile.student_id, f"OLD{self.unique}")

    def test_import_existing_student_with_force_updates_info(self):
        course = self._create_course(name="ForceCourse", teacher=self.teacher)
        profile = UserProfile.objects.get_or_create(user=self.student)[0]
        profile.student_id = f"OLD{self.unique}"
        profile.save(update_fields=["student_id"])
        self.student.real_name = "Old Name"
        self.student.save(update_fields=["real_name"])

        payload = self._build_csv(
            [
                f"{self.student.username},{self.student.email},New Forced Name,NEW{self.unique},",
            ]
        )
        upload = SimpleUploadedFile("students.csv", payload, content_type="text/csv")

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self._import_url(course.id),
            {"file": upload, "force": 1},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["data"]["import"]
        self.assertTrue(result["importResult"])
        self.assertEqual(result["newMembers"], 1)
        self.assertEqual(result["createdUsers"], 0)

        course.refresh_from_db()
        self.student.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(course.student_count, 1)
        self.assertEqual(self.student.real_name, "New Forced Name")
        self.assertEqual(profile.student_id, f"NEW{self.unique}")

    def test_teacher_can_import_students_from_csv(self):
        course = self._create_course(name="ImportableCourse", teacher=self.teacher)
        payload = self._build_csv(
            [
                f"stu_{self.unique}1,stu_{self.unique}1@example.com,Student One,SID{self.unique}1,password1",
                f"stu_{self.unique}2,stu_{self.unique}2@example.com,Student Two,,",
            ]
        )
        upload = SimpleUploadedFile("students.csv", payload, content_type="text/csv")

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self._import_url(course.id),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertEqual(response.data["data"]["import"]["errorCount"], 0)
        self.assertTrue(response.data["data"]["import"]["importResult"])
        self.assertEqual(response.data["data"]["import"]["newMembers"], 2)
        course.refresh_from_db()
        self.assertEqual(course.student_count, 2)

        members = Course_members.objects.filter(course_id=course, role=Course_members.Role.STUDENT)
        self.assertEqual(members.count(), 2)
        created_usernames = set(members.values_list("user_id__username", flat=True))
        self.assertIn(f"stu_{self.unique}1", created_usernames)
        self.assertIn(f"stu_{self.unique}2", created_usernames)

        profile = UserProfile.objects.get(user__username=f"stu_{self.unique}1")
        self.assertTrue(profile.student_id.startswith("SID"))

        batch = Batch_imports.objects.first()
        self.assertIsNotNone(batch)
        self.assertEqual(batch.status, Batch_imports.Status.COMPLETED)
        self.assertTrue(batch.import_result)
        self.assertIsNone(batch.error_log)

    def test_import_without_password_generates_random_password(self):
        course = self._create_course(name="NoPasswordCourse", teacher=self.teacher)
        username = f"nopass_{self.unique}"
        payload = self._build_csv(
            [
                f"{username},{username}@example.com,No Pass Student,,",
            ]
        )
        upload = SimpleUploadedFile("students.csv", payload, content_type="text/csv")

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self._import_url(course.id),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        import_result = response.data["data"]["import"]
        self.assertTrue(import_result["importResult"])
        self.assertEqual(import_result["newMembers"], 1)

        user = User.objects.get(username=username)
        self.assertTrue(user.has_usable_password())
        course.refresh_from_db()
        self.assertEqual(course.student_count, 1)

    def test_rejects_non_teacher_or_admin(self):
        course = self._create_course(name="RestrictedCourse", teacher=self.teacher)
        payload = self._build_csv([f"someone,{self.unique}@example.com,Name,,"])
        upload = SimpleUploadedFile("students.csv", payload, content_type="text/csv")

        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            self._import_url(course.id),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Forbidden.")
        self.assertEqual(Batch_imports.objects.count(), 0)

    def test_course_full_blocks_import(self):
        course = self._create_course(
            name="FullCourse",
            teacher=self.teacher,
            student_limit=1,
        )
        Course_members.objects.create(
            course_id=course,
            user_id=self.student,
            role=Course_members.Role.STUDENT,
        )
        course.student_count = 1
        course.save(update_fields=["student_count"])

        payload = self._build_csv([f"another_{self.unique},another_{self.unique}@ex.com,Another Name,,"])
        upload = SimpleUploadedFile("students.csv", payload, content_type="text/csv")

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self._import_url(course.id),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Course is full.")
        self.assertEqual(Batch_imports.objects.count(), 0)

    def test_import_reports_errors_for_conflicts(self):
        course = self._create_course(name="ErrorCourse", teacher=self.teacher)
        conflict_user = User.objects.create_user(
            username=f"teacher_conflict_{self.unique}",
            email=f"teacher_conflict_{self.unique}@example.com",
            password="pass1234",
            real_name="Existing Teacher",
            identity="teacher",
        )

        payload = self._build_csv(
            [
                f"valid_{self.unique},valid_{self.unique}@example.com,Valid Student,,",
                f"{conflict_user.username},{conflict_user.email},Wrong Role,,",
            ]
        )
        upload = SimpleUploadedFile("students.csv", payload, content_type="text/csv")

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self._import_url(course.id),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        import_result = response.data["data"]["import"]
        self.assertFalse(import_result["importResult"])
        self.assertEqual(import_result["newMembers"], 1)
        self.assertEqual(import_result["errorCount"], 1)
        self.assertEqual(import_result["errors"][0]["row"], 3)

        batch = Batch_imports.objects.latest("created_at")
        self.assertEqual(batch.status, Batch_imports.Status.COMPLETED)
        self.assertFalse(batch.import_result)
        self.assertEqual(len(batch.error_log), 1)

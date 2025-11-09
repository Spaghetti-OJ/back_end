import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Announcements, Courses, Course_members

User = get_user_model()


class CourseAnnouncementAPITestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher_sys",
            email="teacher@ann.com",
            password="pass1234",
            real_name="Teacher Ann",
            identity="teacher",
        )
        self.course = Courses.objects.create(name="SysCourse", teacher_id=self.teacher)
        self.url = lambda course_id=None: reverse(
            "system_announcements:course",
            kwargs={"course_id": course_id or self.course.id},
        )

    def _create_announcement(self, *, course=None, **overrides):
        defaults = {
            "title": "Announcement",
            "content": "Content",
            "course_id": course or self.course,
            "creator_id": self.teacher,
            "is_pinned": False,
        }
        defaults.update(overrides)
        return Announcements.objects.create(**defaults)

    def test_requires_authentication(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lists_pinned_first_then_latest(self):
        now = timezone.now()
        pinned = self._create_announcement(title="Pinned", is_pinned=True)
        latest = self._create_announcement(title="Latest")
        oldest = self._create_announcement(title="Old")

        Announcements.objects.filter(pk=latest.pk).update(
            updated_at=now - timedelta(hours=1)
        )
        Announcements.objects.filter(pk=oldest.pk).update(
            updated_at=now - timedelta(days=1)
        )
        latest.refresh_from_db()
        oldest.refresh_from_db()

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item["title"] for item in response.data["data"]]
        self.assertEqual(titles, ["Pinned", "Latest", "Old"])
        first = response.data["data"][0]
        self.assertEqual(first["title"], "Pinned")
        self.assertTrue(first["pinned"])
        self.assertIsInstance(first["createTime"], int)
        self.assertIsInstance(first["updateTime"], int)
        self.assertEqual(first["creator"]["username"], self.teacher.username)
        self.assertEqual(first["markdown"], pinned.content)

    def test_creator_nullable(self):
        self._create_announcement(title="No Owner", creator_id=None)

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["data"][0]
        self.assertIsNone(payload["creator"])
        self.assertIsNone(payload["updater"])

    def test_nonexistent_course_returns_404(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url(course_id=uuid.uuid4()))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Course not found.")

    def test_public_discussion_course_id_behaves_like_system_announcements(self):
        public_course = Courses.objects.create(name="公開討論區", teacher_id=self.teacher)
        pinned = self._create_announcement(
            course=public_course, title="Public Pinned", is_pinned=True
        )
        latest = self._create_announcement(
            course=public_course, title="Public Latest"
        )

        Announcements.objects.filter(pk=latest.pk).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        latest.refresh_from_db()

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url(course_id=public_course.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item["title"] for item in response.data["data"]]
        self.assertEqual(titles, ["Public Pinned", "Public Latest"])
        self.assertEqual(response.data["data"][0]["markdown"], pinned.content)


class AnnouncementCreateAPITestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="create_teacher",
            email="create_teacher@example.com",
            password="pass1234",
            real_name="Create Teacher",
            identity="teacher",
        )
        self.admin = User.objects.create_user(
            username="create_admin",
            email="create_admin@example.com",
            password="pass1234",
            real_name="Create Admin",
            identity="admin",
        )
        self.ta = User.objects.create_user(
            username="create_ta",
            email="create_ta@example.com",
            password="pass1234",
            real_name="Create TA",
            identity="teacher",
        )
        self.student = User.objects.create_user(
            username="create_student",
            email="create_student@example.com",
            password="pass1234",
            real_name="Create Student",
            identity="student",
        )

        self.course = Courses.objects.create(name="CreateCourse", teacher_id=self.teacher)
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.ta,
            role=Course_members.Role.TA,
        )
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.student,
            role=Course_members.Role.STUDENT,
        )
        self.url = reverse("system_announcements:create")

    def test_requires_authentication(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_can_create_announcement(self):
        self.client.force_authenticate(self.teacher)

        payload = {
            "title": "New Announcement",
            "content": "Important update",
            "course_id": str(self.course.id),
            "is_pinned": True,
        }
        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        self.assertTrue(
            Announcements.objects.filter(title="New Announcement", course_id=self.course).exists()
        )

    def test_ta_can_create_announcement(self):
        self.client.force_authenticate(self.ta)

        payload = {
            "title": "TA Update",
            "content": "TA note",
            "course_id": str(self.course.id),
        }
        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ta_announcement = Announcements.objects.get(title="TA Update")
        self.assertEqual(response.data["data"]["id"], str(ta_announcement.id))

    def test_student_cannot_create_announcement(self):
        self.client.force_authenticate(self.student)

        payload = {
            "title": "Student Update",
            "content": "Student note",
            "course_id": str(self.course.id),
        }
        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Permission denied.")

    def test_admin_can_create_even_without_membership(self):
        self.client.force_authenticate(self.admin)

        payload = {
            "title": "Admin Announcement",
            "content": "Admin note",
            "course_id": str(self.course.id),
        }
        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_payload_returns_400(self):
        self.client.force_authenticate(self.teacher)

        payload = {"course_id": str(self.course.id)}
        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation error.")
class CourseAnnouncementDetailAPITestCase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher_detail",
            email="detail@ann.com",
            password="pass1234",
            real_name="Detail Teacher",
            identity="teacher",
        )
        self.course = Courses.objects.create(name="DetailCourse", teacher_id=self.teacher)
        self.url = lambda course_id=None, ann_id=None: reverse(
            "system_announcements:announcement",
            kwargs={
                "course_id": course_id or self.course.id,
                "ann_id": ann_id,
            },
        )

    def _create_announcement(self, *, course=None, **overrides):
        defaults = {
            "title": "Announcement Detail",
            "content": "Detail Content",
            "course_id": course or self.course,
            "creator_id": self.teacher,
            "is_pinned": False,
        }
        defaults.update(overrides)
        return Announcements.objects.create(**defaults)

    def test_requires_authentication(self):
        announcement = self._create_announcement()

        response = self.client.get(self.url(ann_id=announcement.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_single_announcement_payload(self):
        announcement = self._create_announcement(is_pinned=True)

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url(ann_id=announcement.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["data"][0]
        self.assertEqual(payload["annId"], str(announcement.id))
        self.assertEqual(payload["title"], announcement.title)
        self.assertTrue(payload["pinned"])
        self.assertEqual(payload["creator"]["username"], self.teacher.username)
        self.assertEqual(payload["markdown"], announcement.content)

    def test_nonexistent_course_returns_404(self):
        announcement = self._create_announcement()

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(
            self.url(course_id=uuid.uuid4(), ann_id=announcement.id)
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Course not found.")

    def test_nonexistent_announcement_returns_404(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url(ann_id=999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Announcement not found.")

    def test_public_discussion_course_returns_announcement(self):
        public_course = Courses.objects.create(name="公開討論區", teacher_id=self.teacher)
        announcement = self._create_announcement(course=public_course, title="Public")

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(
            self.url(course_id=public_course.id, ann_id=announcement.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"][0]["title"], "Public")

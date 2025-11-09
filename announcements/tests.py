import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Announcements, Courses

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

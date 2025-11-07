from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Announcements, Courses

User = get_user_model()


class SystemAnnouncementAPITestCase(APITestCase):
    def setUp(self):
        self.url = reverse("system_announcements:list")
        self.teacher = User.objects.create_user(
            username="teacher_sys",
            email="teacher@ann.com",
            password="pass1234",
            real_name="Teacher Ann",
            identity="teacher",
        )
        self.course = Courses.objects.create(name="SysCourse", teacher_id=self.teacher)

    def _create_announcement(self, **overrides):
        defaults = {
            "title": "Announcement",
            "content": "Content",
            "course_id": self.course,
            "creator_id": self.teacher,
            "is_pinned": False,
        }
        defaults.update(overrides)
        return Announcements.objects.create(**defaults)

    def test_lists_pinned_first_then_latest(self):
        now = timezone.now()
        pinned = self._create_announcement(title="Pinned", is_pinned=True)
        latest = self._create_announcement(title="Latest")
        oldest = self._create_announcement(title="Old")

        Announcements.objects.filter(pk=latest.pk).update(updated_at=now - timedelta(hours=1))
        Announcements.objects.filter(pk=oldest.pk).update(updated_at=now - timedelta(days=1))
        latest.refresh_from_db()
        oldest.refresh_from_db()

        response = self.client.get(self.url)

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

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["data"][0]
        self.assertIsNone(payload["creator"])
        self.assertIsNone(payload["updater"])

# assignments/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from assignments.models import Assignments
from courses.models import Courses, Course_members

User = get_user_model()

HOMEWORK_BASE = "/homework/"
COURSE_LIST = "/homework/course/{course_id}/"


def epoch(days=0):
    """回傳 epoch 秒（方便用作 start/end）"""
    return int((timezone.now() + timezone.timedelta(days=days)).timestamp())


class AssignmentsAPITests(TestCase):
    """
    測試 5 支 API：
      - POST   /homework/
      - GET    /homework/<homework_id>
      - PUT    /homework/<homework_id>
      - DELETE /homework/<homework_id>
      - GET    /course/<uuid:course_id>/homework
    """

    # ---------- 測試前置 ----------
    def setUp(self):
        # 注意：你的 User.email 有 unique=True，所以一定要給不同的 email
        self.teacher = User.objects.create_user(
            username="t1", email="t1@example.com", password="x"
        )
        self.ta = User.objects.create_user(
            username="ta1", email="ta1@example.com", password="x"
        )
        self.student = User.objects.create_user(
            username="s1", email="s1@example.com", password="x"
        )

        # 建立課程（欄位名為 teacher_id，是指向 User 的 FK）
        self.course = Courses.objects.create(
            name="人工智慧導論",
            description="",
            teacher_id=self.teacher,
            student_limit=60,
            semester="上學期",
            academic_year="2025",
            is_active=True,
        )

        # 加入課程成員
        Course_members.objects.create(
            course_id=self.course, user_id=self.ta, role=Course_members.Role.TA
        )
        Course_members.objects.create(
            course_id=self.course, user_id=self.student, role=Course_members.Role.STUDENT
        )

        # 三種已認證的 client（使用 Simple JWT）
        self.as_teacher = self._auth_client(self.teacher)
        self.as_ta = self._auth_client(self.ta)
        self.as_student = self._auth_client(self.student)

    # ---------- helpers ----------
    def _auth_client(self, user):
        client = APIClient()
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def _create_hw(self, name="HW1"):
        payload = {"name": name, "course_id": str(self.course.id)}
        res = self.as_teacher.post(HOMEWORK_BASE, payload, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        return Assignments.objects.get(course=self.course, title=name)

    # ---------- POST /homework/ ----------
    def test_create_homework_success_by_teacher(self):
        payload = {
            "name": "HW1",
            "course_id": str(self.course.id),
            "markdown": "說明",
            "start": epoch(0),
            "end": epoch(7),
            "problem_ids": [],
        }
        res = self.as_teacher.post(HOMEWORK_BASE, payload, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, "Add homework Success")
        self.assertTrue(Assignments.objects.filter(course=self.course, title="HW1").exists())

    def test_create_homework_success_by_ta(self):
        payload = {"name": "HW1", "course_id": str(self.course.id)}
        res = self.as_ta.post(HOMEWORK_BASE, payload, format="json")
        self.assertEqual(res.status_code, 200)

    def test_create_homework_forbidden_for_student(self):
        payload = {"name": "HW1", "course_id": str(self.course.id)}
        res = self.as_student.post(HOMEWORK_BASE, payload, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertIn("teacher or ta", str(res.data).lower())

    def test_create_homework_duplicate_name_in_same_course(self):
        self._create_hw("HW1")
        res = self.as_teacher.post(
            HOMEWORK_BASE, {"name": "HW1", "course_id": str(self.course.id)}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data, "homework exists in this course")

    def test_create_homework_course_not_exists(self):
        import uuid
        payload = {"name": "HW1", "course_id": str(uuid.uuid4())}
        res = self.as_teacher.post(HOMEWORK_BASE, payload, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data.get("course_id"), "course not exists")

    def test_create_homework_end_before_start(self):
        payload = {"name": "HW1", "course_id": str(self.course.id), "start": epoch(7), "end": epoch(0)}
        res = self.as_teacher.post(HOMEWORK_BASE, payload, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("end", res.data)

    # ---------- GET /homework/<id> ----------
    def test_get_homework_detail(self):
        hw = self._create_hw("HW1")
        res = self.as_student.get(f"{HOMEWORK_BASE}{hw.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["message"], "get homework")
        self.assertEqual(res.data["name"], "HW1")
        self.assertIn("problemIds", res.data)

    def test_get_homework_not_found(self):
        res = self.as_student.get(f"{HOMEWORK_BASE}999999")
        self.assertEqual(res.status_code, 404)

    # ---------- PUT /homework/<id> ----------
    def test_update_homework_success(self):
        hw = self._create_hw("HW1")
        res = self.as_teacher.put(f"{HOMEWORK_BASE}{hw.id}", {"name": "HW1-Updated"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, "Update homework Success")
        hw.refresh_from_db()
        self.assertEqual(hw.title, "HW1-Updated")

    def test_update_homework_forbidden_for_student(self):
        hw = self._create_hw("HW1")
        res = self.as_student.put(f"{HOMEWORK_BASE}{hw.id}", {"name": "X"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_update_homework_duplicate_name(self):
        self._create_hw("HW1")
        hw2 = self._create_hw("HW2")
        res = self.as_teacher.put(
            f"{HOMEWORK_BASE}{hw2.id}",
            {"name": "HW1", "course_id": str(self.course.id)},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data, "homework exists in this course")

    # ---------- DELETE /homework/<id> ----------
    def test_delete_homework_success(self):
        hw = self._create_hw("HW1")
        res = self.as_teacher.delete(f"{HOMEWORK_BASE}{hw.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, "Delete homework Success")
        self.assertFalse(Assignments.objects.filter(pk=hw.id).exists())

    def test_delete_homework_forbidden_for_student(self):
        hw = self._create_hw("HW1")
        res = self.as_student.delete(f"{HOMEWORK_BASE}{hw.id}")
        self.assertEqual(res.status_code, 403)

    # ---------- GET /course/<course_id>/homework ----------
    def test_list_homeworks_by_course(self):
        self._create_hw("HW1")
        self._create_hw("HW2")
        url = COURSE_LIST.format(course_id=str(self.course.id))
        res = self.as_student.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["message"], "get homeworks")
        names = [it["name"] for it in res.data["items"]]
        self.assertSetEqual(set(names), {"HW1", "HW2"})

    def test_list_homeworks_course_not_exists(self):
        import uuid
        url = COURSE_LIST.format(course_id=str(uuid.uuid4()))
        res = self.as_student.get(url)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data, "course not exists")

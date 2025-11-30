from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from problems.models import Problems
from submissions.models import Submission
from ..models import Course_members, Courses

User = get_user_model()


class CourseScoreboardAPITestCase(APITestCase):
    url_name = "courses:scoreboard:detail"

    def setUp(self):
        super().setUp()
        self.client.defaults["HTTP_HOST"] = "127.0.0.1"
        self.teacher = User.objects.create_user(
            username="sb_teacher",
            email="sb_teacher@example.com",
            password="pass1234",
            real_name="Teacher Scoreboard",
            identity="teacher",
        )
        self.ta_user = User.objects.create_user(
            username="sb_ta",
            email="sb_ta@example.com",
            password="pass1234",
            real_name="TA Scoreboard",
            identity="student",
        )
        self.admin = User.objects.create_user(
            username="sb_admin",
            email="sb_admin@example.com",
            password="pass1234",
            real_name="Admin Scoreboard",
            identity="admin",
        )
        self.other_teacher = User.objects.create_user(
            username="sb_other_teacher",
            email="sb_other_teacher@example.com",
            password="pass1234",
            real_name="Other Teacher",
            identity="teacher",
        )
        self.student_one = User.objects.create_user(
            username="sb_student_one",
            email="sb_student_one@example.com",
            password="pass1234",
            real_name="Student One",
            identity="student",
        )
        self.student_two = User.objects.create_user(
            username="sb_student_two",
            email="sb_student_two@example.com",
            password="pass1234",
            real_name="Student Two",
            identity="student",
        )
        self.outsider = User.objects.create_user(
            username="sb_outsider",
            email="sb_outsider@example.com",
            password="pass1234",
            real_name="Outsider",
            identity="student",
        )

        self.course = Courses.objects.create(
            name="Scoreboard 101",
            description="Scoreboard course",
            teacher_id=self.teacher,
        )
        self.other_course = Courses.objects.create(
            name="Other Course",
            description="Other",
            teacher_id=self.teacher,
        )

        Course_members.objects.create(
            course_id=self.course,
            user_id=self.student_one,
            role=Course_members.Role.STUDENT,
        )
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.student_two,
            role=Course_members.Role.STUDENT,
        )
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.ta_user,
            role=Course_members.Role.TA,
        )

        self.problem1 = Problems.objects.create(
            title="Problem 1",
            description="desc",
            creator_id=self.teacher,
            course_id=self.course,
        )
        self.problem2 = Problems.objects.create(
            title="Problem 2",
            description="desc",
            creator_id=self.teacher,
            course_id=self.course,
        )
        self.other_problem = Problems.objects.create(
            title="Problem 3",
            description="other course",
            creator_id=self.teacher,
            course_id=self.other_course,
        )

        now = timezone.now()
        early = now - timedelta(hours=2)
        start_cutoff = now - timedelta(hours=1, minutes=30)
        late = now - timedelta(hours=1)

        Submission.objects.create(
            problem_id=self.problem1.id,
            user=self.student_one,
            language_type=2,
            source_code="print(1)",
            score=90,
            created_at=early,
        )
        Submission.objects.create(
            problem_id=self.problem1.id,
            user=self.student_one,
            language_type=2,
            source_code="print(2)",
            score=40,
            created_at=late,
        )
        Submission.objects.create(
            problem_id=self.problem1.id,
            user=self.student_two,
            language_type=2,
            source_code="print(3)",
            score=100,
            created_at=late,
        )
        Submission.objects.create(
            problem_id=self.problem2.id,
            user=self.student_one,
            language_type=2,
            source_code="print(4)",
            score=30,
            created_at=start_cutoff,
        )
        Submission.objects.create(
            problem_id=self.other_problem.id,
            user=self.student_one,
            language_type=2,
            source_code="print(5)",
            score=80,
            created_at=late,
        )

        self.start_cutoff_ts = start_cutoff.timestamp()

    def _url(self, course_id, pids=None, **params):
        url = reverse(self.url_name, kwargs={"course_id": course_id})
        query = []
        if pids:
            query.append("pids=" + ",".join(str(pid) for pid in pids))
        for key, value in params.items():
            query.append(f"{key}={value}")
        if query:
            return f"{url}?{'&'.join(query)}"
        return url

    @staticmethod
    def _payload(response):
        return response.data.get("data", response.data)

    def test_requires_authentication(self):
        response = self.client.get(
            self._url(self.course.id, pids=[self.problem1.id, self.problem2.id])
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_denied_for_student(self):
        self.client.force_authenticate(self.student_one)

        response = self.client.get(
            self._url(self.course.id, pids=[self.problem1.id, self.problem2.id])
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Permission denied")

    def test_permission_denied_for_teacher_not_in_course(self):
        self.client.force_authenticate(self.other_teacher)

        response = self.client.get(
            self._url(self.course.id, pids=[self.problem1.id, self.problem2.id])
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Permission denied")

    def test_ta_can_view_scoreboard(self):
        self.client.force_authenticate(self.ta_user)

        response = self.client.get(
            self._url(self.course.id, pids=[self.problem1.id, self.problem2.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")

    def test_admin_can_view_scoreboard(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            self._url(self.course.id, pids=[self.problem1.id, self.problem2.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")

    def test_invalid_pids_returns_400(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get(self._url(self.course.id, pids=["abc"]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["message"], "Error occurred when parsing `pids`."
        )

    def test_invalid_start_returns_400(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get(
            self._url(self.course.id, pids=[self.problem1.id], start="not-a-number")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Type of `start` should be float.")

    def test_scoreboard_success_for_teacher(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get(
            self._url(self.course.id, pids=[self.problem1.id, self.problem2.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        payload = self._payload(response)
        self.assertEqual(payload["courseId"], self.course.id)
        self.assertEqual(payload["problemIds"], [self.problem1.id, self.problem2.id])

        students = {item["userId"]: item for item in payload["students"]}
        self.assertEqual(len(students), 2)
        self.assertEqual(students[self.student_one.id]["totalScore"], 120)
        self.assertEqual(students[self.student_one.id]["submittedCount"], 2)
        self.assertEqual(students[self.student_two.id]["totalScore"], 100)
        self.assertEqual(students[self.student_two.id]["submittedCount"], 1)

        stats = {item["problemId"]: item for item in payload["problemStats"]}
        self.assertEqual(stats[self.problem1.id]["maxScore"], 100)
        self.assertEqual(stats[self.problem1.id]["averageScore"], 95.0)
        self.assertEqual(stats[self.problem1.id]["submissionCount"], 3)
        self.assertEqual(stats[self.problem1.id]["submitterCount"], 2)
        self.assertEqual(stats[self.problem2.id]["maxScore"], 30)
        self.assertEqual(stats[self.problem2.id]["averageScore"], 30.0)
        self.assertEqual(stats[self.problem2.id]["submissionCount"], 1)
        self.assertEqual(stats[self.problem2.id]["submitterCount"], 1)

    def test_start_filter_limits_scores(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get(
            self._url(
                self.course.id,
                pids=[self.problem1.id, self.problem2.id],
                start=self.start_cutoff_ts,
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = self._payload(response)
        students = {item["userId"]: item for item in payload["students"]}
        self.assertEqual(students[self.student_one.id]["totalScore"], 70)
        stats = {item["problemId"]: item for item in payload["problemStats"]}
        self.assertEqual(stats[self.problem1.id]["averageScore"], 70.0)

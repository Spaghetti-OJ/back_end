import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import CourseGrade, Course_members, Courses

User = get_user_model()


class CourseGradeViewTests(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher01",
            email="teacher01@example.com",
            password="pass1234",
            real_name="Teacher One",
            identity="teacher",
        )
        self.admin = User.objects.create_user(
            username="admin01",
            email="admin01@example.com",
            password="pass1234",
            real_name="Admin One",
            identity="admin",
        )
        self.student = User.objects.create_user(
            username="student01",
            email="student01@example.com",
            password="pass1234",
            real_name="Student One",
            identity="student",
        )
        self.another_student = User.objects.create_user(
            username="student02",
            email="student02@example.com",
            password="pass1234",
            real_name="Student Two",
            identity="student",
        )
        self.outsider = User.objects.create_user(
            username="student03",
            email="student03@example.com",
            password="pass1234",
            real_name="Student Three",
            identity="student",
        )
        self.ta_user = User.objects.create_user(
            username="assistant01",
            email="assistant01@example.com",
            password="pass1234",
            real_name="Assistant One",
            identity="student",
        )

        self.course = Courses.objects.create(name="Algorithms101", teacher_id=self.teacher)
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.student,
            role=Course_members.Role.STUDENT,
        )
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.another_student,
            role=Course_members.Role.STUDENT,
        )
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.ta_user,
            role=Course_members.Role.TA,
        )
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.admin,
            role=Course_members.Role.TEACHER,
        )

        CourseGrade.objects.create(
            course=self.course,
            student=self.student,
            title="Quiz 1",
            content="Intro quiz",
            score=80,
        )
        CourseGrade.objects.create(
            course=self.course,
            student=self.student,
            title="Midterm",
            content="Midterm exam",
            score=95,
        )

    def test_student_can_view_own_grades(self):
        self.client.force_authenticate(self.student)

        response = self.client.get(self._url(self.course, self.student))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertEqual(len(response.data["grades"]), 2)
        self.assertEqual(response.data["grades"][0]["title"], "Midterm")

    def test_teacher_can_view_student_grades(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get(self._url(self.course, self.student))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["grades"]), 2)

    def test_student_cannot_view_other_student_grades(self):
        self.client.force_authenticate(self.student)

        response = self.client.get(self._url(self.course, self.another_student))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You can only view your score.")

    def test_non_member_cannot_view_course_grades(self):
        self.client.force_authenticate(self.outsider)

        response = self.client.get(self._url(self.course, self.student))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You are not in this course.")

    def test_returns_not_found_when_student_not_in_course(self):
        student = User.objects.create_user(
            username="student04",
            email="student04@example.com",
            password="pass1234",
            real_name="Student Four",
            identity="student",
        )
        self.client.force_authenticate(self.teacher)

        response = self.client.get(self._url(self.course, student))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "The student is not in the course.")

    def test_returns_not_found_when_course_missing(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get(self._url(uuid.uuid4(), self.student))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Course not found.")

    def test_requires_authentication(self):
        response = self.client.get(self._url(self.course, self.student))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_can_create_grade(self):
        self.client.force_authenticate(self.teacher)

        payload = {"title": "Final", "content": "Final exam", "score": 88}
        response = self.client.post(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertTrue(
            CourseGrade.objects.filter(
                course=self.course, student=self.student, title="Final"
            ).exists()
        )

    def test_ta_can_create_grade_with_letter_score(self):
        self.client.force_authenticate(self.ta_user)

        payload = {"title": "Lab 1", "content": "Lab grading", "score": "A+"}
        response = self.client.post(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        grade = CourseGrade.objects.get(
            course=self.course,
            student=self.student,
            title="Lab 1",
        )
        self.assertEqual(grade.score, "A+")

    def test_admin_member_can_create_grade(self):
        self.client.force_authenticate(self.admin)

        payload = {"title": "Project", "content": "Project score", "score": 100}
        response = self.client.post(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            CourseGrade.objects.filter(
                course=self.course, student=self.student, title="Project"
            ).exists()
        )

    def test_student_cannot_create_grade(self):
        self.client.force_authenticate(self.student)

        payload = {"title": "Quiz 3", "content": "", "score": 70}
        response = self.client.post(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You can only view your score.")

    def test_non_member_cannot_create_grade(self):
        self.client.force_authenticate(self.outsider)

        payload = {"title": "Quiz 3", "content": "", "score": 70}
        response = self.client.post(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You are not in this course.")

    def test_duplicate_title_returns_bad_request(self):
        self.client.force_authenticate(self.teacher)

        payload = {"title": "Midterm", "content": "", "score": 96}
        response = self.client.post(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "This title is taken.")

    def test_teacher_can_update_grade_with_new_title(self):
        self.client.force_authenticate(self.teacher)

        payload = {
            "title": "Quiz 1",
            "new_title": "Quiz 1 Updated",
            "content": "Regraded after review",
            "score": 85,
        }
        response = self.client.put(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success.")
        self.assertFalse(
            CourseGrade.objects.filter(
                course=self.course,
                student=self.student,
                title="Quiz 1",
            ).exists()
        )
        updated_grade = CourseGrade.objects.get(
            course=self.course,
            student=self.student,
            title="Quiz 1 Updated",
        )
        self.assertEqual(updated_grade.content, "Regraded after review")
        self.assertEqual(updated_grade.score, 85)

    def test_teacher_can_update_grade_without_new_title(self):
        self.client.force_authenticate(self.teacher)

        payload = {
            "title": "Midterm",
            "content": "Adjusted grading rubric",
            "score": "A-",
        }
        response = self.client.put(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        grade = CourseGrade.objects.get(
            course=self.course,
            student=self.student,
            title="Midterm",
        )
        self.assertEqual(grade.content, "Adjusted grading rubric")
        self.assertEqual(grade.score, "A-")

    def test_update_returns_bad_request_when_new_title_taken(self):
        self.client.force_authenticate(self.teacher)

        payload = {
            "title": "Quiz 1",
            "new_title": "Midterm",
            "content": "Updated",
            "score": 75,
        }
        response = self.client.put(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "This title is taken.")

    def test_student_cannot_update_grade(self):
        self.client.force_authenticate(self.student)

        payload = {
            "title": "Quiz 1",
            "content": "Trying to cheat",
            "score": 100,
        }
        response = self.client.put(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You can only view your score.")

    def test_update_missing_grade_returns_not_found(self):
        self.client.force_authenticate(self.teacher)

        payload = {
            "title": "Quiz X",
            "content": "Nonexistent",
            "score": 60,
        }
        response = self.client.put(
            self._url(self.course, self.student),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Score not found.")

    def test_post_student_not_in_course_returns_not_found(self):
        self.client.force_authenticate(self.teacher)

        payload = {"title": "Pop Quiz", "content": "", "score": 50}
        response = self.client.post(
            self._url(self.course, self.outsider),
            data=payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "The student is not in the course.")

    def test_teacher_can_delete_grade(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.delete(
            self._url(self.course, self.student),
            data={"title": "Quiz 1"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            CourseGrade.objects.filter(
                course=self.course, student=self.student, title="Quiz 1"
            ).exists()
        )

    def test_delete_requires_grading_permission(self):
        self.client.force_authenticate(self.student)

        response = self.client.delete(
            self._url(self.course, self.student),
            data={"title": "Quiz 1"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "You can only view your score.")

    def test_delete_returns_not_found_for_missing_grade(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.delete(
            self._url(self.course, self.student),
            data={"title": "Nonexistent"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Score not found.")

    def test_delete_missing_title_returns_bad_request(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.delete(
            self._url(self.course, self.student),
            data={},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "This field is required.")

    @staticmethod
    def _url(course, student):
        course_id = course.id if hasattr(course, "id") else course
        student_id = student.id if hasattr(student, "id") else student
        return reverse(
            "courses:grade:detail",
            kwargs={"course_id": course_id, "student": student_id},
        )

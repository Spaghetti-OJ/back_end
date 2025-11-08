from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Course_members, Courses, CourseGrade
from ..serializers import CourseGradeItemSerializer, CourseGradeListSerializer

User = get_user_model()


class CourseGradeView(APIView):
    """
    課程成績列表：
     - GET /course/<course_id>/grade/<student>/ 查看特定學生在課程中的成績項目
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseGradeListSerializer

    def get(self, request, course_id, student):
        course = self._get_course(course_id)
        if course is None:
            return Response(
                {"message": "Course not found."}, status=status.HTTP_404_NOT_FOUND
            )

        target_student = self._get_student(student)
        if target_student is None:
            return Response(
                {"message": "The student is not in the course."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not self._is_course_member(course, request.user):
            return Response(
                {"message": "You are not in this course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            getattr(request.user, "identity", None) == User.Identity.STUDENT
            and request.user != target_student
        ):
            return Response(
                {"message": "You can only view your score."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not self._is_student_in_course(course, target_student):
            return Response(
                {"message": "The student is not in the course."},
                status=status.HTTP_404_NOT_FOUND,
            )

        grades_qs = CourseGrade.objects.filter(
            course=course,
            student=target_student,
        ).order_by("-created_at", "-id")

        grade_data = CourseGradeItemSerializer(grades_qs, many=True).data
        payload = {"message": "Success.", "grades": grade_data}
        serializer = self.serializer_class(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def _get_course(course_id):
        try:
            return Courses.objects.get(pk=course_id)
        except Courses.DoesNotExist:
            return None

    @staticmethod
    def _get_student(student_id):
        try:
            return User.objects.get(pk=student_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def _is_course_member(course, user):
        if user is None:
            return False

        if course.teacher_id == user:
            return True

        return Course_members.objects.filter(course_id=course, user_id=user).exists()

    @staticmethod
    def _is_student_in_course(course, student):
        return Course_members.objects.filter(
            course_id=course,
            user_id=student,
            role=Course_members.Role.STUDENT,
        ).exists()

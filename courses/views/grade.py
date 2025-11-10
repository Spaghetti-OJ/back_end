from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Course_members, Courses, CourseGrade
from ..serializers import (
    CourseGradeCreateSerializer,
    CourseGradeItemSerializer,
    CourseGradeListSerializer,
)

User = get_user_model()


class CourseGradeView(APIView):
    """
    課程成績列表/新增：
     - GET /course/<course_id>/grade/<student>/ 查看特定學生在課程中的成績項目
     - POST /course/<course_id>/grade/<student>/ 新增成績（教師/助教/管理員）
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseGradeListSerializer
    create_serializer_class = CourseGradeCreateSerializer

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
        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, course_id, student):
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

        if not self._has_grading_permission(course, request.user):
            return Response(
                {"message": "You can only view your score."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not self._is_student_in_course(course, target_student):
            return Response(
                {"message": "The student is not in the course."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.create_serializer_class(
            data=request.data,
            context={"course": course, "student": target_student},
        )
        if not serializer.is_valid():
            detail = self._extract_error_detail(serializer.errors)
            message = str(detail) if detail else "Invalid data."
            return Response(
                {"message": message}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save(course=course, student=target_student)
        return Response({"message": "Success."}, status=status.HTTP_200_OK)

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

    @staticmethod
    def _has_grading_permission(course, user):
        if user is None:
            return False

        if getattr(user, "identity", None) == User.Identity.ADMIN:
            return True

        if course.teacher_id == user:
            return True

        return Course_members.objects.filter(
            course_id=course,
            user_id=user,
            role__in=(
                Course_members.Role.TA,
                Course_members.Role.TEACHER,
            ),
        ).exists()

    @classmethod
    def _extract_error_detail(cls, errors):
        from rest_framework.exceptions import ErrorDetail

        if isinstance(errors, dict):
            for value in errors.values():
                detail = cls._extract_error_detail(value)
                if detail is not None:
                    return detail
        elif isinstance(errors, list):
            for item in errors:
                detail = cls._extract_error_detail(item)
                if detail is not None:
                    return detail
        elif isinstance(errors, ErrorDetail):
            return errors
        return None

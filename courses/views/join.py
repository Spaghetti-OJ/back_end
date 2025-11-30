from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response

from ..common.responses import api_response
from ..models import Course_members, Courses
from ..serializers import CourseJoinSerializer
from .course_courseid import CourseDetailView

User = get_user_model()


class CourseJoinView(generics.GenericAPIView):
    """
    使用邀請碼加入課程：
     - POST /course/<course_id>/join
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseJoinSerializer

    def post(self, request, course_id, *args, **kwargs):
        course = CourseDetailView._get_course_or_response(course_id)
        if isinstance(course, Response):
            return course

        user = request.user
        if getattr(user, "identity", None) != User.Identity.STUDENT:
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            detail = self._extract_error_detail(serializer.errors)
            message = str(detail) if detail else "Invalid data."
            return api_response(
                message=message, status_code=status.HTTP_400_BAD_REQUEST
            )

        join_code = serializer.validated_data["join_code"]

        if course.join_code is None or join_code != course.join_code:
            return api_response(
                message="Invalid join code.", status_code=status.HTTP_400_BAD_REQUEST
            )

        is_member = course.teacher_id_id == getattr(user, "id", None) or Course_members.objects.filter(
            course_id=course,
            user_id=user,
        ).exists()
        if is_member:
            return api_response(
                message="You are already in this course.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            student_members = Course_members.objects.select_for_update().filter(
                course_id=course, role=Course_members.Role.STUDENT
            )
            current_student_count = student_members.count()
            if course.student_limit is not None and current_student_count >= course.student_limit:
                return api_response(
                    message="Course is full.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            Course_members.objects.create(
                course_id=course,
                user_id=user,
                role=Course_members.Role.STUDENT,
            )

            Courses.objects.filter(pk=course.pk).update(
                student_count=current_student_count + 1
            )

        return api_response(
            data={"course": {"id": course.id}},
            message="Success.",
            status_code=status.HTTP_200_OK,
        )

    @classmethod
    def _extract_error_detail(cls, errors):
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

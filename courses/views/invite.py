from django.db import IntegrityError
from rest_framework import permissions, status
from rest_framework.views import APIView

from ..common.responses import api_response
from ..models import Courses
from ..serializers import CourseInviteCodeSerializer


class CourseInviteCodeView(APIView):
    """
    課程邀請代碼端點：
     - POST /course/<course_id>/invite-code/ 產生課程邀請代碼（教師/管理員）
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_id):
        course = self._get_course(course_id)
        if course is None:
            return api_response(
                message="Course not found.", status_code=status.HTTP_404_NOT_FOUND
            )

        permission_error = self._check_permission(request.user, course)
        if permission_error is not None:
            return permission_error

        try:
            course.regenerate_join_code()
        except IntegrityError:
            return api_response(
                message="Failed to generate invite code.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = CourseInviteCodeSerializer(course)
        return api_response(
            data=serializer.data,
            message="Success.",
            status_code=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_course(course_id):
        try:
            return Courses.objects.get(pk=course_id)
        except (Courses.DoesNotExist, ValueError):
            return None

    @staticmethod
    def _check_permission(user, course):
        identity = getattr(user, "identity", None)
        if identity not in ("teacher", "admin"):
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )

        if identity == "teacher" and course.teacher_id != user:
            return api_response(
                message="You are not in this course.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return None

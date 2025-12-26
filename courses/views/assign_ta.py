from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..common.responses import api_response
from ..models import Course_members
from ..serializers import CourseAssignTASerializer
from .course_courseid import CourseDetailView

User = get_user_model()


class CourseAssignTAView(APIView):
    """
    分配助教權限：
     - POST /course/<course_id>/assign-ta/
    """

    serializer_class = CourseAssignTASerializer

    def post(self, request, course_id):
        course = CourseDetailView._get_course_or_response(course_id)
        if isinstance(course, Response):
            return course

        permission_error = CourseDetailView._check_edit_permission(request.user, course)
        if permission_error is not None:
            return permission_error

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            detail = self._extract_error_detail(serializer.errors)
            message = str(detail) if detail else "Invalid data."
            return api_response(
                message=message, status_code=status.HTTP_400_BAD_REQUEST
            )

        username = serializer.validated_data["username"]
        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return api_response(
                message="User not found.", status_code=status.HTTP_404_NOT_FOUND
            )

        if getattr(target_user, "identity", None) != User.Identity.STUDENT:
            return api_response(
                message="User is not a student.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        membership, _ = Course_members.objects.get_or_create(
            course_id=course,
            user_id=target_user,
            defaults={"role": Course_members.Role.TA},
        )
        if membership.role != Course_members.Role.TA:
            membership.role = Course_members.Role.TA
            membership.save(update_fields=["role"])

        return api_response(message="Success.", status_code=status.HTTP_200_OK)

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

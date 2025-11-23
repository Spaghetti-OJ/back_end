from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from ..common.responses import api_response

from ..models import Course_members, Courses
from ..serializers import CourseDetailSerializer

User = get_user_model()


class CourseDetailView(generics.GenericAPIView):
    """
    課程詳情端點：
     - GET /course/<course_id>/ 取得課程資訊與成員（需為課程成員）
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseDetailSerializer

    def get(self, request, course_id, *args, **kwargs):
        course = self._get_course_or_response(course_id)
        if isinstance(course, Response):
            return course

        user = request.user
        is_teacher = course.teacher_id_id == getattr(user, "id", None)
        members = (
            Course_members.objects.filter(course_id=course)
            .select_related("user_id")
            .order_by("joined_at")
        )
        is_member = is_teacher or any(m.user_id.id == user.id for m in members)
        if not is_member:
            return api_response(
                message="You are not in this course.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        tas = [
            membership.user_id
            for membership in members
            if membership.role == Course_members.Role.TA
        ]
        students = [
            membership.user_id
            for membership in members
            if membership.role == Course_members.Role.STUDENT
        ]

        payload = {
            "course": course,
            "teacher": course.teacher_id,
            "TAs": tas,
            "students": students,
        }
        serializer = self.get_serializer(payload)
        return api_response(
            data=serializer.data, message="Success.", status_code=status.HTTP_200_OK
        )

    def put(self, request, course_id, *args, **kwargs):
        course = self._get_course_or_response(course_id)
        if isinstance(course, Response):
            return course

        permission_error = self._check_edit_permission(request.user, course)
        if permission_error is not None:
            return permission_error

        ta_usernames = self._extract_ta_payload(request.data)
        if isinstance(ta_usernames, Response):
            return ta_usernames

        student_identifier = self._extract_student_identifier(request)

        try:
            ta_users = self._resolve_ta_users(ta_usernames)
        except ValueError as exc:
            return api_response(
                message=str(exc), status_code=status.HTTP_404_NOT_FOUND
            )

        student_membership = None
        if student_identifier:
            student_lookup = self._resolve_student_membership(course, student_identifier)
            if isinstance(student_lookup, Response):
                return student_lookup
            student_membership = student_lookup

        with transaction.atomic():
            if ta_users is not None:
                self._sync_tas(course, ta_users)
            if student_membership is not None:
                student_membership.delete()

        return api_response(message="Success.", status_code=status.HTTP_200_OK)

    @staticmethod
    def _get_course_or_response(course_id):
        try:
            return Courses.objects.select_related("teacher_id").get(id=course_id)
        except Courses.DoesNotExist:
            return api_response(
                message="Course not found.", status_code=status.HTTP_404_NOT_FOUND
            )

    @staticmethod
    def _check_edit_permission(user, course):
        identity = getattr(user, "identity", None)
        if identity not in ("teacher", "admin"):
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )
        if identity == "teacher" and course.teacher_id_id != getattr(user, "id", None):
            return api_response(
                message="You are not in this course.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return None

    @staticmethod
    def _extract_ta_payload(data):
        if not isinstance(data, dict):
            return api_response(
                message="Invalid payload.", status_code=status.HTTP_400_BAD_REQUEST
            )
        if "TAs" not in data:
            return None

        tas = data.get("TAs")
        if tas is None:
            return []
        if not isinstance(tas, list):
            return api_response(
                message="TAs must be provided as a list.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        normalized = []
        for username in tas:
            if not isinstance(username, str):
                return api_response(
                    message="TAs must be provided as usernames.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            trimmed = username.strip()
            if not trimmed:
                return api_response(
                    message="TA username cannot be blank.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            normalized.append(trimmed)
        return normalized

    @staticmethod
    def _extract_student_identifier(request):
        identifier = request.query_params.get("student")
        if identifier:
            identifier = identifier.strip()
        if not identifier and isinstance(request.data, dict):
            raw_student = request.data.get("student")
            if raw_student:
                identifier = str(raw_student).strip()
        return identifier or None

    @staticmethod
    def _resolve_ta_users(usernames):
        if usernames is None:
            return None
        if not usernames:
            return []

        users = list(User.objects.filter(username__in=usernames))
        found_usernames = {user.username for user in users}
        missing = next((name for name in usernames if name not in found_usernames), None)
        if missing:
            raise ValueError(f"User: {missing} not found.")
        return users

    @staticmethod
    def _resolve_student_membership(course, student_identifier):
        try:
            student = User.objects.get(pk=student_identifier)
        except (User.DoesNotExist, ValueError):
            return api_response(
                message="Student not found.", status_code=status.HTTP_404_NOT_FOUND
            )

        membership = Course_members.objects.filter(
            course_id=course,
            user_id=student,
            role=Course_members.Role.STUDENT,
        ).first()

        if membership is None:
            return api_response(
                message="Student not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        return membership

    @staticmethod
    def _sync_tas(course, ta_users):
        desired_ids = {user.id for user in ta_users}
        Course_members.objects.filter(
            course_id=course, role=Course_members.Role.TA
        ).exclude(user_id__in=desired_ids).delete()

        existing_memberships = Course_members.objects.filter(
            course_id=course, user_id__in=desired_ids
        )
        membership_map = {membership.user_id_id: membership for membership in existing_memberships}

        for user in ta_users:
            membership = membership_map.get(user.id)
            if membership:
                if membership.role != Course_members.Role.TA:
                    membership.role = Course_members.Role.TA
                    membership.save(update_fields=["role"])
                continue
            Course_members.objects.create(
                course_id=course,
                user_id=user,
                role=Course_members.Role.TA,
            )

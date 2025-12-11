from collections.abc import Mapping
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

        student_lists = self._extract_student_lists(request.data)
        if isinstance(student_lists, Response):
            return student_lists
        remove_ids, new_ids = student_lists

        with transaction.atomic():
            try:
                locked_course = Courses.objects.select_for_update().get(pk=course.pk)
            except Courses.DoesNotExist:
                return api_response(
                    message="Course not found.", status_code=status.HTTP_404_NOT_FOUND
                )

            student_memberships = list(
                Course_members.objects.select_for_update().filter(
                    course_id=locked_course,
                    role=Course_members.Role.STUDENT,
                )
            )
            student_membership_map = {
                str(membership.user_id_id): membership
                for membership in student_memberships
            }

            to_remove = []
            for student_id in remove_ids:
                membership = student_membership_map.get(student_id)
                if membership is None:
                    return api_response(
                        message="Student not found.",
                        status_code=status.HTTP_404_NOT_FOUND,
                    )
                to_remove.append(membership)

            new_ids_set = set(new_ids)
            existing_memberships = Course_members.objects.select_for_update().filter(
                course_id=locked_course, user_id__in=new_ids_set
            )
            existing_map = {
                str(membership.user_id_id): membership
                for membership in existing_memberships
            }
            for student_id in remove_ids:
                existing_map.pop(student_id, None)

            new_users = list(User.objects.filter(id__in=new_ids_set))
            found_ids = {str(user.id) for user in new_users}
            missing_new = next((sid for sid in new_ids_set if sid not in found_ids), None)
            if missing_new:
                return api_response(
                    message="Student not found.", status_code=status.HTTP_404_NOT_FOUND
                )

            for user in new_users:
                if getattr(user, "identity", None) != User.Identity.STUDENT:
                    return api_response(
                        message="User is not a student.",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                if str(user.id) in existing_map:
                    return api_response(
                        message="Student already in this course.",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            current_student_count = len(student_memberships)
            final_student_count = (
                current_student_count - len(to_remove) + len(new_users)
            )
            if (
                locked_course.student_limit is not None
                and final_student_count > locked_course.student_limit
            ):
                return api_response(
                    message="Course is full.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            if to_remove:
                Course_members.objects.filter(
                    pk__in=[membership.pk for membership in to_remove]
                ).delete()

            if new_users:
                Course_members.objects.bulk_create(
                    [
                        Course_members(
                            course_id=locked_course,
                            user_id=user,
                            role=Course_members.Role.STUDENT,
                        )
                        for user in new_users
                    ]
                )

            Courses.objects.filter(pk=locked_course.pk).update(
                student_count=final_student_count
            )

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
    def _extract_student_lists(data):
        if not isinstance(data, Mapping):
            return api_response(
                message="Invalid payload.", status_code=status.HTTP_400_BAD_REQUEST
            )

        remove_ids = CourseDetailView._normalize_student_id_list(data.get("remove"), "remove")
        if isinstance(remove_ids, Response):
            return remove_ids

        new_ids = CourseDetailView._normalize_student_id_list(data.get("new"), "new")
        if isinstance(new_ids, Response):
            return new_ids

        return remove_ids, new_ids

    @staticmethod
    def _normalize_student_id_list(value, field_name):
        if value is None:
            return []
        if not isinstance(value, list):
            return api_response(
                message=f"{field_name} must be provided as a list.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        normalized = []
        for raw in value:
            student_id = str(raw).strip()
            if not student_id:
                return api_response(
                    message=f"{field_name} cannot contain blank student ids.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            normalized.append(student_id)
        return normalized

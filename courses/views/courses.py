from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ErrorDetail
from ..common.responses import api_response

from ..models import Courses
from ..serializers import (
    CourseCreateSerializer,
    CourseListSerializer,
    CourseUpdateSerializer,
)


class CourseListCreateView(generics.GenericAPIView):
    """
    管理課程列表的讀寫端點：
     - GET /course/ 取得授課或加入的課程列表
     - POST /course/ 建立課程（教師/管理員）
     - PUT /course/ 編輯課程（擁有者/管理員）
     - DELETE /course/ 刪除課程（擁有者/管理員）
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CourseListSerializer
        if self.request.method == "PUT":
            return CourseUpdateSerializer
        return CourseCreateSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "identity", None) == "admin":
            return Courses.objects.select_related("teacher_id").order_by("-created_at")
        return (
            Courses.objects.select_related("teacher_id")
            .filter(Q(teacher_id=user) | Q(members__user_id=user))
            .distinct()
            .order_by("-created_at")
        )

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            data={"courses": serializer.data},
            message="Success.",
            status_code=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, "identity", None) not in ("teacher", "admin"):
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            detail = self._extract_error_detail(serializer.errors)
            message = str(detail) if detail else "Invalid data."
            error_code = getattr(detail, "code", None) if detail else None
            status_code = (
                status.HTTP_404_NOT_FOUND
                if error_code == "user_not_found"
                else status.HTTP_400_BAD_REQUEST
            )
            return api_response(message=message, status_code=status_code)

        teacher = serializer.validated_data["teacher"]
        if user.identity == "teacher" and teacher != user:
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )

        course = serializer.save()
        return api_response(
            data={"course": {"id": course.id}},
            message="Success.",
            status_code=status.HTTP_200_OK,
        )

    def put(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, "identity", None) not in ("teacher", "admin"):
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )

        raw_course_id = request.data.get("course_id")
        if isinstance(raw_course_id, str):
            course_id = raw_course_id.strip()
        elif raw_course_id is not None:
            course_id = str(raw_course_id).strip()
        else:
            course_id = ""
        if not course_id:
            return api_response(
                message="Course not found.", status_code=status.HTTP_404_NOT_FOUND
            )

        try:
            course_obj = Courses.objects.get(pk=course_id)
        except (Courses.DoesNotExist, ValueError):
            return api_response(
                message="Course not found.", status_code=status.HTTP_404_NOT_FOUND
            )

        if user.identity != "admin" and course_obj.teacher_id != user:
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )

        payload = {
            "new_course": request.data.get("new_course"),
            "teacher": request.data.get("teacher"),
        }
        serializer = self.get_serializer(instance=course_obj, data=payload)
        if not serializer.is_valid():
            detail = self._extract_error_detail(serializer.errors)
            message = str(detail) if detail else "Invalid data."
            error_code = getattr(detail, "code", None) if detail else None
            status_code = (
                status.HTTP_404_NOT_FOUND
                if error_code == "user_not_found"
                else status.HTTP_400_BAD_REQUEST
            )
            return api_response(message=message, status_code=status_code)

        serializer.save()
        return api_response(message="Success.", status_code=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, "identity", None) not in ("teacher", "admin"):
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )

        raw_course_id = request.data.get("course_id")
        if isinstance(raw_course_id, str):
            course_id = raw_course_id.strip()
        elif raw_course_id is not None:
            course_id = str(raw_course_id).strip()
        else:
            course_id = ""
        if not course_id:
            return api_response(
                message="Course not found.", status_code=status.HTTP_404_NOT_FOUND
            )

        try:
            course_obj = Courses.objects.get(pk=course_id)
        except (Courses.DoesNotExist, ValueError):
            return api_response(
                message="Course not found.", status_code=status.HTTP_404_NOT_FOUND
            )

        if user.identity != "admin" and course_obj.teacher_id != user:
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )

        course_obj.delete()
        return api_response(message="Success.", status_code=status.HTTP_200_OK)

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

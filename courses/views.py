from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response

from .models import Courses
from .serializers import CourseCreateSerializer, CourseListSerializer


class CourseView(generics.GenericAPIView):
    """
    GET /course/  — 取得課程列表
    POST /course/ — 建立課程
    """
    
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CourseListSerializer
        return CourseCreateSerializer

    def get_queryset(self):
        user = self.request.user
        return (
            Courses.objects.select_related("teacher_id")
            .filter(Q(teacher_id=user) | Q(members__user_id=user))
            .distinct()
            .order_by("-created_at")
        )

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"message": "Success.", "courses": serializer.data})

    def post(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, "identity", None) not in ("teacher", "admin"):
            return Response({"message": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            detail = self._extract_error_detail(serializer.errors)
            message = str(detail) if detail else "Invalid data."
            error_code = getattr(detail, "code", None) if detail else None
            status_code = status.HTTP_404_NOT_FOUND if error_code == "user_not_found" else status.HTTP_400_BAD_REQUEST
            return Response({"message": message}, status=status_code)

        teacher = serializer.validated_data["teacher"]
        if user.identity == "teacher" and teacher != user:
            return Response({"message": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer.save()
        return Response({"message": "Success."}, status=status.HTTP_200_OK)

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

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from courses.models import Announcements, Courses, Course_members

from .serializers import AnnouncementCreateSerializer, SystemAnnouncementSerializer


class CourseAnnouncementListView(generics.GenericAPIView):
    """
    GET /ann/<course_id>/ann - 取得指定課程公告列表。
    若 <course_id> 為「公開討論區」課程的 ID，則等同於原系統公告列表。
    """

    serializer_class = SystemAnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        course_id = kwargs.get("course_id")
        try:
            course = Courses.objects.get(pk=course_id)
        except Courses.DoesNotExist:
            return Response(
                {"message": "Course not found."}, status=status.HTTP_404_NOT_FOUND
            )

        queryset = (
            Announcements.objects.select_related("creator_id")
            .filter(course_id=course)
            .order_by("-is_pinned", "-updated_at")
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response({"data": serializer.data})


class AnnouncementCreateView(generics.GenericAPIView):
    """POST /ann/ - 建立新的課程公告。"""

    serializer_class = AnnouncementCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation error.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        course = serializer.validated_data["course_id"]
        if not self._has_grade_permission(request.user, course):
            return Response(
                {"message": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        announcement = serializer.save(creator_id=request.user)
        payload = {
            "data": {
                "id": str(announcement.id),
                "created_at": int(announcement.created_at.timestamp()),
            }
        }
        return Response(payload, status=status.HTTP_201_CREATED)

    @staticmethod
    def _has_grade_permission(user, course: Courses) -> bool:

        if getattr(user, "identity", None) == "admin":
            return True

        if course.teacher_id == user:
            return True

        return Course_members.objects.filter(
            course_id=course,
            user_id=user,
            role__in=[Course_members.Role.TEACHER, Course_members.Role.TA],
        ).exists()

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from courses.models import Announcements, Courses

from .serializers import SystemAnnouncementSerializer


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

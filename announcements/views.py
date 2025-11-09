from rest_framework import generics, permissions, status
from rest_framework.response import Response

from courses.models import Announcements, Courses

from .serializers import SystemAnnouncementSerializer


class CourseAnnouncementBaseView(generics.GenericAPIView):
    serializer_class = SystemAnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_course(self, *, course_id):
        try:
            return Courses.objects.get(pk=course_id)
        except Courses.DoesNotExist:
            return None


class CourseAnnouncementListView(CourseAnnouncementBaseView):
    """
    GET /ann/<course_id>/ann - 取得指定課程公告列表。
    若 <course_id> 為「公開討論區」課程的 ID，則等同於原系統公告列表。
    """

    def get(self, request, *args, **kwargs):
        course_id = kwargs.get("course_id")
        course = self._get_course(course_id=course_id)
        if course is None:
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


class CourseAnnouncementRetrieveView(CourseAnnouncementBaseView):
    """
    GET /ann/<course_id>/<ann_id> - 取得單一公告內容。
    """

    def get(self, request, *args, **kwargs):
        course_id = kwargs.get("course_id")
        announcement_id = kwargs.get("ann_id")

        course = self._get_course(course_id=course_id)
        if course is None:
            return Response(
                {"message": "Course not found."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            announcement = Announcements.objects.select_related("creator_id").get(
                course_id=course, pk=announcement_id
            )
        except Announcements.DoesNotExist:
            return Response(
                {"message": "Announcement not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(announcement)
        return Response({"data": [serializer.data]})

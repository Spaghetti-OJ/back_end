from rest_framework import generics, permissions
from rest_framework.response import Response

from courses.models import Announcements

from .serializers import SystemAnnouncementSerializer


class SystemAnnouncementListView(generics.ListAPIView):
    """
    GET /ann/ - 系統公告列表
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = SystemAnnouncementSerializer

    def get_queryset(self):
        return (
            Announcements.objects.select_related("creator_id")
            .order_by("-is_pinned", "-updated_at")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"data": serializer.data})

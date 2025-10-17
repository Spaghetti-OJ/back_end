from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from .models import Courses
from .serializers import CourseCreateSerializer


class CourseCreateView(generics.CreateAPIView):
    queryset = Courses.objects.all()
    serializer_class = CourseCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, "identity", None) not in ("teacher", "admin"):
            raise PermissionDenied("只有老師或管理員可以建立課程。")
        serializer.save()

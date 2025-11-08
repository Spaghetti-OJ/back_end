from rest_framework import generics, permissions, status
from rest_framework.response import Response

from ..models import Course_members, Courses
from ..serializers import CourseDetailSerializer


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
        is_member = is_teacher or Course_members.objects.filter(
            course_id=course, user_id=user
        ).exists()

        if not is_member:
            return Response(
                {"message": "You are not in this course."},
                status=status.HTTP_403_FORBIDDEN,
            )

        members = (
            Course_members.objects.filter(course_id=course)
            .select_related("user_id")
            .order_by("joined_at")
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

        serializer = self.get_serializer(
            {
                "message": "Success.",
                "course": course,
                "teacher": course.teacher_id,
                "TAs": tas,
                "students": students,
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def _get_course_or_response(course_id):
        if not course_id:
            return Response(
                {"message": "Course not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            return Courses.objects.select_related("teacher_id").get(id=course_id)
        except Courses.DoesNotExist:
            return Response(
                {"message": "Course not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

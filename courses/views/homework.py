from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from courses.models import Courses, Course_members
from assignments.models import Assignments
from courses.serializers.homework import HomeworkListItemSerializer

def is_teacher_or_ta(user, course) -> bool:
    if getattr(course, "teacher_id_id", None) == user.id or getattr(course, "teacher_id", None) == user:
        return True
    return Course_members.objects.filter(course_id=course, user_id=user, role=Course_members.Role.TA).exists()

class CourseHomeworkListByIdView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        try:
            course = Courses.objects.get(pk=course_id)
        except Courses.DoesNotExist:
            return Response("course not exists", status=status.HTTP_404_NOT_FOUND)

        staff_like = is_teacher_or_ta(request.user, course)
        qs = (
            Assignments.objects
            .filter(course=course)
            .select_related("course", "creator")
            .prefetch_related("assignment_problems")
            .order_by("-created_at", "id")
        )

        ser = HomeworkListItemSerializer(qs, many=True, context={"is_staff_like": staff_like, "user": request.user})
        return Response({"message": "get homeworks", "items": ser.data}, status=status.HTTP_200_OK)
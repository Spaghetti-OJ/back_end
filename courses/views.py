from collections import defaultdict

from django.db.models import Count, Q
from assignments.models import Assignments
from problems.models import Problems
from submissions.models import Submission
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ErrorDetail, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Course_members, Courses
from .serializers import (
    CourseCreateSerializer,
    CourseListSerializer,
    CourseSummarySerializer,
)


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


class CourseSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if getattr(request.user, "identity", None) != "admin":
            raise PermissionDenied("只有管理員可以查看課程統計。")

        courses = Courses.objects.all().order_by("name")
        course_ids = list(courses.values_list("id", flat=True))

        member_counts = Course_members.objects.filter(course_id__in=course_ids).values("course_id").annotate(total=Count("id"))
        member_count_map = {entry["course_id"]: entry["total"] for entry in member_counts}

        assignment_counts = Assignments.objects.filter(course_id__in=course_ids).values("course_id").annotate(total=Count("id"))
        assignment_count_map = {entry["course_id"]: entry["total"] for entry in assignment_counts}

        problem_counts = Problems.objects.filter(course_id__in=course_ids).values("course_id").annotate(total=Count("id"))
        problem_count_map = {entry["course_id"]: entry["total"] for entry in problem_counts}

        problem_rows = list(Problems.objects.filter(course_id__in=course_ids).values("id", "course_id"))
        problem_ids = [row["id"] for row in problem_rows]

        submission_count_map = defaultdict(int)
        if problem_ids:
            submission_counts = Submission.objects.filter(problem_id__in=problem_ids).values("problem_id").annotate(total=Count("id"))
            submissions_per_problem = {entry["problem_id"]: entry["total"] for entry in submission_counts}

            for row in problem_rows:
                submission_count_map[row["course_id"]] += submissions_per_problem.get(row["id"], 0)

        breakdown = []
        for course in courses:
            course_id = course.id
            breakdown.append(
                {
                    "course": course.name,
                    "userCount": member_count_map.get(course_id, 0),
                    "homeworkCount": assignment_count_map.get(course_id, 0),
                    "submissionCount": submission_count_map.get(course_id, 0),
                    "problemCount": problem_count_map.get(course_id, 0),
                }
            )

        data = {
            "message": "Success.",
            "courseCount": len(breakdown),
            "breakdown": breakdown,
        }

        serializer = CourseSummarySerializer(data)
        return Response(serializer.data)

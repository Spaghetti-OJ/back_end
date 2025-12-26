from collections import Counter, defaultdict

from django.db.models import Count
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from ..common.responses import api_response

from assignments.models import Assignments
from problems.models import Problems
from submissions.models import Submission

from ..models import Course_members, Courses
from ..serializers import CourseSummarySerializer


class CourseSummaryView(APIView):
    """
    課程統計摘要：
     - GET /course/summary 取得所有課程的統計資訊（僅管理員）
    """


    def get(self, request):
        if getattr(request.user, "identity", None) != "admin":
            raise PermissionDenied("只有管理員可以查看課程統計。")

        courses = Courses.objects.all().order_by("name")
        course_ids = [course.id for course in courses]

        member_counts = (
            Course_members.objects.filter(course_id__in=course_ids)
            .values("course_id")
            .annotate(total=Count("id"))
        )
        member_count_map = {entry["course_id"]: entry["total"] for entry in member_counts}

        assignment_counts = (
            Assignments.objects.filter(course_id__in=course_ids)
            .values("course_id")
            .annotate(total=Count("id"))
        )
        assignment_count_map = {
            entry["course_id"]: entry["total"] for entry in assignment_counts
        }

        problem_rows = list(
            Problems.objects.filter(course_id__in=course_ids).values("id", "course_id")
        )
        problem_count_map = dict(Counter(row["course_id"] for row in problem_rows))
        problem_ids = [row["id"] for row in problem_rows]

        submission_count_map = defaultdict(int)
        if problem_ids:
            submission_counts = (
                Submission.objects.filter(problem_id__in=problem_ids)
                .values("problem_id")
                .annotate(total=Count("id"))
            )
            submissions_per_problem = {
                entry["problem_id"]: entry["total"] for entry in submission_counts
            }

            for row in problem_rows:
                submission_count_map[row["course_id"]] += submissions_per_problem.get(
                    row["id"], 0
                )

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
            "courseCount": len(breakdown),
            "breakdown": breakdown,
        }

        serializer = CourseSummarySerializer(data)
        return api_response(data=serializer.data, message="Success.")

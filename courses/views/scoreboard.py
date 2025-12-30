from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from django.contrib.auth import get_user_model
from django.db.models import Count, Max
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from ..common.responses import api_response
from ..models import Course_members, Courses
from ..serializers import CourseScoreboardSerializer
from problems.models import Problems
from submissions.models import Submission

User = get_user_model()


class CourseScoreboardView(APIView):
    """
    課程計分板：
     - GET /course/<course_id>/scoreboard/ 取得計分板資料（教師/助教/管理員）

    Query:
      - pids (required, comma separated ints): 題目 ID 列表
      - start (optional, float timestamp): 開始時間（含）
      - end (optional, float timestamp): 結束時間（含）

    Response:
      200: Success. 內含 students 成績、problemStats、timeRange
      400: pids 解析錯誤或 start/end 型別錯誤
      403: 無評分權限
    """

    def get(self, request, course_id):
        course = self._get_course(course_id)
        if course is None:
            return api_response(
                message="Course not found.", status_code=status.HTTP_404_NOT_FOUND
            )

        if not self._has_grading_permission(course, request.user):
            return api_response(
                message="Permission denied", status_code=status.HTTP_403_FORBIDDEN
            )

        raw_pids = request.query_params.get("pids")
        problem_ids = self._parse_problem_ids(raw_pids)
        if problem_ids is None:
            return api_response(
                message="Error occurred when parsing `pids`.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        start_param = request.query_params.get("start")
        start_dt = self._parse_timestamp(start_param, "start")
        if isinstance(start_dt, str):
            return api_response(
                message=start_dt, status_code=status.HTTP_400_BAD_REQUEST
            )

        end_param = request.query_params.get("end")
        end_dt = self._parse_timestamp(end_param, "end")
        if isinstance(end_dt, str):
            return api_response(
                message=end_dt, status_code=status.HTTP_400_BAD_REQUEST
            )

        scoreboard = self._build_scoreboard(course, problem_ids, start_dt, end_dt)
        serializer = CourseScoreboardSerializer(scoreboard)
        return api_response(
            data=serializer.data, message="Success.", status_code=status.HTTP_200_OK
        )

    @staticmethod
    def _parse_problem_ids(raw_pids: Optional[str]) -> Optional[List[int]]:
        if raw_pids is None:
            return None

        try:
            ids = [int(pid.strip()) for pid in raw_pids.split(",") if pid.strip()]
        except (TypeError, ValueError):
            return None

        if not ids:
            return None

        seen = set()
        unique_ids = []
        for pid in ids:
            if pid not in seen:
                seen.add(pid)
                unique_ids.append(pid)
        return unique_ids

    @staticmethod
    def _parse_timestamp(
        value: Optional[str], field_name: str
    ) -> Union[datetime, str, None]:
        if value is None:
            return None
        try:
            ts = float(value)
        except (TypeError, ValueError):
            return f"Type of `{field_name}` should be float."
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    @staticmethod
    def _get_course(course_id) -> Optional[Courses]:
        try:
            return Courses.objects.get(pk=course_id)
        except (Courses.DoesNotExist, ValueError, TypeError):
            return None

    @staticmethod
    def _has_grading_permission(course: Courses, user) -> bool:
        if user is None:
            return False

        if getattr(user, "identity", None) == User.Identity.ADMIN:
            return True

        if course.teacher_id == user:
            return True

        return Course_members.objects.filter(
            course_id=course,
            user_id=user,
            role__in=(
                Course_members.Role.TA,
                Course_members.Role.TEACHER,
            ),
        ).exists()

    def _build_scoreboard(
        self,
        course: Courses,
        problem_ids: List[int],
        start_dt: Optional[datetime],
        end_dt: Optional[datetime],
    ) -> Dict:
        students = list(
            Course_members.objects.filter(
                course_id=course, role=Course_members.Role.STUDENT
            ).select_related("user_id")
        )
        student_users = [member.user_id for member in students]

        course_problem_ids = set(
            Problems.objects.filter(id__in=problem_ids, course_id=course).values_list(
                "id", flat=True
            )
        )
        filtered_problem_ids = [pid for pid in problem_ids if pid in course_problem_ids]

        problem_qs = Problems.objects.filter(id__in=filtered_problem_ids)
        problem_max_score_map = {p.id: p.max_score for p in problem_qs}

        submissions_qs = Submission.objects.filter(
            problem_id__in=filtered_problem_ids,
            user__in=student_users,
        )
        if start_dt is not None:
            submissions_qs = submissions_qs.filter(created_at__gte=start_dt)
        if end_dt is not None:
            submissions_qs = submissions_qs.filter(created_at__lte=end_dt)

        best_scores = submissions_qs.values("user_id", "problem_id").annotate(
            best_score=Max("score")
        )
        best_score_map: Dict[Tuple, int] = {
            (row["user_id"], row["problem_id"]): row["best_score"]
            for row in best_scores
        }

        submission_counts = submissions_qs.values("problem_id").annotate(
            total=Count("id"), submitters=Count("user_id", distinct=True)
        )
        submission_count_map = {
            row["problem_id"]: row["total"] for row in submission_counts
        }
        submitter_count_map = {
            row["problem_id"]: row["submitters"] for row in submission_counts
        }

        students_payload = []
        for member in students:
            user = member.user_id
            scores = {}
            total_score = 0
            submitted_count = 0
            for pid in filtered_problem_ids:
                key = (user.id, pid)
                best_score = best_score_map.get(key, 0)
                scores[str(pid)] = best_score
                if key in best_score_map:
                    submitted_count += 1
                total_score += best_score

            students_payload.append(
                {
                    "userId": user.id,
                    "username": user.username,
                    "realName": user.real_name,
                    "scores": scores,
                    "totalScore": total_score,
                    "submittedCount": submitted_count,
                }
            )

        problem_stats = []
        for pid in filtered_problem_ids:
            best_scores_for_problem = [
                score
                for (uid, prob), score in best_score_map.items()
                if prob == pid
            ]
            submitters = submitter_count_map.get(pid, 0)
            average_score = (
                float(sum(best_scores_for_problem)) / submitters
                if submitters > 0
                else 0.0
            )
            problem_stats.append(
                {
                    "problemId": pid,
                    "maxScore": max(best_scores_for_problem) if best_scores_for_problem else 0,
                    "averageScore": round(average_score, 2),
                    "submissionCount": submission_count_map.get(pid, 0),
                    "submitterCount": submitters,
                    "fullScore": problem_max_score_map.get(pid, 100),
                }
            )

        payload = {
            "courseId": course.id,
            "problemIds": filtered_problem_ids,
            "timeRange": {"start": start_dt, "end": end_dt},
            "students": students_payload,
            "problemStats": problem_stats,
        }
        return payload

from typing import List, Optional

from django.utils import timezone
from rest_framework import serializers
from datetime import datetime, timezone as dt_timezone

from assignments.models import Assignments, Assignment_problems
from courses.models import Courses
from problems.models import Problems
from submissions.models import Submission


def to_dt_from_epoch(value: Optional[int]):
    if value in (None, "", 0):
        return None
    try:
        return datetime.fromtimestamp(
            int(value),
            tz=timezone.get_current_timezone(),
        )
    except (TypeError, ValueError, OSError):
        raise serializers.ValidationError("invalid timestamp")


def to_epoch_from_dt(dt):
    if not dt:
        return None
    return int(dt.timestamp())


class HomeworkCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    course_id = serializers.UUIDField()
    markdown = serializers.CharField(required=False, allow_blank=True, default="")
    start = serializers.IntegerField(required=False, allow_null=True)
    end = serializers.IntegerField(required=False, allow_null=True)
    problem_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )
    scoreboard_status = serializers.IntegerField(required=False, allow_null=True)
    penalty = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        # 解析課程
        try:
            course = Courses.objects.get(pk=attrs["course_id"])
        except Courses.DoesNotExist:
            raise serializers.ValidationError("course not exists")
        attrs["_course"] = course

        # 名稱唯一（同課程）
        if Assignments.objects.filter(course=course, title=attrs["name"]).exists():
            raise serializers.ValidationError("homework exists in this course")

        # 時間轉換（epoch -> aware datetime in UTC）
        start = attrs.get("start")
        end = attrs.get("end")

        attrs["_start_dt"] = (
            datetime.fromtimestamp(start, tz=dt_timezone.utc)
            if start is not None
            else None
        )
        attrs["_end_dt"] = (
            datetime.fromtimestamp(end, tz=dt_timezone.utc)
            if end is not None
            else None
        )

        return attrs
# ---------- 詳情輸出 ----------
class HomeworkDetailSerializer(serializers.Serializer):
    message = serializers.CharField()
    name = serializers.CharField()
    start = serializers.IntegerField(allow_null=True)
    end = serializers.IntegerField(allow_null=True)
    problemIds = serializers.ListField(child=serializers.IntegerField())
    markdown = serializers.CharField(allow_blank=True)
    studentStatus = serializers.DictField()
    penalty = serializers.CharField(allow_blank=True)
    
    @staticmethod
    def from_instance(hw: Assignments, problem_ids: List[int], is_teacher_or_ta: bool, penalty_text: str = ""):
        return {
            "message": "get homework",
            "name": hw.title,
            "start": to_epoch_from_dt(hw.start_time),
            "end": to_epoch_from_dt(hw.due_time),
            "problemIds": problem_ids,
            "markdown": hw.description or "",
            "studentStatus": "teacher_or_ta" if is_teacher_or_ta else "student",
            "penalty": penalty_text or "",
        }


# ---------- 更新 ----------
class HomeworkUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    markdown = serializers.CharField(required=False, allow_blank=True)
    start = serializers.IntegerField(required=False, allow_null=True)
    end = serializers.IntegerField(required=False, allow_null=True)
    problem_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    scoreboard_status = serializers.IntegerField(required=False, allow_null=True)
    penalty = serializers.CharField(required=False, allow_blank=True)
    max_attempts = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        # 時間檢查
        start_epoch = attrs.get("start", None)
        end_epoch = attrs.get("end", None)
        start_dt = to_dt_from_epoch(start_epoch) if start_epoch is not None else None
        end_dt = to_dt_from_epoch(end_epoch) if end_epoch is not None else None
        if start_dt and end_dt and end_dt < start_dt:
            raise serializers.ValidationError({"end": "end earlier than start"})

        # 若指定 problem_ids，檢查是否存在
        if "problem_ids" in attrs:
            pids = attrs.get("problem_ids") or []
            not_found = []
            for pid in pids:
                if not Problems.objects.filter(pk=pid).exists():
                    not_found.append(pid)
            if not_found:
                raise serializers.ValidationError({"problem_ids": f"problems not found: {not_found}"})

        # 驗證 max_attempts
        if "max_attempts" in attrs:
            ma = attrs.get("max_attempts")
            if ma is not None and ma != -1 and ma < 1:
                raise serializers.ValidationError({"max_attempts": "max_attempts must be -1 or >=1"})

        attrs["_start_dt"] = start_dt
        attrs["_end_dt"] = end_dt
        return attrs
    
class HomeworkListResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    items = serializers.ListField(child=serializers.DictField())

def make_list_item_from_instance(
    hw: Assignments, problem_ids: List[int], is_teacher_or_ta: bool, penalty_text: str = ""
):
    """課程清單每一個 item 的輸出 shape"""
    return {
        "id": hw.id,
        "name": hw.title,
        "start": to_epoch_from_dt(hw.start_time),
        "end": to_epoch_from_dt(hw.due_time),
        "problemIds": problem_ids,
        "markdown": hw.description or "",
        "studentStatus": "teacher_or_ta" if is_teacher_or_ta else "student",
        "penalty": penalty_text or "",
    }
class AddProblemsItemSerializer(serializers.Serializer):
    """
    單題目的可選參數：
    - id: 題目 ID（必填）
    - weight/special_judge/time_limit/memory_limit/attempt_quota/order_index 皆為可選
    """
    id = serializers.IntegerField(required=True)
    weight = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    special_judge = serializers.BooleanField(required=False)
    time_limit = serializers.IntegerField(required=False, allow_null=True)
    memory_limit = serializers.IntegerField(required=False, allow_null=True)
    attempt_quota = serializers.IntegerField(required=False, allow_null=True)
    order_index = serializers.IntegerField(required=False)

class AddProblemsInSerializer(serializers.Serializer):
    """
    支援兩種輸入格式：
    1) {"problem_ids": [1,2,3]}
    2) {"problems": [{"id":1,"weight":1.5}, {"id":2,"special_judge":true}]}
    兩者擇一即可；若同時提供，以 problems 為主。
    """
    problem_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=False
    )
    problems = serializers.ListField(
        child=AddProblemsItemSerializer(), required=False, allow_empty=False
    )

    def validate(self, data):
        if not data.get("problems") and not data.get("problem_ids"):
            raise serializers.ValidationError("problem_ids or problems is required")
        return data

class HomeworkDeadlineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    markdown = serializers.CharField(allow_blank=True)
    course_id = serializers.UUIDField()
    start = serializers.DateTimeField(allow_null=True)
    end = serializers.DateTimeField(allow_null=True)
    is_overdue = serializers.BooleanField()
    server_time = serializers.DateTimeField()
    
class HomeworkProblemStatsSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    order_index = serializers.IntegerField()
    weight = serializers.DecimalField(max_digits=5, decimal_places=2)
    title = serializers.CharField()

    participant_count = serializers.IntegerField()
    total_submission_count = serializers.IntegerField()
    avg_attempts_per_user = serializers.FloatField()
    avg_score = serializers.FloatField()

    ac_user_count = serializers.IntegerField()
    partial_user_count = serializers.IntegerField()
    unsolved_user_count = serializers.IntegerField()

    first_ac_time = serializers.DateTimeField(allow_null=True)


class HomeworkStatsSerializer(serializers.Serializer):
    homework_id = serializers.IntegerField()
    course_id = serializers.UUIDField()

    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True, allow_null=True)
    start_time = serializers.DateTimeField(allow_null=True)
    due_time = serializers.DateTimeField(allow_null=True)
    problem_count = serializers.IntegerField()

    overview = serializers.DictField()
    problems = HomeworkProblemStatsSerializer(many=True)

class ScoreboardProblemSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    best_score = serializers.IntegerField()
    max_possible_score = serializers.IntegerField()
    solve_status = serializers.CharField()

class ScoreboardRowSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    user_id = serializers.UUIDField()
    username = serializers.CharField()
    real_name = serializers.CharField()

    total_score = serializers.IntegerField()
    max_total_score = serializers.IntegerField()
    is_late = serializers.BooleanField()

    first_ac_time = serializers.DateTimeField(allow_null=True)
    last_submission_time = serializers.DateTimeField(allow_null=True)

    problems = ScoreboardProblemSerializer(many=True)

class HomeworkScoreboardSerializer(serializers.Serializer):
    assignment_id = serializers.IntegerField()
    title = serializers.CharField()
    course_id = serializers.UUIDField()
    items = ScoreboardRowSerializer(many=True)

class HomeworkSubmissionListItemSerializer(serializers.ModelSerializer):
    """
    GET /homework/{id}/submissions 用的單筆 submission 輸出格式
    """

    # 跟 Table Users 對應：Users.id / Users.username
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    # 額外的 display 欄位
    language = serializers.CharField(source="get_language_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "problem_id",
            "user_id",
            "language_type",
            "status",
            "score",
            "max_score",
            "execution_time",
            "memory_usage",
            "is_late",
            "penalty_applied",
            "attempt_number",
            "judge_server",
            "created_at",
            "judged_at",

            # 額外資訊
            "username",
            "language",
            "status_display",
        ]
        read_only_fields = fields

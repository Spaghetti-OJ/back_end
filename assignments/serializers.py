from typing import List, Optional
from django.utils import timezone
from rest_framework import serializers
from datetime import datetime


from assignments.models import Assignments, Assignment_problems
from courses.models import Courses
from problems.models import Problems
from rest_framework import serializers

def to_dt_from_epoch(value: Optional[int]):
    if value in (None, "", 0):
        return None
    try:
        return timezone.datetime.fromtimestamp(int(value), tz=timezone.get_current_timezone())
    except Exception:
        raise serializers.ValidationError("invalid timestamp")

def to_epoch_from_dt(dt):
    if not dt:
        return None
    return int(dt.timestamp())


# ---------- 建立 ----------
class HomeworkCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    course_id = serializers.UUIDField()
    markdown = serializers.CharField(required=False, allow_blank=True, default="")
    start = serializers.IntegerField(required=False, allow_null=True)
    end = serializers.IntegerField(required=False, allow_null=True)
    problem_ids = serializers.ListField(child=serializers.IntegerField(),
                                        required=False, default=list)
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

        # 時間轉換
        start = attrs.get("start")
        end = attrs.get("end")
        attrs["_start_dt"] = datetime.fromtimestamp(start, tz=timezone.utc) if start is not None else None
        attrs["_end_dt"]   = datetime.fromtimestamp(end,   tz=timezone.utc) if end   is not None else None
        return attrs

# ---------- 詳情輸出 ----------
class HomeworkDetailSerializer(serializers.Serializer):
    # 指定的輸出格式
    message = serializers.CharField()
    name = serializers.CharField()
    start = serializers.IntegerField(allow_null=True)
    end = serializers.IntegerField(allow_null=True)
    problemIds = serializers.ListField(child=serializers.IntegerField())
    markdown = serializers.CharField(allow_blank=True)
    studentStatus = serializers.CharField()
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
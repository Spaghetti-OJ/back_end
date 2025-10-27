from rest_framework import serializers
from django.utils import timezone
from .models import Assignments, Assignment_problems
from courses.models import Courses, Course_members

# ---- 通用工具 ----
def epoch_to_dt(v):
    if v is None:
        return None
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    return timezone.datetime.fromtimestamp(v, tz=timezone.utc)

# ---- 輸入序列化 (對應測試 payload 欄位) ----
class HomeworkInSerializer(serializers.Serializer):
    # 測試使用的欄位命名
    name = serializers.CharField(required=True, allow_blank=False)
    course_id = serializers.CharField(required=True)  # 測試用字串，可能傳不存在的 UUID 字串
    markdown = serializers.CharField(required=False, allow_blank=True, default="")
    start = serializers.IntegerField(required=False, allow_null=True)
    end = serializers.IntegerField(required=False, allow_null=True)
    problem_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )

    def validate_course_id(self, value):
        # 依照測試：不存在要回 {"course_id": "course not exists"} 且 400
        try:
            course = Courses.objects.get(pk=value)
        except (Courses.DoesNotExist, ValueError):
            raise serializers.ValidationError("course not exists")
        return value  # 保留原值，真正的 Course 物件在 create/update 由 view 取

    def validate(self, attrs):
        start = attrs.get("start")
        end = attrs.get("end")
        if start is not None and end is not None:
            try:
                if int(end) < int(start):
                    # 依照測試：要在 'end' 欄位下回錯
                    raise serializers.ValidationError({"end": "end must be >= start"})
            except (TypeError, ValueError):
                pass
        return attrs


# ---- 輸出序列化 (GET /homework/{id} 期待欄位) ----
class HomeworkDetailOutSerializer(serializers.Serializer):
    # 測試預期有 message、name、problemIds 等
    id = serializers.IntegerField()
    message = serializers.CharField()
    name = serializers.CharField()
    course_id = serializers.IntegerField()
    markdown = serializers.CharField(allow_blank=True)
    start = serializers.IntegerField(allow_null=True)
    end = serializers.IntegerField(allow_null=True)
    problemIds = serializers.ListField(child=serializers.IntegerField())

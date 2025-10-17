from decimal import Decimal
from rest_framework import serializers
from .models import Assignments, Assignment_problems
from courses.models import Courses
from problems.models import Problems


class AssignmentProblemSerializer(serializers.ModelSerializer):
    # 寫入用：用 problem_id 指定題目
    problem_id = serializers.PrimaryKeyRelatedField(
        source="problem", queryset=Problems.objects.all(), write_only=True
    )
    # 讀取用：顯示題目 __str__
    problem = serializers.StringRelatedField(read_only=True)

    # 新增：單題作答配額（None=不限；>=1 限制）
    attempt_quota = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )

    class Meta:
        model = Assignment_problems
        fields = (
            "id", "problem", "problem_id",
            "order_index", "weight",
            "special_judge",
            "time_limit", "memory_limit",
            "attempt_quota",           # <- 新增欄位
            "is_active", "partial_score",
            "hint_text", "created_at",
        )
        read_only_fields = ("id", "created_at", "problem")

    def validate_weight(self, v):
        # 0 <= weight
        if Decimal(v) < Decimal("0"):
            raise serializers.ValidationError("weight must be >= 0")
        return v

    def validate_order_index(self, v):
        if v < 1:
            raise serializers.ValidationError("order_index must be >= 1")
        return v


class AssignmentSerializer(serializers.ModelSerializer):
    course_id = serializers.PrimaryKeyRelatedField(
        source="course", queryset=Courses.objects.all()
    )
    # 讀取：帶出作業下的題目
    problems = AssignmentProblemSerializer(
        source="assignment_problems", many=True, read_only=True
    )

    class Meta:
        model = Assignments
        fields = (
            "id", "title", "description", "course_id", "creator",
            "start_time", "due_time", "late_penalty", "max_attempts",
            "visibility", "status", "ip_restriction",
            "created_at", "updated_at", "problems",
        )
        read_only_fields = ("id", "creator", "created_at", "updated_at")

    # 可選：建立時把 creator 設成 request.user
    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["creator"] = request.user
        return super().create(validated_data)


# ---- 給端點用的小型序列化器 ----

class AssignmentAttachProblemSerializer(serializers.Serializer):
    """POST /homework/{id}/problems 用：附加或更新某題在此作業的配置"""
    problem_id = serializers.PrimaryKeyRelatedField(
        queryset=Problems.objects.all()
    )
    order_index = serializers.IntegerField(min_value=1, required=False, default=1)
    weight = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default="1.00")
    special_judge = serializers.BooleanField(required=False, default=False)
    time_limit = serializers.IntegerField(required=False, allow_null=True)
    memory_limit = serializers.IntegerField(required=False, allow_null=True)
    attempt_quota = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    is_active = serializers.BooleanField(required=False, default=True)
    partial_score = serializers.BooleanField(required=False, default=True)
    hint_text = serializers.CharField(required=False, allow_blank=True, default="")


class AssignmentProblemQuotaSerializer(serializers.Serializer):
    """PUT /homework/{id}/problems/{problemId}/quota 用"""
    attempt_quota = serializers.IntegerField(allow_null=True, min_value=1)

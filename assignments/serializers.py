from decimal import Decimal
from rest_framework import serializers
from .models import Assignments
from courses.models import Courses 

class AssignmentCreateSerializer(serializers.ModelSerializer):
    # 前端只傳 course_id；creator 由後端填
    course_id = serializers.PrimaryKeyRelatedField(
        source="course", queryset=Courses.objects.all(), write_only=True
    )

    class Meta:
        model = Assignments
        fields = (
            "id",
            "title",
            "description",
            "course_id",
            "start_time",
            "due_time",
            "late_penalty",
            "max_attempts",
            "visibility",
            "status",
            "ip_restriction",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
    def validate(self, attrs):
        start = attrs.get("start_time")
        due = attrs.get("due_time")
        if start and due and due < start:
            raise serializers.ValidationError("due_time must be >= start_time.")

        late_penalty = attrs.get("late_penalty", Decimal("0.00"))
        if not (Decimal("0.00") <= late_penalty <= Decimal("100.00")):
            raise serializers.ValidationError("late_penalty must be between 0 and 100.")

        max_attempts = attrs.get("max_attempts", -1)
        if max_attempts != -1 and max_attempts < 1:
            raise serializers.ValidationError("max_attempts must be -1 or >= 1.")
        return attrs

    def create(self, validated):
        # 由後端灌入建立者
        validated["creator"] = self.context["request"].user
        return super().create(validated)
from typing import Any, Dict

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from .models import Courses

User = get_user_model()


class CourseCreateSerializer(serializers.ModelSerializer):
    teacher = serializers.SerializerMethodField(read_only=True)

    class TeacherSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ("id", "username", "real_name", "identity")

    class Meta:
        model = Courses
        fields = [
            "id",
            "name",
            "description",
            "student_limit",
            "semester",
            "academic_year",
            "join_code",
            "is_active",
            "student_count",
            "created_at",
            "updated_at",
            "teacher",
        ]
        read_only_fields = [
            "id",
            "join_code",
            "is_active",
            "student_count",
            "created_at",
            "updated_at",
            "teacher",
        ]
        extra_kwargs = {
            "student_limit": {"required": True, "allow_null": False},
            "semester": {"required": True, "allow_blank": False, "allow_null": False},
            "academic_year": {"required": True, "allow_blank": False, "allow_null": False},
        }

    def create(self, validated_data: Dict[str, Any]) -> Courses:
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            raise serializers.ValidationError("無法辨識當前使用者。")

        validated_data["teacher_id"] = request.user

        try:
            return super().create(validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"join_code": ["無法產生唯一的 join_code，請稍後再試。"]}
            ) from exc

    def get_teacher(self, obj: Courses) -> Dict[str, Any]:
        teacher = obj.teacher_id
        if not isinstance(teacher, User):
            try:
                teacher = User.objects.get(pk=obj.teacher_id)
            except User.DoesNotExist:
                return {}
        return self.TeacherSerializer(teacher).data

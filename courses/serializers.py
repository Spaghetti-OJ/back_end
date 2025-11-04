import re
from typing import Any, Dict

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Courses

User = get_user_model()


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "real_name", "identity")

class CourseCreateSerializer(serializers.Serializer):
    COURSE_PATTERN = re.compile(r"^[a-zA-Z0-9._\- ]+$")

    course = serializers.CharField(required=True)
    teacher = serializers.CharField(required=True)

    def validate_course(self, value: str) -> str:
        trimmed = value.strip()
        if not trimmed or not self.COURSE_PATTERN.match(trimmed):
            raise serializers.ValidationError("Not allowed name.", code="invalid_course_name")
        if Courses.objects.filter(name__iexact=trimmed).exists():
            raise serializers.ValidationError("Course exists.", code="course_exists")
        return trimmed

    def validate_teacher(self, value: str) -> User:
        try:
            teacher = User.objects.get(username=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("User not found.", code="user_not_found") from exc

        if teacher.identity != "teacher":
            raise serializers.ValidationError("User not found.", code="user_not_found")

        return teacher

    def create(self, validated_data: Dict[str, Any]) -> Courses:
        teacher: User = validated_data["teacher"]
        course_name: str = validated_data["course"]
        return Courses.objects.create(name=course_name, teacher_id=teacher)

class CourseListSerializer(serializers.ModelSerializer):
    course = serializers.CharField(source="name")
    teacher = TeacherSerializer(source="teacher_id", read_only=True)

    class Meta:
        model = Courses
        fields = ("id", "course", "teacher")


class CourseSummarySerializer(serializers.Serializer):
    class BreakdownItem(serializers.Serializer):
        course = serializers.CharField()
        userCount = serializers.IntegerField()
        homeworkCount = serializers.IntegerField()
        submissionCount = serializers.IntegerField()
        problemCount = serializers.IntegerField()

    message = serializers.CharField(default="Success.")
    courseCount = serializers.IntegerField()
    breakdown = BreakdownItem(many=True)

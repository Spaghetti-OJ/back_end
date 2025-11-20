from rest_framework import serializers

from ..models import Courses
from .courses import TeacherSerializer


class CourseInfoSerializer(serializers.ModelSerializer):
    course = serializers.CharField(source="name")
    description = serializers.CharField(allow_blank=True)
    joinCode = serializers.CharField(source="join_code", allow_null=True)
    studentLimit = serializers.IntegerField(source="student_limit", allow_null=True)
    academicYear = serializers.CharField(source="academic_year", allow_blank=True)
    studentCount = serializers.IntegerField(source="student_count")
    isActive = serializers.BooleanField(source="is_active")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Courses
        fields = (
            "id",
            "course",
            "description",
            "joinCode",
            "studentLimit",
            "semester",
            "academicYear",
            "studentCount",
            "isActive",
            "createdAt",
            "updatedAt",
        )


class CourseDetailSerializer(serializers.Serializer):
    course = CourseInfoSerializer()
    teacher = TeacherSerializer()
    TAs = TeacherSerializer(many=True)
    students = TeacherSerializer(many=True)

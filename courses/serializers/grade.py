from rest_framework import serializers

from ..models import CourseGrade


class CourseGradeItemSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source="created_at")

    class Meta:
        model = CourseGrade
        fields = ("title", "content", "score", "timestamp")


class CourseGradeListSerializer(serializers.Serializer):
    message = serializers.CharField(default="Success.")
    grades = CourseGradeItemSerializer(many=True)

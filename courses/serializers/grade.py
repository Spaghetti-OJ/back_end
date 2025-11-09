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


class CourseGradeDeleteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=CourseGrade._meta.get_field("title").max_length)

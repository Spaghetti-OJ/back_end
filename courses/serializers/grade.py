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


class CourseGradeCreateSerializer(serializers.ModelSerializer):
    score = serializers.JSONField()

    class Meta:
        model = CourseGrade
        fields = ("title", "content", "score")

    def validate_title(self, value: str) -> str:
        course = self.context.get("course")
        student = self.context.get("student")
        if course is None or student is None:
            return value

        if CourseGrade.objects.filter(
            course=course,
            student=student,
            title=value,
        ).exists():
            raise serializers.ValidationError("This title is taken.")
        return value

    def validate_score(self, value):
        if isinstance(value, bool):
            raise serializers.ValidationError("Score must be a number or letter.")
        if isinstance(value, (int, float, str)):
            if isinstance(value, str) and not value.strip():
                raise serializers.ValidationError("Score cannot be blank.")
            return value
        raise serializers.ValidationError("Score must be a number or letter.")


class CourseGradeDeleteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=True, allow_blank=False)

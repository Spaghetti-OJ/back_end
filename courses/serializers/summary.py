from rest_framework import serializers


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

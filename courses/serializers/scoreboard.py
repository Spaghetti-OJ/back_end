from rest_framework import serializers


class CourseScoreboardTimeRangeSerializer(serializers.Serializer):
    start = serializers.DateTimeField(allow_null=True)
    end = serializers.DateTimeField(allow_null=True)


class CourseScoreboardProblemStatSerializer(serializers.Serializer):
    problemId = serializers.IntegerField()
    maxScore = serializers.IntegerField()
    averageScore = serializers.FloatField()
    submissionCount = serializers.IntegerField()
    submitterCount = serializers.IntegerField()
    fullScore = serializers.IntegerField()


class CourseScoreboardStudentSerializer(serializers.Serializer):
    userId = serializers.UUIDField()
    username = serializers.CharField()
    realName = serializers.CharField()
    scores = serializers.DictField(
        child=serializers.IntegerField(), allow_empty=True
    )
    totalScore = serializers.IntegerField()
    submittedCount = serializers.IntegerField()


class CourseScoreboardSerializer(serializers.Serializer):
    courseId = serializers.IntegerField()
    problemIds = serializers.ListField(child=serializers.IntegerField())
    timeRange = CourseScoreboardTimeRangeSerializer()
    students = CourseScoreboardStudentSerializer(many=True)
    problemStats = CourseScoreboardProblemStatSerializer(many=True)

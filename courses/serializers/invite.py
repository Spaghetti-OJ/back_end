from rest_framework import serializers

from ..models import Courses


class CourseInviteCodeSerializer(serializers.ModelSerializer):
    joinCode = serializers.CharField(source="join_code")

    class Meta:
        model = Courses
        fields = ("joinCode",)

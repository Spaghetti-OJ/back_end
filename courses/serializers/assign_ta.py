from rest_framework import serializers


class CourseAssignTASerializer(serializers.Serializer):
    username = serializers.CharField(required=True)

    def validate_username(self, value: str) -> str:
        trimmed = str(value or "").strip()
        if not trimmed:
            raise serializers.ValidationError("Username is required.")
        return trimmed

import re

from rest_framework import serializers


class CourseJoinSerializer(serializers.Serializer):
    JOIN_CODE_PATTERN = re.compile(r"^[A-Z0-9]{7}$")

    joinCode = serializers.CharField(source="join_code", required=True)

    def validate_joinCode(self, value: str) -> str:
        trimmed = str(value or "").strip().upper()
        if not self.JOIN_CODE_PATTERN.fullmatch(trimmed):
            raise serializers.ValidationError(
                "Invalid join code.", code="invalid_join_code"
            )
        return trimmed

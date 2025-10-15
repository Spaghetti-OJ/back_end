from rest_framework import serializers
from .models import Problems, Problem_subtasks, Test_cases, Tags, Problem_tags

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = ["id", "name", "usage_count"]

class ProblemSerializer(serializers.ModelSerializer):
    creator_id = serializers.PrimaryKeyRelatedField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Problems
        fields = [
            "id", "title", "difficulty", "max_score", "is_public",
            "total_submissions", "accepted_submissions", "acceptance_rate",
            "like_count", "view_count", "total_quota",
            "description", "input_description", "output_description",
            "sample_input", "sample_output", "hint",
            "subtask_description", "supported_languages",
            "creator_id", "course_id",
            "created_at", "updated_at",
            "tags",
        ]
        read_only_fields = [
            "acceptance_rate", "like_count", "view_count",
            "total_submissions", "accepted_submissions",
            "creator_id", "created_at", "updated_at",
        ]

class SubtaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem_subtasks
        fields = [
            "id", "problem_id", "subtask_no", "weight",
            "time_limit_ms", "memory_limit_mb",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test_cases
        fields = [
            "id", "subtask_id", "idx",
            "input_path", "output_path",
            "input_size", "output_size",
            "checksum_in", "checksum_out",
            "status", "created_at",
        ]
        read_only_fields = ["created_at"]

class ProblemTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem_tags
        fields = ["problem_id", "tag_id", "added_by"]
        read_only_fields = ["added_by"]

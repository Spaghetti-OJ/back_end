from rest_framework import serializers
from ..models import Problems, Problem_subtasks, Test_cases, Tags, Problem_tags

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = ["id", "name", "usage_count"]


class TestCaseSerializer(serializers.ModelSerializer):
    """完整測試案例資訊（管理員用）"""
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


class TestCaseStudentSerializer(serializers.ModelSerializer):
    """學生版測試案例（隱藏敏感資訊）"""
    class Meta:
        model = Test_cases
        fields = [
            "id", "idx",
            "input_size", "output_size",
            "status",
        ]


class SubtaskSerializer(serializers.ModelSerializer):
    """完整 subtask 資訊（管理員用）"""
    test_cases = TestCaseSerializer(many=True, read_only=True)

    class Meta:
        model = Problem_subtasks
        fields = [
            "id", "problem_id", "subtask_no", "weight",
            "time_limit_ms", "memory_limit_mb",
            "created_at", "updated_at",
            "test_cases",
        ]
        read_only_fields = ["created_at", "updated_at"]


class SubtaskStudentSerializer(serializers.ModelSerializer):
    """學生版 subtask（隱藏測試案例敏感資訊）"""
    test_cases = TestCaseStudentSerializer(many=True, read_only=True)

    class Meta:
        model = Problem_subtasks
        fields = [
            "id", "subtask_no", "weight",
            "time_limit_ms", "memory_limit_mb",
            "test_cases",
        ]


class ProblemSerializer(serializers.ModelSerializer):
    creator_id = serializers.PrimaryKeyRelatedField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('courses.models', fromlist=['Courses']).Courses.objects.all(),
        required=True,
        allow_null=False
    )

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


class ProblemDetailSerializer(serializers.ModelSerializer):
    """管理員版題目詳情（包含完整的 subtasks 和 test_cases）"""
    creator_id = serializers.PrimaryKeyRelatedField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    subtasks = SubtaskSerializer(many=True, read_only=True)

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
            "tags", "subtasks",
        ]
        read_only_fields = [
            "acceptance_rate", "like_count", "view_count",
            "total_submissions", "accepted_submissions",
            "creator_id", "created_at", "updated_at",
        ]


class ProblemStudentSerializer(serializers.ModelSerializer):
    """學生版題目詳情（隱藏敏感資訊 + 加上個人化資訊）"""
    tags = TagSerializer(many=True, read_only=True)
    subtasks = SubtaskStudentSerializer(many=True, read_only=True)
    
    # 個人化資訊（需在 view 中動態設定）
    submit_count = serializers.IntegerField(read_only=True, default=0)
    high_score = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Problems
        fields = [
            "id", "title", "difficulty", "max_score", "is_public",
            "total_submissions", "accepted_submissions", "acceptance_rate",
            "total_quota",
            "description", "input_description", "output_description",
            "sample_input", "sample_output", "hint",
            "subtask_description", "supported_languages",
            "course_id",
            "created_at",
            "tags", "subtasks",
            "submit_count", "high_score",
        ]
        read_only_fields = [
            "acceptance_rate", "total_submissions", "accepted_submissions",
            "created_at",
        ]

class ProblemTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem_tags
        fields = ["problem_id", "tag_id", "added_by"]
        read_only_fields = ["added_by"]

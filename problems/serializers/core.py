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
    # allow client to submit a list of tag ids when creating/updating a problem
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), write_only=True, required=False
    )
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
            "tags", "tag_ids",
        ]
        read_only_fields = [
            "acceptance_rate", "like_count", "view_count",
            "total_submissions", "accepted_submissions",
            "creator_id", "created_at", "updated_at",
        ]

    def create(self, validated_data):
        # Extract tag_ids (write-only field)
        tag_ids = validated_data.pop('tag_ids', None)
        
        # If tag_ids not provided, check if 'tags' was sent in initial_data
        # (since 'tags' is read_only, it won't be in validated_data)
        if tag_ids is None and hasattr(self, 'initial_data'):
            raw_tags = self.initial_data.get('tags')
            print(f"[DEBUG] create() initial_data.tags = {raw_tags}")  # DEBUG
            if isinstance(raw_tags, (list, tuple)):
                # Convert to list of ints
                tag_ids = []
                for v in raw_tags:
                    try:
                        tag_ids.append(int(v))
                    except (ValueError, TypeError):
                        pass
                print(f"[DEBUG] create() extracted tag_ids = {tag_ids}")  # DEBUG

        # Create problem instance
        problem = super().create(validated_data)
        
        # Attach tags if provided
        if tag_ids:
            from django.db.models import F
            tags_qs = Tags.objects.filter(id__in=tag_ids)
            print(f"[DEBUG] create() tags_qs count = {tags_qs.count()}")  # DEBUG
            problem.tags.set(tags_qs)
            # usage_count 累加
            Tags.objects.filter(id__in=tags_qs.values_list('id', flat=True)).update(usage_count=F('usage_count') + 1)
        else:
            print(f"[DEBUG] create() no tag_ids to attach")  # DEBUG
        
        return problem

    def update(self, instance, validated_data):
        # Extract tag_ids (write-only field)
        tag_ids = validated_data.pop('tag_ids', None)
        
        print(f"[DEBUG] update() called, tag_ids from validated_data = {tag_ids}")  # DEBUG
        
        # If tag_ids not provided, check if 'tags' was sent in initial_data
        if tag_ids is None and hasattr(self, 'initial_data'):
            raw_tags = self.initial_data.get('tags')
            print(f"[DEBUG] update() initial_data.tags = {raw_tags}")  # DEBUG
            if isinstance(raw_tags, (list, tuple)):
                tag_ids = []
                for v in raw_tags:
                    try:
                        tag_ids.append(int(v))
                    except (ValueError, TypeError):
                        pass
                print(f"[DEBUG] update() extracted tag_ids = {tag_ids}")  # DEBUG

        # Update problem instance
        problem = super().update(instance, validated_data)
        
        # Update tags if provided
        if tag_ids is not None:
            from django.db.models import F
            old_ids = set(instance.tags.values_list('id', flat=True))
            tags_qs = Tags.objects.filter(id__in=tag_ids)
            new_ids = set(tags_qs.values_list('id', flat=True))
            added = new_ids - old_ids
            removed = old_ids - new_ids
            print(f"[DEBUG] update() tags_qs count = {tags_qs.count()}, ids = {list(new_ids)} added={added} removed={removed}")  # DEBUG
            problem.tags.set(tags_qs)
            if added:
                Tags.objects.filter(id__in=added).update(usage_count=F('usage_count') + 1)
            if removed:
                Tags.objects.filter(id__in=removed).update(usage_count=F('usage_count') - 1)
            print(f"[DEBUG] update() after set, problem.tags.count() = {problem.tags.count()}")  # DEBUG
        else:
            print(f"[DEBUG] update() tag_ids is None, not updating tags")  # DEBUG
        
        return problem


class ProblemDetailSerializer(serializers.ModelSerializer):
    """管理員版題目詳情（包含完整的 subtasks 和 test_cases）"""
    creator_id = serializers.PrimaryKeyRelatedField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), write_only=True, required=False
    )
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
            "tags", "tag_ids", "subtasks",
        ]
        read_only_fields = [
            "acceptance_rate", "like_count", "view_count",
            "total_submissions", "accepted_submissions",
            "creator_id", "created_at", "updated_at",
        ]


class ProblemStudentSerializer(serializers.ModelSerializer):
    """學生版題目詳情（隱藏敏感資訊 + 加上個人化資訊）"""
    tags = TagSerializer(many=True, read_only=True)
    # include tag_ids as write-only for consistency if used in admin flows
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), write_only=True, required=False
    )
    subtasks = SubtaskStudentSerializer(many=True, read_only=True)
    
    # 個人化資訊（需在 view 中動態設定）
    submit_count = serializers.IntegerField(read_only=True, default=0)
    high_score = serializers.IntegerField(read_only=True, default=0)
    is_liked_by_user = serializers.SerializerMethodField()

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
            "tags", "tag_ids", "subtasks",
            "submit_count", "high_score", "is_liked_by_user",
        ]
        read_only_fields = [
            "acceptance_rate", "total_submissions", "accepted_submissions",
            "created_at",
        ]

    def get_is_liked_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            from ..models import ProblemLike
            return ProblemLike.objects.filter(problem=obj, user=request.user).exists()
        return False

class ProblemTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem_tags
        fields = ["problem_id", "tag_id", "added_by"]
        read_only_fields = ["added_by"]


class ProblemLikeSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = __import__('problems.models', fromlist=['ProblemLike']).ProblemLike
        fields = ['id', 'problem', 'user', 'user_username', 'created_at']
        read_only_fields = ['id', 'user', 'user_username', 'created_at']


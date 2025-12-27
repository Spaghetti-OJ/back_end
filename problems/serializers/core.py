from rest_framework import serializers
from ..models import Problems, Problem_subtasks, Test_cases, Tags, Problem_tags
from typing import Optional

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

class ProblemManageSerializer(serializers.ModelSerializer):
    """題目管理用的 Serializer（建立/更新）"""
    
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="標籤 ID 列表"
    )
    
    static_analysis_rules = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'forbid-loops',
            'forbid-arrays', 
            'forbid-stl',
            'forbid-functions'
        ]),
        required=False,
        default=list,
        help_text="靜態分析規則列表。有效值: 'forbid-loops', 'forbid-arrays', 'forbid-stl', 'forbid-functions'"
    )
    
    forbidden_functions = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
        help_text="禁止使用的函數名稱列表。當 static_analysis_rules 包含 'forbid-functions' 時必填"
    )

    class Meta:
        model = Problems
        fields = [
            'id', 'title', 'description', 'difficulty', 'is_public',
            'max_score', 'total_quota',
            'input_description', 'output_description',
            'sample_input', 'sample_output',
            'hint', 'subtask_description',
            'supported_languages',
            'solution_code', 'solution_code_language',
            'use_custom_checker', 'checker_name',
            'static_analysis_rules', 'forbidden_functions',
            'course_id', 'tags',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        """驗證靜態分析規則和禁止函數的一致性"""
        rules = attrs.get('static_analysis_rules', [])
        forbidden_funcs = attrs.get('forbidden_functions', [])
        
        # 如果是更新操作，需要考慮現有值
        if self.instance:
            if 'static_analysis_rules' not in attrs:
                rules = self.instance.static_analysis_rules or []
            if 'forbidden_functions' not in attrs:
                forbidden_funcs = self.instance.forbidden_functions or []
        
        # 驗證：當選擇 forbid-functions 時，必須提供至少一個禁止函數
        if 'forbid-functions' in rules:
            if not forbidden_funcs:
                raise serializers.ValidationError({
                    'forbidden_functions': '當啟用 forbid-functions 規則時，必須至少指定一個禁止使用的函數。'
                })
            # 驗證每個函數名稱
            for func in forbidden_funcs:
                if not func or not func.strip():
                    raise serializers.ValidationError({
                        'forbidden_functions': '函數名稱不能為空字串。'
                    })
        
        return attrs

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
    course_name = serializers.CharField(source="course_id.name", read_only=True)
    
    # 靜態分析設定
    static_analysis_rules = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'forbid-loops',
            'forbid-arrays', 
            'forbid-stl',
            'forbid-functions'
        ]),
        required=False,
        default=list,
        help_text="靜態分析規則列表。有效值: 'forbid-loops', 'forbid-arrays', 'forbid-stl', 'forbid-functions'"
    )
    
    forbidden_functions = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
        help_text="禁止使用的函數名稱列表。當 static_analysis_rules 包含 'forbid-functions' 時必填"
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
            # solution code fields for test generation
            "solution_code", "solution_code_language",
            # custom checker settings
            "use_custom_checker", "checker_name",
            # static analysis settings
            "static_analysis_rules", "forbidden_functions",
            "creator_id", "course_id", "course_name",
            "created_at", "updated_at",
            "tags", "tag_ids",
        ]
        read_only_fields = [
            "acceptance_rate", "like_count", "view_count",
            "total_submissions", "accepted_submissions",
            "creator_id", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        """驗證靜態分析規則和禁止函數的一致性"""
        rules = attrs.get('static_analysis_rules', [])
        forbidden_funcs = attrs.get('forbidden_functions', [])
        
        # 如果是更新操作，需要考慮現有值
        if self.instance:
            if 'static_analysis_rules' not in attrs:
                rules = self.instance.static_analysis_rules or []
            if 'forbidden_functions' not in attrs:
                forbidden_funcs = self.instance.forbidden_functions or []
        
        # 驗證：當選擇 forbid-functions 時，必須提供至少一個禁止函數
        if 'forbid-functions' in rules:
            if not forbidden_funcs:
                raise serializers.ValidationError({
                    'forbidden_functions': '當啟用 forbid-functions 規則時，必須至少指定一個禁止使用的函數。'
                })
            # 驗證每個函數名稱
            for func in forbidden_funcs:
                if not func or not func.strip():
                    raise serializers.ValidationError({
                        'forbidden_functions': '函數名稱不能為空字串。'
                    })
        
        return attrs

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
    
    # 靜態分析設定（唯讀，管理員視角顯示用）
    static_analysis_config = serializers.SerializerMethodField()
    use_static_analysis = serializers.SerializerMethodField()

    class Meta:
        model = Problems
        fields = [
            "id", "title", "difficulty", "max_score", "is_public",
            "total_submissions", "accepted_submissions", "acceptance_rate",
            "like_count", "view_count", "total_quota",
            "description", "input_description", "output_description",
            "sample_input", "sample_output", "hint",
            "subtask_description", "supported_languages",
            # custom checker settings
            "use_custom_checker", "checker_name",
            # static analysis settings
            "static_analysis_rules", "forbidden_functions",
            "static_analysis_config", "use_static_analysis",
            "creator_id", "course_id",
            "created_at", "updated_at",
            "tags", "tag_ids", "subtasks",
        ]
        read_only_fields = [
            "acceptance_rate", "like_count", "view_count",
            "total_submissions", "accepted_submissions",
            "creator_id", "created_at", "updated_at",
        ]

    def get_static_analysis_config(self, obj):
        """取得靜態分析配置（供前端顯示）"""
        return obj.get_static_analysis_config()

    def get_use_static_analysis(self, obj):
        """是否啟用靜態分析"""
        return obj.use_static_analysis


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
    
    # 靜態分析設定（學生只需知道是否啟用）
    use_static_analysis = serializers.SerializerMethodField()

    class Meta:
        model = Problems
        fields = [
            "id", "title", "difficulty", "max_score", "is_public",
            "total_submissions", "accepted_submissions", "acceptance_rate",
            "total_quota",
            "description", "input_description", "output_description",
            "sample_input", "sample_output", "hint",
            "subtask_description", "supported_languages",
            # custom checker settings (read-only for students)
            "use_custom_checker", "checker_name",
            # static analysis (read-only for students)
            "static_analysis_rules", "use_static_analysis",
            "course_id",
            "created_at",
            "tags", "tag_ids", "subtasks",
            "submit_count", "high_score", "is_liked_by_user",
        ]
        read_only_fields = [
            "acceptance_rate", "total_submissions", "accepted_submissions",
            "use_custom_checker", "checker_name",
            "static_analysis_rules",
            "created_at",
        ]

    def get_use_static_analysis(self, obj):
        """是否啟用靜態分析"""
        return obj.use_static_analysis

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


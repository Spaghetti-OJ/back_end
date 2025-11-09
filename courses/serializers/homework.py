from rest_framework import serializers
from assignments.models import Assignments
from submissions.models import UserProblemStats

class HomeworkListItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source="title", read_only=True)
    markdown = serializers.CharField(source="description", read_only=True)
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    problemIds = serializers.SerializerMethodField()
    studentStatus = serializers.SerializerMethodField()

    class Meta:
        model = Assignments
        fields = ["id", "name", "start", "end", "problemIds", "markdown", "studentStatus"]

    def get_start(self, obj):
        dt = obj.start_time
        return int(dt.timestamp()) if dt else None

    def get_end(self, obj):
        dt = obj.due_time
        return int(dt.timestamp()) if dt else None

    def get_problemIds(self, obj):
        return list(obj.assignment_problems.order_by("order_index").values_list("problem_id", flat=True))

    def get_studentStatus(self, obj):
        """
        教師/助教 => 'all'
        學生 => 根據 UserProblemStats 推出：
            - 全部 solved => 'solved'
            - 有 partial => 'partial'
            - 其餘 => 'unsolved'
        """
        is_staff_like = self.context.get("is_staff_like", False)
        user = self.context.get("user")

        if is_staff_like:
            return "all"

        # 學生：取該作業下的所有 problem 狀態
        stats = UserProblemStats.objects.filter(user=user, assignment_id=obj.id)
        if not stats.exists():
            return "unsolved"

        statuses = list(stats.values_list("solve_status", flat=True))
        if all(s == "solved" for s in statuses):
            return "solved"
        elif any(s == "partial" for s in statuses):
            return "partial"
        else:
            return "unsolved"
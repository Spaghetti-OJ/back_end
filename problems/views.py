from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status, permissions
# from .serializers import ProblemCreateSerializer

# class ProblemManageView(APIView):
#     permission_classes = [permissions.IsAdminUser]  # 建議：只有管理員可建題

#     def post(self, request):
#         ser = ProblemCreateSerializer(data=request.data, context={"request": request})
#         if not ser.is_valid():
#             return Response({"success": False, "errors": ser.errors}, status=422)
#         problem = ser.save()
#         return Response({"success": True, "problem_id": problem.id}, status=201)

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Problems, Problem_subtasks, Test_cases, Tags
from .serializers import (
    ProblemSerializer, ProblemDetailSerializer, ProblemStudentSerializer,
    SubtaskSerializer, TestCaseSerializer, TagSerializer
)
from .permissions import IsOwnerOrReadOnly, IsTeacherOrAdmin
from rest_framework.pagination import PageNumberPagination

class ProblemsViewSet(viewsets.ModelViewSet):
    queryset = Problems.objects.all().order_by("-created_at")
    serializer_class = ProblemSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(creator_id=self.request.user)

    def perform_update(self, serializer):
        #serializer.save(creator_id=self.get_object().creator_id)
        serializer.save(creator_id=serializer.instance.creator_id)

class SubtasksViewSet(viewsets.ModelViewSet):
    queryset = Problem_subtasks.objects.all().order_by("problem_id", "subtask_no")
    serializer_class = SubtaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        problem = serializer.validated_data["problem_id"]
        if problem.creator_id != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the problem owner can modify its subtasks.")
        serializer.save()

    def perform_update(self, serializer):
        problem = serializer.instance.problem_id
        if problem.creator_id != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the problem owner can modify its subtasks.")
        serializer.save()
        
    def perform_destroy(self, instance):
        problem = instance.problem_id
        if problem.creator_id != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the problem owner can delete its subtasks.")
        instance.delete()

class TestCasesViewSet(viewsets.ModelViewSet):
    queryset = Test_cases.objects.all().order_by("subtask_id", "idx")
    serializer_class = TestCaseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def _ensure_owner(self, subtask):
        problem = subtask.problem_id
        if problem.creator_id != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the problem owner can modify its test cases.")

    def perform_create(self, serializer):
        subtask = serializer.validated_data["subtask_id"]
        self._ensure_owner(subtask)
        serializer.save()

    def perform_update(self, serializer):
        subtask = serializer.instance.subtask_id
        self._ensure_owner(subtask)
        serializer.save()
        
    def perform_destroy(self, instance):
        subtask = instance.subtask_id
        self._ensure_owner(subtask)
        instance.delete()

class TagsViewSet(viewsets.ModelViewSet):
    queryset = Tags.objects.all().order_by("name")
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProblemPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProblemListView(APIView):
    """
    GET /api/problem/ — 題目列表
    支援篩選: ?difficulty=easy&is_public=true&course_id=3
    支援分頁: ?page=1&page_size=20
    """
    permission_classes = []

    def get(self, request):
        queryset = Problems.objects.all().select_related('creator_id').prefetch_related('tags', 'subtasks')
        
        # 篩選：difficulty
        difficulty = request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # 篩選：is_public
        is_public = request.query_params.get('is_public')
        if is_public is not None:
            is_public_bool = is_public.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_public=is_public_bool)
        
        # 篩選：course_id
        course_id = request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        # 權限過濾：未登入或非 owner/課程成員只能看 is_public=True
        user = request.user
        if not user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        elif not (user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']):
            # 普通使用者：只能看公開的 + 自己建的 + 所屬課程的
            from django.db.models import Q
            from courses.models import Course_members
            user_courses = Course_members.objects.filter(user_id=user).values_list('course_id', flat=True)
            queryset = queryset.filter(
                Q(is_public=True) | Q(creator_id=user) | Q(course_id__in=user_courses)
            )
        
        # 排序
        ordering = request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        # 分頁
        paginator = ProblemPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ProblemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ProblemSerializer(queryset, many=True)
        return Response(serializer.data)


class ProblemDetailView(APIView):
    """
    GET /api/problem/<id> — 題目詳情（學生視角）
    權限：公開題目所有人可見；私有題目只有 creator、課程成員、admin 可見
    回傳：簡化版測試案例 + 個人化資訊（submitCount, highScore）
    """
    permission_classes = []

    def get(self, request, pk):
        try:
            problem = Problems.objects.select_related('creator_id', 'course_id').prefetch_related(
                'tags', 'subtasks__test_cases'
            ).get(pk=pk)
        except Problems.DoesNotExist:
            return Response({"detail": "Problem not found."}, status=404)
        
        # 權限檢查
        user = request.user
        if not problem.is_public:
            if not user.is_authenticated:
                return Response({"detail": "Authentication required."}, status=401)
            
            # admin/staff 可看全部
            if user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']:
                pass
            # owner 可看
            elif problem.creator_id == user:
                pass
            # 課程成員可看
            elif problem.course_id:
                from courses.models import Course_members
                is_course_member = Course_members.objects.filter(
                    course_id=problem.course_id,
                    user_id=user
                ).exists()
                if not is_course_member:
                    return Response({"detail": "You do not have permission to view this problem."}, status=403)
            else:
                return Response({"detail": "You do not have permission to view this problem."}, status=403)
        
        # 序列化
        serializer = ProblemStudentSerializer(problem)
        data = serializer.data
        
        # 加上個人化資訊（如果已登入）
        if user.is_authenticated:
            # TODO: 當有 submissions app 時，查詢該用戶對此題目的提交次數和最高分
            # from submissions.models import Submissions
            # user_submissions = Submissions.objects.filter(problem_id=problem, user_id=user)
            # data['submit_count'] = user_submissions.count()
            # data['high_score'] = user_submissions.aggregate(Max('score'))['score__max'] or 0
            data['submit_count'] = 0  # 暫時預設值
            data['high_score'] = 0
        else:
            data['submit_count'] = 0
            data['high_score'] = 0
        
        return Response(data)


class ProblemManageView(APIView):
    """
    POST /api/problem/manage — 建立題目（僅 admin/teacher）
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request):
        serializer = ProblemSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=422)
        problem = serializer.save(creator_id=request.user)
        return Response({"success": True, "problem_id": problem.id}, status=201)


# PUT/DELETE /api/problem/manage/<id> — 修改/刪除題目
# GET /api/problem/manage/<id> — 管理員視角題目詳情
class ProblemManageDetailView(APIView):
    permission_classes = [IsTeacherOrAdmin, IsAuthenticated]

    def get_object_for_modify(self, pk, user):
        """用於 PUT/DELETE，只有 owner 或課程 TA/teacher 可操作"""
        problem = get_object_or_404(Problems, pk=pk)
        
        if problem.creator_id == user:
            return problem
        
        if problem.course_id:
            from courses.models import Course_members
            is_course_staff = Course_members.objects.filter(
                course_id=problem.course_id,
                user_id=user,
                role__in=['ta', 'teacher']
            ).exists()
            if is_course_staff:
                return problem
        
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Only the problem owner or course TA/teacher can modify or delete this problem.")

    def get(self, request, pk):
        """
        GET /api/problem/manage/<id> — 管理員視角的題目詳情
        回傳：完整測試案例 + 統計資訊（ACUser, submitter）
        權限：Teacher/Admin 可看全部；或是 owner/課程 TA
        """
        try:
            problem = Problems.objects.select_related('creator_id', 'course_id').prefetch_related(
                'tags', 'subtasks__test_cases'
            ).get(pk=pk)
        except Problems.DoesNotExist:
            return Response({"detail": "Problem not found."}, status=404)
        
        # 權限檢查：admin/teacher 可看全部
        user = request.user
        if not (user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']):
            # 不是 admin/teacher，檢查是否為 owner 或課程 TA
            if problem.creator_id != user:
                if problem.course_id:
                    from courses.models import Course_members
                    is_course_staff = Course_members.objects.filter(
                        course_id=problem.course_id,
                        user_id=user,
                        role__in=['ta', 'teacher']
                    ).exists()
                    if not is_course_staff:
                        return Response({"detail": "Not enough permission"}, status=403)
                else:
                    return Response({"detail": "Not enough permission"}, status=403)
        
        # 使用完整版 serializer
        serializer = ProblemDetailSerializer(problem)
        data = serializer.data
        
        # 加上統計資訊
        # TODO: 當有 submissions app 時，計算統計
        # from submissions.models import Submissions
        # from django.db.models import Count, Q
        # stats = Submissions.objects.filter(problem_id=problem).aggregate(
        #     ac_users=Count('user_id', filter=Q(status='AC'), distinct=True),
        #     submitters=Count('user_id', distinct=True),
        #     total_submissions=Count('id')
        # )
        # data['ac_user_count'] = stats['ac_users']
        # data['submitter_count'] = stats['submitters']
        
        data['ac_user_count'] = 0  # 暫時預設值
        data['submitter_count'] = 0
        data['can_view_stdout'] = True  # 預設值，可從 settings 或題目設定讀取
        
        return Response(data)

    @transaction.atomic
    def put(self, request, pk):
        problem = self.get_object_for_modify(pk, request.user)
        serializer = ProblemSerializer(problem, data=request.data, partial=True, context={"request": request})
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=422)
        serializer.save(creator_id=problem.creator_id)  # 保留 owner
        return Response({"success": True, "problem_id": problem.id}, status=200)

    @transaction.atomic
    def delete(self, request, pk):
        problem = self.get_object_for_modify(pk, request.user)
        problem.delete()
        return Response({"success": True}, status=204)



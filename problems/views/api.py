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

from ..models import Problems, Problem_subtasks, Test_cases, Tags, Problem_tags
from ..serializers import (
    ProblemSerializer, ProblemDetailSerializer, ProblemStudentSerializer,
    SubtaskSerializer, TestCaseSerializer, TagSerializer
)
from ..permissions import IsOwnerOrReadOnly, IsTeacherOrAdmin
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Max
from submissions.models import Submission
from ..models import ProblemLike
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import models as dj_models

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

class TagListCreateView(APIView):
    """GET /tags/ 取得所有標籤
    POST /tags/ 建立新標籤（需要登入，建議僅教師/管理員；此處暫允任何登入使用者）
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        tags = Tags.objects.all().order_by('name')
        return Response(TagSerializer(tags, many=True).data)

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=401)
        ser = TagSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=422)
        tag = ser.save()
        return Response(TagSerializer(tag).data, status=201)


class ProblemTagAddView(APIView):
    """POST /problem/<id>/tags  將現有標籤加入題目
    Body: {"tag_id": 1} 或 {"tagId": 1}
    權限：題目擁有者 / 課程 TA / 教師 / 管理員
    若標籤已存在於題目，回傳 400。
    """
    permission_classes = [IsAuthenticated]

    def _get_problem_for_modify(self, problem_id, user):
        problem = get_object_or_404(Problems, pk=problem_id)
        if user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']:
            return problem
        if problem.creator_id == user:
            return problem
        if problem.course_id:
            from courses.models import Course_members
            is_staff = Course_members.objects.filter(
                course_id=problem.course_id,
                user_id=user,
                role__in=['ta', 'teacher']
            ).exists()
            if is_staff:
                return problem
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Not enough permission to modify problem tags.")

    def post(self, request, pk):
        problem = self._get_problem_for_modify(pk, request.user)
        tag_id = request.data.get('tag_id') or request.data.get('tagId')
        if tag_id is None:
            return Response({"detail": "tag_id is required"}, status=400)
        try:
            tag_id = int(tag_id)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid tag_id"}, status=400)
        tag = Tags.objects.filter(pk=tag_id).first()
        if not tag:
            return Response({"detail": "Tag not found."}, status=404)
        # 已存在關聯？
        if Problem_tags.objects.filter(problem_id=problem, tag_id=tag).exists():
            return Response({"detail": "Tag already attached to problem."}, status=400)
        from django.db.models import F
        Problem_tags.objects.create(problem_id=problem, tag_id=tag, added_by=request.user)
        Tags.objects.filter(pk=tag.pk).update(usage_count=F('usage_count') + 1)
        tag.refresh_from_db()
        return Response({"detail": "Tag added", "tag": TagSerializer(tag).data}, status=201)


class ProblemTagRemoveView(APIView):
    """DELETE /problem/<id>/tags/<tag_id>  從題目移除標籤
    權限：題目擁有者 / 課程 TA / 教師 / 管理員
    若關聯不存在則回傳 404。
    """
    permission_classes = [IsAuthenticated]

    def _get_problem_for_modify(self, problem_id, user):
        problem = get_object_or_404(Problems, pk=problem_id)
        if user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']:
            return problem
        if problem.creator_id == user:
            return problem
        if problem.course_id:
            from courses.models import Course_members
            is_staff = Course_members.objects.filter(
                course_id=problem.course_id,
                user_id=user,
                role__in=['ta', 'teacher']
            ).exists()
            if is_staff:
                return problem
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Not enough permission to modify problem tags.")

    def delete(self, request, pk, tag_id):
        problem = self._get_problem_for_modify(pk, request.user)
        try:
            tag_id_int = int(tag_id)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid tag_id"}, status=400)
        tag = Tags.objects.filter(pk=tag_id_int).first()
        if not tag:
            return Response({"detail": "Tag not found."}, status=404)
        rel = Problem_tags.objects.filter(problem_id=problem, tag_id=tag).first()
        if not rel:
            return Response({"detail": "Tag not attached to this problem."}, status=404)
        from django.db.models import F
        rel.delete()
        Tags.objects.filter(pk=tag.pk).update(usage_count=F('usage_count') - 1)
        tag.refresh_from_db()
        return Response({"detail": "Tag removed", "tag": TagSerializer(tag).data}, status=200)


class ProblemPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProblemListView(APIView):
    """
    GET /api/problem/ — 題目列表
    支援篩選: ?difficulty=easy&is_public=public|course|hidden&course_id=3
    支援分頁: ?page=1&page_size=20
    """
    permission_classes = []

    def get_permissions(self):
        # allow anonymous GET, but require teacher/admin for POST
        if getattr(self, 'request', None) is not None and self.request.method == 'POST':
            return [IsTeacherOrAdmin()]
        return []

    def get(self, request):
        queryset = Problems.objects.all().select_related('creator_id').prefetch_related('tags', 'subtasks')
        
        # 篩選：difficulty
        difficulty = request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # 篩選：is_public
        visibility = request.query_params.get('is_public')
        if visibility in ('public','course','hidden'):
            queryset = queryset.filter(is_public=visibility)
        
        # 篩選：course_id
        course_id = request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
    # 權限過濾：未登入或非 owner/課程成員只能看 is_public=public
        user = request.user
        if not user.is_authenticated:
            # Fallback: treat legacy boolean true as public during migration window
            queryset = queryset.filter(is_public__in=['public', True, 1])
        elif not (user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']):
            # 普通使用者：只能看公開的 + 自己建的 + 所屬課程的
            from django.db.models import Q
            from courses.models import Course_members
            user_courses = Course_members.objects.filter(user_id=user).values_list('course_id', flat=True)
            queryset = queryset.filter(
                Q(is_public__in=['public', True, 1]) | Q(creator_id=user) | Q(is_public='course', course_id__in=user_courses)
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

    # 重要：不允許在 /problem/ 進行建立，統一走 /problem/manage
    # 若誤用 POST /problem/，回傳 405，請改用 /problem/manage
    def post(self, request):
        return Response({"detail": "Method Not Allowed. Use POST /problem/manage to create."}, status=405)


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
        visibility = getattr(problem, 'is_public', 'hidden')
        # Treat legacy boolean True as public, False as hidden
        legacy_public = visibility in (True, 1)
        visibility_normalized = 'public' if legacy_public else visibility
        if visibility_normalized not in ('public'):
            # not public -> need auth
            if not user.is_authenticated:
                return Response({"detail": "Authentication required."}, status=401)
            # admin/teacher
            if user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']:
                pass
            elif problem.creator_id == user:
                pass
            elif visibility_normalized == 'course' and problem.course_id:
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
        
        
        # A: 簡單實作：若使用者已登入，直接從 Submission 聚合該 user 在此題的次數與最高分
        # 未登入則回傳 null（前端可解讀為需登入才會看到個人化資訊）
        if user.is_authenticated:
            stats = Submission.objects.filter(problem_id=problem.id, user=user).aggregate(
                submit_count=Count('id'),
                high_score=Max('score'),
            )
            data['submit_count'] = stats.get('submit_count') or 0
            data['high_score'] = stats.get('high_score') or 0
        else:
            data['submit_count'] = None
            data['high_score'] = None
        
        return Response(data)


import math

class ProblemStatsView(APIView):
    """
    GET /problem/<id>/stats — 題目統計資訊
    權限：需要登入
    回傳：AC 用戶、嘗試用戶、平均分數、標準差、分數分布、狀態統計、top10執行時間/記憶體
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Defensive: some dependent apps/tables may be missing while local migrations are being fixed.
        # Wrap DB access in OperationalError to return a clear 503 instead of crashing the server.
        from django.db.utils import OperationalError
        try:
            from courses.models import Course_members
            from submissions.models import Submission

            # 1. 題目存在性
            try:
                problem = Problems.objects.get(pk=pk)
            except Problems.DoesNotExist:
                return Response({"detail": "Problem not found."}, status=404)

            # 2. 總學生數（該課程所有學生）
            course_id = getattr(problem, 'course_id', None)
            total_students = 0
            if course_id:
                total_students = Course_members.objects.filter(course_id=course_id, role='student').count()

            # 3. 所有提交
            submissions = Submission.objects.filter(problem_id=pk)

            # 4. 嘗試過的用戶數
            tried_user_ids = submissions.values_list('user', flat=True).distinct()
            tried_user_count = len(tried_user_ids)

            # 5. AC 用戶數
            ac_user_ids = submissions.filter(status='accepted').values_list('user', flat=True).distinct()
            ac_user_count = len(ac_user_ids)

            # 6. 分數統計
            scores = list(submissions.values_list('score', flat=True))
            average = sum(scores) / len(scores) if scores else 0
            std = math.sqrt(sum((s - average) ** 2 for s in scores) / len(scores)) if scores else 0

            # 7. 分數分布
            score_distribution = {}
            for s in scores:
                score_distribution[s] = score_distribution.get(s, 0) + 1
            score_distribution = [ {'score': k, 'count': v} for k, v in sorted(score_distribution.items()) ]

            # 8. 狀態統計
            status_count = {}
            for row in submissions.values('status').annotate(cnt=Count('id')):
                status_count[row['status']] = row['cnt']

            # 9. top10執行時間
            top10_runtime = list(submissions.filter(execution_time__gt=0).order_by('execution_time')[:10].values('id', 'user', 'execution_time', 'score', 'status'))

            # 10. top10記憶體
            top10_memory = list(submissions.filter(memory_usage__gt=0).order_by('memory_usage')[:10].values('id', 'user', 'memory_usage', 'score', 'status'))

            return Response({
                "acUserRatio": [ac_user_count, total_students],
                "triedUserCount": tried_user_count,
                "average": average,
                "std": std,
                "scoreDistribution": score_distribution,
                "statusCount": status_count,
                "top10RunTime": top10_runtime,
                "top10MemoryUsage": top10_memory,
            }, status=200)
        except OperationalError as e:
            # Helpful diagnostic for local dev when migrations/tables are missing
            return Response({
                "detail": "Service temporarily unavailable: dependent database tables appear to be missing.",
                "error": str(e),
            }, status=503)

class ProblemHighScoreView(APIView):
    """
    GET /api/problem/<id>/high-score — 取得使用者在該題目的最高分數
    需要登入；回傳該使用者在此題的最高分
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            problem = Problems.objects.get(pk=pk)
        except Problems.DoesNotExist:
            return Response({"detail": "Problem not found."}, status=404)
        
        user = request.user
        high_score = Submission.objects.filter(
            problem_id=problem.id,
            user=user
        ).aggregate(high_score=Max('score')).get('high_score')
        
        # 若從未提交過，回傳 0
        if high_score is None:
            high_score = 0
        
        return Response({"score": high_score}, status=200)


class ProblemManageView(APIView):
    """
    POST /api/problem/manage — 建立題目（僅 admin/teacher）
    """
    # 允許已登入；實際權限在 post() 內判斷：
    # admin/teacher 直接允許；否則需為該 course 的 TA
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProblemSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=422)

        # 權限檢查：
        user = request.user
        is_admin_teacher = bool(
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or getattr(user, "identity", None) in ["admin", "teacher"]
        )

        course_obj = serializer.validated_data.get("course_id")
        if not is_admin_teacher:
            # 必須是該課程 TA 才能出題
            from courses.models import Course_members
            is_course_ta = Course_members.objects.filter(
                course_id=course_obj,
                user_id=user,
                role='ta',
            ).exists()
            if not is_course_ta:
                return Response({"detail": "Not enough permission: need admin/teacher or TA of the course."}, status=403)

        # 嚴格驗證 tags（若提供）
        tags_data = request.data.get('tags')
        tag_ids = []
        if tags_data is not None:
            if isinstance(tags_data, (list, tuple)):
                for v in tags_data:
                    try:
                        tag_ids.append(int(v))
                    except (ValueError, TypeError):
                        return Response({"success": False, "errors": {"tags": f"Invalid tag id: {v}"}}, status=400)

                from ..models import Tags
                existing_ids = set(Tags.objects.filter(id__in=tag_ids).values_list('id', flat=True))
                missing_ids = [tid for tid in tag_ids if tid not in existing_ids]
                if missing_ids:
                    return Response({"success": False, "errors": {"tags": f"Tag IDs do not exist: {missing_ids}"}}, status=400)

        problem = serializer.save(creator_id=request.user)

        # 綁定已驗證之 tags
        if tags_data is not None:
            from ..models import Tags
            tags_qs = Tags.objects.filter(id__in=tag_ids)
            problem.tags.set(tags_qs)

        return Response({"success": True, "problem_id": problem.id}, status=201)


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def problem_like_toggle(request, pk):
    """POST /problem/<id>/like - 按讚
    DELETE /problem/<id>/like - 取消按讚
    """
    try:
        problem = Problems.objects.get(pk=pk)
    except Problems.DoesNotExist:
        return Response({"detail": "Problem not found."}, status=404)

    user = request.user

    try:
        with transaction.atomic():
            existing = ProblemLike.objects.filter(problem=problem, user=user).first()

            if request.method == 'POST':
                if existing:
                    return Response({"detail": "You already liked this problem."}, status=400)
                ProblemLike.objects.create(problem=problem, user=user)
                # update counter
                Problems.objects.filter(pk=pk).update(like_count=dj_models.F('like_count') + 1)
                problem.refresh_from_db()
                return Response({"detail": "Liked", "likes_count": problem.like_count}, status=201)

            # method == DELETE
            if not existing:
                return Response({"detail": "You have not liked this problem."}, status=400)
            existing.delete()
            Problems.objects.filter(pk=pk).update(like_count=dj_models.F('like_count') - 1)
            problem.refresh_from_db()
            return Response({"detail": "Unliked", "likes_count": problem.like_count}, status=200)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"problem_like_toggle failed: {e}", exc_info=True)
        return Response({"detail": "Operation failed"}, status=500)


@api_view(['GET'])
def problem_likes_count(request, pk):
    """GET /problem/<id>/likes - 取得點讚數（簡單回傳 like_count）"""
    try:
        problem = Problems.objects.get(pk=pk)
    except Problems.DoesNotExist:
        return Response({"detail": "Problem not found."}, status=404)
    return Response({"likes_count": problem.like_count}, status=200)


class UserLikedProblemsView(generics.ListAPIView):
    """GET /user/likes - 列出已按讚的題目（需登入）"""
    permission_classes = [IsAuthenticated]
    serializer_class = ProblemStudentSerializer

    def get_queryset(self):
        user = self.request.user
        liked_ids = ProblemLike.objects.filter(user=user).values_list('problem', flat=True)
        return Problems.objects.filter(id__in=liked_ids).order_by('-created_at')


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
        
        # Extract and validate tags before saving
        tags_data = request.data.get('tags')
        tag_ids = []
        if tags_data is not None:
            if isinstance(tags_data, (list, tuple)):
                for v in tags_data:
                    try:
                        tag_ids.append(int(v))
                    except (ValueError, TypeError):
                        return Response({"success": False, "errors": {"tags": f"Invalid tag id: {v}"}}, status=400)
                
                # Strict validation: all tag ids must exist
                from ..models import Tags
                existing_tags = Tags.objects.filter(id__in=tag_ids)
                existing_ids = set(existing_tags.values_list('id', flat=True))
                missing_ids = [tid for tid in tag_ids if tid not in existing_ids]
                if missing_ids:
                    return Response({
                        "success": False, 
                        "errors": {"tags": f"Tag IDs do not exist: {missing_ids}"}
                    }, status=400)
        
        serializer.save(creator_id=problem.creator_id)  # 保留 owner
        
        # Update tags if provided
        if tags_data is not None:
            from ..models import Tags
            tags_qs = Tags.objects.filter(id__in=tag_ids)
            problem.tags.set(tags_qs)
        
        return Response({"success": True, "problem_id": problem.id}, status=200)

    @transaction.atomic
    def delete(self, request, pk):
        problem = self.get_object_for_modify(pk, request.user)
        problem.delete()
        return Response({"success": True}, status=204)

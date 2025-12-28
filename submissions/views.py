from django.shortcuts import render, get_object_or_404
from django.db import models, transaction, IntegrityError
from django.http import Http404
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.utils import timezone
from django.db.models import Count
from rest_framework.views import APIView
from problems.models import Problems, Problem_subtasks, Test_cases
from user.models import User
import uuid
from datetime import datetime
import logging

# 統一的 API 響應格式
def api_response(data=None, message="OK", status_code=200):
    """
    統一的 API 響應格式
    Args:
        data: 響應數據
        message: 響應消息
        status_code: HTTP 狀態碼
    Returns:
        Response 對象，包含標準格式的響應
    """
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response({
        "data": data,
        "message": message,
        "status": status_str,
    }, status=status_code)

from .models import Editorial, EditorialLike, UserProblemSolveStatus
from .serializers import (
    EditorialSerializer, 
    EditorialCreateSerializer, 
    EditorialLikeSerializer,
    UserStatusSerializer
)
from problems.models import Problems
from courses.models import Courses, Course_members


def update_user_problem_stats(submission):
    """
    更新使用者題目解題統計（全域層級）
    
    根據提交結果更新 UserProblemSolveStatus，包括：
    - 總提交數
    - AC 提交數
    - 最佳分數
    - 首次解題時間
    - 最後提交時間
    - 解題狀態（never_tried/attempted/partial_solved/fully_solved）
    - 最佳執行時間和記憶體使用
    """
    from django.utils import timezone
    from django.db.models import F
    
    try:
        # 取得或創建 UserProblemSolveStatus
        stats, created = UserProblemSolveStatus.objects.get_or_create(
            user=submission.user,
            problem_id=submission.problem_id,
            defaults={
                'total_submissions': 0,
                'ac_submissions': 0,
                'best_score': 0,
                'solve_status': 'never_tried',
            }
        )
        
        # 更新總提交數
        stats.total_submissions = F('total_submissions') + 1
        
        # 更新最後提交時間
        stats.last_submission_time = submission.created_at
        
        # 如果是 AC (status='0')
        if submission.status == '0':
            stats.ac_submissions = F('ac_submissions') + 1
            
            # 更新首次解題時間（如果是第一次 AC）
            if not stats.first_solve_time:
                stats.first_solve_time = submission.judged_at or timezone.now()
        
        # 先保存以計算 F() 表達式
        stats.save()
        stats.refresh_from_db()
        
        # 更新最佳分數
        if submission.score > stats.best_score:
            stats.best_score = submission.score
        
        # 更新最佳執行時間（只在有效時更新）
        if submission.execution_time > 0:
            if stats.best_execution_time is None or submission.execution_time < stats.best_execution_time:
                stats.best_execution_time = submission.execution_time
            stats.total_execution_time += submission.execution_time
        
        # 更新最佳記憶體使用（只在有效時更新）
        if submission.memory_usage > 0:
            if stats.best_memory_usage is None or submission.memory_usage < stats.best_memory_usage:
                stats.best_memory_usage = submission.memory_usage
        
        # 更新解題狀態
        if stats.best_score >= 100:
            stats.solve_status = 'fully_solved'
        elif stats.best_score > 0:
            stats.solve_status = 'partial_solved'
        elif stats.total_submissions == 0:
            stats.solve_status = 'never_tried'
        else:
            stats.solve_status = 'attempted'
        
        stats.save()
        
        logger = logging.getLogger(__name__)
        logger.info(f'Updated solve status for user {submission.user.id} problem {submission.problem_id}: '
                   f'status={stats.solve_status}, best_score={stats.best_score}, '
                   f'total_submissions={stats.total_submissions}')
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f'Failed to update user problem solve status: {str(e)}', exc_info=True)

''' 這邊不再需要了，算成績的部分交給前端處理
def update_user_assignment_stats(submission, assignment_id):
    """
    更新使用者作業題目統計（作業層級）
    
    根據提交結果更新 UserProblemStats，包括：
    - 總提交數
    - 最佳分數
    - 首次 AC 時間
    - 最後提交時間
    - 解題狀態（unsolved/partial/solved）
    - 最佳執行時間和記憶體使用
    - 遲交處理
    """
    from django.utils import timezone
    from django.db.models import F
    from .models import UserProblemStats
    from assignments.models import Assignments, Assignment_problems
    
    try:
        # 檢查是否屬於作業
        if not assignment_id:
            return
        
        # 檢查 assignment 和 problem 的關聯
        try:
            assignment = Assignments.objects.get(id=assignment_id)
            assignment_problem = Assignment_problems.objects.get(
                assignment=assignment,
                problem_id=submission.problem_id
            )
        except (Assignments.DoesNotExist, Assignment_problems.DoesNotExist):
            # 如果作業或題目不存在，跳過
            return
        
        # 取得或創建 UserProblemStats
        stats, created = UserProblemStats.objects.get_or_create(
            user=submission.user,
            assignment_id=assignment_id,
            problem_id=submission.problem_id,
            defaults={
                'total_submissions': 0,
                'best_score': 0,
                'max_possible_score': assignment_problem.weight * 100 if assignment_problem.weight else 100,
                'solve_status': 'unsolved',
            }
        )
        
        # 更新總提交數
        stats.total_submissions = F('total_submissions') + 1
        
        # 更新最後提交時間
        stats.last_submission_time = submission.created_at
        
        # 檢查是否遲交
        if assignment.due_time and submission.created_at > assignment.due_time:
            stats.is_late = True
            # 計算遲交罰分
            if assignment.late_penalty > 0:
                stats.penalty_score = assignment.late_penalty
        
        # 先保存以計算 F() 表達式
        stats.save()
        stats.refresh_from_db()
        
        # 更新最佳分數（考慮遲交罰分）
        final_score = submission.score
        if stats.is_late and stats.penalty_score > 0:
            final_score = int(submission.score * (1 - float(stats.penalty_score) / 100))
        
        if final_score > stats.best_score:
            stats.best_score = final_score
            stats.best_submission = submission
        
        # 如果是 AC (status='0') 且還沒有 first_ac_time
        if submission.status == '0' and not stats.first_ac_time:
            stats.first_ac_time = submission.judged_at or timezone.now()
        
        # 更新最佳執行時間
        if submission.execution_time > 0:
            if stats.best_execution_time is None or submission.execution_time < stats.best_execution_time:
                stats.best_execution_time = submission.execution_time
        
        # 更新最佳記憶體使用
        if submission.memory_usage > 0:
            if stats.best_memory_usage is None or submission.memory_usage < stats.best_memory_usage:
                stats.best_memory_usage = submission.memory_usage
        
        # 更新解題狀態
        if stats.best_score >= stats.max_possible_score:
            stats.solve_status = 'solved'
        elif stats.best_score > 0:
            stats.solve_status = 'partial'
        else:
            stats.solve_status = 'unsolved'
        
        stats.save()
        
        logger = logging.getLogger(__name__)
        logger.info(f'Updated assignment stats for user {submission.user.id} '
                   f'assignment {assignment_id} problem {submission.problem_id}: '
                   f'status={stats.solve_status}, best_score={stats.best_score}, '
                   f'is_late={stats.is_late}')
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f'Failed to update user assignment stats: {str(e)}', exc_info=True)
'''

class BasePermissionMixin:
    """基礎權限檢查 Mixin - 提供通用權限檢查方法"""
    
    def check_teacher_permission(self, user, problem_id):
        """檢查用戶是否為該問題所屬課程的老師或 TA"""
        try:
            problem = Problems.objects.select_related('course_id').get(id=problem_id)
        except Problems.DoesNotExist:
            raise NotFound("問題不存在")
        
        if not problem.course_id:
            raise PermissionDenied("此問題未關聯到任何課程")
        
        course = problem.course_id
        
        # 檢查是否為課程主要老師
        if course.teacher_id == user:
            return True
        
        # 檢查是否為課程成員中的老師或 TA 角色
        is_course_staff = Course_members.objects.filter(
            course_id=course,
            user_id=user,
            role__in=[Course_members.Role.TEACHER, Course_members.Role.TA]
        ).exists()
        
        if not is_course_staff:
            raise PermissionDenied("您沒有權限管理此問題")
        
        return True
    
    def check_submission_view_permission(self, user, submission):
        """檢查是否有查看提交的權限"""
        # 0. 管理員和 staff 可以查看所有提交
        if user.is_staff or user.is_superuser:
            return True
        
        # 1. 如果是提交者本人，可以查看
        if submission.user == user:
            return True
        
        # 2. 檢查是否為該問題所屬課程的老師或 TA
        try:
            problem = Problems.objects.select_related('course_id').get(id=submission.problem_id)
            
            # 如果題目沒有關聯課程，暫時允許查看
            if not problem.course_id:
                return True
            
            course = problem.course_id
            
            # 檢查是否為課程主要老師
            if course.teacher_id == user:
                return True
            
            # 檢查是否為課程成員中的老師或 TA 角色
            is_course_staff = Course_members.objects.filter(
                course_id=course,
                user_id=user,
                role__in=[Course_members.Role.TEACHER, Course_members.Role.TA]
            ).exists()
            
            return is_course_staff
            
        except Exception:
            return False
    
    def get_viewable_submissions(self, user, queryset):
        """獲取該用戶可以查看的提交"""
        if user.is_staff or user.is_superuser:
            return queryset
        
        # 實作完整權限檢查
        from django.db.models import Q
        from problems.models import Problems
        from courses.models import Course_members
        
        # 構建複合查詢條件
        viewable_conditions = Q()
        
        # 1. 用戶自己的提交永遠可見
        viewable_conditions |= Q(user=user)
        
        # 2. 獲取用戶作為老師/TA的所有課程ID
        teaching_courses = Course_members.objects.filter(
            user_id=user,
            role__in=[Course_members.Role.TEACHER, Course_members.Role.TA]
        ).values_list('course_id', flat=True)
        
        # 3. 獲取用戶作為主要老師的課程ID
        from courses.models import Courses
        primary_teaching_courses = Courses.objects.filter(
            teacher_id=user
        ).values_list('id', flat=True)
        
        # 4. 合併所有有教學權限的課程
        all_teaching_courses = list(teaching_courses) + list(primary_teaching_courses)
        
        if all_teaching_courses:
            # 5. 獲取這些課程下所有題目的ID
            course_problems = Problems.objects.filter(
                course_id__in=all_teaching_courses
            ).values_list('id', flat=True)
            
            if course_problems:
                # 6. 可以查看這些題目的所有提交
                viewable_conditions |= Q(problem_id__in=course_problems)
        
        # 7. 對於沒有關聯課程的題目，根據系統策略決定
        # 這裡採用保守策略：只有管理員可以查看無課程題目的提交
        # 如果要允許所有人查看，可以加上：
        # orphan_problems = Problems.objects.filter(course_id__isnull=True).values_list('id', flat=True)
        # if orphan_problems:
        #     viewable_conditions |= Q(problem_id__in=orphan_problems)
        
        return queryset.filter(viewable_conditions).distinct()


class EditorialListCreateView(BasePermissionMixin, generics.ListCreateAPIView):
    """題解列表和創建 API"""
    
    def get_queryset(self):
        problem_id = self.kwargs['problem_id']
        
        # 檢查問題是否存在
        try:
            Problems.objects.get(id=problem_id)
        except Problems.DoesNotExist:
            raise NotFound("問題不存在")
            
        return Editorial.objects.filter(
            problem_id=problem_id,
            status='published'
        ).order_by('-likes_count', '-created_at')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EditorialCreateSerializer
        return EditorialSerializer
    
    def create(self, request, *args, **kwargs):
        """創建題解時先檢查權限"""
        problem_id = self.kwargs['problem_id']
        
        # 在序列化器驗證之前先檢查老師權限
        try:
            self.check_teacher_permission(request.user, problem_id)
        except (PermissionDenied, NotFound) as e:
            return api_response(
                data=None,
                message=str(e),
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # 調用父類的 create 方法
        response = super().create(request, *args, **kwargs)
        
        # 如果創建成功，使用 EditorialSerializer 返回完整資料
        if response.status_code == status.HTTP_201_CREATED:
            editorial = Editorial.objects.get(id=response.data['id'])
            serializer = EditorialSerializer(editorial, context={'request': request})
            return api_response(
                data=serializer.data,
                message='題解創建成功',
                status_code=status.HTTP_201_CREATED
            )
        
        return response
    
    def list(self, request, *args, **kwargs):
        """獲取題解列表"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            data=serializer.data,
            message='獲取題解列表成功',
            status_code=status.HTTP_200_OK
        )
    
    def perform_create(self, serializer):
        """創建題解時設定相關欄位"""
        problem_id = self.kwargs['problem_id']
        
        serializer.save(
            problem_id=problem_id,
            author=self.request.user,
            status='published',
            published_at=timezone.now()
        )


class EditorialDetailView(BasePermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    """題解詳情、更新和刪除 API"""
    
    def get_queryset(self):
        problem_id = self.kwargs['problem_id']
        return Editorial.objects.filter(problem_id=problem_id)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return EditorialCreateSerializer
        return EditorialSerializer
    
    def get_object(self):
        """根據 problem_id 和 solution_id 獲取題解"""
        problem_id = self.kwargs['problem_id']
        solution_id = self.kwargs['solution_id']
        
        # 驗證UUID格式
        try:
            uuid.UUID(str(solution_id))
        except (ValueError, TypeError):
            raise ValidationError("無效的題解ID格式")
        
        # 檢查問題是否存在
        try:
            Problems.objects.get(id=problem_id)
        except Problems.DoesNotExist:
            raise NotFound("問題不存在")
        
        obj = get_object_or_404(
            Editorial,
            id=solution_id,
            problem_id=problem_id
        )
        
        # 修改/刪除權限檢查：只有課程老師可以操作
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            self.check_teacher_permission(self.request.user, problem_id)
        
        # 增加瀏覽次數（只有 GET 請求）
        if self.request.method == 'GET':
            Editorial.objects.filter(id=solution_id).update(
                views_count=models.F('views_count') + 1
            )
        
        return obj
    
    def retrieve(self, request, *args, **kwargs):
        """獲取題解詳情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            data=serializer.data,
            message='獲取題解詳情成功',
            status_code=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        """更新題解"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # 使用 EditorialSerializer 返回完整資料
        editorial_serializer = EditorialSerializer(instance, context={'request': request})
        return api_response(
            data=editorial_serializer.data,
            message='題解更新成功',
            status_code=status.HTTP_200_OK
        )
    
    def destroy(self, request, *args, **kwargs):
        """刪除題解"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return api_response(
            data=None,
            message='題解刪除成功',
            status_code=status.HTTP_204_NO_CONTENT
        )
    
    def perform_update(self, serializer):
        """更新題解時保持 problem_id 不變"""
        problem_id = self.kwargs['problem_id']
        serializer.save(problem_id=problem_id)


@api_view(['POST', 'DELETE'])
def editorial_like_toggle(request, problem_id, solution_id):
    """題解按讚/取消按讚"""
    
    # 驗證UUID格式
    try:
        uuid.UUID(str(solution_id))
    except (ValueError, TypeError):
        return api_response(
            data=None,
            message='無效的題解ID格式',
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # 檢查問題是否存在
    try:
        Problems.objects.get(id=problem_id)
    except Problems.DoesNotExist:
        return api_response(
            data=None,
            message='問題不存在',
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # 驗證題解是否存在
    editorial = get_object_or_404(
        Editorial,
        id=solution_id,
        problem_id=problem_id,
        status='published'
    )
    
    user = request.user
    
    try:
        with transaction.atomic():
            existing_like = EditorialLike.objects.filter(
                editorial=editorial,
                user=user
            ).first()
            
            if request.method == 'POST':
                # 按讚
                if existing_like:
                    return api_response(
                        data=None,
                        message='您已經對這篇題解按過讚了',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # 創建按讚記錄
                like = EditorialLike.objects.create(
                    editorial=editorial,
                    user=user
                )
                
                # 更新按讚數
                Editorial.objects.filter(id=solution_id).update(
                    likes_count=models.F('likes_count') + 1
                )
                
                return api_response(
                    data={
                        'is_liked': True,
                        'likes_count': editorial.likes_count + 1
                    },
                    message='按讚成功',
                    status_code=status.HTTP_201_CREATED
                )
            
            elif request.method == 'DELETE':
                # 取消按讚
                if not existing_like:
                    return api_response(
                        data=None,
                        message='您尚未對這篇題解按讚',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # 刪除按讚記錄
                existing_like.delete()
                
                # 更新按讚數
                Editorial.objects.filter(id=solution_id).update(
                    likes_count=models.F('likes_count') - 1
                )
                
                return api_response(
                    data={
                        'is_liked': False,
                        'likes_count': max(0, editorial.likes_count - 1)
                    },
                    message='取消按讚成功',
                    status_code=status.HTTP_200_OK
                )
    
    except Exception as e:
        # 記錄完整錯誤但不回傳給客戶端
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Editorial update failed: {str(e)}", exc_info=True)
        
        return api_response(
            data=None,
            message='操作失敗，請稍後再試',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ===== 新增：Submission API Views =====

from .models import Submission, SubmissionResult
from .serializers import (
    SubmissionBaseCreateSerializer,
    SubmissionCodeUploadSerializer,
    SubmissionListSerializer,
    SubmissionDetailSerializer,
    SubmissionCodeSerializer,
    SubmissionStdoutSerializer
)


class SubmissionListCreateView(BasePermissionMixin, generics.ListCreateAPIView):
    """
    GET /submission/ - 獲取提交列表
    POST /submission/ - 創建新提交
    POST /submission/ - 還沒實作黑名單

    """
    
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SubmissionBaseCreateSerializer
        return SubmissionListSerializer
    
    def get_queryset(self):
        queryset = Submission.objects.select_related('user').order_by('-created_at')
        
        # 篩選參數
        problem_id = self.request.query_params.get('problem_id')
        username = self.request.query_params.get('username')
        status_filter = self.request.query_params.get('status')
        course_id = self.request.query_params.get('course_id')
        language_type = self.request.query_params.get('language_type')
        before = self.request.query_params.get('before')  # Unix 時間戳記 (秒)
        after = self.request.query_params.get('after')    # Unix 時間戳記 (秒)
        ip_prefix = self.request.query_params.get('ip_prefix')  # IP 網段前綴
        
        # 套用篩選條件
        if problem_id:
            queryset = queryset.filter(problem_id=problem_id)
        
        if username:
            queryset = queryset.filter(user__username=username)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if course_id:
            try:
                # 透過課程找到所有題目，再篩選提交
                problem_ids = Problems.objects.filter(course_id=course_id).values_list('id', flat=True)
                queryset = queryset.filter(problem_id__in=problem_ids)
            except (ValueError, TypeError) as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'Invalid course_id parameter: {course_id}, error: {e}')
                queryset = queryset.none()  # 查詢失敗返回空結果
        
        if language_type:
            try:
                queryset = queryset.filter(language_type=int(language_type))
            except ValueError:
                pass  # 忽略無效的語言類型
        
        if before:
            try:
                # 將 Unix 時間戳記轉換為 timezone-aware datetime 物件 (UTC)
                before_dt = datetime.fromtimestamp(int(before), tz=timezone.utc)
                queryset = queryset.filter(created_at__lt=before_dt)
            except (ValueError, TypeError, OSError):
                pass  # 忽略無效的時間格式
        
        if after:
            try:
                # 將 Unix 時間戳記轉換為 timezone-aware datetime 物件 (UTC)
                after_dt = datetime.fromtimestamp(int(after), tz=timezone.utc)
                queryset = queryset.filter(created_at__gt=after_dt)
            except (ValueError, TypeError, OSError):
                pass  # 忽略無效的時間格式
        
        # IP 網段前綴篩選
        if ip_prefix:
            try:
                # 支援 CIDR 格式 (例如 192.168.1.0/24) 或簡單前綴 (例如 192.168.)
                if '/' in ip_prefix:
                    # CIDR 格式：使用 ipaddress 模組進行正確的 IP 範圍過濾
                    import ipaddress
                    from django.db.models import Q
                    import struct
                    import socket
                    
                    network = ipaddress.ip_network(ip_prefix, strict=False)
                    
                    # 使用 Django ORM 的自定義過濾
                    # 由於 IP 地址存儲為字符串，我們需要逐一檢查
                    matching_ips = []
                    for submission in queryset:
                        try:
                            ip_obj = ipaddress.ip_address(submission.ip_address)
                            if ip_obj in network:
                                matching_ips.append(submission.id)
                        except (ValueError, AttributeError):
                            continue
                    
                    queryset = queryset.filter(id__in=matching_ips)
                else:
                    # 簡單前綴匹配：例如 "192.168." 會匹配所有 192.168.x.x
                    queryset = queryset.filter(ip_address__startswith=ip_prefix)
            except (ValueError, TypeError) as e:
                logger = logging.getLogger(__name__)
                logger.warning(f'Invalid ip_prefix parameter: {ip_prefix}, error: {e}')
                pass  # 忽略無效的 IP 前綴
        
        return self.get_viewable_submissions(self.request.user, queryset)
    
    def get_client_ip(self, request):
        """獲取客戶端 IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
    
    def is_ip_blacklisted(self, ip):
        """檢查 IP 是否在黑名單中"""
        # TODO: 實作 IP 黑名單邏輯
        # 可以從資料庫、Redis 或配置文件讀取黑名單
        # 範例：
        # from django.core.cache import cache
        # blacklist = cache.get('ip_blacklist', set())
        # return ip in blacklist
        
        # 目前暫時返回 False（不阻擋任何 IP）
        return False
    
    def post(self, request, *args, **kwargs):
        """創建新提交 (NOJ 兼容版本)"""
        
        try:
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'POST /submission/ data: {request.data}')
            
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                # 處理驗證錯誤，返回 NOJ 格式的錯誤信息
                errors = serializer.errors
                logger.error(f'Validation errors: {errors}')
                
                if 'problem_id' in errors:
                    if 'required' in str(errors['problem_id']):
                        return api_response(data=None, message="problemId is required!", status_code=status.HTTP_400_BAD_REQUEST)
                    elif 'min_value' in str(errors['problem_id']):
                        return api_response(data=None, message="problemId is required!", status_code=status.HTTP_400_BAD_REQUEST)
                    else:
                        return api_response(data=None, message="Unexisted problem id.", status_code=status.HTTP_404_NOT_FOUND)
                
                if 'language_type' in errors:
                    if 'required' in str(errors['language_type']):
                        return api_response(data=None, message="post data missing!", status_code=status.HTTP_400_BAD_REQUEST)
                    elif 'not allowed language' in str(errors['language_type']):
                        return api_response(data=None, message="not allowed language", status_code=status.HTTP_403_FORBIDDEN)
                    else:
                        return api_response(data=None, message=f"languageType 驗證失敗: {errors['language_type']}", status_code=status.HTTP_400_BAD_REQUEST)
                
                # 其他驗證錯誤
                error_details = '; '.join([f"{field}: {', '.join(msgs)}" for field, msgs in errors.items()])
                return api_response(data=None, message=f"資料驗證失敗: {error_details}", status_code=status.HTTP_400_BAD_REQUEST)
            
            # 額外的安全檢查
            problem_id = serializer.validated_data['problem_id']
            user = request.user
            # 確保用戶已通過身份驗證（防止 AnonymousUser 進入此邏輯）
            if not getattr(user, "is_authenticated", False):
                return api_response(
                    data=None,
                    message="Authentication credentials were not provided.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            
            # 1. Rate Limiting - 提交速率限制（每分鐘最多 10 次）
            from django.core.cache import cache
            rate_limit_key = f"submission_rate:{user.id}"
            current_count = cache.get(rate_limit_key, 0)
            
            if current_count >= 10:
                # 計算等待時間
                ttl = cache.ttl(rate_limit_key)
                wait_for = max(ttl, 1) if ttl else 60
                return api_response(
                    data={'waitFor': wait_for},
                    message="Submit too fast!",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 增加計數
            cache.set(rate_limit_key, current_count + 1, 60)  # 60 秒過期
            
            # 2. IP 黑名單檢查
            client_ip = self.get_client_ip(request)
            if self.is_ip_blacklisted(client_ip):
                logger.warning(f'Blocked submission from blacklisted IP: {client_ip}')
                return api_response(
                    data=None,
                    message="Invalid IP address",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # 3. 題目權限檢查（先檢查題目是否存在，並獲取 quota 設定）
            from problems.models import Problems
            from .models import UserProblemQuota
            try:
                problem = Problems.objects.get(id=problem_id)
                
                # 檢查題目可見性
                if problem.is_public == 'hidden':
                    # Hidden 題目只有創建者和管理員可以提交
                    if problem.creator_id != user and not user.is_staff:
                        return api_response(
                            data=None,
                            message="problem permission denied",
                            status_code=status.HTTP_403_FORBIDDEN
                        )
                elif problem.is_public == 'course':
                    # Course 題目需要檢查是否在課程中
                    from courses.models import Courses, Course_members
                    course = problem.course_id
                    # 若題目未關聯任何課程，則不應允許提交
                    if course is None:
                        return api_response(
                            data=None,
                            message="problem permission denied",
                            status_code=status.HTTP_403_FORBIDDEN
                        )
                    # 檢查用戶是否是課程成員（老師、助教或學生）
                    if not Course_members.objects.filter(
                        course_id=course,
                        user_id=user
                    ).exists():
                        return api_response(
                            data=None,
                            message="problem permission denied",
                            status_code=status.HTTP_403_FORBIDDEN
                        )
            except Problems.DoesNotExist:
                return api_response(
                    data=None,
                    message="Unexisted problem id.",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # 4. Quota 檢查 - 檢查用戶是否還有提交配額
            # 先檢查題目層級的 total_quota 設定
            problem_quota = problem.total_quota  # -1 = 無限制, >= 0 = 有限制
            
            # Wrap quota check and submission save in a single atomic transaction
            # to ensure consistency (prevent quota decrement without submission save)
            with transaction.atomic():
                if problem_quota >= 0:
                    # 題目有配額限制，需要檢查/建立 UserProblemQuota 記錄
                    # Use explicit try-except pattern to avoid race condition with get_or_create
                    try:
                        # Try to get existing quota record with row-level lock
                        quota = UserProblemQuota.objects.select_for_update().get(
                            user=user,
                            problem_id=problem_id,
                            assignment_id=None  # Global quota (no assignment)
                        )
                    except UserProblemQuota.DoesNotExist:
                        # Record doesn't exist, create it
                        # The unique constraint will handle concurrent creates
                        try:
                            quota = UserProblemQuota.objects.create(
                                user=user,
                                problem_id=problem_id,
                                assignment_id=None,
                                total_quota=problem_quota,
                                remaining_attempts=problem_quota
                            )
                        except IntegrityError:
                            # If another thread created it concurrently, get it with lock
                            quota = UserProblemQuota.objects.select_for_update().get(
                                user=user,
                                problem_id=problem_id,
                                assignment_id=None
                            )
                    
                    # 如果記錄已存在但 total_quota 與題目設定不同，可能是題目設定更新了
                    # 這裡我們不自動更新，保持原有配額（避免用戶突然獲得更多或更少配額）
                    
                    if quota.remaining_attempts == 0:
                        return api_response(
                            data=None,
                            message="you have used all your quotas",
                            status_code=status.HTTP_403_FORBIDDEN
                        )
                    
                    # 減少配額
                    # Note: remaining_attempts can be -1 (unlimited) if manually set by admin
                    # In this case, we preserve the unlimited quota by not decrementing
                    if quota.remaining_attempts > 0:
                        quota.remaining_attempts -= 1
                        quota.save()
                else:
                    # 題目無配額限制，但仍檢查是否有手動設定的 UserProblemQuota
                    try:
                        quota = UserProblemQuota.objects.select_for_update().get(
                            user=user,
                            problem_id=problem_id,
                            assignment_id=None  # Global quota (no assignment)
                        )
                        if quota.remaining_attempts == 0:
                            return api_response(
                                data=None,
                                message="you have used all your quotas",
                                status_code=status.HTTP_403_FORBIDDEN
                            )
                        # Note: remaining_attempts can be -1 (unlimited) if manually set
                        # In this case, we preserve the unlimited quota by not decrementing
                        if quota.remaining_attempts > 0:
                            quota.remaining_attempts -= 1
                            quota.save()
                    except UserProblemQuota.DoesNotExist:
                        # 沒有任何配額限制，允許提交
                        pass
                
                # Save submission within the same transaction to ensure atomicity
                submission = serializer.save()
            
            # NOJ 格式響應
            return api_response(
                data=None,
                message=f"submission received.{submission.id}",
                status_code=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            # 序列化器拋出的驗證錯誤
            error_message = str(e.detail[0]) if hasattr(e, 'detail') and e.detail else str(e)
            if 'problem' in error_message.lower():
                return api_response(data=None, message="Unexisted problem id.", status_code=status.HTTP_404_NOT_FOUND)
            return api_response(data=None, message=f"資料驗證錯誤: {error_message}", status_code=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            # 其他系統錯誤
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"提交創建失敗: {str(e)}", exc_info=True)
            return api_response(data=None, message=f"系統錯誤: {str(e)[:200]}", status_code=status.HTTP_400_BAD_REQUEST)
    
    def list(self, request, *args, **kwargs):
        """獲取提交列表 (NOJ 兼容版本)"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # 支援分頁參數
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # NOJ 格式響應（分頁版本）
            return api_response(
                data={
                    'results': serializer.data,
                    'count': queryset.count()
                },
                message='here you are, bro',
                status_code=status.HTTP_200_OK
            )
        
        serializer = self.get_serializer(queryset, many=True)
        # NOJ 格式響應
        return api_response(
            data={
                'results': serializer.data,
                'count': queryset.count()
            },
            message='here you are, bro',
            status_code=status.HTTP_200_OK
        )


class SubmissionRetrieveUpdateView(BasePermissionMixin, generics.RetrieveUpdateAPIView):
    """
    GET /submission/{id} - 獲取提交詳情
    PUT /submission/{id} - 上傳程式碼
    """
    
    lookup_field = 'id'
    
    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return SubmissionCodeUploadSerializer
        return SubmissionDetailSerializer
    
    def get_queryset(self):
        if self.request.method == 'PUT':
            # PUT 只能操作自己的提交
            return Submission.objects.filter(user=self.request.user)
        else:
            # GET 可以查看有權限的提交
            queryset = Submission.objects.select_related('user')
            return self.get_viewable_submissions(self.request.user, queryset)
    
    def retrieve(self, request, *args, **kwargs):
        """獲取提交詳情 (NOJ 兼容版本)"""
        try:
            # 先嘗試找到提交對象（不考慮權限過濾）
            submission_id = kwargs.get('id')
            try:
                submission = Submission.objects.select_related('user').get(id=submission_id)
            except Submission.DoesNotExist:
                return api_response(data=None, message="can not find submission", status_code=status.HTTP_404_NOT_FOUND)
            
            # 再檢查查看權限
            if not self.check_submission_view_permission(request.user, submission):
                return api_response(data=None, message="no permission", status_code=status.HTTP_403_FORBIDDEN)
            
            serializer = self.get_serializer(submission)
            
            # NOJ 格式響應：添加 message 字段
            return api_response(
                data=serializer.data,
                message='here you are, bro',
                status_code=status.HTTP_200_OK
            )
        
        except Exception as e:
            return api_response(data=None, message="can not find submission", status_code=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, *args, **kwargs):
        """上傳程式碼 (NOJ 兼容版本)"""
        try:
            # 先嘗試找到提交對象（不考慮用戶過濾）
            submission_id = kwargs.get('id')
            try:
                submission = Submission.objects.get(id=submission_id)
            except Submission.DoesNotExist:
                return api_response(data=None, message="can not find the source file", status_code=status.HTTP_400_BAD_REQUEST)
            
            # NOJ 權限檢查
            if submission.user != request.user:
                return api_response(data=None, message="user not equal!", status_code=status.HTTP_403_FORBIDDEN)
            
            # 檢查是否已經判題完成
            if submission.is_judged:
                return api_response(data=None, message=f"{submission.id} has finished judgement.", status_code=status.HTTP_403_FORBIDDEN)
            
            # 檢查是否已經上傳過程式碼
            if submission.source_code and submission.source_code.strip():
                return api_response(data=None, message=f"{submission.id} has been uploaded source file!", status_code=status.HTTP_403_FORBIDDEN)
            
            # 檢查是否有程式碼內容
            source_code = request.data.get('source_code', '') if hasattr(request.data, 'get') else ''
            if isinstance(request.data, dict):
                source_code = request.data.get('source_code', '')
            elif hasattr(request, 'FILES') and 'code' in request.FILES:
                # 支援檔案上傳 (NOJ 原格式)
                code_file = request.FILES['code']
                try:
                    source_code = code_file.read().decode('utf-8')
                except UnicodeDecodeError:
                    return api_response(data=None, message="can not find the source file", status_code=status.HTTP_400_BAD_REQUEST)
            
            if not source_code or not source_code.strip():
                return api_response(data=None, message="empty file", status_code=status.HTTP_400_BAD_REQUEST)
            
            # 使用序列化器處理數據
            serializer = self.get_serializer(submission, data={'source_code': source_code})
            if not serializer.is_valid():
                return api_response(data=None, message="can not find the source file", status_code=status.HTTP_400_BAD_REQUEST)
            
            updated_submission = serializer.save()
            
            # NOJ 格式響應 - 對程式題回應判題開始
            return api_response(
                data=None,
                message=f"{updated_submission.id} send to judgement.",
                status_code=status.HTTP_200_OK
            )
        
        except Submission.DoesNotExist:
            return api_response(data=None, message="can not find the source file", status_code=status.HTTP_400_BAD_REQUEST)
        
        except PermissionDenied:
            return api_response(data=None, message="user not equal!", status_code=status.HTTP_403_FORBIDDEN)
        
        except Exception as e:
            return api_response(data=None, message="can not find the source file", status_code=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
def submission_output_view(request, id, task_no, case_no):
    """
    GET /submission/{id}/output/{task_no}/{case_no}
    """

    # 1. 找 submission
    try:
        submission = Submission.objects.get(id=id)
    except Submission.DoesNotExist:
        return api_response(None, "submission not found", 404)

    # 2. 權限檢查
    mixin = BasePermissionMixin()
    if not mixin.check_submission_view_permission(request.user, submission):
        return api_response(None, "no permission", 403)

    # 3. 找 subtask
    try:
        subtask = Problem_subtasks.objects.get(
            problem_id=submission.problem_id,
            subtask_no=task_no
        )
    except Problem_subtasks.DoesNotExist:
        return api_response(None, "task_no not found", 404)

    # 4. 找 test_case（task_no + case_no）
    # 注意：我們嘗試找 test_case 來驗證，但實際查詢 SubmissionResult 時主要用 test_case_index
    test_case = None
    test_case_id = None
    try:
        test_case = Test_cases.objects.get(
            subtask_id=subtask.id,
            idx=case_no
        )
        test_case_id = test_case.id
    except Test_cases.DoesNotExist:
        logger.warning(f'Test case not found: subtask_id={subtask.id}, idx={case_no}')
        # 即使找不到 test_case，也繼續用 test_case_index 查詢

    # 5. 找結果
    # 重要：查詢需要 subtask_id + test_case_index（因為 test_case_index 只是相對於 subtask 的編號）
    try:
        result = SubmissionResult.objects.filter(
            submission_id=submission.id,
            subtask_id=subtask.id,
            test_case_index=case_no
        ).order_by('-created_at').first()
        
        if not result:
            # 提供詳細的診斷資訊
            all_results = SubmissionResult.objects.filter(submission_id=submission.id)
            total_results = all_results.count()
            
            # 列出該 submission 所有現有的測資結果
            existing_cases = []
            for r in all_results[:10]:  # 最多顯示 10 筆
                existing_cases.append(f"subtask_id={r.subtask_id}, case_index={r.test_case_index}")
            
            error_detail = (
                f"找不到測資結果。"
                f"查詢條件: submission_id={submission.id}, subtask_id={subtask.id}, case_no={case_no}. "
                f"該 submission 共有 {total_results} 筆測資結果"
                f"{': ' + ', '.join(existing_cases) if existing_cases else '（無任何測資結果）'}. "
                f"可能原因: 1) 判題尚未完成 2) subtask_id 不匹配 3) case_no 超出範圍"
            )
            
            return api_response(
                None, 
                error_detail,
                404
            )
    except Exception as e:
        logger.error(f'Error fetching submission result: {str(e)}')
        return api_response(
            None, 
            f"查詢測資結果時發生錯誤：{str(e)}",
            404
        )

    # 6. 回傳
    payload = {
        "submission_id": str(submission.id),
        "task_no": task_no,
        "case_no": case_no,
        "status": result.status,
        "score": result.score,
        "max_score": result.max_score,
        "execution_time": result.execution_time,
        "memory_usage": result.memory_usage,
        "output": result.output_preview or "",
        "error_message": result.error_message or "",
        "judge_message": result.judge_message or "",
    }

    return api_response(payload, "ok", 200)


# 保留原來的個別 view 類以便需要時使用
class SubmissionListView(BasePermissionMixin, generics.ListAPIView):
    """GET /submission/ - 獲取提交列表"""
    
    serializer_class = SubmissionListSerializer
    
    def get_queryset(self):
        queryset = Submission.objects.select_related('user').order_by('-created_at')
        return self.get_viewable_submissions(self.request.user, queryset)
    
    def list(self, request, *args, **kwargs):
        """獲取提交列表 (NOJ 兼容版本)"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # 支援分頁參數
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return api_response(
                data={
                    'results': serializer.data,
                    'count': queryset.count()
                },
                message="here you are, bro",
                status_code=status.HTTP_200_OK
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            data={
                'results': serializer.data,
                'count': queryset.count()
            },
            message='here you are, bro',
            status_code=status.HTTP_200_OK
        )


class SubmissionDetailView(BasePermissionMixin, generics.RetrieveAPIView):
    """GET /submission/{id} - 獲取提交詳情"""
    
    serializer_class = SubmissionDetailSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        queryset = Submission.objects.select_related('user')
        return self.get_viewable_submissions(self.request.user, queryset)
    
    def retrieve(self, request, *args, **kwargs):
        """獲取提交詳情 (NOJ 兼容版本)"""
        try:
            submission = self.get_object()
            
            # 檢查查看權限
            if not self.check_submission_view_permission(request.user, submission):
                return api_response(data=None, message="no permission", status_code=status.HTTP_403_FORBIDDEN)
            
            serializer = self.get_serializer(submission)
            return api_response(
                data=serializer.data,
                message='here you are, bro',
                status_code=status.HTTP_200_OK
            )
        
        except Submission.DoesNotExist:
            return api_response(data=None, message="can not find submission", status_code=status.HTTP_404_NOT_FOUND)


class SubmissionCodeView(BasePermissionMixin, generics.RetrieveAPIView):
    """GET /submission/{id}/code - 獲取提交程式碼"""
    
    serializer_class = SubmissionCodeSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        queryset = Submission.objects.select_related('user')
        return self.get_viewable_submissions(self.request.user, queryset)
    
    def retrieve(self, request, *args, **kwargs):
        """獲取提交程式碼 (NOJ 兼容版本)"""
        try:
            submission = self.get_object()
            
            # 檢查查看權限
            if not self.check_submission_view_permission(request.user, submission):
                return api_response(data=None, message="no permission", status_code=status.HTTP_403_FORBIDDEN)
            
            # 檢查是否有程式碼
            if not submission.source_code:
                return api_response(data=None, message="can not find the source file", status_code=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(submission)
            return api_response(
                data=serializer.data,
                message='here you are, bro',
                status_code=status.HTTP_200_OK
            )
        
        except Submission.DoesNotExist:
            return api_response(data=None, message="can not find submission", status_code=status.HTTP_404_NOT_FOUND)


class SubmissionStdoutView(BasePermissionMixin, generics.RetrieveAPIView):
    """GET /submission/{id}/stdout - 獲取提交標準輸出"""
    
    serializer_class = SubmissionStdoutSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        queryset = Submission.objects.select_related('user').prefetch_related('results')
        return self.get_viewable_submissions(self.request.user, queryset)
    
    def retrieve(self, request, *args, **kwargs):
        """獲取提交標準輸出 (NOJ 兼容版本)"""
        try:
            submission = self.get_object()
            
            # 檢查查看權限
            if not self.check_submission_view_permission(request.user, submission):
                return api_response(data=None, message="no permission", status_code=status.HTTP_403_FORBIDDEN)
            
            serializer = self.get_serializer(submission)
            return api_response(
                data=serializer.data,
                message='here you are, bro',
                status_code=status.HTTP_200_OK
            )
        
        except Submission.DoesNotExist:
            return api_response(data=None, message="can not find submission", status_code=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def submission_rejudge(request, id):
    """GET /submission/{id}/rejudge - 重新判題"""
    
    try:
        try:
            submission = Submission.objects.get(id=id)
        except Submission.DoesNotExist:
            return api_response(data=None, message="can not find submission", status_code=status.HTTP_404_NOT_FOUND)
        
        # NOJ 權限檢查：只有老師和 TA 可以重新判題
        mixin = BasePermissionMixin()
        
        try:
            # 檢查是否為該問題所屬課程的老師或 TA
            mixin.check_teacher_permission(request.user, submission.problem_id)
        except (PermissionDenied, NotFound):
            # 如果不是老師/TA，檢查是否為 staff
            if not request.user.is_staff:
                return api_response(data=None, message="no permission", status_code=status.HTTP_403_FORBIDDEN)
        
        # 檢查提交狀態 - NOJ 格式
        if submission.status == '-2':
            return api_response(data=None, message="can not find the source file", status_code=status.HTTP_400_BAD_REQUEST)
        
        # 重設判題狀態
        submission.status = '-1'  # Pending
        submission.score = 0
        submission.execution_time = -1
        submission.memory_usage = -1
        submission.judged_at = None
        submission.save()
        
        # 清除舊的判題結果
        SubmissionResult.objects.filter(submission=submission).delete()
        
        # 發送到 Sandbox 重新判題
        from .tasks import submit_to_sandbox_task
        try:
            submit_to_sandbox_task.delay(str(submission.id))
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'Rejudge queued for submission: {submission.id}')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Failed to queue rejudge for {submission.id}: {str(e)}')
            # 即使 celery 失敗，也回傳成功（submission 已經重設為 pending）
        
        # NOJ 格式響應
        return api_response(data=None, message=f"{submission.id} rejudge successfully.", status_code=status.HTTP_200_OK)
    
    except Exception as e:
        return api_response(data=None, message="Some error occurred, please contact the admin", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def ranking_view(request):
    """GET /ranking - 獲取排行榜"""
    
    try:
        # 實作排行榜邏輯 - 參照 NOJ 舊有格式
        # 遍歷系統中所有用戶並返回統計資料，不進行排序（由前端處理）
        
        from django.db.models import Count, Q
        
        # 獲取所有用戶的提交統計
        users = User.objects.all()
        ranking_data = []
        
        for user in users:
            # 計算該用戶的統計資料
            user_submissions = Submission.objects.filter(user=user)
            
            # AC 的提交數量 (status='0' 表示 Accepted)
            ac_submissions = user_submissions.filter(status='0')
            ac_submission_count = ac_submissions.count()
            
            # AC 的題目數量 (去重複的 problem_id)
            ac_problems = ac_submissions.values('problem_id').distinct()
            ac_problem_count = ac_problems.count()
            
            # 總提交數量
            total_submission_count = user_submissions.count()
            
            # 獲取用戶頭像
            try:
                profile = user.userprofile
                avatar_url = profile.avatar.url if profile.avatar else None
            except:
                avatar_url = None
            
            # 組裝用戶資料（參照 NOJ 格式）
            user_data = {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'real_name': getattr(user, 'real_name', user.username),
                    'email': user.email,
                    'avatar': avatar_url,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined.isoformat() if user.date_joined else None
                },
                'ACProblem': ac_problem_count,      # AC 的題目數量
                'ACSubmission': ac_submission_count, # AC 的提交數量  
                'Submission': total_submission_count # 總提交數量
            }
            
            ranking_data.append(user_data)
        
        # NOJ 格式：返回所有用戶資料，不進行排序（由前端處理）
        return api_response(
            data={'ranking': ranking_data},
            message='Ranking data retrieved successfully',
            status_code=status.HTTP_200_OK
        )
    
    except Exception as e:
        return api_response(data=None, message="Some error occurred, please contact the admin", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def user_stats_view(request, user_id):
    """
    GET /stats/user/{userId} - 使用者統計
    回傳使用者解題數、提交數、難度分布、接受率、Beats 百分比
    """

    # 1. 找 user
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return api_response(
            data=None,
            message="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # 2. 提交統計
    user_submissions = Submission.objects.filter(user=user)
    total_submissions = user_submissions.count()

    
    ac_submissions = user_submissions.filter(status='0').count()

    if total_submissions > 0:
        acceptance_percent = ac_submissions / total_submissions * 100.0
    else:
        acceptance_percent = 0.0

    # 3. 解題數 + 難度分布
    solved_qs = UserProblemSolveStatus.objects.filter(
        user_id=user.id,
        solve_status='fully_solved',  # 對應 schema 裡的 enum 值
    )
    total_solved = solved_qs.count()

    solved_problem_ids = solved_qs.values_list('problem_id', flat=True)

    difficulty_counts = (
        Problems.objects.filter(id__in=solved_problem_ids)
        .values('difficulty')
        .annotate(cnt=Count('id'))
    )

    def get_diff_count(name):
        for row in difficulty_counts:
            if row['difficulty'] == name:
                return row['cnt']
        return 0

    easy_cnt = get_diff_count('easy')
    medium_cnt = get_diff_count('medium')
    hard_cnt = get_diff_count('hard')

    # 4. Beats：以 fully_solved 題數當基準（優化版：直接在 DB 層過濾）
    # 先計算所有有解題的使用者總數
    total_users = (
        UserProblemSolveStatus.objects
        .filter(solve_status='fully_solved')
        .values('user_id')
        .distinct()
        .count()
    )
    
    if total_users > 0:
        # 只計算 solved_count < total_solved 的使用者數量（在 DB 層級過濾）
        lower_users = (
            UserProblemSolveStatus.objects
            .filter(solve_status='fully_solved')
            .values('user_id')
            .annotate(solved_count=Count('problem_id'))
            .filter(solved_count__lt=total_solved)
            .count()
        )
        beats_percent = lower_users / total_users * 100.0
    else:
        beats_percent = 0.0

    payload = {
        "user_id": user.id,
        "username": user.username,
        "total_solved": total_solved,
        "total_submissions": total_submissions,
        "accept_percent": round(acceptance_percent, 2),
        "difficulty": {
            "easy": easy_cnt,
            "medium": medium_cnt,
            "hard": hard_cnt,
        },
        "beats_percent": round(beats_percent, 2),
    }

    serializer = UserStatusSerializer(payload)
    return api_response(
        data={"user_stats": serializer.data},
        message="here you are, bro",
        status_code=status.HTTP_200_OK
    )


# ==================== Custom Test API ====================

import redis
import json
from django.core.cache import cache
from .sandbox_client import submit_selftest_to_sandbox

# 初始化 Redis client (使用 database 2，避免與 Celery 和 cache 衝突)
try:
    redis_client = redis.Redis(
        host='127.0.0.1',
        port=6379,
        db=2,
        decode_responses=True
    )
    redis_client.ping()  # 測試連接
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f'Redis connection failed: {str(e)}')
    redis_client = None


@api_view(['POST'])
def submit_custom_test(request, problem_id):
    """
    提交自定義測試（不存資料庫）
    
    POST /submissions/{problem_id}/custom-test/
    
    Request Body:
    {
        "language": 2,  // 0=C, 1=C++, 2=Python, 3=Java, 4=JavaScript
        "source_code": "print(input())",
        "stdin": "Hello World"
    }
    
    Response:
    {
        "test_id": "selftest-uuid",
        "submission_id": "selftest-uuid",
        "status": "queued",
        "message": "測試已提交"
    }
    """
    try:
        # 1. 驗證用戶狀態
        if not request.user.is_active:
            return api_response(
                data=None,
                message='使用者帳號已停用',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # 2. 速率限制：每分鐘最多 5 次
        if redis_client:
            rate_limit_key = f"custom_test_rate:{request.user.id}"
            current_count = redis_client.get(rate_limit_key)
            
            if current_count and int(current_count) >= 5:
                return api_response(
                    data=None,
                    message='提交過於頻繁，請稍後再試（每分鐘最多 5 次）',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 增加計數
            pipe = redis_client.pipeline()
            pipe.incr(rate_limit_key)
            pipe.expire(rate_limit_key, 60)  # 60 秒過期
            pipe.execute()
        
        # 3. 驗證輸入
        language_type = request.data.get('language')
        source_code = request.data.get('source_code')
        stdin_data = request.data.get('stdin', '')
        
        if language_type is None:
            return api_response(
                data=None,
                message='language 欄位必填',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if not source_code:
            return api_response(
                data=None,
                message='source_code 欄位必填',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 4. 驗證語言類型
        if language_type not in [0, 1, 2, 3, 4]:
            return api_response(
                data=None,
                message='語言類型無效（0=C, 1=C++, 2=Python, 3=Java, 4=JavaScript）',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 5. 驗證資料大小
        if len(source_code) > 65535:  # 64KB
            return api_response(
                data=None,
                message='程式碼長度不能超過 64KB',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if len(stdin_data) > 10240:  # 10KB
            return api_response(
                data=None,
                message='輸入資料長度不能超過 10KB',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 6. 驗證程式碼不是空白
        if not source_code.strip():
            return api_response(
                data=None,
                message='程式碼不能只包含空白字元',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 7. 驗證題目是否存在
        from problems.models import Problems
        if not Problems.objects.filter(id=problem_id).exists():
            return api_response(
                data=None,
                message='題目不存在',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 8. 異步提交到 Sandbox（使用 Celery 任務）
        from .tasks import submit_selftest_to_sandbox_task
        import uuid
        
        # 產生臨時測試 ID
        test_id = f"selftest-{uuid.uuid4()}"
        
        # 先儲存到 Redis（狀態為 pending）
        if redis_client:
            cache_key = f"custom_test:{request.user.id}:{test_id}"
            
            test_info = {
                'test_id': test_id,
                'problem_id': problem_id,
                'language': language_type,
                'submission_id': test_id,  # 暫時使用 test_id
                'status': 'pending',  # 等待提交
                'created_at': str(timezone.now()),
                'stdin': stdin_data[:100],  # 只儲存前 100 字元
            }
            
            redis_client.setex(
                cache_key,
                1800,  # 30 分鐘
                json.dumps(test_info)
            )
            
            # 記錄到最近測試列表
            recent_key = f"custom_tests:recent:{request.user.id}"
            redis_client.lpush(recent_key, test_id)
            redis_client.ltrim(recent_key, 0, 9)  # 只保留最近 10 個
            redis_client.expire(recent_key, 1800)
        
        # 9. 異步調用 Celery 任務
        try:
            submit_selftest_to_sandbox_task.delay(
                test_id=test_id,
                user_id=request.user.id,
                problem_id=problem_id,
                language_type=language_type,
                source_code=source_code,
                stdin_data=stdin_data
            )
        except Exception as celery_error:
            logger.error(f'Failed to queue custom test task: {str(celery_error)}')
            # 更新 Redis 狀態為失敗
            if redis_client:
                test_info['status'] = 'failed'
                test_info['error'] = 'Failed to queue task'
                redis_client.setex(cache_key, 1800, json.dumps(test_info))
            
            return api_response(
                data=None,
                message='無法將測試加入佇列，請稍後再試',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # 10. 返回結果（使用 api_response）
        return api_response(
            data={
                'test_id': test_id,
                'submission_id': test_id,
                'status': 'pending',
            },
            message='測試已提交，請稍後查詢結果',
            status_code=status.HTTP_202_ACCEPTED
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Custom test submission error: {str(e)}')
        return api_response(
            data=None,
            message=f'提交失敗: {str(e)}',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_custom_test_result(request, custom_test_id):
    """
    查詢自定義測試結果
    
    GET /submissions/custom-test/{custom_test_id}/result/
    
    Response:
    {
        "test_id": "selftest-uuid",
        "problem_id": 123,
        "status": "completed",
        "stdout": "3",
        "stderr": "",
        "time": 0.05,
        "memory": 1024,
        "message": "Score: 100"
    }
    """
    try:
        # 1. 驗證用戶狀態
        if not request.user.is_active:
            return api_response(
                data=None,
                message='使用者帳號已停用',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # 2. 從 Redis 取得測試資訊
        if not redis_client:
            return api_response(
                data=None,
                message='Redis 服務不可用',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        cache_key = f"custom_test:{request.user.id}:{custom_test_id}"
        cached = redis_client.get(cache_key)
        
        if not cached:
            return api_response(
                data=None,
                message='測試結果不存在或已過期（30 分鐘有效期）',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        test_info = json.loads(cached)
        
        # 如果狀態是 pending，表示還在處理中
        if test_info.get('status') == 'pending':
            return api_response(
                data={
                    'test_id': custom_test_id,
                    'problem_id': test_info['problem_id'],
                    'language': test_info['language'],
                    'status': 'pending',
                    'created_at': test_info.get('created_at'),
                },
                message='測試正在處理中',
                status_code=status.HTTP_200_OK
            )
        
        # 如果已經有錯誤，直接返回
        if test_info.get('status') == 'failed':
            return api_response(
                data={
                    'test_id': custom_test_id,
                    'problem_id': test_info['problem_id'],
                    'status': 'failed',
                    'error': test_info.get('error', 'Unknown error'),
                },
                message='測試失敗',
                status_code=status.HTTP_200_OK
            )
        
        submission_id = test_info['submission_id']
        
        # 3. 從 Sandbox 查詢實際結果
        import requests
        from .sandbox_client import SANDBOX_API_URL, SANDBOX_API_KEY
        
        url = f'{SANDBOX_API_URL}/api/v1/submissions/{submission_id}'
        headers = {'X-API-KEY': SANDBOX_API_KEY}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            sandbox_result = response.json()
        except requests.RequestException as e:
            return api_response(
                data=None,
                message=f'無法從 Sandbox 取得結果: {str(e)}',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # 4. 更新 Redis 中的狀態
        test_info['status'] = sandbox_result.get('status', 'unknown')
        test_info['last_updated'] = str(timezone.now())
        redis_client.setex(cache_key, 1800, json.dumps(test_info))
        
        # 5. 返回結果（使用 api_response）
        return api_response(
            data={
                'test_id': custom_test_id,
                'problem_id': test_info['problem_id'],
                'language': test_info['language'],
                'status': sandbox_result.get('status'),
                'stdout': sandbox_result.get('stdout', ''),
                'stderr': sandbox_result.get('stderr', ''),
                'time': sandbox_result.get('time'),
                'memory': sandbox_result.get('memory'),
                'message': sandbox_result.get('message', ''),
                'compile_info': sandbox_result.get('compile_info'),
                'created_at': test_info.get('created_at'),
            },
            message='here you are, bro',
            status_code=status.HTTP_200_OK
        )
        
    except json.JSONDecodeError:
        return api_response(
            data=None,
            message='測試資料格式錯誤',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Get custom test result error: {str(e)}')
        return api_response(
            data=None,
            message=f'查詢失敗: {str(e)}',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ====================
# Sandbox Callback API
# ====================

class SubmissionCallbackAPIView(APIView):
    """
    接收 Sandbox 判題結果的 callback endpoint
    
    Sandbox 判題完成後會 POST 到這個 endpoint
    URL: POST /{callback_url}/submissions/callback/
    """
    permission_classes = [permissions.AllowAny]  # Sandbox 不需要 JWT 認證
    
    def post(self, request):
        """
        處理 Sandbox 回傳的判題結果
        
        預期的 JSON payload:
        {
            "submission_id": "uuid",
            "status": "accepted" | "wrong_answer" | "time_limit_exceeded" | ...,
            "score": 100,
            "execution_time": 123,  // 毫秒
            "memory_usage": 1024,   // KB
            "test_results": [
                {
                    "test_case_id": 1,
                    "test_case_index": 1,
                    "status": "accepted",
                    "execution_time": 50,
                    "memory_usage": 512,
                    "score": 10,
                    "max_score": 10,
                    "error_message": null
                },
                // ... more test results
            ]
        }
        """
        import logging
        from .models import Submission, SubmissionResult
        from django.conf import settings
        
        logger = logging.getLogger(__name__)
        
        try:
            # 1. 驗證請求來源（API Key）
            api_key = request.headers.get('X-API-KEY')
            expected_key = getattr(settings, 'SANDBOX_API_KEY', '')
            
            if expected_key and api_key != expected_key:
                logger.warning(f'Invalid API key from callback: {api_key}')
                return api_response(
                    message='Unauthorized',
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            
            # 2. 解析 payload
            data = request.data
            submission_id = data.get('submission_id')
            judge_status = data.get('status')
            total_score = data.get('score', 0)
            execution_time = data.get('execution_time', 0)
            memory_usage = data.get('memory_usage', 0)
            test_results = data.get('test_results', [])
            
            logger.info(f'Received callback for submission {submission_id}: status={judge_status}, score={total_score}, test_results count={len(test_results)}')
            logger.debug(f'Full callback payload: {data}')
            
            if not submission_id:
                return api_response(
                    message='Missing submission_id',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # 3. 更新 Submission
            with transaction.atomic():
                try:
                    submission = Submission.objects.select_for_update().get(id=submission_id)
                except Submission.DoesNotExist:
                    logger.error(f'Submission not found: {submission_id}')
                    return api_response(
                        message='Submission not found',
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                # 轉換狀態碼（Submission 使用字串狀態碼）
                status_map = {
                    'accepted': '0',  # AC
                    'wrong_answer': '1',  # WA
                    'compile_error': '2',  # CE
                    'time_limit_exceeded': '3',  # TLE
                    'memory_limit_exceeded': '4',  # MLE
                    'runtime_error': '5',  # RE
                }
                submission.status = status_map.get(judge_status, '-1')  # 預設 -1 (pending)
                submission.score = total_score
                submission.execution_time = execution_time
                submission.memory_usage = memory_usage
                submission.judged_at = timezone.now()
                submission.save()
                
                logger.info(f'Updated submission {submission_id}: status={submission.status}, score={total_score}')
                
                # 4. 建立 SubmissionResult 記錄
                from problems.models import Problem_subtasks, Test_cases
                
                # 特殊處理：如果是 CE/SE 且 test_results 數量不足，為所有測資創建相同的錯誤記錄
                if judge_status in ['compile_error', 'system_error']:
                    # 取得該題目的所有測資
                    all_test_cases = []
                    subtasks = Problem_subtasks.objects.filter(problem_id=submission.problem_id).order_by('subtask_no')
                    for subtask in subtasks:
                        test_cases = Test_cases.objects.filter(subtask_id=subtask.id).order_by('idx')
                        all_test_cases.extend(test_cases)
                    
                    # 取得錯誤訊息（從第一筆 test_result 或使用預設值）
                    error_message = data.get('error_message', f'{judge_status.replace("_", " ").title()}')
                    if test_results and len(test_results) > 0:
                        error_message = test_results[0].get('error_message', error_message)
                    
                    # 為每個測資創建或更新錯誤記錄
                    for test_case in all_test_cases:
                        SubmissionResult.objects.update_or_create(
                            submission=submission,
                            subtask_id=test_case.subtask_id.id,
                            test_case_index=test_case.idx,
                            defaults={
                                'problem_id': submission.problem_id,
                                'test_case_id': None,  # CE/SE 時不關聯具體測資
                                'status': judge_status,
                                'execution_time': 0,
                                'memory_usage': 0,
                                'score': 0,
                                'max_score': 100,
                                'error_message': error_message,
                            }
                        )
                    
                    logger.info(f'Created {len(all_test_cases)} {judge_status} results for all test cases of submission {submission_id}')
                elif judge_status == 'accepted' and len(test_results) == 0:
                    # 特殊處理：AC 但沒有回傳 test_results，為所有測資創建 AC 記錄
                    logger.info(f'Processing test_result: specail AC with no test_results')
                    all_test_cases = []
                    subtasks = Problem_subtasks.objects.filter(problem_id=submission.problem_id).order_by('subtask_no')
                    for subtask in subtasks:
                        test_cases = Test_cases.objects.filter(subtask_id=subtask.id).order_by('idx')
                        all_test_cases.extend(test_cases)
                    
                    total_cases = len(all_test_cases)
                    score_per_case = submission.max_score // total_cases if total_cases > 0 else 0
                    
                    for test_case in all_test_cases:
                        SubmissionResult.objects.update_or_create(
                            submission=submission,
                            subtask_id=test_case.subtask_id.id,
                            test_case_index=test_case.idx,
                            defaults={
                                'problem_id': submission.problem_id,
                                'test_case_id': None,
                                'status': 'accepted',
                                'execution_time': execution_time // total_cases if total_cases > 0 else execution_time,
                                'memory_usage': memory_usage,
                                'score': score_per_case,
                                'max_score': score_per_case,
                                'error_message': None,
                            }
                        )
                    
                    logger.info(f'Created {len(all_test_cases)} accepted results for all test cases of submission {submission_id}')
                else:
                    # 正常情況：處理每個測資結果
                    logger.info(f'Processing {len(test_results)} test results normally')
                    
                    if len(test_results) == 0:
                        logger.warning(f'Submission {submission_id} has status={judge_status} but test_results is empty!')
                    
                    for test_result in test_results:
                        # 轉換 status 為字串格式（SubmissionResult 使用字串）
                        result_status = test_result.get('status', 'runtime_error')
                        
                        # 重要：Sandbox 文件中的欄位映射
                        # - Sandbox 的 test_case_id → 實際是 subtask_no（第幾個 subtask）
                        # - Sandbox 的 test_case_index → 測資編號（相對於 subtask）
                        subtask_no = test_result.get('test_case_id')  # Sandbox 用這個欄位傳 subtask 編號
                        test_case_index = test_result.get('test_case_index', 1)  # 測資編號
                        
                        logger.info(f'Processing test_result: subtask_no={subtask_no} (type={type(subtask_no)}), test_case_index={test_case_index}, status={result_status}')
                        
                        if subtask_no is None:
                            logger.warning(f'Missing subtask_no (test_case_id) in test_result')
                            continue
                        
                        # 容錯：嘗試轉換 subtask_no 為整數（防止型別不匹配）
                        try:
                            subtask_no = int(subtask_no)
                        except (ValueError, TypeError):
                            logger.error(f'Invalid subtask_no format: {subtask_no}')
                            continue
                        
                        # 根據 subtask_no 找到實際的 subtask_id
                        try:
                            subtask = Problem_subtasks.objects.get(
                                problem_id=submission.problem_id,
                                subtask_no=subtask_no
                            )
                            subtask_id = subtask.id
                            logger.info(f'Found subtask: subtask_no={subtask_no} -> subtask_id={subtask_id}')
                        except Problem_subtasks.DoesNotExist:
                            # 容錯：如果找不到，嘗試 subtask_no+1（因為 Sandbox 可能從 0 開始）
                            try:
                                logger.warning(f'Subtask not found with subtask_no={subtask_no}, trying subtask_no={subtask_no+1}')
                                subtask = Problem_subtasks.objects.get(
                                    problem_id=submission.problem_id,
                                    subtask_no=subtask_no + 1
                                )
                                subtask_id = subtask.id
                                logger.info(f'Found subtask with adjusted index: subtask_no={subtask_no+1} -> subtask_id={subtask_id}')
                            except Problem_subtasks.DoesNotExist:
                                logger.error(f'Subtask not found even with adjusted index: problem_id={submission.problem_id}, subtask_no={subtask_no} or {subtask_no+1}')
                                continue
                        
                        # 創建或更新記錄
                        result, created = SubmissionResult.objects.update_or_create(
                            submission=submission,
                            subtask_id=subtask_id,
                            test_case_index=test_case_index,
                            defaults={
                                'problem_id': submission.problem_id,
                                'test_case_id': None,  # 實際的 test_case_id 不使用
                                'status': result_status,
                                'execution_time': test_result.get('execution_time', 0),
                                'memory_usage': test_result.get('memory_usage', 0),
                                'score': test_result.get('score', 0),
                                'max_score': test_result.get('max_score', 100),
                                'error_message': test_result.get('error_message'),
                            }
                        )
                        logger.info(f'SubmissionResult {"created" if created else "updated"}: subtask_id={subtask_id}, test_case_index={test_case_index}')
                    
                    logger.info(f'Created {len(test_results)} test results for submission {submission_id}')
                
                # 5. 更新 UserProblemSolveStatus（全域層級）
                update_user_problem_stats(submission)
                '''這邊也不需要了，算成績的部分交給前端處理

                    # 6. 更新 UserProblemStats（作業層級）
                    # 嘗試從 submission 找到對應的 assignment_id
                    # submission model 需要加上 assignment_id 欄位，或者從 context 傳入
                    # 目前先跳過，等 submission model 更新後再啟用
                    # if hasattr(submission, 'assignment_id') and submission.assignment_id:
                    #     update_user_assignment_stats(submission, submission.assignment_id)

                '''
            return api_response(
                data={'submission_id': str(submission_id)},
                message='Callback processed successfully',
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f'Callback processing error: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return api_response(
                message=f'Internal server error: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomTestCallbackAPIView(APIView):
    """
    接收 Sandbox Custom Test 結果的 callback endpoint
    
    Sandbox 完成自定義測試後會 POST 到這個 endpoint
    URL: POST /api/submissions/custom-test-callback/
    """
    permission_classes = [permissions.AllowAny]  # Sandbox 不需要 JWT 認證
    
    def post(self, request):
        """
        處理 Sandbox 回傳的自定義測試結果
        
        預期的 JSON payload:
        {
            "submission_id": "selftest-uuid",
            "status": "completed" | "error",
            "stdout": "output text",
            "stderr": "error text",
            "execution_time": 123,  // 毫秒
            "memory_usage": 1024,   // KB
            "exit_code": 0
        }
        """
        import logging
        from .models import CustomTest
        from django.conf import settings
        
        logger = logging.getLogger(__name__)
        
        try:
            # 1. 驗證請求來源（API Key）
            api_key = request.headers.get('X-API-KEY')
            expected_key = getattr(settings, 'SANDBOX_API_KEY', '')
            
            if expected_key and api_key != expected_key:
                logger.warning(f'Invalid API key from custom test callback: {api_key}')
                return api_response(
                    message='Unauthorized',
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            
            # 2. 解析 payload
            data = request.data
            test_id = data.get('submission_id')  # 實際上是 custom test ID
            test_status = data.get('status')
            stdout = data.get('stdout', '')
            stderr = data.get('stderr', '')
            execution_time = data.get('execution_time', 0)
            memory_usage = data.get('memory_usage', 0)
            exit_code = data.get('exit_code', 0)
            
            logger.info(f'Received custom test callback for {test_id}: status={test_status}')
            
            if not test_id:
                return api_response(
                    message='Missing submission_id',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # 3. 更新 CustomTest
            with transaction.atomic():
                try:
                    custom_test = CustomTest.objects.select_for_update().get(id=test_id)
                except CustomTest.DoesNotExist:
                    logger.error(f'CustomTest not found: {test_id}')
                    return api_response(
                        message='CustomTest not found',
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                # 更新測試結果（CustomTest 使用字串狀態碼）
                custom_test.status = 'completed' if test_status == 'completed' else 'error'
                custom_test.actual_output = stdout
                custom_test.execution_time = execution_time
                custom_test.memory_usage = memory_usage
                custom_test.completed_at = timezone.now()
                
                if stderr or exit_code != 0:
                    custom_test.error_message = stderr or f'Exit code: {exit_code}'
                
                custom_test.save()
                
                logger.info(f'Updated custom test {test_id}: status={custom_test.status}')
            
            return api_response(
                data={'test_id': str(test_id)},
                message='Custom test callback processed successfully',
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f'Custom test callback processing error: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return api_response(
                message=f'Internal server error: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

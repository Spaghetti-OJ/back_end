from django.shortcuts import render, get_object_or_404
from django.db import models, transaction
from django.http import Http404
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.utils import timezone
import uuid

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

from .models import Editorial, EditorialLike
from .serializers import (
    EditorialSerializer, 
    EditorialCreateSerializer, 
    EditorialLikeSerializer
)
from problems.models import Problems
from courses.models import Courses, Course_members


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
    permission_classes = [permissions.IsAuthenticated]
    
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
        ).order_by('-is_official', '-likes_count', '-created_at')
    
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
            response.data = serializer.data
        
        return response
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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
    
    def perform_update(self, serializer):
        """更新題解時保持 problem_id 不變"""
        problem_id = self.kwargs['problem_id']
        serializer.save(problem_id=problem_id)


@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
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
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SubmissionBaseCreateSerializer
        return SubmissionListSerializer
    
    def get_queryset(self):
        queryset = Submission.objects.select_related('user').order_by('-created_at')
        return self.get_viewable_submissions(self.request.user, queryset)
    
    def post(self, request, *args, **kwargs):
        """創建新提交 (NOJ 兼容版本)"""
        
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                # 處理驗證錯誤，返回 NOJ 格式的錯誤信息
                errors = serializer.errors
                
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
                        return api_response(data=None, message="invalid data!", status_code=status.HTTP_400_BAD_REQUEST)
                
                # 其他驗證錯誤
                return api_response(data=None, message="invalid data!", status_code=status.HTTP_400_BAD_REQUEST)
            
            # TODO: 添加其他 NOJ 檢查
            # - problem permission denied
            # - homework hasn't start
            # - Invalid IP address
            # - quota check: "you have used all your quotas"
            # - rate limiting: "Submit too fast!" + waitFor
            
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
            return api_response(data=None, message="invalid data!", status_code=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            # 其他系統錯誤
            return api_response(data=None, message="invalid data!", status_code=status.HTTP_400_BAD_REQUEST)
    
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
    
    permission_classes = [permissions.IsAuthenticated]
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


# 保留原來的個別 view 類以便需要時使用
class SubmissionListView(BasePermissionMixin, generics.ListAPIView):
    """GET /submission/ - 獲取提交列表"""
    
    serializer_class = SubmissionListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
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
    permission_classes = [permissions.IsAuthenticated]
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
    permission_classes = [permissions.IsAuthenticated]
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
@permission_classes([permissions.IsAuthenticated])
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
        
        # TODO: 發送到 SandBox 重新判題
        # send_to_sandbox(submission)
        
        # NOJ 格式響應
        return api_response(data=None, message=f"{submission.id} rejudge successfully.", status_code=status.HTTP_200_OK)
    
    except Exception as e:
        return api_response(data=None, message="Some error occurred, please contact the admin", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def ranking_view(request):
    """GET /ranking - 獲取排行榜"""
    
    try:
        # 實作排行榜邏輯 - 參照 NOJ 舊有格式
        # 遍歷系統中所有用戶並返回統計資料，不進行排序（由前端處理）
        
        from django.db.models import Count, Q
        from user.models import User  # 使用自定義的 User 模型
        
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
            
            # 組裝用戶資料（參照 NOJ 格式）
            user_data = {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'real_name': getattr(user, 'real_name', user.username),
                    'email': user.email,
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
            message='here you are, bro',
            status_code=status.HTTP_200_OK
        )
    
    except Exception as e:
        return api_response(data=None, message="Some error occurred, please contact the admin", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

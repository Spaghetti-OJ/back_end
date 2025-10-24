from django.shortcuts import render, get_object_or_404
from django.db import models, transaction
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, NotFound
from django.utils import timezone

from .models import Editorial, EditorialLike
from .serializers import (
    EditorialSerializer, 
    EditorialCreateSerializer, 
    EditorialLikeSerializer
)
from problems.models import Problems
from courses.models import Courses, Course_members


class EditorialPermissionMixin:
    """題解權限檢查 Mixin"""
    
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
            raise PermissionDenied("您沒有權限管理此問題的題解")
        
        return True


class EditorialListCreateView(EditorialPermissionMixin, generics.ListCreateAPIView):
    """題解列表和創建 API"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        problem_id = self.kwargs['problem_id']
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
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
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


class EditorialDetailView(EditorialPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
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
                    return Response(
                        {'detail': '您已經對這篇題解按過讚了'},
                        status=status.HTTP_400_BAD_REQUEST
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
                
                return Response(
                    {
                        'detail': '按讚成功',
                        'is_liked': True,
                        'likes_count': editorial.likes_count + 1
                    },
                    status=status.HTTP_201_CREATED
                )
            
            elif request.method == 'DELETE':
                # 取消按讚
                if not existing_like:
                    return Response(
                        {'detail': '您尚未對這篇題解按讚'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # 刪除按讚記錄
                existing_like.delete()
                
                # 更新按讚數
                Editorial.objects.filter(id=solution_id).update(
                    likes_count=models.F('likes_count') - 1
                )
                
                return Response(
                    {
                        'detail': '取消按讚成功',
                        'is_liked': False,
                        'likes_count': max(0, editorial.likes_count - 1)
                    },
                    status=status.HTTP_200_OK
                )
    
    except Exception as e:
        return Response(
            {'detail': f'操作失敗: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

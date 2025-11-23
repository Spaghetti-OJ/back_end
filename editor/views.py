from django.shortcuts import render

# editor/views.py
"""
草稿視圖
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import CodeDraft
from .serializers import (
    DraftSerializer,
    DraftCreateUpdateSerializer
)


def api_response(data=None, message="", status_code=status.HTTP_200_OK):
    """
    統一的 API 響應格式
    
    Args:
        data: 響應數據
        message: 響應消息
        status_code: HTTP 狀態碼
    
    Returns:
        Response: {"data": ..., "message": ..., "status": "ok/error"}
    """
    response_status = "ok" if 200 <= status_code < 400 else "error"
    
    return Response(
        {
            "data": data,
            "message": message,
            "status": response_status
        },
        status=status_code
    )


class DraftView(APIView):
    """
    單個草稿的 CRUD 操作
    
    GET /editor/draft/{problem_id}/ - 載入草稿
    PUT /editor/draft/{problem_id}/ - 保存/更新草稿
    DELETE /editor/draft/{problem_id}/ - 刪除草稿
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_id):
        """載入草稿"""
        try:
            draft = CodeDraft.objects.get(
                user=request.user,
                problem_id=problem_id
            )
            serializer = DraftSerializer(draft)
            return api_response(
                data=serializer.data,
                message="草稿載入成功",
                status_code=status.HTTP_200_OK
            )
        except CodeDraft.DoesNotExist:
            return api_response(
                data=None,
                message="找不到草稿",
                status_code=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, problem_id):
        """保存/更新草稿"""
        # 嘗試獲取現有草稿
        draft = CodeDraft.objects.filter(
            user=request.user,
            problem_id=problem_id
        ).first()
        
        # 準備數據
        data = request.data.copy()
        data['problem_id'] = problem_id
        
        if draft:
            # 更新現有草稿
            serializer = DraftCreateUpdateSerializer(draft, data=data, partial=True)
        else:
            # 創建新草稿
            serializer = DraftCreateUpdateSerializer(data=data)
        
        if serializer.is_valid():
            draft = serializer.save(user=request.user)
            response_serializer = DraftSerializer(draft)
            return api_response(
                data=response_serializer.data,
                message="草稿保存成功",
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            data=serializer.errors,
            message="草稿保存失敗",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def delete(self, request, problem_id):
        """刪除草稿"""
        try:
            draft = CodeDraft.objects.get(
                user=request.user,
                problem_id=problem_id
            )
            draft.delete()
            return api_response(
                data=None,
                message="草稿刪除成功",
                status_code=status.HTTP_200_OK
            )
        except CodeDraft.DoesNotExist:
            return api_response(
                data=None,
                message="找不到草稿",
                status_code=status.HTTP_404_NOT_FOUND
            )

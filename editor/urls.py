# editor/urls.py
"""
草稿相關路由
"""
from django.urls import path
from .views import DraftView

urlpatterns = [
    # 單個草稿操作
    # GET    /editor/draft/<int:problem_id>/    - 載入特定題目的草稿
    # PUT    /editor/draft/<int:problem_id>/    - 保存/更新草稿（冪等）
    # DELETE /editor/draft/<int:problem_id>/    - 刪除草稿
    path('draft/<int:problem_id>/', DraftView.as_view(), name='draft-detail'),
]

# auths/urls.py

from django.urls import path
from .views import ApiTokenListView

urlpatterns = [
    # GET 和 POST /me/api-tokens/ 都會由 ApiTokenListView 處理
    path('me/api-tokens/', ApiTokenListView.as_view(), name='api-token-list-create'),
]
# auths/urls.py

from django.urls import path
from .views import ApiTokenListView, ApiTokenDetailView

urlpatterns = [
    # GET 和 POST /me/api-tokens/ 都會由 ApiTokenListView 處理
    path('me/api-tokens/', ApiTokenListView.as_view(), name='api-token-list-create'),
    # 處理單一物件的檢視 (GET) 和刪除 (DELETE)
    # <uuid:tokenId> 會捕獲 URL 中的 UUID 字串，並將其作為 `tokenId` 參數傳遞給我們的 View
    path('me/api-tokens/<uuid:tokenId>/', ApiTokenDetailView.as_view(), name='api-token-detail'),
]
# api_tokens/urls.py

from django.urls import path

# 導入你的 views 檔案
# 你的檔案在: api_tokens/views/api_tokens.py
# 所以我們 from .views 導入 api_tokens 模組
from .views import api_tokens

urlpatterns = [
    # 路由: POST / (建立) 和 GET / (列表)
    # 對應: ApiTokenListView
    path('', api_tokens.ApiTokenListView.as_view(), name='api-token-list'),
    
    # 路由: GET /{tokenId} (詳情) 和 DELETE /{tokenId} (刪除)
    # 對應: ApiTokenDetailView
    # 我們使用 <int:tokenId> 來匹配你 view 裡面的 'tokenId' 參數
    path('<uuid:tokenId>', api_tokens.ApiTokenDetailView.as_view(), name='api-token-detail'),
]
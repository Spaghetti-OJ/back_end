# auths/urls.py

from django.urls import path

# 導入你的 views 檔案
# 你的檔案在 auths/views/login_logs.py
from .views import login_logs 

urlpatterns = [
    # 把 'login-logs' 路徑連到 View
    path('login-logs', login_logs.LoginLogListView.as_view(), name='login-log-list'),

    # ... 這裡未來可以放 'register', 'password-reset' 等路由
]
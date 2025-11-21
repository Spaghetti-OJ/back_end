# auths/urls.py
from django.urls import path
from .views import login_logs 
from .views.signup import RegisterView, MeView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from .views.revoke import SessionRevokeView

urlpatterns = [
    path('login-logs/', login_logs.LoginLogListView.as_view(), name='login-log-list-self'),
    path('login-logs/<uuid:userId>/', login_logs.UserLoginLogListView.as_view(), name='user-login-log-list'),
    path('signup/', RegisterView.as_view(), name='register'),
    path('session/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('session/revoke/', SessionRevokeView.as_view(), name='auth-session-revoke'),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"), 
    path("verify/", TokenVerifyView.as_view(), name="token_verify"),
]
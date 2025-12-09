from django.urls import path
from .views import login_logs 
from .views.signup import RegisterView, MeView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from .views.revoke import SessionRevokeView
from .views import activity
from .views.check import CheckAvailabilityView
from .views.email import SendVerificationEmailView, VerifyEmailView

urlpatterns = [
    path('login-logs/', login_logs.LoginLogListView.as_view(), name='login-log-list-self'),
    path('login-logs/<uuid:user_id>/', login_logs.UserLoginLogListView.as_view(), name='user-login-log-list'),
    path('suspicious-activities/', login_logs.SuspiciousLoginListView.as_view(), name='suspicious-activity-list'),
    path('signup/', RegisterView.as_view(), name='register'),
    path('session/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('session/revoke/', SessionRevokeView.as_view(), name='auth-session-revoke'),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"), 
    path("verify/", TokenVerifyView.as_view(), name="token_verify"),
    path('me/', MeView.as_view(), name='me'),
    path('activity/', activity.UserActivityCreateView.as_view(), name='activity-create'),
    path('activity/<uuid:user_id>/', activity.UserActivityListView.as_view(), name='user-activity-list'),
    path('check/<str:item>/', CheckAvailabilityView.as_view(), name='auth-check'),
    path("send-email/", SendVerificationEmailView.as_view(), name="auth-send-email"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
]
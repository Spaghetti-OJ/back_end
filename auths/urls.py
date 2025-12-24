from django.urls import path
from .views import login_logs 
from .views.signup import RegisterView, MeView, LoginView, RefreshView, VerifyView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from .views.revoke import SessionRevokeView
from .views import activity
from .views.check import CheckAvailabilityView
from .views.email import SendVerificationEmailView, VerifyEmailView
from .views.password import ChangePasswordView, ForgotPasswordView, ResetPasswordView
from .views.stats import UserSubmissionActivityView

urlpatterns = [
    path('login-logs/', login_logs.LoginLogListView.as_view(), name='login-log-list-self'),
    path('login-logs/<uuid:user_id>/', login_logs.UserLoginLogListView.as_view(), name='user-login-log-list'),
    path('suspicious-activities/', login_logs.SuspiciousLoginListView.as_view(), name='suspicious-activity-list'),
    path('signup/', RegisterView.as_view(), name='register'),
    path('session/', LoginView.as_view(), name='token_obtain_pair'),
    path('session/revoke/', SessionRevokeView.as_view(), name='auth-session-revoke'),
    path("refresh/", RefreshView.as_view(), name="token_refresh"), 
    path("verify/", VerifyView.as_view(), name="token_verify"),
    path('me/', MeView.as_view(), name='me'),
    path('activity/', activity.UserActivityCreateView.as_view(), name='activity-create'),
    path('activity/<uuid:user_id>/', activity.UserActivityListView.as_view(), name='user-activity-list'),
    path('check/<str:item>/', CheckAvailabilityView.as_view(), name='auth-check'),
    path("send-email/", SendVerificationEmailView.as_view(), name="auth-send-email"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path('stats/submission-activity/<uuid:user_id>/', UserSubmissionActivityView.as_view(), name='user-submission-activity'),
]
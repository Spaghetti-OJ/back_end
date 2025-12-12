from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from ..serializers.password import ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from auths.models import PasswordResetToken
from django.contrib.auth import get_user_model
from django.utils import timezone
import secrets
from user.models import UserProfile

User = get_user_model()

RESET_TOKEN_LIFETIME_MINUTES = 60

def send_password_reset_email(to_email: str, reset_url: str):
    subject = "重設密碼連結"
    message = (
        "您好，\n\n"
        "我們收到您重設密碼的申請。請點擊以下連結重設密碼：\n"
        f"{reset_url}\n\n"
        "若這不是您本人操作，請忽略此信件。\n"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[to_email],
        fail_silently=False,
    )

def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response(
        {
            "data": data,
            "message": message,
            "status": status_str,
        },
        status=status_code,
    )

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return api_response(
                data=serializer.errors,
                message="Invalid password.",
                status_code=400,
            )

        serializer.save()
        return api_response(
            data=None,
            message="Password changed successfully.",
            status_code=200,
        )

class ForgotPasswordView(APIView):
    """
    POST /auth/forgot-password/
    使用者輸入 username，如果有「已驗證的 email」就寄出重設密碼信。
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]

        # 1) 找 user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return api_response(
                data=None,
                message="找不到此使用者。",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 2) 檢查是否有已驗證 email
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return api_response(
                data=None,
                message="此帳號尚未綁定或驗證信箱，無法使用密碼恢復。",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # ⚠️ 依你的實際欄位名稱調整：email / email_verified
        email = getattr(user, "email", None)

        if not email or not profile.email_verified:
            return api_response(
                data=None,
                message="此帳號尚未綁定或驗證信箱，無法使用密碼恢復。",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 3) 產生 token、寫入 DB
        token = secrets.token_urlsafe(32)
        now = timezone.now()
        expires_at = now + timezone.timedelta(minutes=RESET_TOKEN_LIFETIME_MINUTES)

        # 清掉此 user 過期且未使用的 token（可留可不留）
        PasswordResetToken.objects.filter(user=user, used=False, expires_at__lt=now).delete()

        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
        )

        # 4) 組出前端重設密碼連結
        frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000")
        reset_url = f"{frontend_base}/reset-password?token={token}"

        # 5) 寄信
        send_password_reset_email(to_email=email, reset_url=reset_url)

        return api_response(
            data=None,
            message="已寄出重設密碼信，請至驗證信箱查收。",
            status_code=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    POST /auth/reset-password/
    前端帶 token + new_password 來真正重設密碼。
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        now = timezone.now()

        # 1) 找 token
        try:
            prt = PasswordResetToken.objects.select_related("user").get(token=token)
        except PasswordResetToken.DoesNotExist:
            return api_response(
                data=None,
                message="無效的重設連結。",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 2) 檢查 used / expired
        if prt.used:
            return api_response(
                data=None,
                message="此重設連結已被使用。",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if prt.expires_at < now:
            return api_response(
                data=None,
                message="此重設連結已過期。",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 3) 更新密碼
        user = prt.user
        user.set_password(new_password)
        user.save()

        # 4) token 作廢
        prt.used = True
        prt.save()

        return api_response(
            data=None,
            message="密碼已成功重設。",
            status_code=status.HTTP_200_OK,
        )
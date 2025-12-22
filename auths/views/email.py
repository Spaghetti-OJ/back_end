import uuid
from django.conf import settings
from django.core.mail import send_mail

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from user.models import UserProfile
from auths.models import EmailVerificationToken

from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle


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


class SendVerificationEmailView(APIView):
    """
    POST /auth/send-email/ - 寄出驗證信到目前登入使用者的 Email
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "send_email"

    def post(self, request):
        user = request.user

        # 確保有 Profile
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # 1. 使用者沒有設定 email → 不能寄
        if not user.email:
            return api_response(
                data=None,
                message="Email Not Set",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 2. 已經驗證過 → 不寄
        if getattr(profile, "email_verified", False):
            return api_response(
                data=None,
                message="Email Already Verified",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 3. 產生 token，存 DB
        token_str = uuid.uuid4().hex
        EmailVerificationToken.objects.create(
            user=user,
            token=token_str,
        )

        # 4. 組驗證連結
        frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://127.0.0.1:3000")
        verify_url = f"{frontend_base}/verify-email?token={token_str}"

        # 5. 寄信
        subject = "請驗證你的 Email"
        message = f"""
嗨 {user.username}，

請點擊以下連結驗證你的電子郵件：

{verify_url}

如果你沒有在本網站註冊帳號，請忽略此信件。
""".strip()

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER)
        recipient_list = [user.email]

        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )

        # 6. 回應
        return api_response(
            data={"email": user.email},
            message="Verification Email Sent",
            status_code=status.HTTP_200_OK,
        )
    
class VerifyEmailView(APIView):
    """
    POST /auth/verify-email/ - 驗證 Email token，將帳號標記為已驗證
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        token_str = request.data.get("token")

        if not token_str:
            return api_response(
                data=None,
                message="Missing token",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = EmailVerificationToken.objects.select_related("user").get(
                token=token_str
            )
        except EmailVerificationToken.DoesNotExist:
            return api_response(
                data=None,
                message="Invalid Token",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if token.used:
            return api_response(
                data=None,
                message="Token Already Used",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if token.is_expired:
            return api_response(
                data=None,
                message="Token Expired",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = token.user
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # 標記為已驗證（如果已經是 True 就維持）
        if not profile.email_verified:
            profile.email_verified = True
            profile.save()

        # 標記 token 已使用
        token.used = True
        token.save()

        return api_response(
            data={"email": user.email,"username": user.username,
                "user_id": str(user.id),},
            message="Email Verified",
            status_code=status.HTTP_200_OK,
        )

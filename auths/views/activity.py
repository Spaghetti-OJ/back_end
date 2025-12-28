import ipaddress
import logging   
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from user.permissions import IsEmailVerified
from rest_framework.authentication import SessionAuthentication

# API Token 紀錄活動(預留)
# from api_tokens.authentication import ApiTokenAuthentication 

from ..models import UserActivity
from ..serializers.activity import UserActivitySerializer

logger = logging.getLogger(__name__)

# ===================================================================
# ⬇️ HELPER: 統一 API 回應格式 ⬇️
# ===================================================================
def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    if data is None: data = {}
    return Response({"data": data, "message": message, "status": status_str}, status=status_code)
# ===================================================================

class UserActivityCreateView(APIView):
    """
    POST /auth/activity
    記錄使用者活動。
    """
    # authentication_classes = [SessionAuthentication]  # Commented to use global default (includes JWTAuthentication)
    # permission_classes = [IsAuthenticated]  # Removed to use global default (IsAuthenticated + IsEmailVerified)

    def post(self, request):
        serializer = UserActivitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                user=request.user,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return api_response(serializer.data, "活動記錄成功", status_code=status.HTTP_201_CREATED)
        
        return api_response(serializer.errors, "資料格式錯誤", status_code=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        """
        從 request 取得真實 IP 的輔助函式 (強化版)。
        驗證 IP 格式並處理多重代理的情況。
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            for ip in [ip.strip() for ip in x_forwarded_for.split(',')]:
                try:
                    ipaddress.ip_address(ip)
                    return ip
                except ValueError:
                    continue
        
        ip = request.META.get('REMOTE_ADDR')
        try:
            ipaddress.ip_address(ip)
            return ip
        except Exception:
            logger.warning("Could not determine client IP address for request %s. Returning 'unknown'.", request)
            return 'unknown' # Fallback

class UserActivityListView(APIView):
    """
    GET /auth/activity/<uuid:user_id>/
    查看特定使用者的活動記錄 (僅限管理員)。
    """
    # authentication_classes = [SessionAuthentication]  # Commented to use global default (includes JWTAuthentication)
    permission_classes = [IsAdminUser, IsEmailVerified] 

    def get(self, request, user_id):
        activities = UserActivity.objects.filter(user__id=user_id).order_by('-created_at')
        serializer = UserActivitySerializer(activities, many=True)
        return api_response(serializer.data, f"成功取得使用者 {user_id} 的活動紀錄")
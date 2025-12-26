from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import IsAdminUser
from user.permissions import IsEmailVerified
from rest_framework.pagination import PageNumberPagination

from ..models import LoginLog
from ..serializers.login_log import LoginLogSerializer

# ===================================================================

from rest_framework.response import Response 

def api_response(data=None, message="OK", status_code=200):
    """
    統一的 API 回應格式 (這個函式現在是這個檔案專屬的)
    """
    status_str = "ok" if 200 <= status_code < 400 else "error"
    
    if data is None:
        data = {}
        
    return Response({
        "data": data,
        "message": message,
        "status": status_str,
    }, status=status_code)



# ===================================================================
# GET /auth/login-logs
# ===================================================================

class LoginLogListView(APIView):
    
    authentication_classes = [SessionAuthentication]
    # permission_classes = [IsAuthenticated]  # Removed to use global default

    def get(self, request):
        logs = LoginLog.objects.filter(user=request.user).order_by('-created_at')
        serializer = LoginLogSerializer(logs, many=True)
        
        return api_response(serializer.data, "成功取得使用者登入日誌")
    
# ===================================================================
# GET /auth/login-logs/{user_id}
# ===================================================================
class UserLoginLogListView(APIView):
    """
    列出「特定使用者」的所有登入日誌。
    (API: GET /auth/login-logs/<uuid:user_id>)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser, IsEmailVerified]

    def get(self, request, user_id):
        logs = LoginLog.objects.filter(user__id=user_id).order_by('-created_at')
        serializer = LoginLogSerializer(logs, many=True)
        
        
        return api_response(serializer.data, f"成功取得使用者 {user_id} 的登入日誌")
    
# ===================================================================
# --- SuspiciousLoginListView---
# ===================================================================
class SuspiciousLoginListView(APIView):
    """
    列出所有「異常」的登入日誌。
    (API: GET /auth/suspicious-activities/)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser, IsEmailVerified] 

    def get(self, request):
    
        logs = LoginLog.objects.exclude(login_status='success').order_by('-created_at')
        
        paginator = PageNumberPagination()
        paginator.page_size = 20 # 一頁 20 筆
        
        result_page = paginator.paginate_queryset(logs, request)
        
        serializer = LoginLogSerializer(result_page, many=True)
        
        response_data = {
            "results": serializer.data,
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link()
        }
        
        return api_response(response_data, "成功取得異常登入紀錄列表")
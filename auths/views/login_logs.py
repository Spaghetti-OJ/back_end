# auths/views/login_logs.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import IsAdminUser



from ..models import LoginLog
from ..serializers.login_log import LoginLogSerializer

# ===================================================================
# GET /auth/login-logs
# ===================================================================

class LoginLogListView(APIView):
    
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = LoginLog.objects.filter(user=request.user)
        serializer = LoginLogSerializer(logs, many=True)
        return Response(serializer.data)
    
# ===================================================================
# GET /auth/login-logs/{userId}
# ===================================================================
class UserLoginLogListView(APIView):
    """
    列出「特定使用者」的所有登入日誌。
    (API: GET /auth/login-logs/<uuid:userId>)
    """
    authentication_classes = [SessionAuthentication]
    # 權限：必須是管理員 (is_staff=True) 才能看別人的日誌
    permission_classes = [IsAdminUser] 

    def get(self, request, userId):
        """
        處理 GET 請求。
        'userId' 參數會從 urls.py 的 <uuid:userId> 自動傳入。
        """
        
        # 1. 根據 URL 傳入的 userId 過濾日誌
        #    我們使用 user__id 來查詢關聯的 User
        logs = LoginLog.objects.filter(user__id=userId).order_by('-created_at')
        
        # 2. 序列化 (如果找不到，logs 會是空列表，Serializer 會回傳 [])
        serializer = LoginLogSerializer(logs, many=True)
        
        return Response(serializer.data)
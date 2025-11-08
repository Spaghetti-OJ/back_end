# auths/views/login_logs.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from ..models import LoginLog
from ..serializers.login_log import LoginLogSerializer

class LoginLogListView(APIView):
    
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = LoginLog.objects.filter(user=request.user)
        serializer = LoginLogSerializer(logs, many=True)
        return Response(serializer.data)
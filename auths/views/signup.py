from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from auths.serializers.signup import RegisterSerializer, MeSerializer
from rest_framework.permissions import IsAuthenticated

User = get_user_model()

def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response({
        "data": data,
        "message": message,
        "status": status_str,
    }, status=status_code)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return api_response(data=response.data, status_code=response.status_code)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user          
        data = MeSerializer(user).data
        return api_response(data=data, message="Get current user")
from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from auths.serializers.signup import RegisterSerializer, MeSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

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
    skip_email_verification = True

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        user = User.objects.select_related("userprofile").get(pk=user.pk)
        data = RegisterSerializer(user).data
        return api_response(data=data, status_code=201)

class MeView(APIView):
    #permission_classes = [IsAuthenticated]
    skip_email_verification = True

    def get(self, request):
        user = request.user
        data = MeSerializer(user).data
        return api_response(data=data, message="Get current user")
    
class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    skip_email_verification = True

class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    skip_email_verification = True

class VerifyView(TokenVerifyView):
    permission_classes = [AllowAny]
    skip_email_verification = True